"""Apply §6.5 mood bucketing to a tracks DataFrame."""

from __future__ import annotations

import pandas as pd

from mood_rules import AUDIO_FEATURES, assign_dataset_moods


COLUMN_ALIASES = {
    "track_id": ["track_id", "id", "trackid", "spotify_id", "uri"],
    "name": ["name", "track_name", "title", "song"],
    "artist_name": ["artist_name", "artist", "artists"],
    "album_name": ["album_name", "album"],
    "genre": ["genre", "genres", "track_genre"],
    "energy": ["energy"],
    "valence": ["valence"],
    "tempo": ["tempo"],
    "instrumentalness": ["instrumentalness", "instrumental"],
}


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    lower_map = {c.lower().strip(): c for c in df.columns}
    out = df.copy()
    rename: dict[str, str] = {}
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_map:
                rename[lower_map[alias]] = canonical
                break
    out = out.rename(columns=rename)
    missing = [c for c in ["track_id", *AUDIO_FEATURES] if c not in out.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}. Found: {list(df.columns)}")
    return out


def tag_tracks(df: pd.DataFrame, dataset_version: str) -> pd.DataFrame:
    df = normalize_columns(df)
    for col in AUDIO_FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["track_id", *AUDIO_FEATURES])
    df["track_id"] = df["track_id"].astype(str)

    rows = []
    for row in df.to_dict(orient="records"):
        primary, tags = assign_dataset_moods(row)
        rows.append(
            {
                "track_id": row["track_id"],
                "primary_mood": primary,
                "mood_tags": tags,
                "energy": row["energy"],
                "valence": row["valence"],
                "tempo": row["tempo"],
                "instrumentalness": row["instrumentalness"],
                "dataset_version": dataset_version,
            }
        )
    return pd.DataFrame(rows)
