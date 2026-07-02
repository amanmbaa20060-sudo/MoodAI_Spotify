"""Generate a synthetic catalog that satisfies Phase 0 coverage targets (§6.5)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from build_mood_buckets import tag_tracks  # noqa: E402
from mood_rules import DATASET_MOODS, assign_dataset_moods, mood_matches  # noqa: E402

MOOD_PROFILES: dict[str, dict[str, tuple[float, float]]] = {
    "ENERGISED": {
        "energy": (0.71, 0.95),
        "valence": (0.61, 0.9),
        "tempo": (121, 180),
        "instrumentalness": (0.0, 0.4),
    },
    "FOCUSED": {
        "energy": (0.31, 0.59),
        "valence": (0.41, 0.59),
        "tempo": (81, 109),
        "instrumentalness": (0.51, 0.95),
    },
    "LOW_KEY": {
        "energy": (0.05, 0.39),
        "valence": (0.31, 0.59),
        "tempo": (60, 99),
        "instrumentalness": (0.0, 0.5),
    },
    "NOSTALGIC": {
        "energy": (0.31, 0.59),
        "valence": (0.41, 0.69),
        "tempo": (70, 130),
        "instrumentalness": (0.0, 0.5),
    },
    "SAD": {
        "energy": (0.05, 0.34),
        "valence": (0.05, 0.34),
        "tempo": (60, 99),
        "instrumentalness": (0.0, 0.4),
    },
}

GENRES = [
    "indie rock", "pop", "jazz", "classical", "electronic",
    "soul", "ambient", "folk", "hip hop", "r&b",
]


def _sample(rng: np.random.Generator, low: float, high: float) -> float:
    return float(rng.uniform(low, high))


def generate_for_mood(rng: np.random.Generator, mood: str, count: int, start_id: int) -> list[dict]:
    profile = MOOD_PROFILES[mood]
    rows: list[dict] = []
    attempts = 0
    i = start_id
    while len(rows) < count and attempts < count * 20:
        attempts += 1
        track = {
            "track_id": f"track_{i:06d}",
            "name": f"Sample Track {i}",
            "artist_name": f"Artist {rng.integers(1, 200)}",
            "album_name": f"Album {rng.integers(1, 100)}",
            "genre": rng.choice(GENRES),
            "energy": _sample(rng, *profile["energy"]),
            "valence": _sample(rng, *profile["valence"]),
            "tempo": _sample(rng, *profile["tempo"]),
            "instrumentalness": _sample(rng, *profile["instrumentalness"]),
        }
        if mood_matches(track, mood):
            rows.append(track)
            i += 1
    if len(rows) < count:
        raise RuntimeError(f"Could only generate {len(rows)}/{count} tracks for {mood}")
    return rows


def generate_catalog(per_mood: int = 250, extra_untagged: int = 100, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    all_rows: list[dict] = []
    next_id = 1
    for mood in DATASET_MOODS:
        batch = generate_for_mood(rng, mood, per_mood, next_id)
        all_rows.extend(batch)
        next_id += len(batch)

    for _ in range(extra_untagged):
        track = {
            "track_id": f"track_{next_id:06d}",
            "name": f"Untagged Track {next_id}",
            "artist_name": f"Artist {rng.integers(1, 200)}",
            "album_name": f"Album {rng.integers(1, 100)}",
            "genre": rng.choice(GENRES),
            "energy": float(rng.uniform(0.5, 0.65)),
            "valence": float(rng.uniform(0.2, 0.8)),
            "tempo": float(rng.uniform(100, 115)),
            "instrumentalness": float(rng.uniform(0.2, 0.45)),
        }
        primary, tags = assign_dataset_moods(track)
        if not tags:
            all_rows.append(track)
            next_id += 1

    df = pd.DataFrame(all_rows)
    return df.drop_duplicates(subset=["track_id"]).reset_index(drop=True)


def write_manifest(path: Path, df: pd.DataFrame, dataset_version: str) -> None:
    tags = tag_tracks(df, dataset_version)
    mood_counts = {
        mood: int(tags["mood_tags"].apply(lambda t, m=mood: m in t).sum())
        for mood in DATASET_MOODS
    }
    manifest = {
        "dataset_version": dataset_version,
        "track_count": len(df),
        "mood_coverage": mood_counts,
        "adventurous_tags": 0,
        "source": "generate_sample_catalog.py",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-mood", type=int, default=250)
    parser.add_argument("--dataset-version", default="v1.0.0")
    parser.add_argument(
        "--output-csv",
        default="data/seed/v1/sample_tracks.csv",
    )
    parser.add_argument(
        "--output-xlsx",
        default="data/source/tracks.xlsx",
    )
    args = parser.parse_args()

    df = generate_catalog(per_mood=args.per_mood)
    csv_path = Path(args.output_csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)
    print(f"Wrote {csv_path} ({len(df)} tracks)")

    xlsx_path = Path(args.output_xlsx)
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(xlsx_path, index=False)
    print(f"Wrote {xlsx_path}")

    manifest_path = Path("data/dataset_manifest.json")
    write_manifest(manifest_path, df, args.dataset_version)
    print(f"Wrote {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
