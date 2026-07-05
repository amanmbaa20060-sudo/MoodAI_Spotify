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
load_phase_module("phase-3", "app.orchestrator")
from app.candidate_prewarm import CandidatePrewarmService  # noqa: E402
from app.drop_sharding import user_partition, users_for_partition  # noqa: E402
from app.edge_cache import HomeEdgeCache  # noqa: E402
from app.novelty import NoveltyFilterService  # noqa: E402
from app.orchestrator import DiscoveryOrchestrator  # noqa: E402
from app.ranker import MoodAwareRanker  # noqa: E402
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


class DropRepo(FakeRepo):
    def __init__(self):
        super().__init__()
        self._drop = None

    def fetch_candidates(self, mood: str, limit: int = 300):
        prefix = mood.lower()
        return [
            {
                "track_id": f"{prefix}-t{i}",
                "title": f"{mood} track {i}",
                "artist_name": "Artist",
                "genre": "pop",
                "primary_mood": mood,
                "base_rec_score": 0.8,
            }
            for i in range(12)
        ]

    def list_drop(self, user_id: str, drop_date):
        return self._drop

    def save_drop(self, user_id, active_mood, header, header_method, tracks, drop_date):
        self._drop = {
            "drop_id": "drop-1",
            "drop_date": drop_date,
            "mood_at_generation": active_mood,
            "drop_header": header,
            "header_method": header_method,
            "status": "READY",
            "tracks": [
                {
                    **track,
                    "reason_text": "reason",
                    "reason_feature_id": "MOOD_MATCH",
                    "reason_method": "TEMPLATE",
                    "base_score": track.get("score", 0.8),
                }
                for track in tracks
            ],
        }
        return self._drop

    def get_recent_drop_track_ids(self, user_id: str, days: int = 7):
        return set()

    def get_played_track_ids(self, user_id: str):
        return set()

    def get_heard_before_track_ids(self, user_id: str):
        return set()


class TemplateExplanations:
    def attach(self, user_id, mood, tracks):
        enriched = [
            {
                **track,
                "reason_text": f"For {mood}",
                "reason_feature_id": "MOOD_MATCH",
                "reason_method": "TEMPLATE",
                "score": track.get("score", 0.8),
            }
            for track in tracks
        ]
        return f"{mood} drop", "TEMPLATE", enriched


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


def test_generate_drop_regenerates_when_mood_changes():
    repo = DropRepo()
    orchestrator = DiscoveryOrchestrator(
        repository=repo,
        ranker=MoodAwareRanker(),
        novelty_filter=NoveltyFilterService(repo),
        explanations=TemplateExplanations(),
        drop_size=10,
    )
    energised = orchestrator.generate_drop("demo-user", "ENERGISED")
    sad = orchestrator.generate_drop("demo-user", "SAD")

    energised_ids = {track["track_id"] for track in energised["tracks"]}
    sad_ids = {track["track_id"] for track in sad["tracks"]}
    assert energised["mood_at_generation"] == "ENERGISED"
    assert sad["mood_at_generation"] == "SAD"
    assert energised_ids != sad_ids
    assert all(track_id.startswith("energised-") for track_id in energised_ids)
    assert all(track_id.startswith("sad-") for track_id in sad_ids)
