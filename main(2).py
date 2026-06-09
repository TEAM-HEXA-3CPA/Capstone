import sys
import time
import threading
import io

import cv2
import mediapipe as mp

from ultralytics import YOLO
from fastapi import FastAPI
from fastapi.responses import StreamingResponse

app = FastAPI()

# 전역 상태 저장
current_score = 100
current_status = "Starting"

# [수정] AI 엔진과 웹 스트리밍이 프레임을 안전하게 공유하기 위한 전역 변수와 락(Lock)
shared_frame = None
frame_lock = threading.Lock()


@app.get("/")
def root():
    return {
        "message": "server running"
    }


@app.get("/score")
def get_score():
    return {
        "score": current_score,
        "status": current_status
    }


# [추가] 웹 스트리밍 엔드포인트 전용 프레임 생성 함수
# 카메라를 새로 열지 않고, AI 엔진이 갱신해 주는 이미지를 가져와 인코딩만 합니다.
def generate_frames():
    global shared_frame
    while True:
        with frame_lock:
            if shared_frame is None:
                frame_to_send = None
            else:
                frame_to_send = shared_frame.copy()

        if frame_to_send is not None:
            _, buffer = cv2.imencode('.jpg', frame_to_send)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' +
                   buffer.tobytes() + b'\r\n')
        
        # CPU 과부하 방지 및 약 30 FPS 수준 유지
        time.sleep(0.03)


@app.get("/api/stream")
def video_stream():
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace;boundary=frame"
    )


# 눈 깜빡임 분석용 EAR(Eye Aspect Ratio)
def calculate_ear(eye_landmarks, points):
    p2_p6 = abs(
        eye_landmarks[points[1]].y -
        eye_landmarks[points[5]].y
    )

    p3_p5 = abs(
        eye_landmarks[points[2]].y -
        eye_landmarks[points[4]].y
    )

    p1_p4 = abs(
        eye_landmarks[points[0]].x -
        eye_landmarks[points[3]].x
    )

    if p1_p4 == 0:
        return 0

    return (p2_p6 + p3_p5) / (2.0 * p1_p4)


def ai_engine():
    global current_score
    global current_status
    global shared_frame

    print("[시스템] AI 몰입도 엔진 초기화 중...")

    try:
        model = YOLO("yolov8n.pt")
    except Exception as e:
        print(f"[오류] YOLO 모델 로드 실패: {e}")
        return

    mp_face_mesh = mp.solutions.face_mesh

    face_mesh = mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True
    )

    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[오류] 카메라를 열 수 없습니다.")
        return

    print("[시스템] 실시간 분석 시작")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        model(frame, verbose=False)

        mesh_results = face_mesh.process(rgb_frame)

        immersion_score = 100
        status_text = "Focusing"

        if mesh_results.multi_face_landmarks:
            for face_landmarks in mesh_results.multi_face_landmarks:
                left_eye_pts = [33, 160, 158, 133, 153, 144]
                right_eye_pts = [362, 385, 387, 263, 373, 380]

                left_ear = calculate_ear(
                    face_landmarks.landmark,
                    left_eye_pts
                )

                right_ear = calculate_ear(
                    face_landmarks.landmark,
                    right_eye_pts
                )

                avg_ear = (left_ear + right_ear) / 2.0

                if avg_ear < 0.22:
                    immersion_score -= 40
                    status_text = "Drowsiness Alert!"
        else:
            immersion_score = 0
            status_text = "Out of Sight"

        immersion_score = max(0, min(100, immersion_score))

        current_score = immersion_score
        current_status = status_text

        print(f"[AI 상태] score={current_score}, status={current_status}")

        # [수정] 프레임에 현재 상태 실시간 오버레이 텍스트 그리기
        color = (0, 255, 0) if current_status == "Focusing" else (0, 0, 255)
        cv2.putText(
            frame, 
            f"{current_status} | {current_score}pts",
            (10, 30), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.8, 
            color, 
            2
        )

        # [수정] 텍스트가 입혀진 최종 결과 프레임을 안전하게 전역 변수에 백업
        with frame_lock:
            shared_frame = frame.copy()

        # 기존 소스코드에 있던 주기적 대기 유지 (필요에 따라 0.03 등으로 줄이면 화면이 더 부드러워집니다)
        time.sleep(1)

    cap.release()


@app.on_event("startup")
def startup_event():
    thread = threading.Thread(
        target=ai_engine,
        daemon=True
    )
    thread.start()