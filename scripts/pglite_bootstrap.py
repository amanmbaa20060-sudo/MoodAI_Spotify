"""Bootstrap an embedded PGlite-backed local database for smoke tests."""

from __future__ import annotations

import pg8000


def main() -> int:
    conn = pg8000.connect(
        user="postgres",
        password="postgres",
        host="127.0.0.1",
        port=5432,
        database="postgres",
    )
    conn.autocommit = True
    cur = conn.cursor()

    cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", ("app",))
    if cur.fetchone() is None:
        cur.execute("CREATE ROLE app LOGIN PASSWORD 'app'")

    cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("discovery",))
    if cur.fetchone() is None:
        cur.execute("CREATE DATABASE discovery OWNER app")

    conn.close()
    print("BOOTSTRAPPED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
