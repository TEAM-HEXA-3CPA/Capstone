# Drowsiness Detection

라즈베리파이5와 Pi Camera Module v3를 이용한 실시간 졸음 감지 시스템입니다.

MediaPipe Face Landmarker를 활용하여 얼굴 랜드마크를 추출하고, EAR(Eye Aspect Ratio) 값을 기반으로 졸음 여부를 판단합니다.

또한 AWS IoT Core MQTT 통신을 통해 EAR 데이터와 사용자 상태를 실시간으로 전송합니다.

## Features

* 실시간 얼굴 랜드마크 추출
* EAR 기반 눈 감김 감지
* 졸음 상태 경고 표시
* AWS IoT Core MQTT 데이터 전송

## Files

* `ear_detection_local.py`

  * 로컬 환경 EAR 기반 졸음 감지 코드

* `ear_detection_mqtt.py`

  * AWS IoT MQTT 연동 EAR 기반 졸음 감지 코드

* `drowsiness_yolo_mqtt.py`

  * YOLO 기반 졸음 감지 및 AWS IoT MQTT 연동 코드
