"""Shared PostgreSQL helpers — psycopg (Linux/CI) with pg8000 fallback (Windows ARM)."""

from __future__ import annotations

from typing import Any, Sequence
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


def connect(url: str):
    try:
        import psycopg

        return psycopg.connect(url)
    except (ImportError, AttributeError, TypeError):
        import pg8000

        params = _parse_url(url)
        return pg8000.connect(
            user=params["user"],
            password=params["password"],
            host=params["host"],
            port=params["port"],
            database=params["database"],
        )


def to_pg_text_array(values: list[str] | None) -> str:
    if not values:
        return "{}"
    escaped = [v.replace('"', '\\"') for v in values]
    return "{" + ",".join(escaped) + "}"


def execute_values(
    cur,
    sql: str,
    rows: Sequence[Sequence[Any]],
    page_size: int = 500,
    conn=None,
    retries: int = 3,
) -> None:
    """Insert many rows using VALUES %s placeholder."""
    if not rows:
        return
    if "%s" not in sql:
        raise ValueError("SQL must contain %s placeholder for VALUES clause")

    cols = sql.index("%s")
    prefix = sql[:cols]
    suffix = sql[cols + 2 :]
    width = len(rows[0])

    import time

    for i in range(0, len(rows), page_size):
        chunk = rows[i : i + page_size]
        placeholders = ", ".join(
            ["(" + ", ".join(["%s"] * width) + ")"] * len(chunk)
        )
        flat = [item for row in chunk for item in row]
        for attempt in range(retries):
            try:
                cur.execute(prefix + placeholders + suffix, flat)
                if conn is not None:
                    conn.commit()
                break
            except Exception as exc:
                if attempt + 1 >= retries:
                    raise
                if conn is not None:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                err = str(exc).lower()
                if "network" not in err and "ssl" not in err and "interface" not in err:
                    raise
                time.sleep(2 ** attempt)
        if conn is not None and (i + page_size) % (page_size * 20) == 0:
            print(f"  ... {min(i + page_size, len(rows))}/{len(rows)} rows")
