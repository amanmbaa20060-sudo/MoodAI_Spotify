#!/usr/bin/env python3
"""Quick backend + frontend smoke test for Option C (local UI + Render Postgres)."""

from __future__ import annotations

import json
import os
import socket
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from phases.common.db import connect, database_is_available  # noqa: E402


def find_moodai_port() -> int | None:
    preferred: list[int] = []
    env_port = os.getenv("MOODAI_PORT")
    if env_port:
        preferred.append(int(env_port))

    candidates: list[tuple[int, dict]] = []
    for port in preferred + list(range(8010, 8020)):
        if port in preferred and port in [c[0] for c in candidates]:
            continue
        try:
            with urllib.request.urlopen(
                f"http://127.0.0.1:{port}/healthz", timeout=3
            ) as resp:
                data = json.loads(resp.read())
                if data.get("product") == "MoodAI Spotify":
                    candidates.append((port, data))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            continue

    if not candidates:
        return None

    for port, data in candidates:
        if data.get("mode") != "demo":
            return port
    return candidates[0][0]


def db_stats() -> dict:
    url = os.getenv("DATABASE_URL", "")
    if not database_is_available(url):
        return {"available": False}
    with connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM tracks")
        tracks = int(cur.fetchone()[0])
        cur.execute("SELECT COUNT(*) FROM track_mood_tags")
        mood_tags = int(cur.fetchone()[0])
        cur.execute(
            "SELECT COUNT(*) FROM track_mood_tags WHERE primary_mood IS NOT NULL"
        )
        tagged = int(cur.fetchone()[0])
    return {
        "available": True,
        "tracks": tracks,
        "mood_tags": mood_tags,
        "tagged": tagged,
    }


def request_json(url: str, *, method: str = "GET", body: dict | None = None, headers: dict | None = None, timeout: int = 120):
    payload = None
    hdrs = dict(headers or {})
    if body is not None:
        payload = json.dumps(body).encode()
        hdrs.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=payload, method=method, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, json.loads(resp.read())


def main() -> int:
    print("=" * 60)
    print("Option C retest — Render Postgres + local MoodAI")
    print("=" * 60)

    stats = db_stats()
    if not stats.get("available"):
        print("FAIL: DATABASE_URL not reachable")
        return 1
    print(
        f"DB: {stats['tracks']:,} tracks | "
        f"{stats['mood_tags']:,} mood tags | "
        f"{stats['tagged']:,} with primary_mood"
    )

    port = find_moodai_port()
    if port is None:
        print("FAIL: No MoodAI server on ports 8010-8019")
        print("Start with: python scripts/run_local_real.py")
        return 1

    base = f"http://127.0.0.1:{port}"
    print(f"Server: {base}")

    failures = 0

    # Frontend static assets
    for path in ("/", "/assets/app.js"):
        try:
            with urllib.request.urlopen(base + path, timeout=15) as resp:
                body = resp.read()
                ok = resp.status == 200 and len(body) > 0
                print(f"{'OK' if ok else 'FAIL'} GET {path} ({len(body)} bytes)")
                if not ok:
                    failures += 1
                if path == "/" and b"MoodAI" not in body and b"mood" not in body.lower():
                    print("  WARN: index.html may be incomplete")
        except Exception as exc:
            print(f"FAIL GET {path}: {exc}")
            failures += 1

    try:
        with urllib.request.urlopen(base + "/config.js", timeout=5) as resp:
            print(f"OK GET /config.js ({len(resp.read())} bytes)")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print("SKIP GET /config.js (local dev — only generated for Vercel)")
        else:
            print(f"FAIL GET /config.js: {exc}")
            failures += 1

    # Backend health
    try:
        status, health = request_json(base + "/healthz", timeout=15)
        demo = health.get("mode") == "demo"
        print(f"{'OK' if status == 200 else 'FAIL'} /healthz {health}")
        if demo:
            print("  FAIL: still in demo mode (expected production DB)")
            failures += 1
    except Exception as exc:
        print(f"FAIL /healthz: {exc}")
        failures += 1

    headers = {"X-User-Id": "retest-option-c"}

    # Artist lookup (real catalog)
    try:
        status, artist = request_json(
            base + "/v1/artists/lookup/by-name?name=Drake&limit=5",
            headers=headers,
            timeout=120,
        )
        name = artist.get("name")
        tracks = artist.get("tracks") or []
        print(
            f"{'OK' if status == 200 and tracks else 'FAIL'} "
            f"artist lookup: name={name!r} track_count={artist.get('track_count')} "
            f"sample={tracks[0].get('title') if tracks else None!r}"
        )
        if not tracks:
            failures += 1
    except Exception as exc:
        print(f"FAIL artist lookup: {exc}")
        failures += 1

    # Home feed
    try:
        status, home = request_json(base + "/v1/home", headers=headers, timeout=180)
        modules = [m.get("type") for m in home.get("modules", [])]
        print(
            f"{'OK' if status == 200 and modules else 'FAIL'} "
            f"/v1/home mood={home.get('active_mood')} modules={modules}"
        )
        if not modules:
            failures += 1
    except Exception as exc:
        print(f"FAIL /v1/home: {exc}")
        failures += 1

    # Discovery drop (GET — uses active mood)
    try:
        status, drop = request_json(
            base + "/v1/discovery-drop",
            headers=headers,
            timeout=180,
        )
        drop_tracks = drop.get("tracks") or []
        print(
            f"{'OK' if status == 200 and drop_tracks else 'FAIL'} "
            f"discovery: {len(drop_tracks)} tracks drop_id={drop.get('drop_id')}"
        )
        for track in drop_tracks[:2]:
            artists = track.get("artists") or ["?"]
            print(f"  - {track.get('title')} ({artists[0]})")
        if not drop_tracks:
            failures += 1
    except Exception as exc:
        print(f"FAIL discovery: {exc}")
        failures += 1

    print("=" * 60)
    if failures:
        print(f"FAILED ({failures} checks)")
        return 1
    print("ALL CHECKS PASSED")
    print(f"Open UI: {base}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
