"""LLM prewarm for fresh_picks and mood_mix module reasons."""

from __future__ import annotations

import hashlib
import json
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None


class LLMPrewarmService:
    CACHE_PREFIX = "llm:cache:"

    def __init__(self, repository, explanation_service, redis_url: str):
        self.repository = repository
        self.explanation_service = explanation_service
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

    def prewarm_user(self, user_id: str, mood: str, limit: int = 20) -> dict[str, Any]:
        candidates = self.repository.fetch_candidates(mood, limit=limit)[:limit]
        cached = 0
        client = self._redis()
        for track in candidates:
            prompt_hash = hashlib.sha256(
                f"{mood}:{track['track_id']}".encode("utf-8")
            ).hexdigest()
            if client and client.get(f"{self.CACHE_PREFIX}{prompt_hash}"):
                cached += 1
                continue
            _, _, enriched = self.explanation_service.attach(
                user_id=user_id,
                mood=mood,
                tracks=[track],
            )
            if client and enriched:
                client.setex(
                    f"{self.CACHE_PREFIX}{prompt_hash}",
                    6 * 3600,
                    json.dumps(enriched[0]),
                )
                cached += 1
        return {"user_id": user_id, "mood": mood, "prewarmed": cached}

    def prewarm_all_users(self) -> list[dict[str, Any]]:
        results = []
        for user_id in self.repository.list_known_users():
            mood = self.repository.get_active_mood(user_id, "LOW_KEY")
            results.append(self.prewarm_user(user_id, mood))
        return results
