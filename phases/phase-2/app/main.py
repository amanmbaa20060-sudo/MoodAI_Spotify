"""Phase 2 — Trust & Browse (extends Phase 1 MVP)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, Query
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phases.common.config import get_settings  # noqa: E402

from .dependencies import get_user_id
from .explanations import ExplanationService
from .heard_before import HeardBeforeService
from .home import HomeFeedComposer
from .mood_state import MoodStateService
from .novelty import NoveltyFilterService
from .orchestrator import DiscoveryOrchestrator
from .prewarm import LLMPrewarmService
from .push import PushNotificationService
from .ranker import MoodAwareRanker
from .repository import Phase2Repository
from .schemas import (
    ArtistGridItem,
    ArtistSearchResponse,
    DiscoveryDropPayload,
    ExplanationAuditItem,
    HeardBeforeRequest,
    HeardBeforeResponse,
    HomeResponse,
    MoodUpdateRequest,
    MoodUpdateResponse,
    PushSubscribeRequest,
    TrackReason,
)
from .search import VisualSearchAdapter


def build_services():
    settings = get_settings()
    repository = Phase2Repository(settings.database_url)
    ranker = MoodAwareRanker()
    novelty = NoveltyFilterService(repository)
    explanations = ExplanationService(repository, settings)
    push = PushNotificationService(repository, settings.push_notifications_enabled)
    orchestrator = DiscoveryOrchestrator(
        repository=repository,
        ranker=ranker,
        novelty_filter=novelty,
        explanations=explanations,
        drop_size=settings.drop_size,
        on_drop_ready=lambda uid, did, hdr: push.notify_drop_ready(uid, did, hdr),
    )
    mood_state = MoodStateService(repository, settings.default_mood)
    home = HomeFeedComposer(repository, orchestrator, ranker, explanations)
    search = VisualSearchAdapter(repository)
    heard_before = HeardBeforeService(repository)
    prewarm = LLMPrewarmService(repository, explanations, settings.redis_url)
    return settings, repository, mood_state, orchestrator, home, search, heard_before, push, prewarm


def create_app(services: tuple | None = None) -> FastAPI:
    app = FastAPI(title="MoodAI Phase 2 — Trust & Browse", version="2.0.0")
    if services is None:
        (
            settings,
            repository,
            mood_state,
            orchestrator,
            home,
            search,
            heard_before,
            push,
            prewarm,
        ) = build_services()
    else:
        (
            settings,
            repository,
            mood_state,
            orchestrator,
            home,
            search,
            heard_before,
            push,
            prewarm,
        ) = services
    app.state.settings = settings
    app.state.repository = repository
    app.state.mood_state = mood_state
    app.state.orchestrator = orchestrator
    app.state.home = home
    app.state.search = search
    app.state.heard_before = heard_before
    app.state.push = push
    app.state.prewarm = prewarm

    @app.get("/", include_in_schema=False)
    def web_ui() -> FileResponse:
        return FileResponse(Path(__file__).resolve().parent.parent / "static" / "index.html")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok", "phase": "2"}

    @app.get("/v1/home", response_model=HomeResponse)
    def get_home(user_id: str = Depends(get_user_id)) -> dict:
        active_mood = app.state.mood_state.get_active_mood(user_id)
        return app.state.home.compose(
            user_id=user_id,
            active_mood=active_mood,
            mood_gateway_enabled=app.state.settings.mood_gateway_enabled,
            visual_search_enabled=app.state.settings.visual_search_enabled,
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
            visual_search_enabled=app.state.settings.visual_search_enabled,
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

    @app.get("/v1/search/artists", response_model=ArtistSearchResponse)
    def search_artists(
        q: str = Query(..., min_length=1),
        limit: int = Query(24, ge=1, le=48),
        user_id: str = Depends(get_user_id),
    ) -> dict:
        artists = app.state.search.search_artists(q, limit=limit)
        return {"query": q, "user_id": user_id, "artists": artists}

    @app.post(
        "/v1/discovery-drop/tracks/{track_id}/heard-before",
        response_model=HeardBeforeResponse,
    )
    def post_heard_before(
        track_id: str,
        payload: HeardBeforeRequest,
        user_id: str = Depends(get_user_id),
    ) -> dict:
        return app.state.heard_before.report(user_id, track_id, payload.drop_id)

    @app.post("/v1/users/me/push-subscription")
    def subscribe_push(
        payload: PushSubscribeRequest,
        user_id: str = Depends(get_user_id),
    ) -> dict:
        return app.state.push.subscribe(user_id, payload.endpoint)

    @app.get("/internal/explanation-audit", response_model=list[ExplanationAuditItem])
    def explanation_audit(
        user_id: str = Depends(get_user_id),
        limit: int = Query(50, ge=1, le=200),
    ) -> list[dict]:
        return app.state.repository.list_explanation_audit(user_id, limit=limit)

    @app.post("/internal/llm-prewarm")
    def llm_prewarm(user_id: str = Depends(get_user_id)) -> dict:
        mood = app.state.mood_state.get_active_mood(user_id)
        return app.state.prewarm.prewarm_user(user_id, mood)

    return app


# Uvicorn entrypoint: uvicorn app.main:create_app --factory
