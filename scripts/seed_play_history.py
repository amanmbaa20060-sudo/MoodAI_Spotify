"""Seed synthetic play_history and user_mood_preferences for Phase 0 novelty testing."""

from __future__ import annotations

import argparse
import os
import random
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from db import connect, execute_values  # noqa: E402

# Synthetic personas aligned with docs/problemstatement.md §2.3
PERSONAS = [
    {"user_id": "user_routine", "active_mood": "LOW_KEY", "plays": 80},
    {"user_id": "user_indie", "active_mood": "ADVENTUROUS", "plays": 50},
    {"user_id": "user_jazz", "active_mood": "NOSTALGIC", "plays": 40},
    {"user_id": "user_classical", "active_mood": "FOCUSED", "plays": 35},
    {"user_id": "user_heavy", "active_mood": "ENERGISED", "plays": 100},
    {"user_id": "user_new", "active_mood": "LOW_KEY", "plays": 0},
    {"user_id": "user_visual", "active_mood": "LOW_KEY", "plays": 60},
    {"user_id": "user_trust", "active_mood": "FOCUSED", "plays": 45},
    {"user_id": "user_sad", "active_mood": "SAD", "plays": 30},
    {"user_id": "user_nostalgic", "active_mood": "NOSTALGIC", "plays": 55},
]


def fetch_track_ids(conn, limit: int) -> list[str]:
    with conn.cursor() as cur:
        cur.execute("SELECT track_id FROM tracks ORDER BY track_id LIMIT %s", (limit,))
        return [row[0] for row in cur.fetchall()]


def seed(conn, seed_value: int = 42) -> None:
    rng = random.Random(seed_value)
    track_ids = fetch_track_ids(conn, 5000)
    if not track_ids:
        print("No tracks in database. Run excel_to_db.py first.", file=sys.stderr)
        raise SystemExit(1)

    mood_rows = [(p["user_id"], p["active_mood"], True) for p in PERSONAS]
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO user_mood_preferences (user_id, active_mood, persist)
            VALUES %s
            ON CONFLICT (user_id) DO UPDATE SET
                active_mood = EXCLUDED.active_mood,
                persist = EXCLUDED.persist,
                updated_at = NOW()
            """,
            mood_rows,
        )
    conn.commit()

    play_rows: list[tuple[str, str]] = []
    for persona in PERSONAS:
        n = persona["plays"]
        if n == 0:
            continue
        chosen = rng.sample(track_ids, min(n, len(track_ids)))
        play_rows.extend((persona["user_id"], tid) for tid in chosen)

    with conn.cursor() as cur:
        cur.execute("TRUNCATE play_history")
        execute_values(
            cur,
            "INSERT INTO play_history (user_id, track_id) VALUES %s ON CONFLICT DO NOTHING",
            play_rows,
        )
    conn.commit()

    print(f"Seeded {len(PERSONAS)} users, {len(play_rows)} play_history rows.")


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        return 1

    conn = connect(url)
    try:
        seed(conn, args.seed)
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
