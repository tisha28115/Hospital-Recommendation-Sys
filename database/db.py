from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from flask import g
from werkzeug.security import generate_password_hash

from config import settings

try:
    import pymysql  # type: ignore
except Exception:  # pragma: no cover
    pymysql = None


def _ensure_parent_dir(db_path: str) -> None:
    Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)


def _is_mysql(conn: Any) -> bool:
    return conn.__class__.__module__.startswith("pymysql")


def _adapt_sql(conn: Any, sql: str) -> str:
    return sql.replace("?", "%s") if _is_mysql(conn) else sql


def connect() -> Any:
    if settings.db_engine == "mysql":
        if not pymysql:
            raise RuntimeError("MySQL selected but `pymysql` is not installed.")
        return pymysql.connect(
            host=settings.mysql_host,
            port=settings.mysql_port,
            user=settings.mysql_user,
            password=settings.mysql_password,
            database=settings.mysql_database,
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )

    _ensure_parent_dir(settings.db_path)
    conn = sqlite3.connect(settings.db_path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


def get_connection() -> Any:
    if "db_conn" not in g:
        g.db_conn = connect()
    return g.db_conn


def close_connection(_: object | None) -> None:
    conn = g.pop("db_conn", None)
    if conn is not None:
        conn.close()


def init_db(conn: Any) -> None:
    schema_name = "mysql_schema.sql" if _is_mysql(conn) else "schema.sql"
    schema_path = Path(__file__).resolve().parent / schema_name
    with open(schema_path, "r", encoding="utf-8") as file_obj:
        sql = file_obj.read()
    if _is_mysql(conn):
        statements = [statement.strip() for statement in sql.split(";") if statement.strip()]
        cur = conn.cursor()
        for statement in statements:
            cur.execute(statement)
        conn.commit()
        return
    conn.executescript(sql)
    conn.commit()


def ensure_schema_compatibility(conn: Any) -> None:
    if _is_mysql(conn):
        _ensure_mysql_user_schema(conn)
        _ensure_mysql_admin_schema(conn)
        _ensure_mysql_appointment_schema(conn)
        return
    _ensure_sqlite_user_schema(conn)
    _ensure_sqlite_admin_schema(conn)
    _ensure_sqlite_appointment_schema(conn)


def ensure_default_admin(conn: Any) -> None:
    admin_count = fetch_one(conn, "SELECT COUNT(*) AS count FROM admins") or {"count": 0}
    if int(admin_count["count"]) > 0:
        return

    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin").strip().lower()
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")

    execute(
        conn,
        """
        INSERT INTO admins(username, password_hash)
        VALUES(?, ?)
        """,
        (admin_email, generate_password_hash(admin_password)),
    )
    conn.commit()


def _ensure_sqlite_user_schema(conn: Any) -> None:
    columns = {
        row[1]: row
        for row in conn.execute("PRAGMA table_info(users)").fetchall()
    }
    if not columns:
        return

    if "password_hash" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")

    if "firebase_uid" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN firebase_uid TEXT")

    if "city" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN city TEXT")

    if "preferred_language" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN preferred_language TEXT NOT NULL DEFAULT 'en'")
        if "language" in columns:
            conn.execute(
                """
                UPDATE users
                SET preferred_language = COALESCE(NULLIF(language, ''), 'en')
                """
            )

    if "is_admin" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")

    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_firebase_uid ON users(firebase_uid)")
    conn.commit()


def _ensure_sqlite_admin_schema(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL,
          created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def _ensure_sqlite_appointment_schema(conn: Any) -> None:
    columns = {
        row[1]: row
        for row in conn.execute("PRAGMA table_info(appointments)").fetchall()
    }
    if not columns:
        return

    if "hospital_id" not in columns:
        conn.execute("ALTER TABLE appointments ADD COLUMN hospital_id INTEGER")

    if "disease" not in columns:
        conn.execute("ALTER TABLE appointments ADD COLUMN disease TEXT NOT NULL DEFAULT ''")

    if "department" not in columns:
        conn.execute("ALTER TABLE appointments ADD COLUMN department TEXT NOT NULL DEFAULT ''")

    if "appointment_date" not in columns:
        conn.execute("ALTER TABLE appointments ADD COLUMN appointment_date TEXT")
        if "date" in columns:
            conn.execute(
                """
                UPDATE appointments
                SET appointment_date = COALESCE(appointment_date, date)
                """
            )

    if "appointment_time" not in columns:
        conn.execute("ALTER TABLE appointments ADD COLUMN appointment_time TEXT")
        if "time" in columns:
            conn.execute(
                """
                UPDATE appointments
                SET appointment_time = COALESCE(appointment_time, time)
                """
            )

    conn.commit()


def _ensure_mysql_user_schema(conn: Any) -> None:
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM users")
    columns = {row["Field"] if isinstance(row, dict) else row[0] for row in cur.fetchall() or []}
    if not columns:
        return

    statements: list[str] = []
    if "password_hash" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255) NOT NULL DEFAULT ''")
    if "firebase_uid" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN firebase_uid VARCHAR(255) NULL UNIQUE")
    if "city" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN city VARCHAR(255) NULL")
    if "preferred_language" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN preferred_language VARCHAR(10) NOT NULL DEFAULT 'en'")
    if "is_admin" not in columns:
        statements.append("ALTER TABLE users ADD COLUMN is_admin TINYINT(1) NOT NULL DEFAULT 0")

    for statement in statements:
        cur.execute(statement)

    if "preferred_language" not in columns and "language" in columns:
        cur.execute(
            """
            UPDATE users
            SET preferred_language = COALESCE(NULLIF(language, ''), 'en')
            """
        )

    conn.commit()


def _ensure_mysql_admin_schema(conn: Any) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS admins (
          id INT AUTO_INCREMENT PRIMARY KEY,
          username VARCHAR(255) NOT NULL UNIQUE,
          password_hash VARCHAR(255) NOT NULL,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _ensure_mysql_appointment_schema(conn: Any) -> None:
    cur = conn.cursor()
    cur.execute("SHOW COLUMNS FROM appointments")
    columns = {row["Field"] if isinstance(row, dict) else row[0] for row in cur.fetchall() or []}
    if not columns:
        return

    statements: list[str] = []
    if "hospital_id" not in columns:
        statements.append("ALTER TABLE appointments ADD COLUMN hospital_id INT NULL")
    if "disease" not in columns:
        statements.append("ALTER TABLE appointments ADD COLUMN disease VARCHAR(255) NOT NULL DEFAULT ''")
    if "department" not in columns:
        statements.append("ALTER TABLE appointments ADD COLUMN department VARCHAR(255) NOT NULL DEFAULT ''")
    if "appointment_date" not in columns:
        statements.append("ALTER TABLE appointments ADD COLUMN appointment_date DATE NULL")
    if "appointment_time" not in columns:
        statements.append("ALTER TABLE appointments ADD COLUMN appointment_time TIME NULL")

    for statement in statements:
        cur.execute(statement)

    if "appointment_date" not in columns and "date" in columns:
        cur.execute("UPDATE appointments SET appointment_date = COALESCE(appointment_date, date)")
    if "appointment_time" not in columns and "time" in columns:
        cur.execute("UPDATE appointments SET appointment_time = COALESCE(appointment_time, time)")

    conn.commit()


@contextmanager
def transaction(conn: Any) -> Iterator[Any]:
    if _is_mysql(conn):
        conn.begin()
    else:
        conn.execute("BEGIN IMMEDIATE;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def execute(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> int:
    cur = conn.cursor()
    cur.execute(_adapt_sql(conn, sql), params)
    return int(getattr(cur, "lastrowid", 0) or 0)


def fetch_one(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    cur = conn.cursor()
    cur.execute(_adapt_sql(conn, sql), params)
    row = cur.fetchone()
    if not row:
        return None
    return dict(row) if not isinstance(row, dict) else row


def fetch_all(conn: Any, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(_adapt_sql(conn, sql), params)
    rows = cur.fetchall() or []
    return [dict(row) if not isinstance(row, dict) else row for row in rows]


def seed_if_empty(conn: Any) -> None:
    if not settings.seed_data:
        return

    hospital_rows = [
        ("Apollo Multispeciality", "Ahmedabad", "Cardiology", 4.8, 23.0225, 72.5714, 1),
        ("Sterling Care Hospital", "Ahmedabad", "Neurology", 4.6, 23.0300, 72.5800, 0),
        ("Zydus Health Center", "Ahmedabad", "General Medicine", 4.5, 23.0420, 72.5530, 1),
        ("Sunrise Multispeciality", "Vadodara", "General Medicine", 4.7, 22.3078, 73.1815, 1),
        ("Baroda Neuro Care", "Vadodara", "Neurology", 4.5, 22.3140, 73.1700, 0),
        ("Vadodara Heart Center", "Vadodara", "Cardiology", 4.6, 22.3005, 73.1870, 1),
        ("Fortis Heart Institute", "Mumbai", "Cardiology", 4.9, 19.0760, 72.8777, 1),
        ("Lilavati Lifecare", "Mumbai", "Orthopedics", 4.7, 19.0596, 72.8295, 1),
        ("Max Super Speciality", "Delhi", "Neurology", 4.8, 28.6139, 77.2090, 1),
        ("Medanta Care", "Delhi", "General Medicine", 4.7, 28.4595, 77.0266, 1),
        ("Narayana Health", "Bengaluru", "Gastroenterology", 4.6, 12.9716, 77.5946, 1),
        ("Manipal Hospital", "Bengaluru", "Dermatology", 4.5, 12.9352, 77.6245, 0),
        ("Care Emergency Center", "Pune", "Emergency Medicine", 4.4, 18.5204, 73.8567, 1),
    ]
    for row in hospital_rows:
        existing_hospital = fetch_one(
            conn,
            "SELECT id FROM hospitals WHERE lower(name)=? AND lower(city)=?",
            (str(row[0]).lower(), str(row[1]).lower()),
        )
        if not existing_hospital:
            execute(
                conn,
                """
                INSERT INTO hospitals(name, city, specialization, rating, latitude, longitude, emergency_services)
                VALUES(?, ?, ?, ?, ?, ?, ?)
                """,
                row,
            )

    mapping_rows = [
        ("fever", "General Medicine"),
        ("flu", "General Medicine"),
        ("migraine", "Neurology"),
        ("stroke", "Neurology"),
        ("heart attack", "Cardiology"),
        ("chest pain", "Cardiology"),
        ("fracture", "Orthopedics"),
        ("bone pain", "Orthopedics"),
        ("skin rash", "Dermatology"),
        ("acidity", "Gastroenterology"),
        ("stomach pain", "Gastroenterology"),
    ]
    for row in mapping_rows:
        existing_mapping = fetch_one(conn, "SELECT id FROM disease_mapping WHERE lower(disease)=?", (str(row[0]).lower(),))
        if not existing_mapping:
            execute(conn, "INSERT INTO disease_mapping(disease, department) VALUES(?, ?)", row)

    conn.commit()
