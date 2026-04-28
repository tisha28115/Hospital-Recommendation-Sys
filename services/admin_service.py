from __future__ import annotations

from typing import Any

from database.db import execute, fetch_all, fetch_one


def get_stats(conn: Any) -> dict[str, int]:
    users = fetch_one(conn, "SELECT COUNT(*) AS count FROM users") or {"count": 0}
    hospitals = fetch_one(conn, "SELECT COUNT(*) AS count FROM hospitals") or {"count": 0}
    appointments = fetch_one(conn, "SELECT COUNT(*) AS count FROM appointments") or {"count": 0}
    searches = fetch_one(conn, "SELECT COUNT(*) AS count FROM user_history") or {"count": 0}
    return {
        "users": int(users["count"]),
        "hospitals": int(hospitals["count"]),
        "appointments": int(appointments["count"]),
        "searches": int(searches["count"]),
    }


def list_hospitals(conn: Any) -> list[dict[str, Any]]:
    return fetch_all(conn, "SELECT * FROM hospitals ORDER BY rating DESC, name ASC")


def create_hospital(conn: Any, payload: dict[str, Any]) -> dict[str, Any]:
    hospital_id = execute(
        conn,
        """
        INSERT INTO hospitals(name, city, specialization, rating, latitude, longitude, emergency_services)
        VALUES(?, ?, ?, ?, ?, ?, ?)
        """,
        (
            payload["name"],
            payload["city"],
            payload["specialization"],
            payload.get("rating", 0),
            payload.get("latitude"),
            payload.get("longitude"),
            1 if payload.get("emergency_services") else 0,
        ),
    )
    conn.commit()
    return fetch_one(conn, "SELECT * FROM hospitals WHERE id=?", (hospital_id,)) or {}


def update_hospital(conn: Any, hospital_id: int, payload: dict[str, Any]) -> dict[str, Any] | None:
    execute(
        conn,
        """
        UPDATE hospitals
        SET name=?, city=?, specialization=?, rating=?, latitude=?, longitude=?, emergency_services=?
        WHERE id=?
        """,
        (
            payload["name"],
            payload["city"],
            payload["specialization"],
            payload.get("rating", 0),
            payload.get("latitude"),
            payload.get("longitude"),
            1 if payload.get("emergency_services") else 0,
            hospital_id,
        ),
    )
    conn.commit()
    return fetch_one(conn, "SELECT * FROM hospitals WHERE id=?", (hospital_id,))


def delete_hospital(conn: Any, hospital_id: int) -> None:
    execute(conn, "DELETE FROM hospitals WHERE id=?", (hospital_id,))
    conn.commit()
