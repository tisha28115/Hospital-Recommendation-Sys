from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from database.db import get_connection
from services.auth_service import (
    authenticate_admin,
    authenticate_user,
    create_or_sync_firebase_user,
    create_user,
    get_admin_by_id,
    get_user_by_id,
)
from services.firebase_auth_service import verify_firebase_token
from utils.helpers import safe_json_payload


auth_bp = Blueprint("auth", __name__)


@auth_bp.post("/signup")
def signup():
    payload = safe_json_payload(request.get_json(silent=True))
    if payload.get("id_token"):
        try:
            decoded_token = verify_firebase_token(str(payload.get("id_token", "")))
            user = create_or_sync_firebase_user(
                get_connection(),
                firebase_uid=str(decoded_token.get("uid", "")).strip(),
                email=str(decoded_token.get("email", "")).strip().lower(),
                name=str(payload.get("name") or decoded_token.get("name") or ""),
                city=str(payload.get("city", "")).strip(),
                language=str(payload.get("language", "en")).strip().lower() or "en",
            )
        except Exception as exc:
            return jsonify({"status": "error", "message": f"Firebase signup failed: {exc}"}), 400

        session["user_id"] = int(user["id"])
        session["role"] = "user"
        session.pop("admin_id", None)
        return jsonify({"status": "success", "user": user})

    required = ["name", "email", "password"]
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        return jsonify({"status": "error", "message": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_connection()
    try:
        user = create_user(
            conn,
            name=str(payload["name"]).strip(),
            email=str(payload["email"]).strip().lower(),
            password=str(payload["password"]),
            city=str(payload.get("city", "")).strip(),
            language=str(payload.get("language", "en")).strip().lower() or "en",
        )
    except Exception as exc:
        return jsonify({"status": "error", "message": f"Signup failed: {exc}"}), 400

    session["user_id"] = int(user["id"])
    session["role"] = "user"
    session.pop("admin_id", None)
    return jsonify({"status": "success", "user": user})


@auth_bp.post("/login")
def login():
    payload = safe_json_payload(request.get_json(silent=True))
    if payload.get("id_token"):
        try:
            decoded_token = verify_firebase_token(str(payload.get("id_token", "")))
            if not bool(decoded_token.get("email_verified")):
                return jsonify({"status": "error", "message": "Verify your email before logging in."}), 403
            user = create_or_sync_firebase_user(
                get_connection(),
                firebase_uid=str(decoded_token.get("uid", "")).strip(),
                email=str(decoded_token.get("email", "")).strip().lower(),
                name=str(decoded_token.get("name", "")),
                city=str(payload.get("city", "")).strip(),
                language=str(payload.get("language", "en")).strip().lower() or "en",
            )
        except Exception as exc:
            return jsonify({"status": "error", "message": f"Firebase login failed: {exc}"}), 401

        session["user_id"] = int(user["id"])
        session["role"] = "user"
        session.pop("admin_id", None)
        return jsonify({"status": "success", "user": user})

    conn = get_connection()
    user = authenticate_user(
        conn,
        email=str(payload.get("email", "")).strip().lower(),
        password=str(payload.get("password", "")),
    )
    if not user:
        return jsonify({"status": "error", "message": "Invalid email or password"}), 401
    session["user_id"] = int(user["id"])
    session["role"] = "user"
    session.pop("admin_id", None)
    return jsonify({"status": "success", "user": user})


@auth_bp.post("/admin/login")
def admin_login():
    payload = safe_json_payload(request.get_json(silent=True))
    conn = get_connection()
    admin = authenticate_admin(
        conn,
        username=str(payload.get("username", "")).strip().lower(),
        password=str(payload.get("password", "")),
    )
    if not admin:
        return jsonify({"status": "error", "message": "Invalid admin username or password"}), 401
    session.clear()
    session["admin_id"] = int(admin["id"])
    session["role"] = "admin"
    return jsonify({"status": "success", "admin": admin})


@auth_bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"status": "success"})


@auth_bp.get("/me")
def me():
    role = session.get("role")
    if role == "admin":
        admin_id = session.get("admin_id")
        if not admin_id:
            return jsonify({"status": "success", "role": None, "user": None})
        conn = get_connection()
        return jsonify({"status": "success", "role": "admin", "admin": get_admin_by_id(conn, int(admin_id))})

    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "success", "role": None, "user": None})
    conn = get_connection()
    return jsonify({"status": "success", "role": "user", "user": get_user_by_id(conn, int(user_id))})
