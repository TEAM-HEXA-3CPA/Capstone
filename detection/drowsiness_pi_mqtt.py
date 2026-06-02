import cv2
import mediapipe as mp
import time
import numpy as np
import json
import paho.mqtt.client as mqtt
from picamera2 import Picamera2

# =========================
# AWS IoT MQTT 설정
# =========================
ENDPOINT = "a1j2gwsbejyh4o-ats.iot.ap-northeast-2.amazonaws.com"
PORT = 8883
TOPIC = "sensor/ear/data"

CA_CERT = "AmazonRootCA1.pem"
DEVICE_CERT = "device.cert.pem"
PRIVATE_KEY = "device.private.key"

user_id = "abc123"   # 나중에 웹에서 받은 user_id로 바꾸면 됨

mqtt_client = mqtt.Client()
mqtt_client.tls_set(
    ca_certs=CA_CERT,
    certfile=DEVICE_CERT,
    keyfile=PRIVATE_KEY
)

print("AWS IoT 연결 중...")
mqtt_client.connect(ENDPOINT, PORT)
mqtt_client.loop_start()
print("AWS IoT 연결 성공")

# =========================
# MediaPipe 설정
# =========================
model_path = "face_landmarker.task"

BaseOptions = mp.tasks.BaseOptions
FaceLandmarker = mp.tasks.vision.FaceLandmarker
FaceLandmarkerOptions = mp.tasks.vision.FaceLandmarkerOptions
VisionRunningMode = mp.tasks.vision.RunningMode

def calculate_ear(eye_points):
    p2_p6 = np.linalg.norm(np.array(eye_points[1]) - np.array(eye_points[5]))
    p3_p5 = np.linalg.norm(np.array(eye_points[2]) - np.array(eye_points[4]))
    p1_p4 = np.linalg.norm(np.array(eye_points[0]) - np.array(eye_points[3]))

    if p1_p4 == 0:
        return 0.0

    return (p2_p6 + p3_p5) / (2.0 * p1_p4)

current_ear = 0.0
face_detected = False

def render_callback(result, output_image, timestamp_ms):
    global current_ear, face_detected

    if result.face_landmarks:
        face_detected = True
        landmarks = result.face_landmarks[0]

        left_eye_idx = [33, 160, 158, 133, 153, 144]
        right_eye_idx = [362, 385, 387, 263, 373, 380]

        left_eye = [(landmarks[i].x, landmarks[i].y) for i in left_eye_idx]
        right_eye = [(landmarks[i].x, landmarks[i].y) for i in right_eye_idx]

        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)

        current_ear = (left_ear + right_ear) / 2.0
    else:
        face_detected = False
        current_ear = 0.0

options = FaceLandmarkerOptions(
    base_options=BaseOptions(model_asset_path=model_path),
    running_mode=VisionRunningMode.LIVE_STREAM,
    num_faces=1,
    result_callback=render_callback
)

detector = FaceLandmarker.create_from_options(options)

# =========================
# Camera 설정
# =========================
picam2 = Picamera2()
picam2.configure(
    picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (640, 480)}
    )
)
picam2.start()
time.sleep(1)

print("졸음 감지 + MQTT 전송 시작. 종료하려면 q를 누르세요.")

closed_start_time = None
drowsy_alert = False
timestamp_ms = 0
last_publish_time = 0

while True:
    frame = picam2.capture_array()

    mp_image = mp.Image(
        image_format=mp.ImageFormat.SRGB,
        data=frame
    )

    timestamp_ms += 33
    detector.detect_async(mp_image, timestamp_ms)

    avg_ear = current_ear

    if face_detected and avg_ear < 0.22:
        if closed_start_time is None:
            closed_start_time = time.time()
        elif time.time() - closed_start_time >= 2.0:
            drowsy_alert = True
    else:
        closed_start_time = None
        drowsy_alert = False

    # =========================
    # AWS IoT로 EAR 전송
    # 너무 자주 보내지 않게 1초마다 전송
    # =========================
    now = time.time()

    if now - last_publish_time >= 1.0:
        payload = {
            "ear": round(avg_ear, 2),
            "user_id": user_id,
            "status": "DROWSY" if drowsy_alert else "AWAKE",
            "timestamp": int(now)
        }

        mqtt_client.publish(TOPIC, json.dumps(payload))
        print("Published:", payload)

        last_publish_time = now

    # =========================
    # 화면 표시
    # =========================
    if not face_detected:
        cv2.putText(frame, "No Face Detected", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 2)

    elif drowsy_alert:
        cv2.putText(frame, "DROWSINESS WARNING!", (30, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
        cv2.putText(frame, f"EAR: {avg_ear:.3f}", (30, 130),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    else:
        cv2.putText(frame, f"EAR: {avg_ear:.3f}", (30, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)
        cv2.putText(frame, "State: Awake", (30, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

    cv2.imshow("Drowsiness Detection MQTT", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
picam2.stop()
mqtt_client.loop_stop()
mqtt_client.disconnect()
