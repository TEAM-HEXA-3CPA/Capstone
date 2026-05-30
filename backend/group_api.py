# group_api.py
# groups 테이블 DDL (참고용):
#
# CREATE TABLE study_groups (
#     group_id    INT          AUTO_INCREMENT PRIMARY KEY,
#     invite_code VARCHAR(20)  NOT NULL UNIQUE,
#     name        VARCHAR(50)  NOT NULL,
#     password    VARCHAR(255) DEFAULT NULL,   -- bcrypt 해시, 없으면 NULL
#     created_by  VARCHAR(20)  NOT NULL,       -- users.user_id FK
#     created_at  DATETIME     DEFAULT NOW()
# );
#
# CREATE TABLE group_members (
#     id         INT      AUTO_INCREMENT PRIMARY KEY,
#     group_id   INT      NOT NULL,   -- study_groups.group_id FK
#     user_id    VARCHAR(20) NOT NULL, -- users.user_id FK
#     joined_at  DATETIME DEFAULT NOW(),
#     UNIQUE KEY uq_member (group_id, user_id)
# );

import os
import re
import secrets
import pymysql
from flask import Blueprint, request, jsonify, session

groups_bp = Blueprint("groups", __name__, url_prefix="/api/groups")

# ── DB 연결 (signup.py 와 동일한 환경변수 사용) ───────────────────────
DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_USER     = os.environ.get("DB_USER",     "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME     = os.environ.get("DB_NAME",     "hexa")
DB_PORT     = int(os.environ.get("DB_PORT", 3306))


def get_db():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


def _login_required():
    """로그인 안 됐으면 401 반환, 됐으면 None"""
    if "user_id" not in session:
        return jsonify({"ok": False, "message": "로그인이 필요합니다."}), 401
    return None


def _hash_pw(pw: str) -> str:
    try:
        import bcrypt
        return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()
    except ImportError:
        import hashlib
        return hashlib.sha256(pw.encode()).hexdigest()


def _check_pw(plain: str, hashed: str) -> bool:
    try:
        import bcrypt
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except ImportError:
        import hashlib
        return hashlib.sha256(plain.encode()).hexdigest() == hashed


def _gen_invite_code() -> str:
    """FOCUS-XXXX 형태의 유니크 초대 코드 생성"""
    return "FOCUS-" + secrets.token_hex(2).upper()


# =================================================================
# STEP 1 : 초대 코드 검증
# POST /api/groups/verify-invite
# body: { "code": "FOCUS-001" }
# 응답: { ok, groupId, name, hasPassword }  ← 비밀번호 절대 미포함
# =================================================================
@groups_bp.route("/verify-invite", methods=["POST"])
def verify_invite():
    err = _login_required()
    if err:
        return err

    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()

    if not code:
        return jsonify({"ok": False, "message": "초대 코드를 입력해주세요."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT group_id, name, password FROM study_groups WHERE invite_code = %s",
                (code,)
            )
            group = cur.fetchone()

        if not group:
            return jsonify({"ok": False, "message": "유효하지 않은 초대 코드입니다."}), 404

        return jsonify({
            "ok":         True,
            "groupId":    group["group_id"],
            "name":       group["name"],
            "hasPassword": group["password"] is not None   # 비밀번호 값 자체는 미포함
        })

    finally:
        conn.close()


# =================================================================
# STEP 2 : 그룹 입장 (비밀번호 검증 + 멤버 등록)
# POST /api/groups/join
# body: { "code": "FOCUS-001", "password": "..." }  ← 비번 없는 그룹은 password 생략
# =================================================================
@groups_bp.route("/join", methods=["POST"])
def join_group():
    err = _login_required()
    if err:
        return err

    data     = request.get_json(silent=True) or {}
    code     = (data.get("code")     or "").strip().upper()
    password = (data.get("password") or "").strip()
    user_id  = session["user_id"]

    if not code:
        return jsonify({"ok": False, "message": "초대 코드가 없습니다."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # ── 그룹 조회 ────────────────────────────────────────────
            cur.execute(
                "SELECT group_id, name, password FROM study_groups WHERE invite_code = %s",
                (code,)
            )
            group = cur.fetchone()

        if not group:
            return jsonify({"ok": False, "message": "유효하지 않은 초대 코드입니다."}), 404

        # ── 비밀번호 검증 ─────────────────────────────────────────────
        if group["password"] is not None:
            if not password:
                return jsonify({"ok": False, "message": "비밀번호를 입력해주세요."}), 400
            if not _check_pw(password, group["password"]):
                return jsonify({"ok": False, "message": "비밀번호가 올바르지 않습니다."}), 401

        # ── 이미 가입된 멤버인지 확인 ────────────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM group_members WHERE group_id = %s AND user_id = %s",
                (group["group_id"], user_id)
            )
            already = cur.fetchone()

        if already:
            # 이미 가입 → 그냥 입장 허용 (에러 아님)
            return jsonify({
                "ok":      True,
                "groupId": group["group_id"],
                "name":    group["name"],
                "message": "이미 소속된 그룹입니다."
            })

        # ── 멤버 등록 ─────────────────────────────────────────────────
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                (group["group_id"], user_id)
            )
        conn.commit()

        # 세션에 현재 그룹 저장
        session["group_id"]   = group["group_id"]
        session["group_name"] = group["name"]

        return jsonify({
            "ok":      True,
            "groupId": group["group_id"],
            "name":    group["name"],
            "message": f"'{group['name']}' 그룹에 입장했습니다!"
        })

    except pymysql.err.IntegrityError:
        return jsonify({"ok": False, "message": "이미 소속된 그룹입니다."}), 409

    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500

    finally:
        conn.close()


# =================================================================
# 그룹 생성
# POST /api/groups/create
# body: { "name": "캡스톤 A팀", "password": "..." }  ← password 선택
# =================================================================
@groups_bp.route("/create", methods=["POST"])
def create_group():
    err = _login_required()
    if err:
        return err

    data     = request.get_json(silent=True) or {}
    name     = (data.get("name")     or "").strip()
    password = (data.get("password") or "").strip()
    user_id  = session["user_id"]

    if not name:
        return jsonify({"ok": False, "message": "그룹 이름을 입력해주세요."}), 400
    if len(name) > 50:
        return jsonify({"ok": False, "message": "그룹 이름은 50자 이하여야 합니다."}), 400

    hashed_pw   = _hash_pw(password) if password else None

    conn = get_db()
    try:
        # 초대 코드 중복 방지 루프
        for _ in range(5):
            invite_code = _gen_invite_code()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM study_groups WHERE invite_code = %s",
                    (invite_code,)
                )
                if not cur.fetchone():
                    break

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO study_groups (invite_code, name, password, created_by)
                VALUES (%s, %s, %s, %s)
                """,
                (invite_code, name, hashed_pw, user_id)
            )
            group_id = cur.lastrowid

            # 생성자 자동 멤버 등록
            cur.execute(
                "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                (group_id, user_id)
            )
        conn.commit()

        session["group_id"]   = group_id
        session["group_name"] = name

        return jsonify({
            "ok":         True,
            "groupId":    group_id,
            "name":       name,
            "inviteCode": invite_code
        })

    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500

    finally:
        conn.close()


# =================================================================
# 그룹 탈퇴
# POST /api/groups/leave
# =================================================================
@groups_bp.route("/leave", methods=["POST"])
def leave_group():
    err = _login_required()
    if err:
        return err

    user_id = session["user_id"]

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM group_members WHERE user_id = %s",
                (user_id,)
            )
        conn.commit()

        session.pop("group_id",   None)
        session.pop("group_name", None)

        return jsonify({"ok": True, "message": "그룹에서 탈퇴했습니다."})

    except Exception as e:
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500

    finally:
        conn.close()