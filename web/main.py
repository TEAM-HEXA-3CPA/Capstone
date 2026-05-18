# main.py
import sys
import time
import cv2
from ultralytics import YOLO

# MediaPipe 버전 패치 (solutions AttributeError 방지 에러 방어)
import mediapipe as mp
if not hasattr(mp, 'solutions'):
    import mediapipe.python.solutions as solutions
    mp.solutions = solutions

# 눈 깜빡임 분석용 EAR(Eye Aspect Ratio) 산출 알고리즘 함수
def calculate_ear(eye_landmarks, points):
    # 눈의 상하 거리 계산
    p2_p6 = abs(eye_landmarks[points[1]].y - eye_landmarks[points[5]].y)
    p3_p5 = abs(eye_landmarks[points[2]].y - eye_landmarks[points[4]].y)
    # 눈의 좌우 거리 계산
    p1_p4 = abs(eye_landmarks[points[0]].y - eye_landmarks[points[3]].y)
    
    if p1_p4 == 0: return 0
    return (p2_p6 + p3_p5) / (2.0 * p1_p4)

def main():
    print("[시스템] AI 몰입도 엔진을 초기화합니다...")
    
    # 의존성 이슈 방지를 위해 공식 검증된 가중치 모델 로드
    try:
        model = YOLO('yolov8n.pt')
    except Exception as e:
        print(f"[오류] YOLO 모델 로드에 실패했습니다: {e}")
        sys.exit(1)

    # 미디아파이프 안면 메쉬 초기화
    mp_face_mesh = mp.solutions.face_mesh
    face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True)

    # 라즈베리파이 카메라 / 웹캠 개방
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[오류] 카메라를 찾을 수 없거나 열 수 없습니다.")
        sys.exit(1)

    print("[시스템] 실시간 카메라 스트리밍 분석을 시작합니다. (종료: 'q'키 입력)")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        # 프레임 좌우 반전 및 컬러 공간 변환
        frame = cv2.flip(frame, 1)
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 1. YOLOv8 객체 및 사람 감지
        yolo_results = model(frame, verbose=False)
        
        # 2. MediaPipe 정밀 페이스 메쉬 추출 및 EAR 계산
        mesh_results = face_mesh.process(rgb_frame)
        
        immersion_score = 100 # 기본 만점 시작 지점
        status_text = "Focusing"

        if mesh_results.multi_face_landmarks:
            for face_landmarks in mesh_results.multi_face_landmarks:
                # 왼쪽 눈 및 오른쪽 눈 인덱스 랜드마크 데이터 매핑 (기본 수식)
                left_eye_pts = [33, 160, 158, 133, 153, 144]
                right_eye_pts = [362, 385, 387, 263, 373, 380]
                
                left_ear = calculate_ear(face_landmarks.landmark, left_eye_pts)
                right_ear = calculate_ear(face_landmarks.landmark, right_eye_pts)
                avg_ear = (left_ear + right_ear) / 2.0

                # 눈꺼풀 처짐 임계값 필터 (졸음 수치 정밀 패널티 가중치 산출)
                if avg_ear < 0.22:
                    immersion_score -= 40
                    status_text = "Drowsiness Alert!"
        else:
            # 화면 내 안면 미검출 시 (시선 이탈 상태 패널티 최고점 부여)
            immersion_score = 0
            status_text = "Out of Sight"

        # 데이터 안전 캡슐화 제한 범위 세팅 (0~100)
        immersion_score = max(0, min(100, immersion_score))

        # 오버레이 정보 화면 출력
        cv2.putText(frame, f"Score: {immersion_score} pts", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 148, 96), 2)
        cv2.putText(frame, f"State: {status_text}", (20, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255) if immersion_score < 50 else (255, 255, 255), 2)
        
        cv2.imshow("Deep Study AI Engine - Raspberry Pi", frame)

        # AWS IoT Core MQTT 퍼블리시 전송부 시뮬레이션 커넥터 출력
        # (원격 데이터가 실시간으로 쌓여서 웹사이트 리포트 차트 데이터로 가공됩니다.)
        if int(time.time()) % 5 == 0:
            print(f"[AWS 전송] payload = {{ 'score': {immersion_score}, 'status': '{status_text}' }}")

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("[시스템] 분석 엔진이 성공적으로 안전 종료되었습니다.")

if __name__ == "__main__":
    main()