"""In-memory repository for local UI demo when Postgres is unavailable."""

from __future__ import annotations

import csv
import hashlib
import sys
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phases.common.db import database_is_available  # noqa: E402
from scripts.mood_rules import assign_dataset_moods  # noqa: E402

SAMPLE_CATALOG = ROOT / "data" / "seed" / "v1" / "sample_tracks.csv"


def should_use_demo_mode(database_url: str) -> bool:
    import os

    forced = os.getenv("MOODAI_DEMO_MODE", "").lower() in {"1", "true", "yes", "on"}
    if forced:
        return True
    disabled = os.getenv("MOODAI_DEMO_MODE", "").lower() in {"0", "false", "no", "off"}
    if disabled:
        return False
    return not database_is_available(database_url)


class DemoRepository:
    """Serves bundled sample catalog data without PostgreSQL."""

    @staticmethod
    def _artist_id(name: str) -> str:
        return hashlib.md5((name or "unknown").lower().encode("utf-8")).hexdigest()

    def __init__(self) -> None:
        self._moods: dict[str, str] = {}
        self._drops: dict[tuple[str, date], dict[str, Any]] = {}
        self._played: dict[str, set[str]] = {}
        self._heard_before: dict[str, set[str]] = {}
        self._audit: list[dict[str, Any]] = []
        self._tokens: dict[tuple[str, date], int] = {}
        self._tracks = self._load_catalog()

    @staticmethod
    def _load_catalog() -> list[dict[str, Any]]:
        import os

        catalog_path = os.getenv("MOODAI_CATALOG_CSV") or os.getenv("EXCEL_SOURCE_PATH")
        if catalog_path:
            path = Path(catalog_path)
            if not path.is_absolute():
                path = ROOT / path
            if path.exists() and path.name.lower() != "sample_tracks.csv":
                tracks = DemoRepository._load_from_catalog_file(path)
                if tracks:
                    print(f"MoodAI local catalog: loaded {len(tracks):,} tracks from {path.name}")
                    return tracks

        if not SAMPLE_CATALOG.exists():
            return DemoRepository._synthetic_catalog()

        tracks: list[dict[str, Any]] = []
        with SAMPLE_CATALOG.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                features = {
                    "energy": float(row["energy"]),
                    "valence": float(row["valence"]),
                    "tempo": float(row["tempo"]),
                    "instrumentalness": float(row["instrumentalness"]),
                }
                primary, tags = assign_dataset_moods(features)
                tracks.append(
                    {
                        "track_id": row["track_id"],
                        "title": row["name"],
                        "artist_name": row["artist_name"],
                        "album_name": row["album_name"],
                        "genre": row["genre"],
                        "primary_mood": primary or "LOW_KEY",
                        "mood_tags": tags or ([primary] if primary else ["LOW_KEY"]),
                        **features,
                        "base_rec_score": 0.7,
                    }
                )
        print(f"MoodAI local catalog: loaded {len(tracks):,} sample tracks")
        return tracks

    @staticmethod
    def _load_from_catalog_file(path: Path) -> list[dict[str, Any]]:
        import os

        import pandas as pd

        scripts_dir = ROOT / "scripts"
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from build_mood_buckets import normalize_columns, tag_tracks  # noqa: WPS433

        df = pd.read_csv(path)
        df = normalize_columns(df)
        tagged = tag_tracks(df, os.getenv("DATASET_VERSION", "local"))
        tag_by_id = {str(row["track_id"]): row for row in tagged.to_dict(orient="records")}

        tracks: list[dict[str, Any]] = []
        for row in df.to_dict(orient="records"):
            track_id = str(row["track_id"])
            tag = tag_by_id.get(track_id)
            if tag is None:
                continue
            artist = str(row.get("artist_name") or "Unknown")
            if ";" in artist:
                artist = artist.split(";")[0].strip()
            tracks.append(
                {
                    "track_id": track_id,
                    "title": str(row.get("name") or "Unknown"),
                    "artist_name": artist,
                    "album_name": str(row.get("album_name") or ""),
                    "genre": str(row.get("genre") or ""),
                    "primary_mood": tag["primary_mood"] or "LOW_KEY",
                    "mood_tags": tag["mood_tags"] or ["LOW_KEY"],
                    "energy": float(row["energy"]),
                    "valence": float(row["valence"]),
                    "tempo": float(row["tempo"]),
                    "instrumentalness": float(row["instrumentalness"]),
                    "base_rec_score": 0.7,
                }
            )
        return tracks

    @staticmethod
    def _synthetic_catalog() -> list[dict[str, Any]]:
        moods = ["ENERGISED", "FOCUSED", "LOW_KEY", "NOSTALGIC", "SAD"]
        genres = ["indie", "rock", "jazz", "electronic", "ambient"]
        return [
            {
                "track_id": f"track-{idx}",
                "title": f"Track {idx}",
                "artist_name": f"Artist {idx % 12}",
                "album_name": f"Album {idx}",
                "genre": genres[idx % len(genres)],
                "primary_mood": moods[idx % len(moods)],
                "mood_tags": [moods[idx % len(moods)]],
                "energy": 0.2 + (idx % 5) * 0.1,
                "valence": 0.2 + (idx % 4) * 0.1,
                "tempo": 70 + idx,
                "instrumentalness": 0.1 * (idx % 6),
                "base_rec_score": 0.6,
            }
            for idx in range(200)
        ]

    def get_active_mood(self, user_id: str, default_mood: str) -> str:
        return self._moods.get(user_id, default_mood)

    def set_active_mood(self, user_id: str, mood: str, persist: bool) -> None:
        self._moods[user_id] = mood

    def fetch_candidates(self, mood: str, limit: int = 300) -> list[dict[str, Any]]:
        if mood == "ADVENTUROUS":
            pool = list(self._tracks)
        else:
            pool = [
                track
                for track in self._tracks
                if track["primary_mood"] == mood or mood in track["mood_tags"]
            ]
            if not pool:
                pool = list(self._tracks)
        return [{**track} for track in pool[:limit]]

    def get_played_track_ids(self, user_id: str) -> set[str]:
        return set(self._played.get(user_id, set()))

    def get_recent_drop_track_ids(self, user_id: str, days: int = 7) -> set[str]:
        cutoff = date.today() - timedelta(days=days)
        ids: set[str] = set()
        for (uid, drop_date), drop in self._drops.items():
            if uid != user_id or drop_date < cutoff:
                continue
            ids.update(track["track_id"] for track in drop.get("tracks", []))
        return ids

    def list_drop(self, user_id: str, drop_date: date) -> dict[str, Any] | None:
        return self._drops.get((user_id, drop_date))

    def save_drop(
        self,
        user_id: str,
        active_mood: str,
        header: str,
        header_method: str,
        tracks: list[dict[str, Any]],
        drop_date: date,
    ) -> dict[str, Any]:
        drop = {
            "drop_id": f"demo-drop-{user_id}-{drop_date.isoformat()}",
            "drop_date": drop_date,
            "mood_at_generation": active_mood,
            "drop_header": header,
            "header_method": header_method,
            "status": "READY",
            "tracks": [
                {
                    "position": index + 1,
                    "track_id": track["track_id"],
                    "title": track["title"],
                    "artist_name": track.get("artist_name"),
                    "album_name": track.get("album_name"),
                    "genre": track.get("genre"),
                    "reason_text": track["reason_text"],
                    "reason_feature_id": track["reason_feature_id"],
                    "reason_method": track["reason_method"],
                    "base_score": track.get("score", track.get("base_rec_score", 0.5)),
                }
                for index, track in enumerate(tracks)
            ],
        }
        self._drops[(user_id, drop_date)] = drop
        return drop

    def insert_explanation_audit_log(self, **kwargs: Any) -> None:
        self._audit.append(kwargs)

    def list_known_users(self) -> list[str]:
        users = set(self._moods) | set(self._played) | {"demo-user"}
        return sorted(users)

    @staticmethod
    def next_refresh_at() -> datetime:
        tomorrow = date.today() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time()).replace(
            hour=6, tzinfo=timezone.utc
        )

    def search_artists(self, query: str, limit: int = 24) -> list[dict[str, Any]]:
        needle = query.lower().strip()
        artists: dict[str, dict[str, Any]] = {}
        for track in self._tracks:
            name = track["artist_name"] or "Unknown"
            if needle and needle not in name.lower():
                continue
            bucket = artists.setdefault(
                name,
                {
                    "artist_id": self._artist_id(name),
                    "artist_name": name,
                    "track_count": 0,
                    "top_genre": track.get("genre"),
                },
            )
            bucket["track_count"] += 1
        rows = sorted(artists.values(), key=lambda row: (-row["track_count"], row["artist_name"]))
        return rows[:limit]

    def get_artist_with_tracks(
        self, artist_id: str, limit: int = 100
    ) -> dict[str, Any] | None:
        matched_name: str | None = None
        tracks: list[dict[str, Any]] = []
        genres: dict[str, int] = {}

        for track in self._tracks:
            name = track["artist_name"] or "Unknown"
            if self._artist_id(name) != artist_id:
                continue
            matched_name = name
            genre = track.get("genre")
            if genre:
                genres[genre] = genres.get(genre, 0) + 1
            tracks.append(
                {
                    "track_id": track["track_id"],
                    "title": track["title"],
                    "artist_name": name,
                    "album_name": track.get("album_name"),
                    "genre": genre,
                }
            )

        if matched_name is None:
            return None

        tracks.sort(key=lambda row: row["title"])
        top_genre = max(genres, key=genres.get) if genres else None
        return {
            "artist_id": artist_id,
            "artist_name": matched_name,
            "artist_image_url": None,
            "track_count": len(tracks),
            "top_genre": top_genre,
            "tracks": tracks[:limit],
        }

    def record_heard_before(
        self, user_id: str, track_id: str, drop_id: str | None = None
    ) -> str:
        self._heard_before.setdefault(user_id, set()).add(track_id)
        return str(uuid.uuid4())

    def get_heard_before_track_ids(self, user_id: str) -> set[str]:
        return set(self._heard_before.get(user_id, set()))

    def upsert_push_subscription(self, user_id: str, endpoint: str) -> None:
        return None

    def get_push_subscription(self, user_id: str) -> dict[str, Any] | None:
        return None

    def log_push_notification(self, **kwargs: Any) -> None:
        return None

    def list_explanation_audit(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        return [row for row in self._audit if row.get("user_id") == user_id][:limit]

    def get_dominant_play_mood(self, user_id: str) -> str | None:
        mood = self._moods.get(user_id)
        return mood if mood in {"ENERGISED", "FOCUSED", "LOW_KEY", "NOSTALGIC", "SAD"} else "FOCUSED"

    def get_experiment_variant(self, user_id: str, flag_name: str, default: str) -> str:
        return default

    def get_llm_tokens_used(self, user_id: str, usage_date: date) -> int:
        return self._tokens.get((user_id, usage_date), 0)

    def add_llm_token_usage(self, user_id: str, usage_date: date, tokens: int) -> int:
        key = (user_id, usage_date)
        self._tokens[key] = self._tokens.get(key, 0) + tokens
        return self._tokens[key]
