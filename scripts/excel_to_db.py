"""Load Excel/CSV catalog into PostgreSQL with mood tags."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
from build_mood_buckets import normalize_columns, tag_tracks  # noqa: E402
from db import connect, execute_values, to_pg_text_array  # noqa: E402
from mood_rules import DATASET_MOODS  # noqa: E402


def load_catalog(path: Path) -> pd.DataFrame:
    if path.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"Unsupported file type: {path}")


def write_manifest(
    path: Path,
    tags: pd.DataFrame,
    total: int,
    dataset_version: str,
    source: str,
) -> None:
    mood_counts = {
        mood: int(tags["mood_tags"].apply(lambda t, m=mood: m in t).sum())
        for mood in DATASET_MOODS
    }
    tagged = int(tags["primary_mood"].notna().sum())
    manifest = {
        "dataset_version": dataset_version,
        "source": source,
        "track_count": total,
        "mood_tagged_count": tagged,
        "mood_coverage": mood_counts,
        "adventurous_tags": 0,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Wrote {path}")


def upsert_tracks(conn, df: pd.DataFrame) -> None:
    cols = [
        "track_id", "name", "artist_name", "album_name", "genre",
        "energy", "valence", "tempo", "instrumentalness",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    rows = [tuple(row.get(c) for c in cols) for row in df.to_dict(orient="records")]
    sql = """
        INSERT INTO tracks (track_id, name, artist_name, album_name, genre,
                            energy, valence, tempo, instrumentalness)
        VALUES %s
        ON CONFLICT (track_id) DO UPDATE SET
            name = EXCLUDED.name,
            artist_name = EXCLUDED.artist_name,
            album_name = EXCLUDED.album_name,
            genre = EXCLUDED.genre,
            energy = EXCLUDED.energy,
            valence = EXCLUDED.valence,
            tempo = EXCLUDED.tempo,
            instrumentalness = EXCLUDED.instrumentalness
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()


def upsert_mood_tags(conn, tags: pd.DataFrame) -> None:
    def mood_tags_value(raw) -> Any:
        items = list(raw) if raw is not None else []
        if type(conn).__module__.startswith("psycopg"):
            return items
        return to_pg_text_array(items)

    rows = [
        (
            r.track_id,
            r.primary_mood,
            mood_tags_value(r.mood_tags),
            r.energy,
            r.valence,
            r.tempo,
            r.instrumentalness,
            r.dataset_version,
        )
        for r in tags.itertuples(index=False)
    ]
    sql = """
        INSERT INTO track_mood_tags
            (track_id, primary_mood, mood_tags, energy, valence, tempo,
             instrumentalness, dataset_version)
        VALUES %s
        ON CONFLICT (track_id) DO UPDATE SET
            primary_mood = EXCLUDED.primary_mood,
            mood_tags = EXCLUDED.mood_tags,
            energy = EXCLUDED.energy,
            valence = EXCLUDED.valence,
            tempo = EXCLUDED.tempo,
            instrumentalness = EXCLUDED.instrumentalness,
            dataset_version = EXCLUDED.dataset_version,
            tagged_at = NOW()
    """
    with conn.cursor() as cur:
        execute_values(cur, sql, rows)
    conn.commit()


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Load Excel/CSV tracks into Postgres")
    parser.add_argument(
        "--source",
        default=os.getenv("EXCEL_SOURCE_PATH", "data/source/Music_Data.csv"),
        help="Path to .xlsx or .csv",
    )
    parser.add_argument(
        "--dataset-version",
        default=os.getenv("DATASET_VERSION", "v1.1.0"),
    )
    parser.add_argument("--dry-run", action="store_true", help="Tag only; no DB write")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        print(f"Source not found: {source}", file=sys.stderr)
        return 1

    print(f"Loading {source}...")
    raw = load_catalog(source)
    tracks = normalize_columns(raw)
    tags = tag_tracks(tracks, args.dataset_version)

    tagged_count = int(tags["primary_mood"].notna().sum())
    print(f"Tracks: {len(tracks)} | Mood-tagged: {tagged_count}")
    for mood in DATASET_MOODS:
        n = int(tags["mood_tags"].apply(lambda t, m=mood: m in t).sum())
        print(f"  {mood}: {n}")

    out_csv = Path("data/seed/v1/track_mood_tags.csv")
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    tags.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv}")

    write_manifest(
        Path("data/dataset_manifest.json"),
        tags,
        len(tracks),
        args.dataset_version,
        str(source),
    )

    if args.dry_run:
        return 0

    url = os.getenv("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set — dry-run only or set .env", file=sys.stderr)
        return 1

    conn = connect(url)
    try:
        upsert_tracks(conn, tracks)
        upsert_mood_tags(conn, tags)
        print("Database load complete.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
