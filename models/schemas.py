from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


VALID_SEVERITIES = {"low", "medium", "high"}


@dataclass
class RecommendationInput:
    symptoms: str
    disease: str
    severity: str
    city: str
    latitude: float | None
    longitude: float | None
    language: str

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "RecommendationInput":
        severity = str(payload.get("severity", "medium")).strip().lower()
        if severity not in VALID_SEVERITIES:
            severity = "medium"
        latitude = payload.get("latitude")
        longitude = payload.get("longitude")
        city = str(payload.get("location", payload.get("city", ""))).strip()
        return cls(
            symptoms=str(payload.get("symptoms", "")).strip(),
            disease=str(payload.get("disease", "")).strip(),
            severity=severity,
            city=city,
            latitude=float(latitude) if latitude not in (None, "") else None,
            longitude=float(longitude) if longitude not in (None, "") else None,
            language=str(payload.get("language", "en")).strip().lower() or "en",
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
