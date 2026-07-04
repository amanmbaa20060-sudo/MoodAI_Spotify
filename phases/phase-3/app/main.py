"""Phase 3 — Optimization & Scale (extends Phase 2)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phases.common.config import get_settings  # noqa: E402

from .candidate_prewarm import CandidatePrewarmService
from .demo_repository import DemoRepository, should_use_demo_mode
from .dependencies import get_user_id
from .drop_sharding import user_partition, users_for_partition
from .edge_cache import HomeEdgeCache
from .explanations import ExplanationService
from .heard_before import HeardBeforeService
from .home import HomeFeedComposer
from .mood_state import MoodStateService
from .novelty import NoveltyFilterService
from .orchestrator import DiscoveryOrchestrator
from .prewarm import LLMPrewarmService
from .push import PushNotificationService
from .ranker import MoodAwareRanker
from .repository import Phase3Repository
from .schemas import (
    ArtistDetailResponse,
    ArtistSearchResponse,
    DiscoveryDropPayload,
    ExplanationAuditItem,
    HeardBeforeRequest,
    HeardBeforeResponse,
    HomeResponse,
    MoodSuggestionResponse,
    MoodUpdateRequest,
    MoodUpdateResponse,
    PushSubscribeRequest,
    TrackReason,
)
from .search import VisualSearchAdapter
from .smart_mood import SmartMoodDefaultService
from .token_budget import TokenBudgetService


def build_services():
    settings = get_settings()
    demo_mode = should_use_demo_mode(settings.database_url)
    repository = DemoRepository() if demo_mode else Phase3Repository(settings.database_url)
    ranker = MoodAwareRanker()
    novelty = NoveltyFilterService(repository)
    token_budget = TokenBudgetService(repository, settings.llm_token_budget_per_day)
    explanations = ExplanationService(repository, settings, token_budget=token_budget)
    push = PushNotificationService(repository, settings.push_notifications_enabled)
    drop_size = settings.adaptive_drop_size or settings.drop_size
    orchestrator = DiscoveryOrchestrator(
        repository=repository,
        ranker=ranker,
        novelty_filter=novelty,
        explanations=explanations,
        drop_size=drop_size,
        on_drop_ready=lambda uid, did, hdr: push.notify_drop_ready(uid, did, hdr),
    )
    mood_state = MoodStateService(repository, settings.default_mood)
    smart_mood = SmartMoodDefaultService(repository, settings.smart_mood_default_enabled)
    home_cache = HomeEdgeCache(settings.redis_url, settings.home_cache_ttl_seconds)
    home = HomeFeedComposer(repository, orchestrator, ranker, explanations)
    search = VisualSearchAdapter(repository)
    heard_before = HeardBeforeService(repository)
    prewarm = LLMPrewarmService(repository, explanations, settings.redis_url)
    candidate_prewarm = CandidatePrewarmService(repository, ranker, settings.redis_url)
    return (
        settings,
        repository,
        mood_state,
        orchestrator,
        home,
        search,
        heard_before,
        push,
        prewarm,
        smart_mood,
        home_cache,
        candidate_prewarm,
        token_budget,
        demo_mode,
    )


def create_app(services: tuple | None = None) -> FastAPI:
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
            smart_mood,
            home_cache,
            candidate_prewarm,
            token_budget,
            demo_mode,
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
            smart_mood,
            home_cache,
            candidate_prewarm,
            token_budget,
            demo_mode,
        ) = services

    app = FastAPI(title="MoodAI Phase 3 — Optimization & Scale", version="3.0.0")
    static_dir = Path(__file__).resolve().parent.parent / "static"
    for name, value in (
        ("settings", settings),
        ("repository", repository),
        ("mood_state", mood_state),
        ("orchestrator", orchestrator),
        ("home", home),
        ("search", search),
        ("heard_before", heard_before),
        ("push", push),
        ("prewarm", prewarm),
        ("smart_mood", smart_mood),
        ("home_cache", home_cache),
        ("candidate_prewarm", candidate_prewarm),
        ("token_budget", token_budget),
        ("demo_mode", demo_mode),
    ):
        setattr(app.state, name, value)

    @app.get("/", include_in_schema=False)
    def web_ui() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        payload = {
            "status": "ok",
            "phase": "3",
            "product": "MoodAI Spotify",
        }
        if app.state.demo_mode:
            payload["mode"] = "demo"
        return payload

    @app.get("/api/identity", include_in_schema=False)
    def identity() -> dict[str, str]:
        """Helps verify you hit MoodAI and not another local app on the same port."""
        payload = {"product": "MoodAI Spotify", "phase": "3"}
        if app.state.demo_mode:
            payload["mode"] = "demo"
        return payload

    @app.get("/v1/mood/suggestion", response_model=MoodSuggestionResponse)
    def mood_suggestion(user_id: str = Depends(get_user_id)) -> dict:
        return app.state.smart_mood.suggest(user_id)

    @app.get("/v1/home", response_model=HomeResponse)
    def get_home(user_id: str = Depends(get_user_id)) -> dict:
        active_mood = app.state.mood_state.get_active_mood(user_id)
        cached = app.state.home_cache.get(user_id, active_mood)
        if cached:
            return cached

        payload = app.state.home.compose(
            user_id=user_id,
            active_mood=active_mood,
            mood_gateway_enabled=app.state.settings.mood_gateway_enabled,
            visual_search_enabled=app.state.settings.visual_search_enabled,
            drop_size_variant=app.state.repository.get_experiment_variant(
                user_id, "drop_size", str(app.state.settings.adaptive_drop_size)
            ),
        )
        app.state.home_cache.set(user_id, active_mood, payload)
        return payload

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
        app.state.home_cache.invalidate(user_id)
        home_response = app.state.home.compose(
            user_id=user_id,
            active_mood=active_mood,
            mood_gateway_enabled=app.state.settings.mood_gateway_enabled,
            visual_search_enabled=app.state.settings.visual_search_enabled,
            drop_size_variant=app.state.repository.get_experiment_variant(
                user_id, "drop_size", str(app.state.settings.adaptive_drop_size)
            ),
        )
        app.state.home_cache.set(user_id, active_mood, home_response)
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

    @app.get("/v1/artists/lookup/by-name", response_model=ArtistDetailResponse)
    def get_artist_by_name(
        name: str = Query(..., min_length=1),
        limit: int = Query(100, ge=1, le=200),
        user_id: str = Depends(get_user_id),
    ) -> dict:
        artist = app.state.search.get_artist_by_name(name, limit=limit)
        if artist is None:
            raise HTTPException(status_code=404, detail="Artist not found")
        return artist

    @app.get("/v1/artists/{artist_id}", response_model=ArtistDetailResponse)
    def get_artist(
        artist_id: str,
        limit: int = Query(100, ge=1, le=200),
        user_id: str = Depends(get_user_id),
    ) -> dict:
        artist = app.state.search.get_artist(artist_id, limit=limit)
        if artist is None:
            raise HTTPException(status_code=404, detail="Artist not found")
        return artist

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

    @app.post("/internal/candidate-prewarm")
    def candidate_prewarm(user_id: str = Depends(get_user_id)) -> dict:
        mood = app.state.mood_state.get_active_mood(user_id)
        return app.state.candidate_prewarm.prewarm_user(user_id, mood)

    @app.get("/internal/token-budget")
    def token_budget_status(user_id: str = Depends(get_user_id)) -> dict:
        used = app.state.repository.get_llm_tokens_used(user_id, date.today())
        return {
            "user_id": user_id,
            "tokens_used": used,
            "daily_budget": app.state.settings.llm_token_budget_per_day,
            "remaining": max(0, app.state.settings.llm_token_budget_per_day - used),
        }

    @app.get("/internal/drop-shard/{partition}")
    def drop_shard_users(
        partition: int,
        user_id: str = Depends(get_user_id),
    ) -> dict:
        partitions = app.state.settings.drop_partitions
        users = users_for_partition(
            app.state.repository.list_known_users(),
            partition,
            partitions,
        )
        return {
            "partition": partition,
            "partitions": partitions,
            "user_count": len(users),
            "requester_partition": user_partition(user_id, partitions),
            "users": users[:20],
        }

    app.mount("/assets", StaticFiles(directory=static_dir), name="assets")
    return app


# Uvicorn entrypoint: uvicorn app.main:create_app --factory
