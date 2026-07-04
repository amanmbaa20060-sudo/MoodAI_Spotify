"""Visual-first artist search adapter."""

from __future__ import annotations

import hashlib
from typing import Any


def artist_image_url(artist_name: str) -> str:
    """Deterministic placeholder image URL when catalog has no CDN asset."""
    digest = hashlib.md5(artist_name.lower().encode("utf-8")).hexdigest()
    return f"https://picsum.photos/seed/{digest}/300/300"


def artist_id_for_name(artist_name: str) -> str:
    return hashlib.md5((artist_name or "unknown").lower().encode("utf-8")).hexdigest()


class VisualSearchAdapter:
    def __init__(self, repository):
        self.repository = repository

    def search_artists(self, query: str, limit: int = 24) -> list[dict[str, Any]]:
        rows = self.repository.search_artists(query, limit=limit)
        return [self._map_artist_summary(row) for row in rows]

    def get_artist(self, artist_id: str, limit: int = 100) -> dict[str, Any] | None:
        row = self.repository.get_artist_with_tracks(artist_id, limit=limit)
        if row is None:
            return None
        return self._map_artist_detail(row)

    def get_artist_by_name(self, artist_name: str, limit: int = 100) -> dict[str, Any] | None:
        return self.get_artist(artist_id_for_name(artist_name), limit=limit)

    @staticmethod
    def _map_artist_detail(row: dict[str, Any]) -> dict[str, Any]:
        image = row.get("artist_image_url") or artist_image_url(row["artist_name"])
        tracks = [
            {
                "track_id": track["track_id"],
                "title": track["title"],
                "artists": [track["artist_name"]] if track.get("artist_name") else [],
                "album_name": track.get("album_name"),
                "genre": track.get("genre"),
            }
            for track in row.get("tracks", [])
        ]
        return {
            "artist_id": row["artist_id"],
            "name": row["artist_name"],
            "image_url": image,
            "image_alt": f"Artist portrait for {row['artist_name']}",
            "track_count": int(row["track_count"]),
            "top_genre": row.get("top_genre"),
            "tracks": tracks,
        }

    @staticmethod
    def _map_artist_summary(row: dict[str, Any]) -> dict[str, Any]:
        image = row.get("artist_image_url") or artist_image_url(row["artist_name"])
        return {
            "artist_id": row["artist_id"],
            "name": row["artist_name"],
            "image_url": image,
            "image_alt": f"Artist portrait for {row['artist_name']}",
            "track_count": int(row["track_count"]),
            "top_genre": row.get("top_genre"),
        }
