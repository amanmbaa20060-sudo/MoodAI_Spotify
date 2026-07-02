#!/usr/bin/env python3
"""Phase 3 candidate prewarm job — run every 6h."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASE3 = Path(__file__).resolve().parents[1]
for path in (ROOT, PHASE3):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.main import build_services  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prewarm mood-keyed candidate pools")
    parser.add_argument("--user-id", help="Prewarm one user")
    args = parser.parse_args()

    _, _, mood_state, _, _, _, _, _, _, _, candidate_prewarm, _ = build_services()
    if args.user_id:
        mood = mood_state.get_active_mood(args.user_id)
        print(candidate_prewarm.prewarm_user(args.user_id, mood))
    else:
        for result in candidate_prewarm.prewarm_all_users():
            print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
