from __future__ import annotations

from flask import Blueprint, jsonify, session

from database.db import fetch_all, get_connection
from services.appointment_service import list_appointments


history_bp = Blueprint("history", __name__)


@history_bp.get("/history")
def history():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Login required"}), 401

    conn = get_connection()
    search_history = fetch_all(
        conn,
        """
        SELECT uh.*, h.name AS hospital_name, h.city AS hospital_city
        FROM user_history uh
        LEFT JOIN hospitals h ON h.id = uh.hospital_id
        WHERE uh.user_id=?
        ORDER BY uh.created_at DESC, uh.id DESC
        """,
        (int(user_id),),
    )
    appointments = list_appointments(conn, int(user_id))
    return jsonify({"status": "success", "search_history": search_history, "appointments": appointments})
