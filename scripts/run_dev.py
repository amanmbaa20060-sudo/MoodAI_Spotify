#!/usr/bin/env python3
"""Run Phase 3 API + Stitch mobile UI locally."""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHASE3 = ROOT / "phases" / "phase-3"
DEFAULT_PORT = int(os.getenv("MOODAI_PORT", "8010"))


def warn_about_port_8000() -> None:
    """Port 8000 is commonly used by other local demos (e.g. AI Travel Planner)."""
    try:
        with urllib.request.urlopen("http://127.0.0.1:8000/", timeout=2) as response:
            html = response.read().decode("utf-8", errors="ignore")
    except (urllib.error.URLError, TimeoutError, OSError):
        return
    if "MoodAI" in html:
        return
    if "Travel Planner" in html or "travel" in html.lower():
        print(
            "NOTE: http://127.0.0.1:8000/ is another app (AI Travel Planner), not MoodAI.\n"
            f"      Open MoodAI at http://127.0.0.1:{DEFAULT_PORT}/ after this script starts.\n"
        )


def pick_port(preferred: int) -> int:
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise SystemExit(f"No free port found between {preferred} and {preferred + 19}")


def main() -> int:
    warn_about_port_8000()
    port = pick_port(DEFAULT_PORT)
    url = f"http://127.0.0.1:{port}/"

    print("=" * 56)
    print("  MoodAI Spotify — Phase 3 (mobile UI)")
    print(f"  Open: {url}")
    print("  Do NOT use port 8000 if another project runs there.")
    print("  Tip: python scripts/run_local_real.py  (real Music_Data.csv)")
    print("=" * 56)

    cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:create_app",
        "--factory",
        "--reload",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    subprocess.run(cmd, cwd=PHASE3, check=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
