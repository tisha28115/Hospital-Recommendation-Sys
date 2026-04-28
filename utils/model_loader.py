from __future__ import annotations

import os
import pickle
from functools import lru_cache
from typing import Any

from config import settings

try:
    import joblib  # type: ignore
except Exception:  # pragma: no cover
    joblib = None

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None


@lru_cache(maxsize=1)
def load_model() -> Any | None:
    model_path = settings.model_path
    if not model_path or not os.path.exists(model_path):
        return None
    if joblib:
        try:
            return joblib.load(model_path)
        except Exception:
            pass
    with open(model_path, "rb") as file_obj:
        return pickle.load(file_obj)


def predict_with_model(*, disease: str, severity: str, symptoms: str) -> str | None:
    model = load_model()
    if model is None or not hasattr(model, "predict"):
        return None

    if pd is not None and hasattr(model, "feature_names_in_"):
        row = {feature: "" for feature in list(getattr(model, "feature_names_in_", []))}
        for key in row:
            lowered = key.lower()
            if "disease" in lowered:
                row[key] = disease
            elif "severity" in lowered:
                row[key] = severity
            elif "symptom" in lowered:
                row[key] = symptoms
        try:
            prediction = model.predict(pd.DataFrame([row]))
            return str(prediction[0]) if len(prediction) else None
        except Exception:
            pass

    payloads = [
        [[disease, severity]],
        [[symptoms, severity]],
        [[disease, symptoms, severity]],
    ]
    for payload in payloads:
        try:
            prediction = model.predict(payload)
            return str(prediction[0]) if len(prediction) else None
        except Exception:
            continue
    return None
