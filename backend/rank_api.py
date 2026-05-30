# rank_api.py
# 랭킹 관련 API

import os
import pymysql
from flask import Blueprint, jsonify, session

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
            cur.execute("""
                SELECT
                    u.nickname,
                    COALESCE(SUM(f.focus_score), 0) AS total_score,
                    COALESCE(SUM(f.study_seconds), 0) AS total_seconds
                FROM users u
                LEFT JOIN focus_log f
                    ON u.user_id = f.user_id
                    AND DATE(f.recorded_at) = CURDATE()
                GROUP BY u.user_id, u.nickname
                ORDER BY total_score DESC
                LIMIT 10
            """)
            rows = cur.fetchall()

        result = []
        for i, row in enumerate(rows, start=1):
            mins = row["total_seconds"] // 60
            result.append({
                "rank":          i,
                "nickname":      row["nickname"],
                "score":         int(row["total_score"]),
                "study_time":    f"{mins // 60}h {mins % 60}m"
            })

        return jsonify({"ok": True, "data": result})

    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        conn.close()


# =================================================================
# 내 그룹 랭킹
# GET /api/rank/group
# =================================================================
@rank_bp.route("/group")
def group_rank():
    if "user_id" not in session:
        return jsonify({"ok": False, "message": "로그인이 필요합니다."}), 401

    user_id = session["user_id"]
    conn = get_db()
    try:
        # 내가 속한 그룹 조회
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sg.group_id, sg.name
                FROM group_members gm
                JOIN study_groups sg ON gm.group_id = sg.group_id
                WHERE gm.user_id = %s
                LIMIT 1
            """, (user_id,))
            group = cur.fetchone()

        if not group:
            return jsonify({"ok": True, "group": None, "data": []})

        # 그룹 멤버 랭킹
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    u.nickname,
                    u.user_id,
                    COALESCE(SUM(f.focus_score), 0)   AS total_score,
                    COALESCE(SUM(f.study_seconds), 0) AS total_seconds
                FROM group_members gm
                JOIN users u ON gm.user_id = u.user_id
                LEFT JOIN focus_log f
                    ON u.user_id = f.user_id
                    AND DATE(f.recorded_at) = CURDATE()
                WHERE gm.group_id = %s
                GROUP BY u.user_id, u.nickname
                ORDER BY total_score DESC
            """, (group["group_id"],))
            rows = cur.fetchall()

        result = []
        my_rank = None
        for i, row in enumerate(rows, start=1):
            mins = row["total_seconds"] // 60
            result.append({
                "rank":       i,
                "nickname":   row["nickname"],
                "score":      int(row["total_score"]),
                "study_time": f"{mins // 60}h {mins % 60}m",
                "is_me":      row["user_id"] == user_id
            })
            if row["user_id"] == user_id:
                my_rank = i

        return jsonify({
            "ok":       True,
            "group":    {"id": group["group_id"], "name": group["name"]},
            "my_rank":  my_rank,
            "data":     result
        })

    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        conn.close()


# =================================================================
# 내 오늘 점수 및 전체 순위
# GET /api/rank/me
# =================================================================
@rank_bp.route("/me")
def my_rank():
    if "user_id" not in session:
        return jsonify({"ok": False, "message": "로그인이 필요합니다."}), 401

    user_id = session["user_id"]
    conn = get_db()
    try:
        # 오늘 내 점수
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(SUM(focus_score), 0)   AS my_score,
                       COALESCE(SUM(study_seconds), 0) AS my_seconds
                FROM focus_log
                WHERE user_id = %s AND DATE(recorded_at) = CURDATE()
            """, (user_id,))
            me = cur.fetchone()

        # 전체 순위
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) + 1 AS my_global_rank
                FROM (
                    SELECT user_id, SUM(focus_score) AS total_score
                    FROM focus_log
                    WHERE DATE(recorded_at) = CURDATE()
                    GROUP BY user_id
                ) t
                WHERE t.total_score > %s
            """, (me["my_score"],))
            rank_row = cur.fetchone()

        mins = me["my_seconds"] // 60

        return jsonify({
            "ok":          True,
            "score":       int(me["my_score"]),
            "study_time":  f"{mins // 60}h {mins % 60}m",
            "global_rank": rank_row["my_global_rank"]
        })

    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        conn.close()