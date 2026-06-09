"""
FocusMate — 라즈베리파이 통합 AI 엔진
기능: EAR 졸음 감지 → YOLO → MQTT → 웹 스트리밍

현재 버전:
- USER_ID 고정
- MQTT 1분마다 전송
- /api/stream, /stream 둘 다 지원
- 웹 스트리밍 지연 감소용 설정 적용
"""

import time
import threading
import json
import numpy as np
import cv2
import mediapipe as mp

from ultralytics import YOLO
from picamera2 import Picamera2
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

import paho.mqtt.client as mqtt

# =================================================================
# 설정값
# =================================================================

MQTT_ENDPOINT = "a1j2gwsbejyh4o-ats.iot.ap-northeast-2.amazonaws.com"
MQTT_PORT = 8883
MQTT_TOPIC = "sensor/ear/data"

CA_CERT = "AmazonRootCA1.pem"
DEVICE_CERT = "device.cert.pem"
PRIVATE_KEY = "device.private.key"

USER_ID = "focusmate1"

MQTT_INTERVAL = 60
YOLO_INTERVAL = 5
EAR_THRESHOLD = 0.22
DROWSY_TIME = 2.0

CAMERA_WIDTH = 320
CAMERA_HEIGHT = 240
STREAM_SLEEP = 0.1
JPEG_QUALITY = 60

# =================================================================
# 전역 상태
# =================================================================

current_score = 100
current_status = "Starting"
current_ear = 0.0
face_detected = False
drowsy_alert = False
last_yolo_labels = []

shared_frame = None
frame_lock = threading.Lock()

mqtt_client = None

# =================================================================
# FastAPI
# =================================================================

app = FastAPI()

@app.get("/")
def root():
    return {
        "message": "FocusMate AI running",
        "user": USER_ID
    }

@app.get("/score")
def get_score():
    return {
        "score": current_score,
        "status": current_status,
        "ear": round(current_ear, 4),
        "face": face_detected,
        "drowsy": drowsy_alert,
        "objects": last_yolo_labels,
        "user_id": USER_ID
    }

def generate_frames():
    while True:
        with frame_lock:
            frame = shared_frame.copy() if shared_frame is not None else None

        if frame is not None:
            ret, buffer = cv2.imencode(
                ".jpg",
                frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
            )

            if ret:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + buffer.tobytes()
                    + b"\r\n"
                )

        time.sleep(STREAM_SLEEP)

@app.get("/api/stream")
def video_stream_api():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )

@app.get("/stream")
def video_stream():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )

# =================================================================
# MQTT 연결
# =================================================================

def connect_mqtt():
    global mqtt_client

    try:
        mqtt_client = mqtt.Client()

        mqtt_client.tls_set(
            ca_certs=CA_CERT,
            certfile=DEVICE_CERT,
            keyfile=PRIVATE_KEY
        )

        print("[MQTT] AWS IoT Core 연결 중...")

        mqtt_client.connect(
            MQTT_ENDPOINT,
            MQTT_PORT
        )

        mqtt_client.loop_start()

        print("[MQTT] 연결 성공")

    except Exception as e:
        print(f"[MQTT] 연결 실패: {e}")
        mqtt_client = None

# =================================================================
# MQTT 전송
# =================================================================

def publish_mqtt(ear, score, status):
    if mqtt_client is None:
        return

    try:
        payload = json.dumps({
            "user_id": USER_ID,
            "ear": round(ear, 4),
            "score": score,
            "status": status,
            "objects": last_yolo_labels,
            "timestamp": int(time.time())
        })

        mqtt_client.publish(
            MQTT_TOPIC,
            payload
        )

        print(
            f"[MQTT] 전송 → user={USER_ID} | "
            f"EAR={ear:.3f} | score={score} | {status}"
        )

    except Exception as e:
        print(f"[MQTT] 전송 실패: {e}")

# =================================================================
# EAR 계산
# =================================================================

def calculate_ear(eye_points):
    p2_p6 = np.linalg.norm(
        np.array(eye_points[1]) -
        np.array(eye_points[5])
    )

    p3_p5 = np.linalg.norm(
        np.array(eye_points[2]) -
        np.array(eye_points[4])
    )

    p1_p4 = np.linalg.norm(
        np.array(eye_points[0]) -
        np.array(eye_points[3])
    )

    if p1_p4 == 0:
        return 0.0

    return (p2_p6 + p3_p5) / (2.0 * p1_p4)

# =================================================================
# MediaPipe 콜백
# =================================================================

def render_callback(result, output_image, timestamp_ms):
    global current_ear
    global face_detected

    if result.face_landmarks:
        face_detected = True

        landmarks = result.face_landmarks[0]

        left_eye = [
            (landmarks[i].x, landmarks[i].y)
            for i in [33, 160, 158, 133, 153, 144]
        ]

        right_eye = [
            (landmarks[i].x, landmarks[i].y)
            for i in [362, 385, 387, 263, 373, 380]
        ]

        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)

        current_ear = (left_ear + right_ear) / 2.0

    else:
        face_detected = False
        current_ear = 0.0

# =================================================================
# AI 엔진 메인 루프
# =================================================================

def ai_engine():
    global current_score
    global current_status
    global drowsy_alert
    global last_yolo_labels
    global shared_frame

    BaseOptions = mp.tasks.BaseOptions
    FaceLandmarker = mp.tasks.vision.FaceLandmarker
    FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = FaceLandmarkerOptions(
        base_options=BaseOptions(
            model_asset_path="face_landmarker.task"
        ),
        running_mode=VisionRunningMode.LIVE_STREAM,
        num_faces=1,
        result_callback=render_callback
    )

    detector = FaceLandmarker.create_from_options(options)

    print("[YOLO] 모델 로드 중...")

    try:
        yolo_model = YOLO("yolov8n.pt")
        print("[YOLO] 로드 성공")

    except Exception as e:
        print(f"[YOLO] 로드 실패: {e}")
        yolo_model = None

    picam2 = Picamera2()

    picam2.configure(
        picam2.create_preview_configuration(
            main={
                "format": "RGB888",
                "size": (CAMERA_WIDTH, CAMERA_HEIGHT)
            }
        )
    )

    picam2.start()
    time.sleep(1)

    print("[카메라] Picamera2 시작")
    print(f"[시스템] 실시간 분석 시작 | 사용자: {USER_ID}")

    timestamp_ms = 0
    closed_start_time = None
    last_mqtt_time = 0
    last_yolo_time = 0

    try:
        while True:
            frame = picam2.capture_array()

            mp_image = mp.Image(
                image_format=mp.ImageFormat.SRGB,
                data=frame
            )

            timestamp_ms += 33

            detector.detect_async(
                mp_image,
                timestamp_ms
            )

            avg_ear = current_ear

            if face_detected and avg_ear < EAR_THRESHOLD:
                if closed_start_time is None:
                    closed_start_time = time.time()

                elif time.time() - closed_start_time >= DROWSY_TIME:
                    drowsy_alert = True

            else:
                closed_start_time = None
                drowsy_alert = False

            if not face_detected:
                current_score = 0
                current_status = "Out of Sight"

            elif drowsy_alert:
                current_score = 60
                current_status = "Drowsiness Alert!"

            else:
                current_score = 100
                current_status = "Focusing"

            now = time.time()

            if yolo_model and now - last_yolo_time >= YOLO_INTERVAL:
                results = yolo_model(
                    frame,
                    verbose=False,
                    imgsz=320
                )

                labels = []

                for result in results:
                    for box in result.boxes:
                        cls_id = int(box.cls[0])
                        conf = float(box.conf[0])
                        name = yolo_model.names[cls_id]

                        if conf >= 0.4:
                            labels.append(name)

                last_yolo_labels = list(set(labels))
                last_yolo_time = now

            if now - last_mqtt_time >= MQTT_INTERVAL:
                publish_mqtt(
                    avg_ear,
                    current_score,
                    current_status
                )

                last_mqtt_time = now

            if current_status == "Focusing":
                color = (0, 255, 0)
            else:
                color = (0, 0, 255)

            cv2.putText(
                frame,
                f"{current_status} | {current_score}pts | EAR:{avg_ear:.3f}",
                (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                color,
                1
            )

            cv2.putText(
                frame,
                f"User: {USER_ID}",
                (10, 45),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.4,
                (255, 255, 255),
                1
            )

            if last_yolo_labels:
                cv2.putText(
                    frame,
                    f"Objects: {', '.join(last_yolo_labels[:3])}",
                    (10, CAMERA_HEIGHT - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.4,
                    (255, 255, 0),
                    1
                )

            with frame_lock:
                shared_frame = frame.copy()

            print(
                f"[AI] EAR={avg_ear:.3f} | "
                f"{current_status} | {current_score}pts"
            )

            time.sleep(0.03)

    except KeyboardInterrupt:
        print("[시스템] 종료 중...")

    finally:
        picam2.stop()

        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()

        print("[시스템] 종료 완료")

# =================================================================
# FastAPI 시작 시 AI 엔진 실행
# =================================================================

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(
        target=ai_engine,
        daemon=True
    )

    thread.start()

# =================================================================
# 직접 실행
# =================================================================

if __name__ == "__main__":
    import uvicorn

    connect_mqtt()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )