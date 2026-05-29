import os
import pymysql
from flask import Flask, request, redirect

app = Flask(__name__)

DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_USER = os.environ.get("DB_USER", "admin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
DB_NAME = os.environ.get("DB_NAME", "hexa")
DB_PORT = 3306


def get_db_connection():
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=DB_PORT,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor
    )


@app.route("/signup", methods=["POST"])
def signup():
    name = request.form.get("name")
    phone = request.form.get("phone")
    nickname = request.form.get("nickname")
    user_id = request.form.get("user_id")
    password = request.form.get("password")

    dummy_email = f"{user_id}@test.com"

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO users
                (
                    user_id,
                    password,
                    name,
                    phone,
                    nickname,
                    email
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    %s,
                    %s
                )
            """

            cursor.execute(
                sql,
                (
                    user_id,
                    password,
                    name,
                    phone,
                    nickname,
                    dummy_email
                )
            )

        connection.commit()

        return redirect("/control.html")

    except pymysql.err.IntegrityError:
        return """
        <script>
        alert('이미 존재하는 아이디입니다.');
        history.back();
        </script>
        """

    except Exception as e:
        return f"서버 에러 발생: {str(e)}", 500

    finally:
        connection.close()


@app.route("/login", methods=["POST"])
def login():
    user_id = request.form.get("user_id")
    password = request.form.get("password")

    connection = get_db_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
                SELECT *
                FROM users
                WHERE user_id = %s
                AND password = %s
            """

            cursor.execute(
                sql,
                (
                    user_id,
                    password
                )
            )

            user = cursor.fetchone()

        if user:
            return redirect("/control.html")

        return """
        <script>
        alert('아이디 또는 비밀번호가 올바르지 않습니다.');
        history.back();
        </script>
        """

    except Exception as e:
        return f"서버 에러 발생: {str(e)}", 500

    finally:
        connection.close()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )