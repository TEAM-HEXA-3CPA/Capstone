import sys
import time
import threading
import random # 👈 가상 데이터 생성을 위해 추가

import cv2
import mediapipe as mp

from ultralytics import YOLO
from fastapi import FastAPI

app = FastAPI()

# 전역 상태 저장
current_score = 100
current_status = "Starting"


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

    print("[시스템] AI 몰입도 엔진 초기화 중...")

    try:
        model = YOLO("yolov8n.pt")
    except Exception as e:
        print(f"[오류] YOLO 모델 로드 실패: {e}")
        return

    try:
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True
        )
    except Exception as e:
        print(f"[오류] MediaPipe 초기화 실패: {e}")
        return

    print("[시스템] 카메라 장치 연결 시도 중...")
    cap = cv2.VideoCapture(0)

    # 🎯 [교정] 도커 내부에서 카메라를 낼름 열지 못해 서버가 프리징되는 현상 완벽 방지
    if not cap.isOpened():
        print("[경고] 물리 카메라를 찾을 수 없습니다. '시뮬레이션 모드'로 안전하게 전환합니다.")
        print("[시스템] 로그인 및 랭킹 시스템 연동을 위해 백엔드를 활성화 상태로 유지합니다.")
        
        while True:
            # 카메라가 없어도 GIL을 독점하지 않고 다른 쓰레드(Flask 로그인)가 숨 쉴 수 있게 대기시간을 주며 가상 데이터를 쏩니다.
            current_score = random.randint(85, 98)
            current_status = "Focusing (Simulated)"
            time.sleep(2)
            continue

    print("[시스템] 실시간 분석 시작")

    while True:
        try:
            ret, frame = cap.read()

            if not ret:
                print("[경고] 프레임을 읽을 수 없습니다. 루프를 안전하게 유지합니다.")
                time.sleep(1)
                continue

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

            immersion_score = max(
                0,
                min(100, immersion_score)
            )

            current_score = immersion_score
            current_status = status_text

            print(
                f"[AI 상태] score={current_score}, status={current_status}"
            )
            time.sleep(1)
            
        except Exception as loop_e:
            print(f"[엔진 루프 내부 오류 발생]: {loop_e}")
            time.sleep(1)

    cap.release()


@app.on_event("startup")
def startup_event():
    thread = threading.Thread(
        target=ai_engine,
        daemon=True
    )
    thread.start()