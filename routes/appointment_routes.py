from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from database.db import get_connection
from services.appointment_service import AppointmentSlotUnavailableError, create_appointment
from services.auth_service import get_user_by_id
from services.email_service import EmailDeliveryError, send_appointment_confirmation_email
from utils.helpers import safe_json_payload


appointment_bp = Blueprint("appointment", __name__)


@appointment_bp.post("/book_appointment")
def book_appointment():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"status": "error", "message": "Login required"}), 401

    payload = safe_json_payload(request.get_json(silent=True))
    required = ["hospital_id", "disease", "department", "severity", "appointment_date", "appointment_time"]
    missing = [field for field in required if not str(payload.get(field, "")).strip()]
    if missing:
        return jsonify({"status": "error", "message": f"Missing fields: {', '.join(missing)}"}), 400

    conn = get_connection()
    try:
        appointment = create_appointment(
            conn,
            user_id=int(user_id),
            hospital_id=int(payload["hospital_id"]),
            disease=str(payload["disease"]).strip(),
            department=str(payload["department"]).strip(),
            severity=str(payload["severity"]).strip().lower(),
            appointment_date=str(payload["appointment_date"]).strip(),
            appointment_time=str(payload["appointment_time"]).strip(),
        )
    except AppointmentSlotUnavailableError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 409
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400

    user = get_user_by_id(conn, int(user_id)) or {}
    email_sent = False
    email_message = ""
    recipient_email = str(user.get("email", "")).strip()
    if recipient_email:
        try:
            send_appointment_confirmation_email(
                recipient_email=recipient_email,
                recipient_name=str(user.get("name", "")).strip(),
                appointment=appointment,
            )
            email_sent = True
        except EmailDeliveryError as exc:
            email_message = str(exc)
    else:
        email_message = "No user email address is available for appointment confirmation."

    response_message = "Your booking is confirmed."
    if email_sent:
        response_message += " A confirmation email has been sent."
    elif email_message:
        response_message += f" Booking saved, but email was not sent: {email_message}"

    return jsonify(
        {
            "status": "success",
            "message": response_message,
            "email_sent": email_sent,
            "email_message": email_message,
            "appointment": appointment,
        }
    )
