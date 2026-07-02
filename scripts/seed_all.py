"""Phase 0 master seed: catalog → DB → play history → validate."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = Path(__file__).resolve().parent


def run(cmd: list[str]) -> int:
    print(f"\n>> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=ROOT)
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Run full Phase 0 seed pipeline")
    parser.add_argument(
        "--source",
        default="data/source/Music_Data.csv",
        help="Catalog source (.xlsx or .csv)",
    )
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate sample catalog before load",
    )
    parser.add_argument("--dry-run", action="store_true", help="Tag only, skip DB writes")
    parser.add_argument("--skip-play-history", action="store_true")
    args = parser.parse_args()

    if args.generate or not Path(args.source).exists():
        print("Generating sample catalog...")
        rc = run([sys.executable, str(SCRIPTS / "generate_sample_catalog.py")])
        if rc != 0:
            return rc

    load_cmd = [
        sys.executable,
        str(SCRIPTS / "excel_to_db.py"),
        "--source",
        args.source,
    ]
    if args.dry_run:
        load_cmd.append("--dry-run")
    rc = run(load_cmd)
    if rc != 0:
        return rc

    if args.dry_run:
        return run([
            sys.executable,
            str(SCRIPTS / "validate_coverage.py"),
            "--csv",
            "data/seed/v1/track_mood_tags.csv",
        ])

    if not args.skip_play_history:
        rc = run([sys.executable, str(SCRIPTS / "seed_play_history.py")])
        if rc != 0:
            return rc

    for script in ("validate_coverage.py", "verify_mood_pools.py"):
        rc = run([sys.executable, str(SCRIPTS / script)])
        if rc != 0:
            return rc

    print("\nPhase 0 seed pipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
