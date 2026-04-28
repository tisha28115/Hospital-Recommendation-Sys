from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SymptomAnalysis:
    normalized_symptoms: str
    probable_category: str
    matched_keywords: list[str]


_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "Cardiology": [
        "chest pain",
        "chest tightness",
        "palpitations",
        "shortness of breath",
        "breathing issue",
        "breathless",
        "high bp",
        "blood pressure",
        "hypertension",
        "heart",
    ],
    "Neurology": ["migraine", "headache", "head pain", "seizure", "dizziness", "vertigo", "numbness", "tingling"],
    "Dermatology": ["rash", "itching", "itch", "acne", "skin", "eczema", "allergy", "hives"],
    "Gastroenterology": [
        "stomach pain",
        "abdominal pain",
        "diarrhea",
        "vomiting",
        "nausea",
        "acid reflux",
        "acidity",
        "gas",
        "constipation",
        "indigestion",
    ],
    "Orthopedics": ["back pain", "knee pain", "fracture", "joint pain", "shoulder pain", "neck pain", "sprain"],
    "ENT": ["ear pain", "earache", "sore throat", "throat pain", "sinus", "nose bleed", "blocked nose"],
    "General Medicine": ["fever", "cold", "cough", "tired", "fatigue", "body ache", "weakness"],
}


def analyze_symptoms(user_text: str) -> SymptomAnalysis:
    text = (user_text or "").strip()
    t = text.lower()

    best_category = "General Medicine"
    best_hits: list[str] = []
    for category, keywords in _CATEGORY_KEYWORDS.items():
        hits = [k for k in keywords if k in t]
        if len(hits) > len(best_hits):
            best_category = category
            best_hits = hits

    return SymptomAnalysis(normalized_symptoms=text, probable_category=best_category, matched_keywords=best_hits)
