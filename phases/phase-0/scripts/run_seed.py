#!/usr/bin/env python3
"""Phase 0 master seed wrapper — runs the repo-root pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"


def run(cmd: list[str]) -> None:
    print(f"\n>> {' '.join(cmd)}")
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 0 data pipeline")
    parser.add_argument(
        "--source",
        default="data/source/Music_Data.csv",
        help="Catalog CSV/XLSX path relative to repo root",
    )
    parser.add_argument("--skip-db", action="store_true", help="Validate only, no DB load")
    parser.add_argument("--skip-history", action="store_true", help="Skip play_history seed")
    args = parser.parse_args()
    source = args.source

    run([sys.executable, str(SCRIPTS / "build_mood_buckets.py"), "--source", source])
    run([sys.executable, str(SCRIPTS / "validate_coverage.py")])

    if args.skip_db:
        print("\nPhase 0 dry-run complete (no DB load).")
        return 0

    run([sys.executable, str(SCRIPTS / "excel_to_db.py"), "--source", source])
    if not args.skip_history:
        run([sys.executable, str(SCRIPTS / "seed_play_history.py")])
    run([sys.executable, str(SCRIPTS / "verify_mood_pools.py")])
    print("\nPhase 0 pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
