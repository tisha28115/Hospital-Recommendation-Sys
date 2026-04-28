from __future__ import annotations

import sqlite3
from typing import Any

from database.db import fetch_all, fetch_one
from scheduler.availability_checker import get_available_slots


def search_doctors(conn: sqlite3.Connection, query: str) -> list[dict[str, Any]]:
    q = f"%{(query or '').strip()}%"
    return fetch_all(
        conn,
        """
        SELECT * FROM doctors
        WHERE name LIKE ? OR specialization LIKE ? OR hospital LIKE ?
        ORDER BY rating DESC, experience_years DESC, name ASC
        LIMIT 10
        """,
        (q, q, q),
    )


def get_doctor(conn: sqlite3.Connection, doctor_id: int) -> dict[str, Any] | None:
    return fetch_one(conn, "SELECT * FROM doctors WHERE id=?", (doctor_id,))


def recommend_doctors(
    conn: sqlite3.Connection,
    *,
    specialization: str,
    date: str,
    preferred_doctor_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    preferred_doctor_ids = preferred_doctor_ids or []
    like = f"%{specialization.strip()}%"
    rows = fetch_all(
        conn,
        """
        SELECT * FROM doctors
        WHERE specialization LIKE ?
        ORDER BY rating DESC, experience_years DESC, name ASC
        LIMIT 10
        """,
        (like,),
    )

    def score(r: dict[str, Any]) -> tuple[int, float, int]:
        pref = 1 if int(r["id"]) in preferred_doctor_ids else 0
        return (pref, float(r["rating"]), int(r["experience_years"]))

    rows.sort(key=score, reverse=True)
    for r in rows:
        r["available_slots"] = get_available_slots(conn, int(r["id"]), date)
    return rows
