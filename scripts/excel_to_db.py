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


def _clip(value: Any, max_len: int) -> Any:
    if value is None or not isinstance(value, str):
        return value
    return value[:max_len]


def upsert_tracks(conn, df: pd.DataFrame) -> None:
    cols = [
        "track_id", "name", "artist_name", "album_name", "genre",
        "energy", "valence", "tempo", "instrumentalness",
    ]
    for c in cols:
        if c not in df.columns:
            df[c] = None
    before = len(df)
    df = df.drop_duplicates(subset=["track_id"], keep="last")
    dropped = before - len(df)
    if dropped:
        print(f"Dropped {dropped} duplicate track_id rows before upsert")
    rows = [
        (
            _clip(row.get("track_id"), 128),
            _clip(row.get("name"), 512),
            _clip(row.get("artist_name"), 512),
            _clip(row.get("album_name"), 512),
            _clip(row.get("genre"), 256),
            row.get("energy"),
            row.get("valence"),
            row.get("tempo"),
            row.get("instrumentalness"),
        )
        for row in df.to_dict(orient="records")
    ]
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
        execute_values(cur, sql, rows, page_size=200, conn=conn)


def _is_transient_db_error(exc: Exception) -> bool:
    err = str(exc).lower()
    return any(token in err for token in ("network", "ssl", "interface", "connection", "timeout"))


def upsert_mood_tags(conn, tags: pd.DataFrame, url: str) -> None:
    before = len(tags)
    tags = tags.drop_duplicates(subset=["track_id"], keep="last")
    dropped = before - len(tags)
    if dropped:
        print(f"Dropped {dropped} duplicate track_id rows before mood tag upsert")

    use_psycopg = type(conn).__module__.startswith("psycopg")

    def mood_tags_value(raw) -> Any:
        items = list(raw) if raw is not None else []
        if use_psycopg:
            return items
        return to_pg_text_array(items)

    rows = [
        (
            _clip(r.track_id, 128),
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

    with conn.cursor() as cur:
        cur.execute("SELECT track_id FROM track_mood_tags")
        existing = {row[0] for row in cur.fetchall()}
    if existing:
        print(f"Resuming mood tags: {len(existing)} already in database")
        rows = [row for row in rows if row[0] not in existing]
    if not rows:
        print("Mood tags already complete.")
        return

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
    page_size = 100
    total = len(existing) + len(rows)
    done = len(existing)
    index = 0
    while index < len(rows):
        chunk = rows[index : index + page_size]
        for attempt in range(6):
            try:
                with conn.cursor() as cur:
                    execute_values(cur, sql, chunk, page_size=len(chunk), conn=conn)
                index += len(chunk)
                done += len(chunk)
                if done % 2000 < page_size or index >= len(rows):
                    print(f"  ... {done}/{total} mood tags")
                break
            except Exception as exc:
                if not _is_transient_db_error(exc) or attempt + 1 >= 6:
                    raise
                try:
                    conn.close()
                except Exception:
                    pass
                import time

                time.sleep(min(30, 2 ** attempt))
                conn = connect(url)
                use_psycopg = type(conn).__module__.startswith("psycopg")


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
    parser.add_argument(
        "--skip-tracks",
        action="store_true",
        help="Skip track upsert (resume mood tags only)",
    )
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
        if not args.skip_tracks:
            upsert_tracks(conn, tracks)
        upsert_mood_tags(conn, tags, url)
        print("Database load complete.")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
