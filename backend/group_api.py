import os
import secrets
import pymysql
from flask import Blueprint, request, jsonify
from auth import login_required

groups_bp = Blueprint("groups", __name__, url_prefix="/api/groups")

DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_USER     = os.environ.get("DB_USER",     "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME     = os.environ.get("DB_NAME",     "hexa")
DB_PORT     = int(os.environ.get("DB_PORT", 3306))

def get_db():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, port=DB_PORT,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor
    )

def _hash_pw(pw):
    import bcrypt
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def _check_pw(plain, hashed):
    import bcrypt
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def _gen_invite_code():
    return "FOCUS-" + secrets.token_hex(2).upper()


@groups_bp.route("/verify-invite", methods=["POST"])
def verify_invite():
    payload, err = login_required()
    if err: return err
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    if not code:
        return jsonify({"ok": False, "message": "초대 코드를 입력해주세요."}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT group_id, name, password FROM study_groups WHERE invite_code=%s", (code,))
            group = cur.fetchone()
        if not group:
            return jsonify({"ok": False, "message": "유효하지 않은 초대 코드입니다."}), 404
        return jsonify({"ok": True, "groupId": group["group_id"], "name": group["name"],
                        "hasPassword": group["password"] is not None})
    finally:
        conn.close()


@groups_bp.route("/join", methods=["POST"])
def join_group():
    payload, err = login_required()
    if err: return err
    data        = request.get_json(silent=True) or {}
    code        = (data.get("code") or "").strip().upper()
    password    = (data.get("password") or "").strip()
    user_id_str = payload["user_id"]
    if not code:
        return jsonify({"ok": False, "message": "초대 코드가 없습니다."}), 400
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE user_id=%s", (user_id_str,))
            user_record = cur.fetchone()
            if not user_record:
                return jsonify({"ok": False, "message": "존재하지 않는 회원입니다."}), 400
            real_user_id = user_record["id"]
            cur.execute("SELECT group_id, name, password FROM study_groups WHERE invite_code=%s", (code,))
            group = cur.fetchone()
        if not group:
            return jsonify({"ok": False, "message": "유효하지 않은 초대 코드입니다."}), 404
        if group["password"] is not None:
            if not password:
                return jsonify({"ok": False, "message": "비밀번호를 입력해주세요."}), 400
            if not _check_pw(password, group["password"]):
                return jsonify({"ok": False, "message": "비밀번호가 올바르지 않습니다."}), 401
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM group_members WHERE group_id=%s AND user_id=%s",
                        (group["group_id"], real_user_id))
            already = cur.fetchone()
        if already:
            return jsonify({"ok": True, "groupId": group["group_id"], "name": group["name"],
                            "message": "이미 소속된 그룹입니다."})
        with conn.cursor() as cur:
            cur.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s,%s)",
                        (group["group_id"], real_user_id))
        conn.commit()
        return jsonify({"ok": True, "groupId": group["group_id"], "name": group["name"],
                        "message": f"'{group['name']}' 그룹에 입장했습니다!"})
    except pymysql.err.IntegrityError:
        return jsonify({"ok": False, "message": "이미 소속된 그룹입니다."}), 409
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500
    finally:
        conn.close()


@groups_bp.route("/create", methods=["POST"])
def create_group():
    payload, err = login_required()
    if err: return err
    data        = request.get_json(silent=True) or {}
    name        = (data.get("name") or "").strip()
    password    = (data.get("password") or "").strip()
    user_id_str = payload["user_id"]
    if not name:
        return jsonify({"ok": False, "message": "그룹 이름을 입력해주세요."}), 400
    if len(name) > 50:
        return jsonify({"ok": False, "message": "그룹 이름은 50자 이하여야 합니다."}), 400
    hashed_pw = _hash_pw(password) if password else None
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE user_id=%s", (user_id_str,))
            user_record = cur.fetchone()
            if not user_record:
                return jsonify({"ok": False, "message": "존재하지 않는 회원입니다."}), 400
            real_user_id = user_record["id"]
            for _ in range(5):
                invite_code = _gen_invite_code()
                cur.execute("SELECT 1 FROM study_groups WHERE invite_code=%s", (invite_code,))
                if not cur.fetchone():
                    break
            cur.execute(
                "INSERT INTO study_groups (invite_code, name, password, created_by) VALUES (%s,%s,%s,%s)",
                (invite_code, name, hashed_pw, real_user_id)
            )
            group_id = cur.lastrowid
            cur.execute("INSERT INTO group_members (group_id, user_id) VALUES (%s,%s)",
                        (group_id, real_user_id))
        conn.commit()
        return jsonify({"ok": True, "groupId": group_id, "name": name, "inviteCode": invite_code})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500
    finally:
        conn.close()


@groups_bp.route("/leave", methods=["POST"])
def leave_group():
    payload, err = login_required()
    if err: return err
    user_id_str = payload["user_id"]
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE user_id=%s", (user_id_str,))
            user_record = cur.fetchone()
            if not user_record:
                return jsonify({"ok": False, "message": "존재하지 않는 회원입니다."}), 400
            cur.execute("DELETE FROM group_members WHERE user_id=%s", (user_record["id"],))
        conn.commit()
        return jsonify({"ok": True, "message": "그룹에서 탈퇴했습니다."})
    except Exception as e:
        conn.rollback()
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500
    finally:
        conn.close()


@groups_bp.route("/my-code", methods=["GET"])
def my_code():
    payload, err = login_required()
    if err: return err
    user_id_str = payload["user_id"]
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE user_id=%s", (user_id_str,))
            user_record = cur.fetchone()
            if not user_record:
                return jsonify({"ok": False, "message": "존재하지 않는 회원입니다."}), 404
            cur.execute("""
                SELECT sg.invite_code, sg.name
                FROM group_members gm
                JOIN study_groups sg ON gm.group_id = sg.group_id
                WHERE gm.user_id = %s LIMIT 1
            """, (user_record["id"],))
            group = cur.fetchone()
        if not group:
            return jsonify({"ok": False, "message": "소속된 그룹이 없습니다."}), 404
        return jsonify({"ok": True, "invite_code": group["invite_code"], "name": group["name"]})
    except Exception as e:
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500
    finally:
        conn.close()