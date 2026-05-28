import os
import pymysql
from flask import Flask, request, render_template, redirect, url_for

# 현재 폴더 설정 유지
app = Flask(__name__, template_folder='.', static_folder='.', static_url_path='')

# 💡 보내주셨던 AWS Aurora DB 설정 값 그대로 대입
DB_HOST = "hexa-databases.cluster-clw0oikmwous.ap-northeast-2.rds.amazonaws.com"
DB_USER = "admin"
DB_PASSWORD = "A123456!"
DB_NAME = "hexa"
DB_PORT = 3306

def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

# 1. 메인 로그인/회원가입 화면 띄우기
@app.route('/')
@app.route('/index.html')
def login_page():
    return render_template('index.html')

# 2. 회원가입
@app.route('/signup', methods=['POST'])
def signup():
    name = request.form.get('name')
    phone = request.form.get('phone')
    nickname = request.form.get('nickname')
    user_id = request.form.get('user_id')
    password = request.form.get('password')

    dummy_email = f"{user_id}@test.com"

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO users (user_id, password, name, phone, nickname, email)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (user_id, password, name, phone, nickname, dummy_email))

        connection.commit()
        print(f"🎉 {user_id} 회원가입 완료 (더미 이메일: {dummy_email})")

        return redirect(url_for('control_page'))

    except pymysql.err.IntegrityError:
        print("⚠️ 중복된 아이디 입력으로 인해 가입이 거부되었습니다.")
        return "<script>alert('이미 존재하는 아이디입니다!'); history.back();</script>"
    except Exception as e:
        print(f"❌ DB 저장 중 에러 발생: {str(e)}")
        return f"서버 에러 발생: {str(e)}", 500
    finally:
        connection.close()

# 3. 로그인 (신규 추가)
@app.route('/login', methods=['POST'])
def login():
    user_id = request.form.get('user_id')
    password = request.form.get('password')

    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM users WHERE user_id = %s AND password = %s"
            cursor.execute(sql, (user_id, password))
            user = cursor.fetchone()

        if user:
            return redirect(url_for('control_page'))
        else:
            return "<script>alert('아이디 또는 비밀번호가 올바르지 않습니다.'); history.back();</script>"
    except Exception as e:
        print(f"❌ 로그인 중 에러 발생: {str(e)}")
        return f"서버 에러 발생: {str(e)}", 500
    finally:
        connection.close()

# 4. 집중분석 페이지
@app.route('/control')
@app.route('/control.html')
def control_page():
    return render_template('control.html')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)