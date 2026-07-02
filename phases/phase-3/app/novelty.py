"""Novelty filter and diversity selector for Discovery Drop."""

from __future__ import annotations

from collections import Counter

from .repository import Phase1Repository


class NoveltyFilterService:
    def __init__(self, repository: Phase1Repository):
        self.repository = repository

    def exclude_played(self, user_id: str, candidates: list[dict]) -> list[dict]:
        played = self.repository.get_played_track_ids(user_id)
        recent_drop_tracks = self.repository.get_recent_drop_track_ids(user_id)
        heard_before = set()
        if hasattr(self.repository, "get_heard_before_track_ids"):
            heard_before = self.repository.get_heard_before_track_ids(user_id)
        excluded = played | recent_drop_tracks | heard_before
        return [item for item in candidates if item["track_id"] not in excluded]

    def select_diverse(self, candidates: list[dict], count: int = 10) -> list[dict]:
        artist_counts: Counter[str] = Counter()
        genre_counts: Counter[str] = Counter()
        selected: list[dict] = []

        def can_take(item: dict) -> bool:
            artist = item.get("artist_name") or "Unknown Artist"
            return artist_counts[artist] < 2

        first_pass = [item for item in candidates if item.get("genre")]
        for item in first_pass:
            if len(selected) >= count:
                break
            genre = item.get("genre")
            if genre_counts[genre] > 0:
                continue
            if not can_take(item):
                continue
            selected.append(item)
            artist_counts[item.get("artist_name") or "Unknown Artist"] += 1
            genre_counts[genre] += 1
            if len(genre_counts) >= 4:
                break

        for item in candidates:
            if len(selected) >= count:
                break
            if item["track_id"] in {track["track_id"] for track in selected}:
                continue
            if not can_take(item):
                continue
            selected.append(item)
            artist_counts[item.get("artist_name") or "Unknown Artist"] += 1
            genre_counts[item.get("genre") or "Unknown Genre"] += 1

        return selected[:count]
