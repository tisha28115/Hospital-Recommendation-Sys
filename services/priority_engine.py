from __future__ import annotations

from dataclasses import dataclass

from utils.severity_classifier import SeverityResult, classify_severity


@dataclass(frozen=True)
class PriorityDecision:
    severity: SeverityResult
    wins_over_existing: bool


def decide_priority(symptoms_text: str, existing_severity: int | None = None) -> PriorityDecision:
    severity = classify_severity(symptoms_text)
    if existing_severity is None:
        return PriorityDecision(severity=severity, wins_over_existing=True)
    return PriorityDecision(severity=severity, wins_over_existing=severity.level > int(existing_severity))
