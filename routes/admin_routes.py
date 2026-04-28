from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from database.db import get_connection
from services.admin_service import create_hospital, delete_hospital, get_stats, list_hospitals, update_hospital
from utils.helpers import safe_json_payload


admin_bp = Blueprint("admin", __name__, url_prefix="/admin_api")


def _ensure_admin() -> tuple[bool, tuple[dict[str, str], int] | None]:
    if session.get("role") != "admin" or not session.get("admin_id"):
        return False, ({"status": "error", "message": "Admin access required"}, 403)
    return True, None


@admin_bp.get("/stats")
def admin_stats():
    ok, error = _ensure_admin()
    if not ok:
        return jsonify(error[0]), error[1]
    conn = get_connection()
    return jsonify({"status": "success", "stats": get_stats(conn), "hospitals": list_hospitals(conn)})


@admin_bp.post("/hospitals")
def admin_create_hospital():
    ok, error = _ensure_admin()
    if not ok:
        return jsonify(error[0]), error[1]
    payload = safe_json_payload(request.get_json(silent=True))
    conn = get_connection()
    return jsonify({"status": "success", "hospital": create_hospital(conn, payload)})


@admin_bp.put("/hospitals/<int:hospital_id>")
def admin_update_hospital(hospital_id: int):
    ok, error = _ensure_admin()
    if not ok:
        return jsonify(error[0]), error[1]
    payload = safe_json_payload(request.get_json(silent=True))
    conn = get_connection()
    return jsonify({"status": "success", "hospital": update_hospital(conn, hospital_id, payload)})


@admin_bp.delete("/hospitals/<int:hospital_id>")
def admin_delete_hospital(hospital_id: int):
    ok, error = _ensure_admin()
    if not ok:
        return jsonify(error[0]), error[1]
    conn = get_connection()
    delete_hospital(conn, hospital_id)
    return jsonify({"status": "success"})
