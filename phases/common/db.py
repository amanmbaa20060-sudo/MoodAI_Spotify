"""Shared PostgreSQL helpers for phased implementations."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence
from urllib.parse import urlparse


def _parse_url(url: str) -> dict[str, Any]:
    normalized = url.replace("postgresql://", "postgres://")
    parsed = urlparse(normalized)
    return {
        "user": parsed.username,
        "password": parsed.password,
        "host": parsed.hostname or "localhost",
        "port": parsed.port or 5432,
        "database": (parsed.path or "/discovery").lstrip("/"),
    }


def connect(url: str, connect_timeout: int = 10):
    try:
        import psycopg

        return psycopg.connect(url, connect_timeout=connect_timeout)
    except (ImportError, AttributeError, TypeError):
        import pg8000

        params = _parse_url(url)
        return pg8000.connect(
            user=params["user"],
            password=params["password"],
            host=params["host"],
            port=params["port"],
            database=params["database"],
            timeout=connect_timeout,
        )


def database_is_available(url: str, connect_timeout: int = 3) -> bool:
    try:
        with get_connection(url, connect_timeout=connect_timeout) as conn, conn.cursor() as cur:
            cur.execute("SELECT 1")
        return True
    except Exception:
        return False


@contextmanager
def get_connection(url: str, connect_timeout: int = 10) -> Iterator[Any]:
    conn = connect(url, connect_timeout=connect_timeout)
    try:
        yield conn
    finally:
        conn.close()


def fetch_all_dicts(cur) -> list[dict[str, Any]]:
    columns = [item[0] for item in cur.description] if cur.description else []
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def fetch_one_dict(cur) -> dict[str, Any] | None:
    columns = [item[0] for item in cur.description] if cur.description else []
    row = cur.fetchone()
    if row is None:
        return None
    return dict(zip(columns, row))


def execute_values(
    cur,
    sql: str,
    rows: Sequence[Sequence[Any]],
    page_size: int = 500,
) -> None:
    if not rows:
        return
    if "%s" not in sql:
        raise ValueError("SQL must contain %s placeholder for VALUES clause")

    marker_index = sql.index("%s")
    prefix = sql[:marker_index]
    suffix = sql[marker_index + 2 :]
    width = len(rows[0])

    for offset in range(0, len(rows), page_size):
        chunk = rows[offset : offset + page_size]
        placeholders = ", ".join(
            ["(" + ", ".join(["%s"] * width) + ")"] * len(chunk)
        )
        flat = [value for row in chunk for value in row]
        cur.execute(prefix + placeholders + suffix, flat)
