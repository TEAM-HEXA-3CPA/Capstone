import os
import re
import pymysql
import bcrypt
from flask import Flask, request, redirect, jsonify, session
from group_api import groups_bp
from rank_api import rank_bp
from report_api import report_bp

app = Flask(__name__)

# ── [핵심 연결선] 모든 블루프린트 라우터 완벽 등록 ──
app.register_blueprint(groups_bp)
app.register_blueprint(rank_bp)
app.register_blueprint(report_bp)

# 세션 암호화 키
app.secret_key = os.environ.get("SECRET_KEY", "focusmate-secret-key-change-in-prod")

# 인프라 환경 변수 매핑 (이중 변수 방어)
DB_HOST     = os.environ.get("DB_HOST",     "localhost")
DB_USER     = os.environ.get("DB_USER",     "admin")
DB_PASSWORD = os.environ.get("DB_PASS", os.environ.get("DB_PASSWORD", ""))
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

# 비밀번호 유효성 검사 (기존 정책 100% 유지)
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


# ── 회원가입 (Bcrypt 암호화 + 랭킹 자동 초기화 + 상세 에러 번역 가드 완벽 연동) ──
@app.route("/signup", methods=["POST"])
def signup():
    user_id  = request.form.get("user_id", "").strip()
    password = request.form.get("password", "").strip()
    nickname = request.form.get("nickname", "").strip()
    email    = request.form.get("email", "").strip()
    phone    = request.form.get("phone", "").strip()
    name     = request.form.get("name", "").strip()

    print(f"[DEBUG] 회원가입 시도 - ID: {user_id}, Name: {name}")

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

            salt = bcrypt.gensalt()
            hashed_pw = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

            sql = """INSERT INTO users (user_id, password, nickname, email, phone, name) 
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            cur.execute(sql, (user_id, hashed_pw, nickname, email, phone, name))
            
            new_user_db_id = cur.lastrowid
            print(f"[DEBUG] 1단계 성공 - Users 테이블 고유ID 발급 완료: {new_user_db_id}")

            sql_rank = """INSERT INTO user_rankings (user_id, total_score, total_study_time, updated_at)
                          VALUES (%s, 0, 0, NOW())"""
            cur.execute(sql_rank, (new_user_db_id,))
            print(f"[DEBUG] 2단계 성공 - User_rankings 테이블 세팅 완료")

        conn.commit()
        print(f"🎉 [SUCCESS] 회원가입 최종 DB 커밋 성공! ID: {user_id}")

        session["user_id"]  = user_id
        session["nickname"] = nickname
        
        return jsonify({
            "ok": True, 
            "message": "🎉 회원가입이 성공적으로 완료되었습니다!", 
            "user_id": user_id, 
            "nickname": nickname
        })
        
    except Exception as e:
        conn.rollback()
        error_msg = str(e)
        print(f"❌ [SIGNUP ERROR] 회원가입 실패 및 롤백 실행: {error_msg}")

        if hasattr(e, 'args') and len(e.args) > 0:
            err_no = e.args[0]
            if err_no == 3819:
                if "chk_user_name" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 이름(실명) 형식이 올바르지 않습니다. (최소 2글자 이상 입력)"}), 400
                elif "chk_user_id_length" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 아이디는 최소 8자 이상이어야 합니다."}), 400
                return jsonify({"ok": False, "message": "❌ 데이터 입력 규칙(Check 제약조건)을 위반했습니다."}), 400
            elif err_no == 1062:
                if "nickname" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 이미 사용 중인 닉네임입니다."}), 400
                elif "email" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 이미 등록된 이메일 주소입니다."}), 400
                elif "phone" in error_msg:
                    return jsonify({"ok": False, "message": "❌ 이미 등록된 전화번호입니다."}), 400
                return jsonify({"ok": False, "message": "❌ 중복된 정보가 존재하여 가입할 수 없습니다."}), 400

        return jsonify({"ok": False, "message": f"서버 오류가 발생했습니다: {error_msg}"}), 500
    finally:
        conn.close()

# ── 로그인 (Bcrypt 검증 + 기존 SHA256 유저 실시간 자동 마이그레이션 적용) ──
@app.route("/login", methods=["POST"])
def login():
    if request.is_json:
        data = request.get_json()
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

        db_password = user["password"]
        pw_matched = False
        need_migration = False

        if db_password.startswith("$2b$") or db_password.startswith("$2a$"):
            try:
                db_pw_bytes = db_password.encode('utf-8') if isinstance(db_password, str) else db_password
                if bcrypt.checkpw(password.encode('utf-8'), db_pw_bytes):
                    pw_matched = True
            except Exception:
                pw_matched = False
        else:
            import hashlib
            hashed_input_pw = hashlib.sha256(password.encode('utf-8')).hexdigest()
            if hashed_input_pw == db_password:
                pw_matched = True
                need_migration = True

        if not pw_matched:
            return jsonify({"ok": False, "message": "아이디 또는 비밀번호가 올바르지 않습니다."}), 401

        if need_migration:
            new_salt = bcrypt.gensalt()
            new_bcrypt_pw = bcrypt.hashpw(password.encode('utf-8'), new_salt).decode('utf-8')
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE users SET password = %s WHERE user_id = %s",
                        (new_bcrypt_pw, user_id)
                    )
                conn.commit()
                print(f"[MIGRATION] 유저 {user_id} 암호 규격이 최신 Bcrypt로 자동 변경되었습니다.")
            except Exception as update_err:
                print(f"[WARN] 마이그레이션 저장 실패: {str(update_err)}")

        session["user_id"]  = user["user_id"]
        session["nickname"] = user["nickname"]

        with conn.cursor() as cur:
            cur.execute("SELECT group_id FROM group_members WHERE user_id = %s", (user["id"],))
            user_group = cur.fetchone()
            if user_group:
                session["group_id"] = user_group["group_id"]

        return jsonify({
            "ok":       True,
            "nickname": user["nickname"],
            "user_id":  user["user_id"],
            "groupId":  session.get("group_id", None)
        })

    except Exception as e:
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500
    finally:
        conn.close()

# ── 로그아웃 ──
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})

# ── 유저 정보 조회 ──
@app.route("/me")
def me():
    if "user_id" not in session:
        return jsonify({"ok": False}), 401
    return jsonify({
        "ok":       True,
        "user_id":  session["user_id"],
        "nickname": session["nickname"],
        "group_id":  session.get("group_id", None)
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)