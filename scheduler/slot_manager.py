from __future__ import annotations

from database.db import execute, fetch_one


def _is_mysql(conn: object) -> bool:
    return conn.__class__.__module__.startswith("pymysql")


def ensure_slot(conn: object, doctor_id: int, date: str, time: str) -> None:
    if _is_mysql(conn):
        execute(
            conn,
            "INSERT IGNORE INTO doctor_slots(doctor_id, date, time, status) VALUES(?, ?, ?, 'available')",
            (doctor_id, date, time),
        )
    else:
        execute(
            conn,
            "INSERT OR IGNORE INTO doctor_slots(doctor_id, date, time, status) VALUES(?, ?, ?, 'available')",
            (doctor_id, date, time),
        )


def set_slot_status(
    conn: object,
    doctor_id: int,
    date: str,
    time: str,
    status: str,
    *,
    create_if_missing: bool = False,
) -> None:
    if create_if_missing:
        ensure_slot(conn, doctor_id, date, time)
    execute(
        conn,
        "UPDATE doctor_slots SET status=? WHERE doctor_id=? AND date=? AND time=?",
        (status, doctor_id, date, time),
    )


def get_slot_status(conn: object, doctor_id: int, date: str, time: str) -> str | None:
    row = fetch_one(
        conn,
        "SELECT status FROM doctor_slots WHERE doctor_id=? AND date=? AND time=?",
        (doctor_id, date, time),
    )
    return row["status"] if row else None
