import os
import re
import pymysql
from flask import Flask, request, redirect, jsonify, session
from group_api import groups_bp

app = Flask(__name__)
app.register_blueprint(groups_bp)

# 세션 암호화 키 (환경변수로 관리)
app.secret_key = os.environ.get("SECRET_KEY", "focusmate-secret-key-change-in-prod")

# ── DB 연결 설정 ────────────────────────────────────────────────────────
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


# ── 비밀번호 유효성 검사 (백엔드 이중 검증) ────────────────────────────
#    대문자 1개 이상, 소문자 1개 이상, 숫자 1개 이상, 특수문자 1개 이상, 8자 이상
PW_PATTERN = re.compile(
    r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]).{8,}$'
)


# ── 회원가입 ──────────────────────────────────────────────────────────
@app.route("/signup", methods=["POST"])
def signup():
    name     = (request.form.get("name")     or "").strip()
    phone    = (request.form.get("phone")    or "").strip()
    email    = (request.form.get("email")    or "").strip()
    nickname = (request.form.get("nickname") or "").strip()
    user_id  = (request.form.get("user_id")  or "").strip()
    password = (request.form.get("password") or "")

    # ── 서버 측 입력 검증 ────────────────────────────────────────────
    errors = []

    if not name or len(name) > 10:
        errors.append("이름은 1~10자여야 합니다.")
    if not phone:
        errors.append("전화번호를 입력해주세요.")
    if not email or "@" not in email:
        errors.append("올바른 이메일을 입력해주세요.")
    if not nickname or len(nickname) > 10:
        errors.append("닉네임은 1~10자여야 합니다.")
    if not user_id or len(user_id) > 20:
        errors.append("아이디는 1~20자여야 합니다.")
    if not PW_PATTERN.match(password):
        errors.append("비밀번호는 8자 이상, 대·소문자·숫자·특수문자를 각 1개 이상 포함해야 합니다.")

    if errors:
        return jsonify({"ok": False, "message": " / ".join(errors)}), 400

    # ── bcrypt 해싱 ──────────────────────────────────────────────────
    try:
        import bcrypt
        hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except ImportError:
        # bcrypt 없을 시 hashlib 대체 (프로덕션에서는 반드시 bcrypt 사용)
        import hashlib
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users
                    (user_id, password, name, phone, nickname, email)
                VALUES
                    (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, hashed_pw, name, phone, nickname, email)
            )
        conn.commit()

        # 가입 성공 → 세션 저장
        session["user_id"]  = user_id
        session["nickname"] = nickname
        return jsonify({
            "ok":       True,
            "nickname": nickname,
            "user_id":  user_id
        })

    except pymysql.err.IntegrityError as e:
        err_msg = str(e)
        if "nickname" in err_msg:
            return jsonify({"ok": False, "message": "이미 사용 중인 닉네임입니다."}), 409
        elif "user_id" in err_msg:
            return jsonify({"ok": False, "message": "이미 사용 중인 아이디입니다."}), 409
        elif "phone" in err_msg:
            return jsonify({"ok": False, "message": "이미 등록된 전화번호입니다."}), 409
        else:
            return jsonify({"ok": False, "message": "이미 사용 중인 정보가 있습니다."}), 409

    except Exception as e:
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500

    finally:
        conn.close()


# ── 로그인 ────────────────────────────────────────────────────────────
@app.route("/login", methods=["POST"])
def login():
    user_id  = (request.form.get("user_id")  or "").strip()
    password = (request.form.get("password") or "")

    if not user_id or not password:
        return _alert("아이디와 비밀번호를 입력해주세요.")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT user_id, password, nickname FROM users WHERE user_id = %s",
                (user_id,)
            )
            user = cur.fetchone()

        if not user:
            return _alert("아이디 또는 비밀번호가 올바르지 않습니다.")

        # ── 비밀번호 검증 ────────────────────────────────────────────
        pw_matched = False
        try:
            import bcrypt
            pw_matched = bcrypt.checkpw(
                password.encode("utf-8"),
                user["password"].encode("utf-8")
            )
        except ImportError:
            import hashlib
            pw_matched = (hashlib.sha256(password.encode()).hexdigest() == user["password"])

        if not pw_matched:
            return _alert("아이디 또는 비밀번호가 올바르지 않습니다.")

        # ── 로그인 성공 → 세션 저장 후 JSON 반환 ────────────────────
        session["user_id"]  = user["user_id"]
        session["nickname"] = user["nickname"]

        # 프론트가 fetch()로 호출하므로 JSON 반환
        return jsonify({
            "ok":       True,
            "nickname": user["nickname"],
            "user_id":  user["user_id"]
        })

    except Exception as e:
        return f"서버 에러: {str(e)}", 500

    finally:
        conn.close()


# ── 로그아웃 ──────────────────────────────────────────────────────────
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


# ── 현재 로그인 유저 정보 조회 ────────────────────────────────────────
@app.route("/me")
def me():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401
    return jsonify({
        "ok":       True,
        "user_id":  session["user_id"],
        "nickname": session["nickname"]
    })


# ── 내부 헬퍼: alert + history.back() ────────────────────────────────
def _alert(msg: str):
    safe = msg.replace("'", "\\'").replace("\n", "\\n")
    return f"<script>alert('{safe}'); history.back();</script>"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)