"""Phase 1 MVP FastAPI BFF."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phases.common.config import get_settings  # noqa: E402

from .dependencies import get_user_id
from .explanations import ExplanationService
from .home import HomeFeedComposer
from .mood_state import MoodStateService
from .novelty import NoveltyFilterService
from .orchestrator import DiscoveryOrchestrator
from .ranker import MoodAwareRanker
from .repository import Phase1Repository
from .schemas import (
    DiscoveryDropPayload,
    HomeResponse,
    MoodUpdateRequest,
    MoodUpdateResponse,
    TrackReason,
)


def build_services():
    settings = get_settings()
    repository = Phase1Repository(settings.database_url)
    ranker = MoodAwareRanker()
    novelty = NoveltyFilterService(repository)
    explanations = ExplanationService(repository, settings)
    orchestrator = DiscoveryOrchestrator(
        repository=repository,
        ranker=ranker,
        novelty_filter=novelty,
        explanations=explanations,
        drop_size=settings.drop_size,
    )
    mood_state = MoodStateService(repository, settings.default_mood)
    home = HomeFeedComposer(repository, orchestrator, ranker)
    return settings, repository, mood_state, orchestrator, home


def create_app(services: tuple | None = None) -> FastAPI:
    app = FastAPI(title="MoodAI Phase 1 MVP", version="1.0.0")
    if services is None:
        settings, repository, mood_state, orchestrator, home = build_services()
    else:
        settings, repository, mood_state, orchestrator, home = services
    app.state.settings = settings
    app.state.repository = repository
    app.state.mood_state = mood_state
    app.state.orchestrator = orchestrator
    app.state.home = home

    @app.get("/", include_in_schema=False)
    def web_ui() -> FileResponse:
        return FileResponse(Path(__file__).resolve().parent.parent / "static" / "index.html")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/v1/home", response_model=HomeResponse)
    def get_home(user_id: str = Depends(get_user_id)) -> dict:
        active_mood = app.state.mood_state.get_active_mood(user_id)
        return app.state.home.compose(
            user_id=user_id,
            active_mood=active_mood,
            mood_gateway_enabled=app.state.settings.mood_gateway_enabled,
        )

    @app.put("/v1/users/me/mood", response_model=MoodUpdateResponse)
    def put_mood(
        payload: MoodUpdateRequest,
        user_id: str = Depends(get_user_id),
    ) -> dict:
        active_mood = app.state.mood_state.set_active_mood(
            user_id=user_id,
            mood=payload.mood,
            persist=payload.persist,
        )
        home_response = app.state.home.compose(
            user_id=user_id,
            active_mood=active_mood,
            mood_gateway_enabled=app.state.settings.mood_gateway_enabled,
        )
        return {
            "user_id": user_id,
            "active_mood": active_mood,
            "persist": payload.persist,
            "home": home_response,
        }

    @app.get("/v1/discovery-drop", response_model=DiscoveryDropPayload)
    def get_discovery_drop(user_id: str = Depends(get_user_id)) -> dict:
        active_mood = app.state.mood_state.get_active_mood(user_id)
        drop = app.state.repository.list_drop(user_id, date.today())
        if drop is None:
            drop = app.state.orchestrator.generate_drop(user_id, active_mood)
        return {
            "drop_id": drop["drop_id"],
            "drop_date": str(drop["drop_date"]),
            "active_mood": active_mood,
            "header": drop["drop_header"],
            "header_method": drop["header_method"],
            "status": drop["status"],
            "next_refresh_at": app.state.repository.next_refresh_at(),
            "tracks": [
                TrackReason(
                    track_id=track["track_id"],
                    title=track["title"],
                    artists=[track["artist_name"]] if track.get("artist_name") else [],
                    album_name=track.get("album_name"),
                    genre=track.get("genre"),
                    reason_text=track["reason_text"],
                    reason_feature_id=track["reason_feature_id"],
                    reason_method=track["reason_method"],
                    score=float(track["base_score"]),
                )
                for track in drop["tracks"]
            ],
        }

    return app


# Uvicorn entrypoint: uvicorn app.main:create_app --factory
