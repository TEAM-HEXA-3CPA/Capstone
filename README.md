# HEXA

AWS 기반으로 구축한 웹 서비스 프로젝트입니다.  
Docker 컨테이너 환경에서 애플리케이션을 실행하고, GitHub Actions를 이용한 CI/CD 파이프라인을 구축하여 자동 배포가 가능하도록 구현하였습니다.

프로젝트 개요

HEXA는 클라우드 환경에서 실제 서비스 운영 방식을 학습하기 위해 진행한 프로젝트입니다.

주요 목표는 다음과 같습니다.

- Docker 기반 컨테이너 환경 구축
- AWS ECS를 이용한 서비스 운영
- AWS RDS를 이용한 데이터베이스 연동
- Application Load Balancer(ALB)를 통한 트래픽 분산
- GitHub Actions 기반 CI/CD 자동화
- AWS Secrets Manager를 이용한 민감 정보 관리

---

 기술 스택
 Backend
- Python
- Flask

Frontend
- HTML
- CSS
- JavaScript

 Database
- MySQL
- AWS RDS

DevOps / Cloud
- AWS ECS (fargate)
- AWS ECR
- AWS RDS
- AWS ALB
- AWS Secrets Manager
- ALB
- GitHub Actions
- Docker

ECS 기반 웹 서비스
사용자
   ▼
Application Load Balancer (ALB)
   ▼
Amazon ECS (EC2)
   ├── Nginx Container (web)
   │       ▼
   │   Flask Container (backend)
   ▼
Amazon RDS (MySQL)

CI/CD 파이프라인
Developer
   │
   ▼
GitHub Repository
   │
   ▼
GitHub Actions
   │
   ├── Docker Build
   ├── Docker Push
   │
   ▼
Amazon ECR
   │
   ▼
Amazon ECS Service Update
   │
   ▼
New Task Deployment

Raspberry Pi IoT 데이터 수집 파이프라인
Sensor
   │
   ▼
Raspberry Pi
(MediaPipe)
   │
   ▼
AWS IoT Core
   │
   ▼
AWS Lambda
   │
   ▼
Amazon RDS
