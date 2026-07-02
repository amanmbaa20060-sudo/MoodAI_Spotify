"""Focused tests for the Phase 1 MVP services and API."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
PHASE1_DIR = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PHASE1_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE1_DIR))

from phases.common.test_utils import load_phase_module  # noqa: E402

_phase = load_phase_module("phase-1", "app.main")
create_app = _phase.create_app
from app.explanations import ExplanationService  # noqa: E402
from app.novelty import NoveltyFilterService  # noqa: E402
from app.ranker import MoodAwareRanker  # noqa: E402


class FakeRepository:
    def __init__(self):
        self.mood = "LOW_KEY"
        self.drop = None
        self.logged = []

    def get_active_mood(self, user_id: str, default_mood: str) -> str:
        return self.mood or default_mood

    def set_active_mood(self, user_id: str, mood: str, persist: bool) -> None:
        self.mood = mood

    def fetch_candidates(self, mood: str, limit: int = 300):
        return [
            {
                "track_id": f"track-{idx}",
                "title": f"Track {idx}",
                "artist_name": f"Artist {idx % 5}",
                "album_name": f"Album {idx}",
                "genre": ["indie", "rock", "jazz", "electronic", "ambient"][idx % 5],
                "primary_mood": mood if mood != "ADVENTUROUS" else "FOCUSED",
                "mood_tags": [mood] if mood != "ADVENTUROUS" else ["FOCUSED", "LOW_KEY"],
                "energy": 0.2 + (idx % 5) * 0.1,
                "valence": 0.2 + (idx % 4) * 0.1,
                "tempo": 70 + idx,
                "instrumentalness": 0.1 * (idx % 6),
                "base_rec_score": 0.6,
            }
            for idx in range(limit)
        ]

    def get_played_track_ids(self, user_id: str):
        return {"track-1"}

    def get_recent_drop_track_ids(self, user_id: str, days: int = 7):
        return {"track-2"}

    def list_drop(self, user_id: str, drop_date):
        return self.drop

    def save_drop(self, user_id: str, active_mood: str, header: str, header_method: str, tracks, drop_date):
        self.drop = {
            "drop_id": "drop-1",
            "drop_date": drop_date,
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
                    "base_score": track["score"],
                }
                for index, track in enumerate(tracks)
            ],
        }
        return self.drop

    def insert_explanation_audit_log(self, **kwargs):
        self.logged.append(kwargs)

    @staticmethod
    def next_refresh_at():
        from datetime import datetime, timezone

        return datetime.now(timezone.utc)


class FakeSettings:
    llm_provider = "groq"
    groq_api_key = ""
    groq_model = "llama-3.1-8b-instant"
    groq_base_url = "https://api.groq.com/openai/v1"
    default_mood = "LOW_KEY"
    drop_size = 10
    mood_gateway_enabled = True
    database_url = "postgresql://unused"


def test_ranker_prefers_focused_tracks():
    ranker = MoodAwareRanker()
    scored = ranker.score(
        [
            {
                "track_id": "high-focus",
                "primary_mood": "FOCUSED",
                "genre": "ambient",
                "energy": 0.4,
                "valence": 0.5,
                "tempo": 90,
                "instrumentalness": 0.8,
                "base_rec_score": 0.7,
            },
            {
                "track_id": "low-focus",
                "primary_mood": "ENERGISED",
                "genre": "pop",
                "energy": 0.9,
                "valence": 0.8,
                "tempo": 150,
                "instrumentalness": 0.0,
                "base_rec_score": 0.7,
            },
        ],
        "FOCUSED",
    )
    assert scored[0]["track_id"] == "high-focus"


def test_novelty_filter_excludes_played_and_recent():
    repo = FakeRepository()
    novelty = NoveltyFilterService(repo)
    candidates = [{"track_id": "track-1"}, {"track_id": "track-2"}, {"track_id": "track-3"}]
    filtered = novelty.exclude_played("demo-user", candidates)
    assert [track["track_id"] for track in filtered] == ["track-3"]


def test_explanation_service_falls_back_to_templates():
    repo = FakeRepository()
    service = ExplanationService(repo, FakeSettings())
    header, method, tracks = service.attach(
        user_id="demo-user",
        mood="LOW_KEY",
        tracks=[
            {
                "track_id": "track-9",
                "title": "Night Drive",
                "artist_name": "Artist 1",
                "genre": "ambient",
                "primary_mood": "LOW_KEY",
                "score": 1.2,
            }
        ],
    )
    assert method == "TEMPLATE"
    assert header.startswith("10 fresh picks")
    assert tracks[0]["reason_feature_id"] == "TASTE_GENRE"
    assert repo.logged


def test_home_and_mood_endpoints():
    load_phase_module("phase-1", "app.main")
    from app.explanations import ExplanationService
    from app.home import HomeFeedComposer
    from app.main import create_app
    from app.mood_state import MoodStateService
    from app.novelty import NoveltyFilterService
    from app.orchestrator import DiscoveryOrchestrator

    fake_repo = FakeRepository()
    fake_settings = FakeSettings()
    ranker = MoodAwareRanker()
    orchestrator = DiscoveryOrchestrator(
        repository=fake_repo,
        ranker=ranker,
        novelty_filter=NoveltyFilterService(fake_repo),
        explanations=ExplanationService(fake_repo, fake_settings),
        drop_size=10,
    )
    mood_state = MoodStateService(fake_repo, fake_settings.default_mood)
    home = HomeFeedComposer(fake_repo, orchestrator, ranker)
    client = TestClient(
        create_app((fake_settings, fake_repo, mood_state, orchestrator, home))
    )

    home_response = client.get("/v1/home", headers={"X-User-Id": "demo-user"})
    assert home_response.status_code == 200
    assert home_response.json()["modules"][0]["type"] == "mood_gateway"

    mood_response = client.put(
        "/v1/users/me/mood",
        headers={"X-User-Id": "demo-user"},
        json={"mood": "FOCUSED", "persist": True},
    )
    assert mood_response.status_code == 200
    assert mood_response.json()["active_mood"] == "FOCUSED"

    drop_response = client.get("/v1/discovery-drop", headers={"X-User-Id": "demo-user"})
    assert drop_response.status_code == 200
    assert len(drop_response.json()["tracks"]) == 10
