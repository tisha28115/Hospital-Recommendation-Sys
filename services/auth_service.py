from __future__ import annotations
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

from database.db import execute, fetch_one


def create_user(conn: Any, *, name: str, email: str, password: str, city: str = "", language: str = "en") -> dict[str, Any]:
    user_id = execute(
        conn,
        """
        INSERT INTO users(name, email, password_hash, city, preferred_language)
        VALUES(?, ?, ?, ?, ?)
        """,
        (name, email, generate_password_hash(password), city, language),
    )
    conn.commit()
    return fetch_one(conn, "SELECT id, name, email, city, preferred_language, is_admin, created_at FROM users WHERE id=?", (user_id,)) or {}


def get_user_by_email(conn: Any, email: str) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM users WHERE email=?", (email,))


def get_user_by_firebase_uid(conn: Any, firebase_uid: str) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM users WHERE firebase_uid=?", (firebase_uid,))


def create_or_sync_firebase_user(
    conn: Any,
    *,
    firebase_uid: str,
    email: str,
    name: str = "",
    city: str = "",
    language: str = "en",
) -> dict[str, Any]:
    firebase_uid = str(firebase_uid).strip()
    email = str(email).strip().lower()
    if not firebase_uid or not email:
        raise ValueError("Firebase UID and email are required.")

    existing_user = get_user_by_firebase_uid(conn, firebase_uid) or get_user_by_email(conn, email)
    normalized_name = str(name).strip()
    normalized_city = str(city).strip()
    normalized_language = str(language).strip().lower() or "en"

    if existing_user:
        next_name = normalized_name or str(existing_user.get("name", "")).strip() or email.split("@")[0]
        next_city = normalized_city if normalized_city else str(existing_user.get("city", "") or "").strip()
        next_language = normalized_language if normalized_language else str(existing_user.get("preferred_language", "en")).strip().lower() or "en"
        current_firebase_uid = str(existing_user.get("firebase_uid") or "").strip()

        needs_update = any(
            [
                next_name != str(existing_user.get("name", "") or "").strip(),
                email != str(existing_user.get("email", "") or "").strip().lower(),
                next_city != str(existing_user.get("city", "") or "").strip(),
                next_language != str(existing_user.get("preferred_language", "en") or "en").strip().lower(),
                firebase_uid != current_firebase_uid,
            ]
        )
        if needs_update:
            execute(
                conn,
                """
                UPDATE users
                SET name=?, email=?, city=?, preferred_language=?, firebase_uid=?
                WHERE id=?
                """,
                (next_name, email, next_city, next_language, firebase_uid, int(existing_user["id"])),
            )
            conn.commit()
        return get_user_by_id(conn, int(existing_user["id"])) or {}

    user_id = execute(
        conn,
        """
        INSERT INTO users(name, email, password_hash, city, preferred_language, firebase_uid)
        VALUES(?, ?, ?, ?, ?, ?)
        """,
        (
            normalized_name or email.split("@")[0],
            email,
            generate_password_hash(f"firebase:{firebase_uid}"),
            normalized_city,
            normalized_language,
            firebase_uid,
        ),
    )
    conn.commit()
    return get_user_by_id(conn, user_id) or {}


def authenticate_user(conn: Any, *, email: str, password: str) -> dict[str, Any] | None:
    user = fetch_one(conn, "SELECT * FROM users WHERE email=?", (email,))
    if not user:
        return None
    if not check_password_hash(str(user["password_hash"]), password):
        return None
    user.pop("password_hash", None)
    return user


def authenticate_admin(conn: Any, *, username: str, password: str) -> dict[str, Any] | None:
    admin = fetch_one(conn, "SELECT * FROM admins WHERE username=?", (username,))
    if not admin:
        return None
    if not check_password_hash(str(admin["password_hash"]), password):
        return None
    admin.pop("password_hash", None)
    return admin


def get_admin_by_id(conn: Any, admin_id: int) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT id, username, created_at FROM admins WHERE id=?", (admin_id,))


def get_user_by_id(conn: Any, user_id: int) -> dict[str, Any] | None:
    return fetch_one(
        conn,
        "SELECT id, name, email, city, preferred_language, is_admin, created_at FROM users WHERE id=?",
        (user_id,),
    )
