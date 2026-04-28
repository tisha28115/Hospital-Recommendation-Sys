from __future__ import annotations

import os
import json
import re
from typing import Any

try:
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None


class LLMEngine:
    """
    Optional LLM integration point.

    This project runs offline by default; plug in Gemini/OpenAI/etc here if desired.
    """

    def __init__(self) -> None:
        self.provider = (os.getenv("LLM_PROVIDER") or "gemini").lower()
        self.api_key = os.getenv("GEMINI_API_KEY") or os.getenv("LLM_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    def available(self) -> bool:
        return bool(self.provider == "gemini" and self.api_key and genai)

    def chat(self, messages: list[dict[str, Any]]) -> str:
        if not self.available():
            raise RuntimeError("Gemini not available. Install google-generativeai and set GEMINI_API_KEY.")
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        # Very small adapter: concatenate into a single prompt
        prompt = "\n".join([f"{m.get('role','user')}: {m.get('content','')}" for m in messages])
        resp = model.generate_content(prompt)
        return getattr(resp, "text", "") or ""

    def _model(self):
        if not self.available():
            raise RuntimeError("Gemini not available.")
        genai.configure(api_key=self.api_key)
        return genai.GenerativeModel(self.model_name)

    def analyze_for_routing(self, user_text: str) -> dict[str, Any]:
        """
        Returns a small, non-diagnostic JSON-ish dict used for routing:
        - specialization: department/specialty name
        - urgency: mild/moderate/severe/emergency
        """
        if not self.available():
            return {}

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        prompt = (
            "You are a healthcare appointment assistant. Do NOT diagnose.\n"
            "Given the user's message, choose the best department/specialization to consult and an urgency level.\n"
            "Return ONLY JSON with keys: specialization, urgency.\n"
            "Allowed urgency values: mild, moderate, severe, emergency.\n"
            f"User message: {user_text}\n"
        )
        try:
            resp = model.generate_content(prompt)
            text = getattr(resp, "text", "") or ""
        except Exception:
            return {}

        # Light parsing without depending on strict JSON from the model.
        out: dict[str, Any] = {}
        lower = text.lower()
        for u in ["mild", "moderate", "severe", "emergency"]:
            if f"\"{u}\"" in lower or f": {u}" in lower:
                out["urgency"] = u
                break
        for s in [
            "Cardiology",
            "Neurology",
            "Dermatology",
            "Gastroenterology",
            "Orthopedics",
            "ENT",
            "General Medicine",
        ]:
            if s.lower() in lower:
                out["specialization"] = s
                break
        return out

    def classify_intent(self, *, user_text: str, stage: str, user_known: bool) -> dict[str, Any]:
        """
        Lightweight intent/entity extraction to drive the deterministic workflow.

        Returns a dict with keys:
          - intent: chat|goodbye|thanks|cancel|reschedule|check_slots|list_appointments|last_doctor|search_doctor
          - patient_type: first|returning (optional)
          - time: HH:MM (optional)
          - doctor_query: string (optional)
        """
        if not self.available():
            return {}

        allowed = [
            "chat",
            "goodbye",
            "thanks",
            "cancel",
            "reschedule",
            "check_slots",
            "list_appointments",
            "last_doctor",
            "search_doctor",
        ]
        prompt = (
            "You are an appointment assistant. Do NOT diagnose.\n"
            "Extract the user's intent to help route a booking workflow.\n"
            "Return ONLY valid JSON with keys: intent, patient_type, time, doctor_query.\n"
            f"Allowed intent values: {allowed}\n"
            "patient_type must be one of: first, returning, or null.\n"
            "time must be in 24h HH:MM if present, else null.\n"
            f"Current stage: {stage}\n"
            f"User already identified: {str(bool(user_known)).lower()}\n"
            f"User message: {user_text}\n"
        )

        try:
            text = getattr(self._model().generate_content(prompt), "text", "") or ""
        except Exception:
            return {}

        # Extract a JSON object from the response.
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return {}
        try:
            obj = json.loads(m.group(0))
        except Exception:
            return {}

        if isinstance(obj, dict) and obj.get("intent") in allowed:
            return obj
        return {}
