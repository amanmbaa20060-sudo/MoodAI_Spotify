#!/usr/bin/env python3
"""Start MoodAI locally with the real UI and real catalog data."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from phases.common.db import connect, database_is_available  # noqa: E402


def postgres_track_count(database_url: str) -> int | None:
    if not database_is_available(database_url):
        return None
    try:
        with connect(database_url) as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM tracks")
            return int(cur.fetchone()[0])
    except Exception:
        return None


def main() -> int:
    database_url = os.getenv("DATABASE_URL", "postgresql://app:app@localhost:5432/discovery")
    catalog = os.getenv("EXCEL_SOURCE_PATH", "data/source/Music_Data.csv")
    catalog_path = ROOT / catalog if not Path(catalog).is_absolute() else Path(catalog)

    print("=" * 60)
    print("  MoodAI — local run with real UI + real dataset")
    print("=" * 60)

    track_count = postgres_track_count(database_url)
    if track_count and track_count > 1000:
        os.environ["MOODAI_DEMO_MODE"] = "false"
        print(f"  Postgres: connected ({track_count:,} tracks)")
        print("  Mode:     production API against local database")
    elif track_count is not None and track_count > 0:
        os.environ["MOODAI_DEMO_MODE"] = "false"
        print(f"  Postgres: connected ({track_count:,} tracks — consider re-seeding)")
        print("  Mode:     production API against local database")
    else:
        os.environ.pop("MOODAI_DEMO_MODE", None)
        if catalog_path.exists():
            os.environ.setdefault("EXCEL_SOURCE_PATH", str(catalog_path.relative_to(ROOT)))
            print(f"  Postgres: not available")
            print(f"  Catalog:  {catalog_path.name} ({catalog_path.stat().st_size // (1024 * 1024)} MB)")
            print("  Mode:     in-memory catalog from Music_Data.csv (first start may take ~30s)")
        else:
            print("  Postgres: not available")
            print(f"  Catalog:  {catalog_path} not found — using bundled sample tracks")
            print("  Mode:     demo sample catalog")

        print()
        print("  For full Postgres locally:")
        print("    1. Install Docker Desktop")
        print("    2. docker compose up -d")
        print("    3. python scripts/apply_schemas.py")
        print("    4. python scripts/seed_all.py --source data/source/Music_Data.csv")
        print()
        print("  Or point DATABASE_URL in .env to your Render external Postgres URL.")

    print()
    print("  Starting UI at http://127.0.0.1:8010/  (Ctrl+C to stop)")
    print("=" * 60)
    print()

    return subprocess.call([sys.executable, str(ROOT / "scripts" / "run_dev.py")])


if __name__ == "__main__":
    raise SystemExit(main())
