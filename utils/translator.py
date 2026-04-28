from __future__ import annotations

TRANSLATIONS = {
    "hi": {
        "Top hospital recommendations": "शीर्ष अस्पताल सुझाव",
        "Emergency support available": "आपातकालीन सुविधा उपलब्ध",
        "Previously visited hospitals": "पहले देखे गए अस्पताल",
        "Recommendation complete": "सिफारिश पूरी हुई",
    }
}


def translate_label(text: str, language: str) -> str:
    language = (language or "en").lower()
    if language == "en":
        return text
    return TRANSLATIONS.get(language, {}).get(text, text)
