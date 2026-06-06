# auth.py — JWT 공통 유틸리티
import os
import jwt
from datetime import datetime, timezone, timedelta
from flask import request, jsonify

JWT_SECRET  = os.environ.get("SECRET_KEY", "focusmate-secret-key-change-in-prod")
JWT_ALGO    = "HS256"
JWT_EXPIRES = 30  # 분


def issue_token(user_id: str, nickname: str, group_id=None) -> str:
    """JWT 발급 (30분 만료)"""
    payload = {
        "user_id":  user_id,
        "nickname": nickname,
        "group_id": group_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRES),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGO)


def decode_token(token: str) -> dict:
    """JWT 검증 및 페이로드 반환. 실패 시 None"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_current_user():
    """
    요청 헤더에서 Bearer 토큰을 꺼내 검증 후 페이로드 반환.
    실패 시 (None, 401 Response) 반환.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"ok": False, "message": "로그인이 필요합니다."}), 401)

    token = auth_header[7:]
    payload = decode_token(token)
    if not payload:
        return None, (jsonify({"ok": False, "message": "토큰이 만료되었거나 유효하지 않습니다."}), 401)

    return payload, None


def login_required():
    """
    Blueprint 라우터에서 호출.
    성공: (payload, None)
    실패: (None, (response, status))
    """
    return get_current_user()