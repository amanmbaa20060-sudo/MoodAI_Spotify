#!/usr/bin/env python3
"""Generate a fresh discovery drop for a new user (Groq explanations)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8013"
USER = f"groq-user-{uuid.uuid4().hex[:8]}"
MOOD = "ENERGISED"


def call(method: str, path: str, body: dict | None = None) -> dict:
    payload = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path,
        data=payload,
        method=method,
        headers={
            "X-User-Id": USER,
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        return json.loads(resp.read())


def main() -> int:
    print(f"New user: {USER}")
    print(f"Server:   {BASE}")

    mood = call("PUT", "/v1/users/me/mood", {"mood": MOOD, "persist": True})
    print(f"Mood set: {mood.get('active_mood')}")

    print("Generating discovery drop via home feed (may take 1-2 min)...")
    home = mood.get("home") or call("GET", "/v1/home")
    drop_mod = next(
        (m for m in home.get("modules", []) if m.get("type") == "discovery_drop"),
        None,
    )
    if not drop_mod:
        print("FAIL: no discovery_drop module in home response")
        return 1
    drop = drop_mod["data"]
    tracks = drop.get("tracks") or []
    llm = sum(1 for t in tracks if t.get("reason_method") == "LLM")
    tmpl = sum(1 for t in tracks if t.get("reason_method") == "TEMPLATE")

    print(f"\nDrop: {drop.get('drop_id')}")
    print(f"Header ({drop.get('header_method')}): {drop.get('header')!r}")
    print(f"Tracks: {len(tracks)} | LLM: {llm} | Template: {tmpl}")
    for track in tracks[:5]:
        print(
            f"  [{track.get('reason_method')}] {track.get('title')} — "
            f"{track.get('reason_text')!r}"
        )

    print(f"\nOpen UI: {BASE}/")
    print(f"  User id for API: {USER}")
    return 0 if llm else 1


if __name__ == "__main__":
    raise SystemExit(main())
