"""BFF edge cache for mood-keyed home responses."""

from __future__ import annotations

import json
import time
from typing import Any

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None


class HomeEdgeCache:
    PREFIX = "home:"

    def __init__(self, redis_url: str, ttl_seconds: int):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        self._memory: dict[str, tuple[float, dict[str, Any]]] = {}
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

    def _key(self, user_id: str, mood: str) -> str:
        return f"{self.PREFIX}{user_id}:{mood}"

    def get(self, user_id: str, mood: str) -> dict[str, Any] | None:
        key = self._key(user_id, mood)
        client = self._redis()
        if client:
            raw = client.get(key)
            return json.loads(raw) if raw else None

        entry = self._memory.get(key)
        if entry and entry[0] > time.time():
            return entry[1]
        return None

    def set(self, user_id: str, mood: str, payload: dict[str, Any]) -> None:
        key = self._key(user_id, mood)
        client = self._redis()
        if client:
            client.setex(key, self.ttl_seconds, json.dumps(payload))
            return
        self._memory[key] = (time.time() + self.ttl_seconds, payload)

    def invalidate(self, user_id: str, mood: str | None = None) -> None:
        client = self._redis()
        if mood is not None:
            keys = [self._key(user_id, mood)]
        elif client:
            keys = list(client.scan_iter(f"{self.PREFIX}{user_id}:*"))
        else:
            keys = [k for k in self._memory if k.startswith(f"{self.PREFIX}{user_id}:")]

        for key in keys:
            if client:
                client.delete(key)
            self._memory.pop(key, None)
