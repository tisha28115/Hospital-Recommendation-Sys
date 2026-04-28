from __future__ import annotations

import sqlite3
from typing import Any

from database.db import execute, fetch_all, fetch_one


def get_user(conn: sqlite3.Connection, user_id: int) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM users WHERE id=?", (user_id,))


def search_users_by_name(conn: sqlite3.Connection, name_query: str, limit: int = 5) -> list[dict[str, Any]]:
    q = f"%{(name_query or '').strip()}%"
    return fetch_all(
        conn,
        "SELECT * FROM users WHERE name LIKE ? ORDER BY created_at DESC, id DESC LIMIT ?",
        (q, int(limit)),
    )


def find_user(conn: sqlite3.Connection, *, email: str | None, phone: str | None) -> dict[str, Any] | None:
    if email:
        row = fetch_one(conn, "SELECT * FROM users WHERE email=?", (email,))
        if row:
            return row
    if phone:
        row = fetch_one(conn, "SELECT * FROM users WHERE phone=?", (phone,))
        if row:
            return row
    return None


def create_user(
    conn: sqlite3.Connection,
    *,
    name: str,
    email: str | None = None,
    phone: str | None = None,
    language: str | None = None,
) -> dict[str, Any]:
    user_id = execute(
        conn,
        "INSERT INTO users(name, email, phone, language) VALUES(?, ?, ?, ?)",
        (name, email, phone, language),
    )
    conn.commit()
    return fetch_one(conn, "SELECT * FROM users WHERE id=?", (user_id,)) or {}


def update_language(conn: sqlite3.Connection, user_id: int, language: str) -> None:
    execute(conn, "UPDATE users SET language=? WHERE id=?", (language, user_id))
    conn.commit()


def get_patient_history(conn: sqlite3.Connection, user_id: int) -> list[dict[str, Any]]:
    return fetch_all(
        conn,
        """
        SELECT ph.*, d.name AS doctor_name, d.specialization AS doctor_specialization
        FROM patient_history ph
        LEFT JOIN doctors d ON d.id = ph.doctor_id
        WHERE ph.user_id=?
        ORDER BY ph.visit_date DESC, ph.id DESC
        """,
        (user_id,),
    )


def get_last_appointment(conn: sqlite3.Connection, user_id: int) -> dict[str, Any] | None:
    return fetch_one(
        conn,
        """
        SELECT a.*, d.name AS doctor_name, d.specialization AS doctor_specialization
        FROM appointments a
        JOIN doctors d ON d.id = a.doctor_id
        WHERE a.user_id=? AND a.status='confirmed'
        ORDER BY a.created_at DESC, a.id DESC
        LIMIT 1
        """,
        (user_id,),
    )
