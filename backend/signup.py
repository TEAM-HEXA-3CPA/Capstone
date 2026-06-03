import os
import re
import pymysql
import hashlib
from flask import Flask, request, redirect, jsonify, session
from group_api import groups_bp
from rank_api import rank_bp

app = Flask(__name__)

# ── 핵심 연계: 모든 블루프린트 라우터 결속 ──
app.register_blueprint(groups_bp)
app.register_blueprint(rank_bp)

# 세션 관리용 보안 키 정의
app.secret_key = os.environ.get("SECRET_KEY", "focusmate-secret-key-change-in-prod")

# 다른 작업자 변동 내역 호환용 이중 방어 인프라 환경 변수 매핑
DB_HOST     = os.environ.get("DB_HOST", "localhost")
DB_USER     = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASS", os.environ.get("DB_PASSWORD", ""))
DB_NAME     = os.environ.get("DB_NAME", "hexa")
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

# 기존 비밀번호 정규식 유효성 정책 100% 유지
def is_valid_password(password):
    if len(password) < 8:
        return False
    if not re.search(r"[A-Z]", password):
        return False
    if not re.search(r"[a-z]", password):
        return False
    if not re.search(r"\d", password):
        return False
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False
    return True

def _alert(message):
    return f"<script>alert('{message}'); history.back();</script>"

# ── 회원가입 기능 (기존 폼 양식 로직 완벽 보존) ──
@app.route("/signup", methods=["POST"])
def signup():
    user_id = request.form.get("user_id", "").strip()
    password = request.form.get("password", "").strip()
    nickname = request.form.get("nickname", "").strip()
    email = request.form.get("email", "").strip()
    phone = request.form.get("phone", "").strip()

    if not (user_id and password and nickname):
        return _alert("필수 입력 항목이 누락되었습니다.")

    if not is_valid_password(password):
        return _alert("비밀번호는 영문 대/소문자, 숫자, 특수문자를 포함하여 8자 이상이어야 합니다.")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE user_id = %s", (user_id,))
            if cur.fetchone():
                return _alert("이미 존재하는 아이디입니다.")

            hashed_pw = hashlib.sha256(password.encode()).hexdigest()

            sql = """INSERT INTO users (user_id, password, nickname, email, phone) 
                     VALUES (%s, %s, %s, %s, %s)"""
            cur.execute(sql, (user_id, hashed_pw, nickname, email, phone))
        conn.commit()

        session["user_id"] = user_id
        session["nickname"] = nickname
        return redirect("/main-home.html")
    except Exception as e:
        return f"서버 회원가입 오류: {str(e)}", 500
    finally:
        conn.close()

# ── 로그인 기능 (기존 세션 주입 규칙 완벽 유지) ──
@app.route("/login", methods=["POST"])
def login():
    if request.is_json:
        data = request.get_json()
        user_id = data.get("user_id", "").strip()
        password = data.get("password", "").strip()
    else:
        user_id = request.form.get("user_id", "").strip()
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

        hashed_input_pw = hashlib.sha256(password.encode()).hexdigest()
        if hashed_input_pw != user["password"]:
            return jsonify({"ok": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401

        session["user_id"] = user["user_id"]
        session["nickname"] = user["nickname"]

        # 로그인 시 소속 그룹 아이디 세션 동기화 연계
        with conn.cursor() as cur:
            cur.execute("SELECT group_id FROM group_members WHERE user_id = %s", (user["user_id"],))
            user_group = cur.fetchone()
            if user_group:
                session["group_id"] = user_group["group_id"]

        return jsonify({
            "ok": True,
            "nickname": user["nickname"],
            "user_id": user["user_id"],
            "groupId": session.get("group_id", None)
        })
    except Exception as e:
        return jsonify({"ok": False, "message": f"서버 내부 로그인 실패: {str(e)}"}), 500
    finally:
        conn.close()

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

@app.route("/me")
def me():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401
    return jsonify({
        "ok": True,
        "user_id": session["user_id"],
        "nickname": session["nickname"],
        "group_id": session.get("group_id", None)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)