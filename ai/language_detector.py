from __future__ import annotations

import re


def detect_language(text: str) -> str:
    """
    Lightweight, offline language detection.

    Returns ISO-ish codes used by googletrans: en, hi, etc.
    """
    if not text:
        return "en"

    # Hindi/Devanagari
    if re.search(r"[\u0900-\u097F]", text):
        return "hi"

    # Basic heuristic for English
    if re.search(r"[A-Za-z]", text):
        return "en"

    return "en"

