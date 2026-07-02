#!/usr/bin/env python3
"""Sharded drop generator worker for horizontal scale."""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASE3 = Path(__file__).resolve().parents[1]
for path in (ROOT, PHASE3):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.drop_sharding import users_for_partition  # noqa: E402
from app.main import build_services  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate drops for one shard partition")
    parser.add_argument("--partition", type=int, required=True)
    parser.add_argument("--partitions", type=int, default=None)
    args = parser.parse_args()

    settings, repository, mood_state, orchestrator, _, _, _, _, _, _, _, _ = build_services()
    partitions = args.partitions or settings.drop_partitions
    users = users_for_partition(repository.list_known_users(), args.partition, partitions)
    print(f"Partition {args.partition}/{partitions}: {len(users)} users")

    for user_id in users:
        mood = mood_state.get_active_mood(user_id)
        if repository.list_drop(user_id, date.today()):
            continue
        drop = orchestrator.generate_drop(user_id, mood)
        print(f"  {user_id}: {drop.get('status')} ({drop.get('track_count', len(drop.get('tracks', [])))} tracks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
