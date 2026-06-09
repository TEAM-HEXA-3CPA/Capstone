import os
import re
import pymysql
import bcrypt
from flask import Flask, request, jsonify
from auth import issue_token, login_required
from group_api import groups_bp
from rank_api import rank_bp
from report_api import report_bp

app = Flask(__name__)

app.register_blueprint(groups_bp)
app.register_blueprint(rank_bp)
app.register_blueprint(report_bp)

app.secret_key = os.environ.get("SECRET_KEY", "focusmate-secret-key-change-in-prod")

DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_USER     = os.environ.get("DB_USER",     "admin")
DB_PASSWORD = os.environ.get("DB_PASS", os.environ.get("DB_PASSWORD", ""))
DB_NAME     = os.environ.get("DB_NAME",     "hexa")
DB_PORT     = int(os.environ.get("DB_PORT", 3306))

def get_db():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASSWORD,
        database=DB_NAME, port=DB_PORT,
        charset="utf8mb4", cursorclass=pymysql.cursors.DictCursor
    )

def is_valid_password(password):
    if len(password) < 8: return False
    if not re.search(r"[A-Z]", password): return False
    if not re.search(r"[a-z]", password): return False
    if not re.search(r"\d", password): return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password): return False
    return True


# ── 회원가입 ──
@app.route("/signup", methods=["POST"])
def signup():
    user_id  = request.form.get("user_id", "").strip()
    password = request.form.get("password", "").strip()
    nickname = request.form.get("nickname", "").strip()
    email    = request.form.get("email", "").strip()
    phone    = request.form.get("phone", "").strip()
    name     = request.form.get("name", "").strip()

    if not (user_id and password and nickname and name):
        return jsonify({"ok": False, "message": "필수 입력 항목이 누락되었습니다."}), 400
    if not is_valid_password(password):
        return jsonify({"ok": False, "message": "비밀번호는 영문 대/소문자, 숫자, 특수문자를 포함하여 8자 이상이어야 합니다."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE user_id = %s", (user_id,))
            if cur.fetchone():
                return jsonify({"ok": False, "message": "이미 존재하는 아이디입니다."}), 400

            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute(
                "INSERT INTO users (user_id, password, nickname, email, phone, name) VALUES (%s,%s,%s,%s,%s,%s)",
                (user_id, hashed_pw, nickname, email, phone, name)
            )
            new_id = cur.lastrowid
            cur.execute(
                "INSERT INTO user_rankings (user_id, total_score, total_study_time, updated_at) VALUES (%s,0,0,NOW())",
                (new_id,)
            )
        conn.commit()

        token = issue_token(user_id, nickname)
        return jsonify({"ok": True, "message": "🎉 회원가입이 완료되었습니다!",
                        "token": token, "user_id": user_id, "nickname": nickname})

    except Exception as e:
        conn.rollback()
        error_msg = str(e)
        if hasattr(e, 'args') and len(e.args) > 0:
            err_no = e.args[0]
            if err_no == 3819:
                if "chk_user_name" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 이름 형식이 올바르지 않습니다."}), 400
                elif "chk_user_id_length" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 아이디는 최소 4자 이상이어야 합니다."}), 400
                return jsonify({"ok": False, "message": "❌ 데이터 입력 규칙을 위반했습니다."}), 400
            elif err_no == 1062:
                if "nickname" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 이미 사용 중인 닉네임입니다."}), 400
                elif "email" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 이미 등록된 이메일입니다."}), 400
                elif "phone" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 이미 등록된 전화번호입니다."}), 400
                return jsonify({"ok": False, "message": "❌ 중복된 정보가 존재합니다."}), 400
        return jsonify({"ok": False, "message": f"서버 오류: {error_msg}"}), 500
    finally:
        conn.close()


# ── 로그인 ──
@app.route("/login", methods=["POST"])
def login():
    if request.is_json:
        data     = request.get_json()
        user_id  = data.get("user_id", "").strip()
        password = data.get("password", "").strip()
    else:
        user_id  = request.form.get("user_id", "").strip()
        password = request.form.get("password", "").strip()

    if not user_id or not password:
        return jsonify({"ok": False, "message": "아이디와 비밀번호를 입력해주세요."}), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cur.fetchone()

        if not user:
            return jsonify({"ok": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401

        db_password    = user["password"]
        pw_matched     = False
        need_migration = False

        if db_password.startswith("$2b$") or db_password.startswith("$2a$"):
            try:
                pw_matched = bcrypt.checkpw(password.encode('utf-8'), db_password.encode('utf-8'))
            except Exception:
                pw_matched = False
        else:
            import hashlib
            if hashlib.sha256(password.encode('utf-8')).hexdigest() == db_password:
                pw_matched     = True
                need_migration = True

        if not pw_matched:
            return jsonify({"ok": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401

        if need_migration:
            try:
                new_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                with conn.cursor() as cur:
                    cur.execute("UPDATE users SET password=%s WHERE user_id=%s", (new_pw, user_id))
                conn.commit()
            except Exception:
                pass

        group_id = None
        with conn.cursor() as cur:
            cur.execute("SELECT group_id FROM group_members WHERE user_id = %s", (user["id"],))
            row = cur.fetchone()
            if row:
                group_id = row["group_id"]

        # ★ JWT 발급
        token = issue_token(user["user_id"], user["nickname"], group_id)
        return jsonify({
            "ok":       True,
            "token":    token,
            "nickname": user["nickname"],
            "user_id":  user["user_id"],
            "group_id": group_id
        })

    except Exception as e:
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500
    finally:
        conn.close()


# ── 로그아웃 (클라이언트에서 토큰 삭제하면 끝) ──
@app.route("/logout", methods=["POST"])
def logout():
    return jsonify({"ok": True})


# ── 내 정보 조회 ──
@app.route("/me")
def me():
    payload, err = login_required()
    if err:
        return err
    return jsonify({
        "ok":       True,
        "user_id":  payload["user_id"],
        "nickname": payload["nickname"],
        "group_id": payload.get("group_id")
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)