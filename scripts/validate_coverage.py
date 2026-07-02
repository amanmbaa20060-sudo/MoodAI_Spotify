"""Validate mood coverage per docs/architecture.md §6.5."""

from __future__ import annotations

import argparse
import ast
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from db import connect  # noqa: E402
from mood_rules import DATASET_MOODS  # noqa: E402

MIN_PER_MOOD = 200
MIN_TAGGED_RATIO = 0.8
MIN_TOTAL_TRACKS = 1000
MIN_TAGGED_ABSOLUTE = 1000


def _parse_mood_tags(value) -> list:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        return ast.literal_eval(value)
    return list(value)


def validate_df(tags: pd.DataFrame, total_tracks: int) -> list[str]:
    errors: list[str] = []

    if total_tracks < MIN_TOTAL_TRACKS:
        errors.append(f"Total tracks {total_tracks} < {MIN_TOTAL_TRACKS}")

    if "ADVENTUROUS" in tags.get("primary_mood", pd.Series(dtype=str)).values:
        errors.append("ADVENTUROUS must not appear in primary_mood")

    for _, row in tags.iterrows():
        for tag in _parse_mood_tags(row.get("mood_tags")):
            if tag == "ADVENTUROUS":
                errors.append(f"ADVENTUROUS in mood_tags for track {row['track_id']}")
                break

    tagged = tags[tags["primary_mood"].notna()]
    tagged_count = len(tagged)
    if total_tracks:
        tagged_ratio = tagged_count / total_tracks
        if tagged_count < MIN_TAGGED_ABSOLUTE and tagged_ratio < MIN_TAGGED_RATIO:
            errors.append(
                f"Tagged tracks {tagged_count} < {MIN_TAGGED_ABSOLUTE} "
                f"and ratio {tagged_ratio:.1%} < {MIN_TAGGED_RATIO:.0%}"
            )

    for mood in DATASET_MOODS:
        count = tags["mood_tags"].apply(lambda t, m=mood: m in _parse_mood_tags(t)).sum()
        if count < MIN_PER_MOOD:
            errors.append(f"{mood}: {count} tracks (need >= {MIN_PER_MOOD})")

    return errors


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Validate tagged CSV instead of database")
    args = parser.parse_args()

    if args.csv:
        tags = pd.read_csv(args.csv)
        tags["mood_tags"] = tags["mood_tags"].apply(_parse_mood_tags)
        total = len(tags)
    else:
        url = os.environ.get("DATABASE_URL")
        if not url:
            print("DATABASE_URL not set", file=sys.stderr)
            return 1
        conn = connect(url)
        tags = pd.read_sql("SELECT * FROM track_mood_tags", conn)
        tags["mood_tags"] = tags["mood_tags"].apply(_parse_mood_tags)
        total = int(pd.read_sql("SELECT COUNT(*) AS c FROM tracks", conn)["c"].iloc[0])
        conn.close()

    errors = validate_df(tags, total)
    if errors:
        print("VALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("VALIDATION PASSED")
    tagged = tags[tags["primary_mood"].notna()]
    print(f"  Catalog: {total} tracks | Mood-tagged: {len(tagged)} ({len(tagged)/total:.1%})")
    for mood in DATASET_MOODS:
        count = tags["mood_tags"].apply(lambda t, m=mood: m in _parse_mood_tags(t)).sum()
        print(f"  {mood}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
