from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from database.db import get_connection
from models.schemas import RecommendationInput
from services.recommendation_service import build_recommendation
from utils.helpers import safe_json_payload


chat_bp = Blueprint("chat", __name__)


@chat_bp.post("/chatbot")
def chatbot():
    payload = safe_json_payload(request.get_json(silent=True))
    message = str(payload.get("message", "")).strip()
    if not message:
        return jsonify({"status": "error", "message": "Message is required"}), 400

    severity = "medium"
    lowered = message.lower()
    if any(token in lowered for token in ["urgent", "emergency", "severe", "high"]):
        severity = "high"
    elif any(token in lowered for token in ["mild", "small", "low"]):
        severity = "low"

    recommendation_input = RecommendationInput(
        symptoms=message,
        disease="",
        severity=severity,
        city=str(payload.get("city", "")).strip(),
        latitude=float(payload["latitude"]) if payload.get("latitude") not in (None, "") else None,
        longitude=float(payload["longitude"]) if payload.get("longitude") not in (None, "") else None,
        language=str(payload.get("language", "en")).strip().lower() or "en",
    )
    conn = get_connection()
    result = build_recommendation(conn, session.get("user_id"), recommendation_input)
    return jsonify(result)
