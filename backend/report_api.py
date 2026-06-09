import os
import pymysql
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from auth import login_required

report_bp = Blueprint("report", __name__, url_prefix="/api/report")

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


@report_bp.route("/weekly")
def weekly_report():
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
            real_user_id   = user_record["id"]
            seven_days_ago = datetime.now() - timedelta(days=7)
            cur.execute("""
                SELECT start_time, end_time, avg_focus_score, drowsy_count, away_count
                FROM focus_summary_logs
                WHERE user_id = %s AND start_time >= %s
                ORDER BY start_time ASC
            """, (real_user_id, seven_days_ago))
            rows = cur.fetchall()

        if not rows:
            return jsonify({"ok": True, "data": [], "summary": {
                "avg_score": 0, "total_sessions": 0, "total_drowsy": 0, "total_away": 0
            }})

        today = datetime.now().date()

        def day_label(dt):
            diff = (today - dt.date()).days
            if diff == 0: return "오늘"
            if diff == 1: return "1일 전"
            return f"{diff}일 전"

        def time_label(dt):
            h  = dt.hour
            hm = dt.strftime("%H:%M")
            if   5 <= h < 12:  prefix = "오전"
            elif 12 <= h < 18: prefix = "오후"
            elif 18 <= h < 22: prefix = "저녁"
            else:               prefix = "심야"
            return f"{prefix} {hm}"

        sessions_data = []
        for row in rows:
            start = row["start_time"]
            if isinstance(start, str):
                start = datetime.fromisoformat(start)
            sessions_data.append({
                "day":    day_label(start),
                "time":   time_label(start),
                "score":  round(float(row["avg_focus_score"])),
                "drowsy": int(row["drowsy_count"]),
                "away":   int(row["away_count"]),
            })

        total   = len(sessions_data)
        summary = {
            "avg_score":      round(sum(s["score"]  for s in sessions_data) / total),
            "total_sessions": total,
            "total_drowsy":   sum(s["drowsy"] for s in sessions_data),
            "total_away":     sum(s["away"]   for s in sessions_data),
        }
        return jsonify({"ok": True, "data": sessions_data, "summary": summary})
    except Exception as e:
        return jsonify({"ok": False, "message": f"서버 에러: {str(e)}"}), 500
    finally:
        conn.close()