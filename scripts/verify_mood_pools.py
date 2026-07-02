"""Verify mood pool SQL queries meet Phase 0 targets (architecture §6.5)."""

from __future__ import annotations

import os
import sys

import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from db import connect, execute_values  # noqa: E402
from mood_rules import DATASET_MOODS  # noqa: E402

MIN_PER_MOOD = 200

QUERIES = {
    "total_tracks": "SELECT COUNT(*) FROM tracks",
    "tagged_tracks": "SELECT COUNT(*) FROM track_mood_tags WHERE primary_mood IS NOT NULL",
    "adventurous_tags": """
        SELECT COUNT(*) FROM track_mood_tags
        WHERE primary_mood = 'ADVENTUROUS'
           OR 'ADVENTUROUS' = ANY(mood_tags)
    """,
    "mood_pool": """
        SELECT COUNT(*) FROM tracks t
        JOIN track_mood_tags m ON t.track_id = m.track_id
        WHERE %s = ANY(m.mood_tags)
    """,
}


def main() -> int:
    load_dotenv()
    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    conn = connect(url)
    errors: list[str] = []
    try:
        with conn.cursor() as cur:
            cur.execute(QUERIES["total_tracks"])
            total = cur.fetchone()[0]
            print(f"Total tracks: {total}")

            cur.execute(QUERIES["tagged_tracks"])
            tagged = cur.fetchone()[0]
            print(f"Tagged tracks: {tagged}")

            cur.execute(QUERIES["adventurous_tags"])
            adv = cur.fetchone()[0]
            print(f"ADVENTUROUS tags: {adv}")
            if adv != 0:
                errors.append(f"ADVENTUROUS count must be 0, got {adv}")

            if total < 1000:
                errors.append(f"Total tracks {total} < 1000")

            for mood in DATASET_MOODS:
                cur.execute(QUERIES["mood_pool"], (mood,))
                count = cur.fetchone()[0]
                print(f"  Pool {mood}: {count}")
                if count < MIN_PER_MOOD:
                    errors.append(f"{mood} pool {count} < {MIN_PER_MOOD}")
    finally:
        conn.close()

    if errors:
        print("\nVERIFY FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("\nVERIFY PASSED — mood pools ready for Phase 1 ranker.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
