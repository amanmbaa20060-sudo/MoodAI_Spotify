#!/usr/bin/env python3
"""Apply all SQL schemas to DATABASE_URL (local or Render Postgres)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from phases.common.db import get_connection  # noqa: E402

load_dotenv(ROOT / ".env")

SCHEMA_FILES = (
    ROOT / "sql" / "schema.sql",
    ROOT / "phases" / "phase-1" / "sql" / "schema.sql",
    ROOT / "phases" / "phase-2" / "sql" / "schema.sql",
    ROOT / "phases" / "phase-3" / "sql" / "schema.sql",
)


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL is not set", file=sys.stderr)
        return 1

    for path in SCHEMA_FILES:
        if not path.exists():
            print(f"ERROR: missing schema file {path}", file=sys.stderr)
            return 1
        sql = path.read_text(encoding="utf-8")
        print(f">> Applying {path.relative_to(ROOT)}")
        with get_connection(database_url) as conn, conn.cursor() as cur:
            cur.execute(sql)
            conn.commit()

    print("All schemas applied successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
