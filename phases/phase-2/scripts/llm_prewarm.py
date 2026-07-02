#!/usr/bin/env python3
"""Phase 2 LLM prewarm job — run every 6h via cron."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASE2 = Path(__file__).resolve().parents[1]
for path in (ROOT, PHASE2):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.main import build_services  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="LLM prewarm for home module reasons")
    parser.add_argument("--user-id", help="Prewarm a single user (default: all known users)")
    args = parser.parse_args()

    _, _, mood_state, _, _, _, _, _, prewarm = build_services()
    if args.user_id:
        mood = mood_state.get_active_mood(args.user_id)
        result = prewarm.prewarm_user(args.user_id, mood)
        print(result)
    else:
        for result in prewarm.prewarm_all_users():
            print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
