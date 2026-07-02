"""Phase 3 tests — caching, smart mood, sharding, token budget."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
PHASE3_DIR = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PHASE3_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE3_DIR))

from phases.common.test_utils import load_phase_module  # noqa: E402

load_phase_module("phase-3", "app.edge_cache")
from app.candidate_prewarm import CandidatePrewarmService  # noqa: E402
from app.drop_sharding import user_partition, users_for_partition  # noqa: E402
from app.edge_cache import HomeEdgeCache  # noqa: E402
from app.smart_mood import SmartMoodDefaultService  # noqa: E402
from app.token_budget import TokenBudgetService  # noqa: E402


class FakeRepo:
    def __init__(self):
        self.tokens = 0
        self.mood = "FOCUSED"

    def get_dominant_play_mood(self, user_id: str):
        return self.mood

    def get_active_mood(self, user_id: str, default: str):
        return default

    def fetch_candidates(self, mood: str, limit: int = 300):
        return [{"track_id": f"t{i}", "primary_mood": mood, "genre": "jazz", "base_rec_score": 0.5} for i in range(5)]

    def list_known_users(self):
        return ["u1", "u2", "u3"]

    def get_llm_tokens_used(self, user_id: str, usage_date):
        return self.tokens

    def add_llm_token_usage(self, user_id: str, usage_date, tokens: int):
        self.tokens += tokens
        return self.tokens


class FakeRanker:
    def score(self, candidates, mood):
        return [{**c, "score": 1.0} for c in candidates]


def test_home_edge_cache_roundtrip():
    cache = HomeEdgeCache("redis://unused", ttl_seconds=60)
    payload = {"user_id": "demo", "active_mood": "LOW_KEY"}
    cache.set("demo", "LOW_KEY", payload)
    assert cache.get("demo", "LOW_KEY") == payload
    cache.invalidate("demo", "LOW_KEY")
    assert cache.get("demo", "LOW_KEY") is None


def test_smart_mood_uses_history_when_enabled():
    service = SmartMoodDefaultService(FakeRepo(), enabled=True)
    result = service.suggest("demo-user")
    assert result["suggested_mood"] == "FOCUSED"
    assert result["source"] == "listening_history"


def test_drop_sharding_is_stable():
    assert user_partition("demo-user", 4) == user_partition("demo-user", 4)
    users = users_for_partition(["a", "b", "c", "d"], partition=0, partitions=2)
    assert all(user_partition(u, 2) == 0 for u in users)


def test_token_budget_blocks_overspend():
    repo = FakeRepo()
    budget = TokenBudgetService(repo, daily_budget=100)
    assert budget.can_spend("u", 50)
    budget.record("u", 60)
    assert not budget.can_spend("u", 50)


def test_candidate_prewarm_counts_tracks():
    service = CandidatePrewarmService(FakeRepo(), FakeRanker(), "redis://unused")
    result = service.prewarm_user("demo", "LOW_KEY")
    assert result["cached"] == 5
