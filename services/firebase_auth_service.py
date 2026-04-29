# from __future__ import annotations

# from pathlib import Path
# from typing import Any

# from config import settings

# try:
#     import firebase_admin
#     from firebase_admin import auth, credentials
# except Exception:  # pragma: no cover
#     firebase_admin = None
#     auth = None
#     credentials = None


# def assert_firebase_auth_ready() -> None:
#     if firebase_admin is None or auth is None or credentials is None:
#         raise RuntimeError(
#             "Firebase Admin SDK is not installed. Install `firebase-admin` before starting the app."
#         )

#     service_account_path = settings.firebase_service_account_path.strip()
#     if not service_account_path:
#         raise RuntimeError(
#             "FIREBASE_SERVICE_ACCOUNT_PATH is not set. Point it to your Firebase Admin SDK JSON file."
#         )

#     if not Path(service_account_path).is_file():
#         raise RuntimeError(
#             f"Firebase service account file was not found at: {service_account_path}"
#         )


# def firebase_auth_status() -> dict[str, str | bool]:
#     try:
#         assert_firebase_auth_ready()
#     except RuntimeError as exc:
#         return {"ready": False, "message": str(exc)}
#     return {"ready": True, "message": "Firebase Authentication is configured."}


# def _get_app() -> Any:
#     assert_firebase_auth_ready()

#     try:
#         return firebase_admin.get_app()
#     except ValueError:
#         options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
#         credential = credentials.Certificate(settings.firebase_service_account_path)
#         return firebase_admin.initialize_app(credential, options=options)


# def verify_firebase_token(id_token: str) -> dict[str, Any]:
#     cleaned_token = (id_token or "").strip()
#     if not cleaned_token:
#         raise RuntimeError("Missing Firebase ID token.")

#     _get_app()
#     return dict(auth.verify_id_token(cleaned_token))

from __future__ import annotations

from pathlib import Path
from typing import Any
import os

from config import settings

try:
    import firebase_admin
    from firebase_admin import auth, credentials
except Exception:  # pragma: no cover
    firebase_admin = None
    auth = None
    credentials = None


def assert_firebase_auth_ready() -> None:
    if firebase_admin is None or auth is None or credentials is None:
        raise RuntimeError(
            "Firebase Admin SDK is not installed. Install `firebase-admin` before starting the app."
        )

    service_account_path = os.environ.get(
        "FIREBASE_SERVICE_ACCOUNT_PATH",
        settings.firebase_service_account_path,
    )

    if not service_account_path:
        raise RuntimeError(
            "FIREBASE_SERVICE_ACCOUNT_PATH is not set."
        )

    if not Path(service_account_path).is_file():
        raise RuntimeError(
            f"Firebase service account file was not found at: {service_account_path}"
        )


def firebase_auth_status() -> dict[str, str | bool]:
    try:
        assert_firebase_auth_ready()
    except RuntimeError as exc:
        return {"ready": False, "message": str(exc)}
    return {"ready": True, "message": "Firebase Authentication is configured."}


def _get_app() -> Any:
    assert_firebase_auth_ready()

    try:
        return firebase_admin.get_app()
    except ValueError:
        service_account_path = os.environ.get(
            "FIREBASE_SERVICE_ACCOUNT_PATH",
            settings.firebase_service_account_path,
        )

        options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None

        cred = credentials.Certificate(service_account_path)
        return firebase_admin.initialize_app(cred, options=options)


def verify_firebase_token(id_token: str) -> dict[str, Any]:
    cleaned_token = (id_token or "").strip()
    if not cleaned_token:
        raise RuntimeError("Missing Firebase ID token.")

    _get_app()
    return dict(auth.verify_id_token(cleaned_token))