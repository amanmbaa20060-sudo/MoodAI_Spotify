#!/usr/bin/env python3
"""Verify Groq LLM is configured and responding."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv

load_dotenv(ROOT / ".env")

from phases.common.config import Settings  # noqa: E402
from phases.common.db import connect  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "explanations",
    ROOT / "phases" / "phase-3" / "app" / "explanations.py",
)
explanations = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(explanations)
GroqLLMGateway = explanations.GroqLLMGateway


def main() -> int:
    settings = Settings()
    print("LLM configuration")
    print(f"  provider: {settings.llm_provider}")
    print(f"  model:    {settings.groq_model}")
    print(f"  base_url: {settings.groq_base_url}")
    print(
        f"  api_key:  {'set (' + settings.groq_api_key[:8] + '...)' if settings.groq_api_key else 'MISSING'}"
    )

    if not settings.groq_api_key:
        print("\nFAIL: GROQ_API_KEY not set")
        return 1

    sample_tracks = [
        {
            "track_id": "test_1",
            "title": "Blinding Lights",
            "artist_name": "The Weeknd",
            "genre": "pop",
            "primary_mood": "ENERGISED",
        }
    ]

    print("\nCalling Groq API...")
    gateway = GroqLLMGateway(settings)
    try:
        result = gateway.generate_drop_explanations("ENERGISED", sample_tracks)
        print("OK Groq response received")
        print(f"  header:  {result.get('header')!r}")
        print(f"  reasons: {result.get('reasons')}")
    except Exception as exc:
        print(f"FAIL Groq call: {type(exc).__name__}: {exc}")
        return 1

    url = os.getenv("DATABASE_URL")
    if url:
        print("\nExplanation usage in DB:")
        try:
            with connect(url) as conn, conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT generation_method, model_id, COUNT(*) AS n
                    FROM explanation_audit_log
                    GROUP BY generation_method, model_id
                    ORDER BY n DESC
                    """
                )
                rows = cur.fetchall()
                if rows:
                    for method, model, count in rows:
                        print(f"  {method}: {count} (model={model})")
                else:
                    print("  (no audit rows yet)")

                cur.execute(
                    """
                    SELECT generation_method, rendered_text, created_at
                    FROM explanation_audit_log
                    ORDER BY created_at DESC
                    LIMIT 5
                    """
                )
                recent = cur.fetchall()
                if recent:
                    print("\nLatest explanations:")
                    for method, text, created in recent:
                        print(f"  [{method}] {text!r}")
        except Exception as exc:
            print(f"  DB check skipped: {exc}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
