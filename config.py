from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / "v.env"


def _load_env_file() -> None:
    if not ENV_FILE.is_file():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_env_file()


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI Hospital Recommendation Assistant"
    secret_key: str = os.getenv("SECRET_KEY", "change-this-secret-key")
    db_engine: str = os.getenv("DB_ENGINE", "sqlite").lower()
    db_path: str = os.getenv("APP_DB_PATH", str(BASE_DIR / "database" / "app.db"))
    firebase_project_id: str = os.getenv("FIREBASE_PROJECT_ID", "hospital-recommendation-9d085")
    firebase_service_account_path: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH", "")
    mysql_host: str = os.getenv("MYSQL_HOST", "localhost")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_user: str = os.getenv("MYSQL_USER", "root")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "")
    mysql_database: str = os.getenv("MYSQL_DATABASE", "hospital_recommendation")
    seed_data: bool = os.getenv("APP_SEED_DATA", "1") == "1"
    model_path: str = os.getenv("MODEL_PATH", str(BASE_DIR / "ai" / "hospital_model.pkl"))
    top_k_recommendations: int = int(os.getenv("TOP_K_RECOMMENDATIONS", "5"))


settings = Settings()
