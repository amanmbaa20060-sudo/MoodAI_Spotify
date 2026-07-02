"""Candidate pool prewarm — Redis cache for ranker inputs."""

from __future__ import annotations

import json
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None


class CandidatePrewarmService:
    PREFIX = "candidates:"

    def __init__(self, repository, ranker, redis_url: str):
        self.repository = repository
        self.ranker = ranker
        self.redis_url = redis_url
        self._client = None

    def _redis(self):
        if redis is None:
            return None
        if self._client is None:
            try:
                client = redis.from_url(self.redis_url, decode_responses=True)
                client.ping()
                self._client = client
            except Exception:
                self._client = False
        return self._client if self._client is not False else None

    def prewarm_user(self, user_id: str, mood: str, limit: int = 120) -> dict[str, Any]:
        candidates = self.repository.fetch_candidates(mood, limit=limit)
        scored = self.ranker.score(candidates, mood)
        client = self._redis()
        key = f"{self.PREFIX}{user_id}:{mood}"
        if client:
            client.setex(key, 6 * 3600, json.dumps(scored))
        return {"user_id": user_id, "mood": mood, "cached": len(scored)}

    def get_cached(self, user_id: str, mood: str) -> list[dict[str, Any]] | None:
        client = self._redis()
        if not client:
            return None
        raw = client.get(f"{self.PREFIX}{user_id}:{mood}")
        return json.loads(raw) if raw else None

    def prewarm_all_users(self) -> list[dict[str, Any]]:
        results = []
        for user_id in self.repository.list_known_users():
            mood = self.repository.get_active_mood(user_id, "LOW_KEY")
            results.append(self.prewarm_user(user_id, mood))
        return results
