from __future__ import annotations

from typing import Iterator

from database.db import connect, init_db, seed_if_empty


def get_db() -> Iterator[object]:
    conn = connect()
    init_db(conn)
    seed_if_empty(conn)
    try:
        yield conn
    finally:
        conn.close()
