from __future__ import annotations

import math
import re
from typing import Any


CITY_COORDINATES: dict[str, tuple[float, float]] = {
    "ahmedabad": (23.0225, 72.5714),
    "vadodara": (22.3072, 73.1812),
    "mumbai": (19.0760, 72.8777),
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "pune": (18.5204, 73.8567),
}

CITY_ALIASES: dict[str, str] = {
    "ahmedabad": "ahmedabad",
    "ahemdabad": "ahmedabad",
    "amdavad": "ahmedabad",
    "vadodara": "vadodara",
    "baroda": "vadodara",
    "mumbai": "mumbai",
    "bombay": "mumbai",
    "delhi": "delhi",
    "new delhi": "delhi",
    "bengaluru": "bengaluru",
    "bangalore": "bengaluru",
    "pune": "pune",
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def canonicalize_city_name(city: str) -> str:
    normalized = normalize_text(city).lower()
    return CITY_ALIASES.get(normalized, normalized)


def haversine_distance_km(
    latitude_a: float | None,
    longitude_a: float | None,
    latitude_b: float | None,
    longitude_b: float | None,
) -> float | None:
    if None in (latitude_a, longitude_a, latitude_b, longitude_b):
        return None
    earth_radius_km = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [latitude_a, longitude_a, latitude_b, longitude_b])
    lat_delta = lat2 - lat1
    lon_delta = lon2 - lon1
    step = math.sin(lat_delta / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(lon_delta / 2) ** 2
    return round(2 * earth_radius_km * math.asin(math.sqrt(step)), 2)


def resolve_user_coordinates(city: str, latitude: float | None, longitude: float | None) -> tuple[float | None, float | None]:
    if latitude is not None and longitude is not None:
        return latitude, longitude
    coords = CITY_COORDINATES.get(canonicalize_city_name(city))
    return coords if coords else (None, None)


def safe_json_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    return payload if isinstance(payload, dict) else {}
