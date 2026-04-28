from __future__ import annotations

from datetime import time as dt_time, timedelta

from database.db import fetch_all


def _time_to_hhmm(v: object) -> str:
    if isinstance(v, str):
        return v[:5]
    if isinstance(v, dt_time):
        return v.strftime("%H:%M")
    if isinstance(v, timedelta):
        total_seconds = int(v.total_seconds())
        hours = (total_seconds // 3600) % 24
        minutes = (total_seconds % 3600) // 60
        return f"{hours:02d}:{minutes:02d}"
    return str(v)[:5]


def get_available_slots(conn: object, doctor_id: int, date: str) -> list[str]:
    rows = fetch_all(
        conn,
        "SELECT time FROM doctor_slots WHERE doctor_id=? AND date=? AND status='available' ORDER BY time",
        (doctor_id, date),
    )
    return [_time_to_hhmm(r["time"]) for r in rows]
