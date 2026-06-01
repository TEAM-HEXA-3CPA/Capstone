# rank_api.py
# 실시간 DB 테이블 순번(id) 매칭 및 동적 파라미터 연동을 반영한 최종 랭킹 API

import os
import pymysql
from flask import Blueprint, jsonify, session, request  # 👈 [교정] request 임포트 추가

rank_bp = Blueprint("rank", __name__, url_prefix="/api/rank")

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


# =================================================================
# 전체 랭킹 TOP 10
# GET /api/rank/global
# =================================================================
@rank_bp.route("/global")
def global_rank():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            # LEFT JOIN으로 변경하여 회원 테이블에 ID가 없어도 랭킹은 무조건 끄집어냅니다.
            cur.execute("""
                SELECT 
                    COALESCE(u.nickname, CONCAT('미등록 회원(ID:', r.user_id, ')')) AS nickname, 
                    COALESCE(u.user_id, 'none') AS string_id,
                    r.total_score, 
                    r.total_study_time
                FROM user_rankings r
                LEFT JOIN users u ON r.user_id = u.id
                ORDER BY r.total_score DESC
                LIMIT 10
            """)
            rows = cur.fetchall()

        result = []
        for i, row in enumerate(rows, start=1):
            time_val = row["total_study_time"]
            time_str = f"{time_val}h" if isinstance(time_val, (int, float)) else str(time_val)

            result.append({
                "rank":          i,
                "nickname":      row["nickname"],
                "string_id":     row["string_id"],
                "score":         int(row["total_score"]),
                "study_time":    time_str
            })

        response = jsonify({"ok": True, "data": result})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    except Exception as e:
        response = jsonify({"ok": False, "message": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500
    finally:
        conn.close()


# =================================================================
# 내 그룹 랭킹
# GET /api/rank/group?user_id=아이디
# =================================================================
@rank_bp.route("/group")
def group_rank():
    # 🎯 [교정] 하드코딩 12를 지우고, URL 매개변수에서 로그인한 유저의 진짜 아이디를 읽어옵니다.
    user_id = request.args.get("user_id")
    
    if not user_id:
        response = jsonify({"ok": False, "message": "로그인이 필요하거나 유저 ID가 누락되었습니다."})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 401

    conn = get_db()
    try:
        # 내가 속한 그룹 조회 (전달받은 문자열 아이디 혹은 고유 숫자로 모두 조회 가능하도록 분기)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sg.group_id, sg.name
                FROM group_members gm
                JOIN study_groups sg ON gm.group_id = sg.group_id
                JOIN users u ON gm.user_id = u.id
                WHERE u.user_id = %s OR u.id = %s
                LIMIT 1
            """, (user_id, user_id))
            group = cur.fetchone()

        if not group:
            response = jsonify({"ok": True, "group": None, "data": []})
            response.headers.add("Access-Control-Allow-Origin", "*")
            return response

        # 그룹 멤버 랭킹 조회
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    u.nickname, 
                    u.user_id AS string_id,
                    COALESCE(r.total_score, 0) AS total_score, 
                    COALESCE(r.total_study_time, 0) AS total_study_time
                FROM group_members gm
                JOIN users u ON gm.user_id = u.id
                LEFT JOIN user_rankings r ON u.id = r.user_id
                WHERE gm.group_id = %s
                ORDER BY total_score DESC
            """, (group["group_id"],))
            rows = cur.fetchall()

        result = []
        my_rank = None
        for i, row in enumerate(rows, start=1):
            time_val = row["total_study_time"]
            time_str = f"{time_val}h" if isinstance(time_val, (int, float)) else str(time_val)

            # 문자열 아이디(string_id) 혹은 순번 고유번호(id) 중 하나라도 일치하면 본인 하이라이트 처리
            is_me_check = (row["string_id"] == user_id or str(user_id) == str(row["string_id"]))
            result.append({
                "rank":       i,
                "nickname":   row["nickname"],
                "string_id":  row["string_id"],
                "score":      int(row["total_score"]),
                "study_time": time_str,
                "is_me":      is_me_check
            })
            if is_me_check:
                my_rank = i

        response = jsonify({
            "ok":       True,
            "group":    {"id": group["group_id"], "name": group["name"]},
            "my_rank":  my_rank,
            "data":     result
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    except Exception as e:
        response = jsonify({"ok": False, "message": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500
    finally:
        conn.close()


# =================================================================
# 내 오늘 점수 및 전체 순위
# GET /api/rank/me?user_id=아이디
# =================================================================
@rank_bp.route("/me")
def my_rank():
    # 🎯 [교정] 하드코딩 12를 지우고, URL 매개변수에서 로그인한 유저의 진짜 아이디를 읽어옵니다.
    user_id = request.args.get("user_id")
    
    if not user_id:
        response = jsonify({"ok": False, "message": "로그인이 필요하거나 유저 ID가 누락되었습니다."})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 401

    conn = get_db()
    try:
        # 내 누적 점수 조회
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    COALESCE(r.total_score, 0) AS my_score,
                    COALESCE(r.total_study_time, 0) AS my_time
                FROM users u
                LEFT JOIN user_rankings r ON u.id = r.user_id
                WHERE u.user_id = %s OR u.id = %s
            """, (user_id, user_id))
            me = cur.fetchone()

        if not me:
            me = {"my_score": 0, "my_time": 0}

        # 전체 순위 계산
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) + 1 AS my_global_rank
                FROM user_rankings
                WHERE total_score > %s
            """, (me["my_score"],))
            rank_row = cur.fetchone()

        time_val = me["my_time"]
        time_str = f"{time_val}h" if isinstance(time_val, (int, float)) else str(time_val)

        response = jsonify({
            "ok":          True,
            "score":       int(me["my_score"]),
            "study_time":  time_str,
            "global_rank": rank_row["my_global_rank"]
        })
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    except Exception as e:
        response = jsonify({"ok": False, "message": str(e)})
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response, 500
    finally:
        conn.close()