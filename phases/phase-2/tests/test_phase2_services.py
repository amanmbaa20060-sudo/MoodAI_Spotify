"""Phase 2 tests — search, heard-before, and API extensions."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[3]
PHASE2_DIR = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(PHASE2_DIR) not in sys.path:
    sys.path.insert(0, str(PHASE2_DIR))

from phases.common.test_utils import load_phase_module  # noqa: E402

load_phase_module("phase-2", "app.search")
from app.heard_before import HeardBeforeService  # noqa: E402
from app.search import VisualSearchAdapter, artist_image_url  # noqa: E402


class FakeRepo:
    def __init__(self):
        self.heard: set[str] = set()
        self.artists = [
            {
                "artist_id": "a1",
                "artist_name": "Aurora Lights",
                "artist_image_url": None,
                "track_count": 12,
                "top_genre": "ambient",
            }
        ]

    def search_artists(self, query: str, limit: int = 24):
        return [a for a in self.artists if query.lower() in a["artist_name"].lower()][:limit]

    def record_heard_before(self, user_id: str, track_id: str, drop_id: str | None) -> str:
        self.heard.add(track_id)
        return "report-1"

    def get_heard_before_track_ids(self, user_id: str) -> set[str]:
        return self.heard


def test_artist_image_url_is_deterministic():
    assert artist_image_url("Aurora") == artist_image_url("Aurora")
    assert artist_image_url("Aurora").startswith("https://")


def test_visual_search_adapter_maps_grid_dto():
    adapter = VisualSearchAdapter(FakeRepo())
    results = adapter.search_artists("aurora")
    assert len(results) == 1
    assert results[0]["name"] == "Aurora Lights"
    assert results[0]["image_alt"].startswith("Artist portrait")


def test_heard_before_excludes_track():
    repo = FakeRepo()
    service = HeardBeforeService(repo)
    result = service.report("demo-user", "track-99", "drop-1")
    assert result["excluded_count"] == 1
    assert "track-99" in repo.heard


def test_search_endpoint():
    load_phase_module("phase-2", "app.main")
    from app.main import create_app

    fake_repo = FakeRepo()
    fake_settings = type(
        "S",
        (),
        {
            "database_url": "postgresql://unused",
            "redis_url": "redis://localhost",
            "default_mood": "LOW_KEY",
            "drop_size": 10,
            "mood_gateway_enabled": True,
            "visual_search_enabled": True,
            "push_notifications_enabled": False,
            "llm_provider": "groq",
            "groq_api_key": "",
            "groq_model": "llama-3.1-8b-instant",
            "groq_base_url": "https://api.groq.com/openai/v1",
        },
    )()

    class StubSearch:
        def search_artists(self, query, limit=24):
            return [{"artist_id": "x", "name": query, "image_url": "http://img", "image_alt": "alt", "track_count": 1}]

    client = TestClient(
        create_app(
            (
                fake_settings,
                fake_repo,
                None,
                None,
                None,
                StubSearch(),
                None,
                None,
                None,
            )
        )
    )
    response = client.get("/v1/search/artists?q=test", headers={"X-User-Id": "demo-user"})
    assert response.status_code == 200
    assert response.json()["artists"][0]["name"] == "test"
