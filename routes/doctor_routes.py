from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from database.db import get_connection
from models.schemas import RecommendationInput
from services.recommendation_service import build_recommendation
from utils.helpers import safe_json_payload


recommendation_bp = Blueprint("recommendation", __name__)


@recommendation_bp.post("/recommend")
def recommend():
    payload = safe_json_payload(request.get_json(silent=True))
    recommendation_input = RecommendationInput.from_payload(payload)
    if not recommendation_input.symptoms and not recommendation_input.disease:
        return jsonify({"status": "error", "message": "Provide symptoms or disease"}), 400

    conn = get_connection()
    result = build_recommendation(conn, session.get("user_id"), recommendation_input)
    return jsonify(result)
