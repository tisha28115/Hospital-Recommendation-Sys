from __future__ import annotations

from typing import Any

from database.db import execute, fetch_all, fetch_one
from services.email_service import build_hospital_maps_link


class AppointmentSlotUnavailableError(Exception):
    pass


def _table_columns(conn: Any, table_name: str) -> dict[str, dict[str, Any]]:
    if not table_name.replace("_", "").isalnum():
        raise ValueError("Invalid table name.")

    if conn.__class__.__module__.startswith("pymysql"):
        cur = conn.cursor()
        cur.execute(f"SHOW COLUMNS FROM `{table_name}`")
        columns: dict[str, dict[str, Any]] = {}
        for row in cur.fetchall() or []:
            column_name = row["Field"] if isinstance(row, dict) else row[0]
            column_type = row.get("Type") if isinstance(row, dict) else row[1]
            is_required = (
                str(row.get("Null", "YES")).upper() == "NO"
                if isinstance(row, dict)
                else str(row[2]).upper() == "NO"
            )
            default_value = row.get("Default") if isinstance(row, dict) else row[4]
            columns[str(column_name)] = {
                "type": column_type,
                "notnull": is_required,
                "default": default_value,
            }
        return columns

    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    columns: dict[str, dict[str, Any]] = {}
    for row in rows:
        column_name = row[1]
        columns[str(column_name)] = {
            "type": row[2],
            "notnull": row[3],
            "default": row[4],
        }
    return columns


def _resolve_legacy_doctor_id(conn: Any, department: str, hospital_id: int) -> int | None:
    doctor = fetch_one(
        conn,
        """
        SELECT id
        FROM doctors
        WHERE lower(specialization) LIKE ?
        ORDER BY rating DESC, experience_years DESC, id ASC
        LIMIT 1
        """,
        (f"%{department.strip().lower()}%",),
    )
    if doctor:
        return int(doctor["id"])

    hospital = fetch_one(conn, "SELECT name FROM hospitals WHERE id=?", (hospital_id,))
    if hospital and hospital.get("name"):
        doctor = fetch_one(
            conn,
            """
            SELECT id
            FROM doctors
            WHERE lower(hospital)=?
            ORDER BY rating DESC, experience_years DESC, id ASC
            LIMIT 1
            """,
            (str(hospital["name"]).strip().lower(),),
        )
        if doctor:
            return int(doctor["id"])

    doctor = fetch_one(conn, "SELECT id FROM doctors ORDER BY rating DESC, experience_years DESC, id ASC LIMIT 1")
    return int(doctor["id"]) if doctor else None


def create_appointment(
    conn: Any,
    *,
    user_id: int,
    hospital_id: int,
    disease: str,
    department: str,
    severity: str,
    appointment_date: str,
    appointment_time: str,
) -> dict[str, Any]:
    appointment_columns = _table_columns(conn, "appointments")
    existing_appointment = fetch_one(
        conn,
        """
        SELECT id
        FROM appointments
        WHERE hospital_id=?
          AND appointment_date=?
          AND appointment_time=?
          AND status IN ('booked', 'confirmed')
        LIMIT 1
        """,
        (hospital_id, appointment_date, appointment_time),
    )
    if existing_appointment:
        raise AppointmentSlotUnavailableError("Mentioned Slot is already booked.Sorry please select another slot!!")

    insert_payload: dict[str, Any] = {
        "user_id": user_id,
        "hospital_id": hospital_id,
        "disease": disease,
        "department": department,
        "severity": severity,
        "appointment_date": appointment_date,
        "appointment_time": appointment_time,
    }

    if "doctor_id" in appointment_columns:
        doctor_id = _resolve_legacy_doctor_id(conn, department, hospital_id)
        if appointment_columns["doctor_id"]["notnull"] and doctor_id is None:
            raise ValueError("No doctor data available to complete appointment booking.")
        insert_payload["doctor_id"] = doctor_id

    if "date" in appointment_columns:
        insert_payload["date"] = appointment_date

    if "time" in appointment_columns:
        insert_payload["time"] = appointment_time

    if "symptoms" in appointment_columns:
        insert_payload["symptoms"] = disease

    column_names = [column for column in insert_payload if column in appointment_columns]
    placeholders = ", ".join(["?"] * len(column_names))
    columns_sql = ", ".join(column_names)
    params = tuple(insert_payload[column] for column in column_names)

    appointment_id = execute(
        conn,
        f"INSERT INTO appointments({columns_sql}) VALUES({placeholders})",
        params,
    )
    conn.commit()
    appointment = fetch_one(conn, "SELECT * FROM appointments WHERE id=?", (appointment_id,)) or {}
    hospital = fetch_one(
        conn,
        """
        SELECT
            name AS hospital_name,
            city AS hospital_city,
            latitude AS hospital_latitude,
            longitude AS hospital_longitude
        FROM hospitals
        WHERE id=?
        """,
        (hospital_id,),
    ) or {}
    appointment.update(hospital)
    appointment["hospital_maps_link"] = build_hospital_maps_link(appointment)
    return appointment


def list_appointments(conn: Any, user_id: int) -> list[dict[str, Any]]:
    appointments = fetch_all(
        conn,
        """
        SELECT
            a.*,
            h.name AS hospital_name,
            h.city AS hospital_city,
            h.specialization,
            h.latitude AS hospital_latitude,
            h.longitude AS hospital_longitude
        FROM appointments a
        JOIN hospitals h ON h.id = a.hospital_id
        WHERE a.user_id=?
        ORDER BY a.created_at DESC, a.id DESC
        """,
        (user_id,),
    )
    for appointment in appointments:
        appointment["hospital_maps_link"] = build_hospital_maps_link(appointment)
    return appointments
