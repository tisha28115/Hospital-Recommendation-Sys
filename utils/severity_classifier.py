from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SeverityResult:
    level: int  # 1..4
    label: str  # mild/moderate/severe/emergency
    reasons: list[str]


_EMERGENCY = [
    "chest pain",
    "breathing problem",
    "shortness of breath",
    "unconscious",
    "fainting",
    "severe bleeding",
    "stroke",
    "seizure",
]
_SEVERE = ["high fever", "severe pain", "vomiting blood", "blood in stool", "head injury"]
_MODERATE = ["fever", "migraine", "rash", "infection", "diarrhea", "vomiting", "back pain"]


def _contains_any(text: str, phrases: list[str]) -> list[str]:
    t = (text or "").lower()
    hits: list[str] = []
    for p in phrases:
        if p in t:
            hits.append(p)
    return hits


def classify_severity(user_text: str) -> SeverityResult:
    text = (user_text or "").lower()
    reasons = _contains_any(text, _EMERGENCY)
    if reasons:
        return SeverityResult(level=4, label="emergency", reasons=reasons)

    reasons = _contains_any(text, _SEVERE)
    if reasons:
        return SeverityResult(level=3, label="severe", reasons=reasons)

    reasons = _contains_any(text, _MODERATE)
    if reasons:
        return SeverityResult(level=2, label="moderate", reasons=reasons)

    # Heuristic: lots of exclamation/caps can indicate distress, but never upgrade to emergency.
    if re.search(r"!{2,}", user_text or ""):
        return SeverityResult(level=2, label="moderate", reasons=["distress punctuation"])

    return SeverityResult(level=1, label="mild", reasons=[])
