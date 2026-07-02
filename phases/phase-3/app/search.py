"""Visual-first artist search adapter."""

from __future__ import annotations

import hashlib
from typing import Any


def artist_image_url(artist_name: str) -> str:
    """Deterministic placeholder image URL when catalog has no CDN asset."""
    digest = hashlib.md5(artist_name.lower().encode("utf-8")).hexdigest()
    return f"https://picsum.photos/seed/{digest}/300/300"


class VisualSearchAdapter:
    def __init__(self, repository):
        self.repository = repository

    def search_artists(self, query: str, limit: int = 24) -> list[dict[str, Any]]:
        rows = self.repository.search_artists(query, limit=limit)
        results: list[dict[str, Any]] = []
        for row in rows:
            image = row.get("artist_image_url") or artist_image_url(row["artist_name"])
            results.append(
                {
                    "artist_id": row["artist_id"],
                    "name": row["artist_name"],
                    "image_url": image,
                    "image_alt": f"Artist portrait for {row['artist_name']}",
                    "track_count": int(row["track_count"]),
                    "top_genre": row.get("top_genre"),
                }
            )
        return results
