from __future__ import annotations

import json
from typing import Any

from config import settings
from database.db import execute, fetch_all, fetch_one
from models.schemas import RecommendationInput
from utils.helpers import canonicalize_city_name, haversine_distance_km, normalize_text, resolve_user_coordinates
from utils.model_loader import predict_with_model
from utils.translator import translate_label


SYMPTOM_TO_DISEASE = {
    "fever": "flu",
    "headache": "migraine",
    "chest pain": "heart attack",
    "breathlessness": "heart attack",
    "skin rash": "skin rash",
    "itching": "skin rash",
    "fracture": "fracture",
    "swelling": "bone pain",
    "stomach pain": "stomach pain",
    "acidity": "acidity",
    "vomiting": "stomach pain",
}

DISEASE_TO_DEPARTMENT = {
    "flu": "General Medicine",
    "fever": "General Medicine",
    "migraine": "Neurology",
    "stroke": "Neurology",
    "heart attack": "Cardiology",
    "chest pain": "Cardiology",
    "fracture": "Orthopedics",
    "bone pain": "Orthopedics",
    "skin rash": "Dermatology",
    "acidity": "Gastroenterology",
    "stomach pain": "Gastroenterology",
}

SEVERITY_WEIGHT = {"low": 0.4, "medium": 0.7, "high": 1.0}


def infer_disease(symptoms: str, manual_disease: str) -> str:
    if manual_disease:
        return manual_disease.strip().lower()
    lowered = normalize_text(symptoms).lower()
    for keyword, disease in SYMPTOM_TO_DISEASE.items():
        if keyword in lowered:
            return disease
    return "fever"


def infer_department(conn: Any, disease: str, severity: str, symptoms: str) -> str:
    model_prediction = predict_with_model(disease=disease, severity=severity, symptoms=symptoms)
    if model_prediction:
        cleaned = model_prediction.strip()
        if cleaned in set(DISEASE_TO_DEPARTMENT.values()):
            return cleaned
        disease = cleaned.lower()

    mapping = fetch_one(conn, "SELECT department FROM disease_mapping WHERE lower(disease)=?", (disease.lower(),))
    if mapping:
        return str(mapping["department"])
    return DISEASE_TO_DEPARTMENT.get(disease.lower(), "General Medicine")


def rank_hospitals(
    hospitals: list[dict[str, Any]],
    *,
    department: str,
    severity: str,
    city: str,
    latitude: float | None,
    longitude: float | None,
) -> list[dict[str, Any]]:
    user_lat, user_lng = resolve_user_coordinates(city, latitude, longitude)
    ranked: list[dict[str, Any]] = []
    for hospital in hospitals:
        match_score = 1.0 if hospital["specialization"].lower() == department.lower() else 0.5
        rating_score = float(hospital.get("rating") or 0) / 5
        distance_km = haversine_distance_km(
            user_lat,
            user_lng,
            float(hospital["latitude"]) if hospital.get("latitude") is not None else None,
            float(hospital["longitude"]) if hospital.get("longitude") is not None else None,
        )
        distance_score = 0.5 if distance_km is None else max(0.0, 1 - min(distance_km, 50) / 50)
        emergency_bonus = 0.2 if severity == "high" and int(hospital.get("emergency_services") or 0) == 1 else 0.0
        score = round((match_score * 0.45) + (SEVERITY_WEIGHT[severity] * 0.2) + (rating_score * 0.2) + (distance_score * 0.15) + emergency_bonus, 4)
        hospital_copy = dict(hospital)
        hospital_copy["distance_km"] = distance_km
        hospital_copy["recommendation_score"] = score
        ranked.append(hospital_copy)

    if severity == "high":
        ranked.sort(
            key=lambda hospital: (
                hospital["distance_km"] if hospital["distance_km"] is not None else 9999,
                -int(hospital.get("emergency_services") or 0),
                -float(hospital["recommendation_score"]),
            )
        )
    else:
        ranked.sort(key=lambda hospital: (-float(hospital["recommendation_score"]), hospital["distance_km"] or 9999))
    return ranked[: min(settings.top_k_recommendations, 3)]


def fetch_hospitals_by_location(conn: Any, city: str) -> tuple[list[dict[str, Any]], str, str]:
    normalized_city = canonicalize_city_name(city)
    if not normalized_city:
        hospitals = fetch_all(conn, "SELECT * FROM hospitals ORDER BY rating DESC, name ASC")
        return hospitals, "", "all"

    exact_match = fetch_all(
        conn,
        """
        SELECT *
        FROM hospitals
        WHERE lower(city)=?
        ORDER BY rating DESC, name ASC
        """,
        (normalized_city,),
    )
    if exact_match:
        return exact_match, city, "exact"

    partial_match = fetch_all(
        conn,
        """
        SELECT *
        FROM hospitals
        WHERE lower(city) LIKE ?
        ORDER BY rating DESC, name ASC
        """,
        (f"%{normalized_city}%",),
    )
    if partial_match:
        resolved_city = str(partial_match[0].get("city") or city)
        return partial_match, resolved_city, "partial"

    return [], city, "unmatched"


def resolve_nearest_hospital_city(conn: Any, city: str) -> str | None:
    user_lat, user_lng = resolve_user_coordinates(city, None, None)
    if user_lat is None or user_lng is None:
        return None

    city_rows = fetch_all(
        conn,
        """
        SELECT city, AVG(latitude) AS latitude, AVG(longitude) AS longitude
        FROM hospitals
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
        GROUP BY city
        """
    )
    nearest_city: str | None = None
    nearest_distance: float | None = None
    for row in city_rows:
        distance_km = haversine_distance_km(
            user_lat,
            user_lng,
            float(row["latitude"]) if row.get("latitude") is not None else None,
            float(row["longitude"]) if row.get("longitude") is not None else None,
        )
        if distance_km is None:
            continue
        if nearest_distance is None or distance_km < nearest_distance:
            nearest_distance = distance_km
            nearest_city = str(row["city"])
    return nearest_city


def build_recommendation(conn: Any, user_id: int | None, recommendation_input: RecommendationInput) -> dict[str, Any]:
    disease = infer_disease(recommendation_input.symptoms, recommendation_input.disease)
    department = infer_department(conn, disease, recommendation_input.severity, recommendation_input.symptoms)
    hospitals, resolved_city, location_match_type = fetch_hospitals_by_location(conn, recommendation_input.city)
    if recommendation_input.city and not hospitals:
        return {
            "status": "error",
            "message": f"No hospitals found in or near {recommendation_input.city}. Please try another city.",
            "requested_location": recommendation_input.city,
            "resolved_location": resolved_city or recommendation_input.city,
            "location_match_type": location_match_type,
        }
    top_hospitals = rank_hospitals(
        hospitals,
        department=department,
        severity=recommendation_input.severity,
        city=resolved_city or recommendation_input.city,
        latitude=recommendation_input.latitude,
        longitude=recommendation_input.longitude,
    )

    previous_visits: list[dict[str, Any]] = []
    if user_id:
        previous_visits = fetch_all(
            conn,
            """
            SELECT h.id, h.name, h.city, h.specialization, uh.created_at
            FROM user_history uh
            LEFT JOIN hospitals h ON h.id = uh.hospital_id
            WHERE uh.user_id=? AND h.id IS NOT NULL
            ORDER BY uh.created_at DESC
            LIMIT 5
            """,
            (user_id,),
        )
        execute(
            conn,
            """
            INSERT INTO user_history(user_id, disease, severity, symptoms, hospital_id, city, recommendation_snapshot)
            VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                disease,
                recommendation_input.severity,
                recommendation_input.symptoms,
                int(top_hospitals[0]["id"]) if top_hospitals else None,
                recommendation_input.city,
                json.dumps(top_hospitals),
            ),
        )
        conn.commit()

    return {
        "status": "success",
        "title": translate_label("Top hospital recommendations", recommendation_input.language),
        "summary": translate_label("Recommendation complete", recommendation_input.language),
        "disease": disease.title(),
        "department": department,
        "severity": recommendation_input.severity,
        "requested_location": recommendation_input.city,
        "resolved_location": resolved_city or recommendation_input.city,
        "location_match_type": location_match_type,
        "emergency_mode": recommendation_input.severity == "high",
        "emergency_note": translate_label("Emergency support available", recommendation_input.language) if recommendation_input.severity == "high" else "",
        "recommended_hospitals": top_hospitals,
        "previously_visited_hospitals": previous_visits,
        "chatbot_reply": (
            f"Based on {disease.title()} and {recommendation_input.severity} severity, "
            f"I recommend {department} hospitals in {resolved_city or recommendation_input.city or 'your area'}."
        ),
    }
