import os
import pymysql
from flask import Blueprint, jsonify
from auth import login_required

rank_bp = Blueprint("rank", __name__, url_prefix="/api/rank")

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


@rank_bp.route("/global")
def global_rank():
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(u.nickname, CONCAT('미등록(', r.user_id, ')')) AS nickname,
                       COALESCE(u.user_id, 'none') AS string_id,
                       r.total_score, r.total_study_time
                FROM user_rankings r
                LEFT JOIN users u ON r.user_id = u.id
                ORDER BY r.total_score DESC LIMIT 10
            """)
            rows = cur.fetchall()
        result = []
        for i, row in enumerate(rows, start=1):
            time_val = row["total_study_time"]
            result.append({
                "rank":       i,
                "nickname":   row["nickname"],
                "string_id":  row["string_id"],
                "score":      int(row["total_score"]),
                "study_time": f"{time_val}h" if isinstance(time_val, (int, float)) else str(time_val)
            })
        return jsonify({"ok": True, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        conn.close()


@rank_bp.route("/group")
def group_rank():
    payload, err = login_required()
    if err: return err
    user_id = payload["user_id"]
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sg.group_id, sg.name
                FROM group_members gm
                JOIN study_groups sg ON gm.group_id = sg.group_id
                JOIN users u ON gm.user_id = u.id
                WHERE u.user_id = %s LIMIT 1
            """, (user_id,))
            group = cur.fetchone()
        if not group:
            return jsonify({"ok": True, "group": None, "data": []})
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.nickname, u.user_id AS string_id,
                       COALESCE(r.total_score, 0) AS total_score,
                       COALESCE(r.total_study_time, 0) AS total_study_time
                FROM group_members gm
                JOIN users u ON gm.user_id = u.id
                LEFT JOIN user_rankings r ON u.id = r.user_id
                WHERE gm.group_id = %s ORDER BY total_score DESC
            """, (group["group_id"],))
            rows = cur.fetchall()
        result  = []
        my_rank = None
        for i, row in enumerate(rows, start=1):
            is_me    = row["string_id"] == user_id
            time_val = row["total_study_time"]
            result.append({
                "rank":       i,
                "nickname":   row["nickname"],
                "string_id":  row["string_id"],
                "score":      int(row["total_score"]),
                "study_time": f"{time_val}h" if isinstance(time_val, (int, float)) else str(time_val),
                "is_me":      is_me
            })
            if is_me: my_rank = i
        return jsonify({"ok": True, "group": {"id": group["group_id"], "name": group["name"]},
                        "my_rank": my_rank, "data": result})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        conn.close()


@rank_bp.route("/me")
def my_rank():
    payload, err = login_required()
    if err: return err
    user_id = payload["user_id"]
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COALESCE(r.total_score, 0) AS my_score,
                       COALESCE(r.total_study_time, 0) AS my_time
                FROM users u
                LEFT JOIN user_rankings r ON u.id = r.user_id
                WHERE u.user_id = %s
            """, (user_id,))
            me = cur.fetchone() or {"my_score": 0, "my_time": 0}
            cur.execute("SELECT COUNT(*)+1 AS my_global_rank FROM user_rankings WHERE total_score > %s",
                        (me["my_score"],))
            rank_row = cur.fetchone()
        time_val = me["my_time"]
        return jsonify({
            "ok":          True,
            "score":       int(me["my_score"]),
            "study_time":  f"{time_val}h" if isinstance(time_val, (int, float)) else str(time_val),
            "global_rank": rank_row["my_global_rank"]
        })
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 500
    finally:
        conn.close()