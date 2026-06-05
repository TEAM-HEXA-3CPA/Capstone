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
            "ok":          True,
            "groupId":    group["group_id"],
            "name":       group["name"],
            "hasPassword": group["password"] is not None
        })

    finally:
        conn.close()


# =================================================================
# STEP 2 : 그룹 입장 (비밀번호 검증 + 멤버 등록)
# POST /api/groups/join
# =================================================================
@groups_bp.route("/join", methods=["POST"])
def join_group():
    err = _login_required()
    if err:
        return err

    data     = request.get_json(silent=True) or {}
    code     = (data.get("code")     or "").strip().upper()
    password = (data.get("password") or "").strip()
    user_id_str = session["user_id"] # 세션의 문자열 아이디 ('dbwldnd')

    if not code:
        return jsonify({"ok": False, "message": "초대 코드가 없습니다."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 🎯 [교정] 명세서 규격 동기화: 문자열 아이디로 users 테이블의 진짜 숫자 id(PK)를 먼저 찾습니다. [cite: 35, 39]
            cur.execute("SELECT id FROM users WHERE user_id = %s", (user_id_str,))
            user_record = cur.fetchone()
            if not user_record:
                return jsonify({"ok": False, "message": "존재하지 않는 회원 정보입니다."}), 400
            
            real_user_id = user_record["id"] # DB 내부 일련번호 (숫자)

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
            # 🎯 [교정] group_members.user_id는 int 타입이므로 real_user_id(숫자)로 검사합니다. [cite: 35]
            cur.execute(
                "SELECT id FROM group_members WHERE group_id = %s AND user_id = %s",
                (group["group_id"], real_user_id)
            )
            already = cur.fetchone()

        if already:
            return jsonify({
                "ok":      True,
                "groupId": group["group_id"],
                "name":    group["name"],
                "message": "이미 소속된 그룹입니다."
            })

        # ── 멤버 등록 ─────────────────────────────────────────────────
        with conn.cursor() as cur:
            # 🎯 [교정] 가입할 때도 동일하게 real_user_id(숫자)를 넣어 외래키 충돌을 방지합니다. [cite: 35]
            cur.execute(
                "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                (group["group_id"], real_user_id)
            )
        conn.commit()

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
# =================================================================
@groups_bp.route("/create", methods=["POST"])
def create_group():
    err = _login_required()
    if err:
        return err

    data     = request.get_json(silent=True) or {}
    name     = (data.get("name")     or "").strip()
    password = (data.get("password") or "").strip()
    user_id_str = session["user_id"]

    if not name:
        return jsonify({"ok": False, "message": "그룹 이름을 입력해주세요."}), 400
    if len(name) > 50:
        return jsonify({"ok": False, "message": "그룹 이름은 50자 이하여야 합니다."}), 400

    hashed_pw   = _hash_pw(password) if password else None

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 🎯 [교정] 세션의 문자열 아이디로 users 테이블의 진짜 숫자 id(PK)를 가져옵니다. [cite: 36, 39]
            cur.execute("SELECT id FROM users WHERE user_id = %s", (user_id_str,))
            user_record = cur.fetchone()

            if not user_record:
                return jsonify({"ok": False, "message": "존재하지 않는 회원 정보입니다."}), 400

            real_user_id = user_record["id"]

            # 초대 코드 중복 방지 루프
            for _ in range(5):
                invite_code = _gen_invite_code()
                cur.execute(
                    "SELECT 1 FROM study_groups WHERE invite_code = %s",
                    (invite_code,)
                )
                if not cur.fetchone():
                    break

            # 🎯 [교정] study_groups.created_by에 숫자형 ID(real_user_id)를 주입해 1452 에러를 차단합니다. [cite: 36]
            cur.execute(
                """
                INSERT INTO study_groups (invite_code, name, password, created_by)
                VALUES (%s, %s, %s, %s)
                """,
                (invite_code, name, hashed_pw, real_user_id)
            )
            group_id = cur.lastrowid

            # 🎯 [교정] group_members.user_id에도 동일하게 숫자형 ID를 매핑합니다. [cite: 35]
            cur.execute(
                "INSERT INTO group_members (group_id, user_id) VALUES (%s, %s)",
                (group_id, real_user_id)
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

    user_id_str = session["user_id"]

    conn = get_db()
    try:
        with conn.cursor() as cur:
            # 🎯 [교정] 탈퇴할 때도 먼저 숫자 ID를 추적해옵니다. [cite: 35, 39]
            cur.execute("SELECT id FROM users WHERE user_id = %s", (user_id_str,))
            user_record = cur.fetchone()
            if not user_record:
                return jsonify({"ok": False, "message": "존재하지 않는 회원 정보입니다."}), 400
            
            real_user_id = user_record["id"]

            # 🎯 [교정] 숫자형 ID를 기반으로 group_members의 매핑 행을 안전하게 삭제합니다. [cite: 35]
            cur.execute(
                "DELETE FROM group_members WHERE user_id = %s",
                (real_user_id,)
            )
        conn.commit()

        session.pop("group_id",   None)
        session.pop("group_name", None)

        return jsonify({"ok": True, "message": "그룹에서 탈퇴했습니다."})

    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500

    finally:
        conn.close()

# =================================================================
# 내 그룹 초대코드 조회
# GET /api/groups/my-code
# =================================================================
@groups_bp.route("/my-code", methods=["GET"])
def my_code():
    err = _login_required()
    if err:
        return err

    user_id_str = session["user_id"]

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE user_id = %s", (user_id_str,))
            user_record = cur.fetchone()
            if not user_record:
                return jsonify({"ok": False, "message": "존재하지 않는 회원입니다."}), 404

            real_user_id = user_record["id"]

            cur.execute("""
                SELECT sg.invite_code, sg.name
                FROM group_members gm
                JOIN study_groups sg ON gm.group_id = sg.group_id
                WHERE gm.user_id = %s
                LIMIT 1
            """, (real_user_id,))
            group = cur.fetchone()

        if not group:
            return jsonify({"ok": False, "message": "소속된 그룹이 없습니다."}), 404

        return jsonify({"ok": True, "invite_code": group["invite_code"], "name": group["name"]})

    except Exception as e:
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500
    finally:
        conn.close()