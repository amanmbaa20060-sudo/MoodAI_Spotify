"""Response and request models for the Phase 1 API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MoodUpdateRequest(BaseModel):
    mood: str
    persist: bool = True


class TrackReason(BaseModel):
    track_id: str
    title: str
    artists: list[str]
    album_name: str | None = None
    genre: str | None = None
    reason_text: str
    reason_feature_id: str
    reason_method: Literal["LLM", "TEMPLATE"]
    score: float


class DiscoveryDropPayload(BaseModel):
    drop_id: str
    drop_date: str
    active_mood: str
    header: str
    header_method: Literal["LLM", "TEMPLATE"]
    status: str
    next_refresh_at: datetime
    tracks: list[TrackReason] = Field(default_factory=list)


class HomeModule(BaseModel):
    type: str
    data: dict


class HomeResponse(BaseModel):
    user_id: str
    mood_options: list[str]
    active_mood: str
    feature_flags: dict[str, bool | str]
    modules: list[HomeModule]


class MoodUpdateResponse(BaseModel):
    user_id: str
    active_mood: str
    persist: bool
    home: HomeResponse


class MoodSuggestionResponse(BaseModel):
    suggested_mood: str
    source: str
    confidence: float
    time_of_day_mood: str | None = None


class ArtistGridItem(BaseModel):
    artist_id: str
    name: str
    image_url: str
    image_alt: str
    track_count: int
    top_genre: str | None = None


class ArtistSearchResponse(BaseModel):
    query: str
    user_id: str
    artists: list[ArtistGridItem]


class HeardBeforeRequest(BaseModel):
    drop_id: str | None = None


class HeardBeforeResponse(BaseModel):
    report_id: str
    user_id: str
    track_id: str
    excluded_count: int
    message: str


class PushSubscribeRequest(BaseModel):
    endpoint: str


class ExplanationAuditItem(BaseModel):
    recommendation_id: str
    user_id: str
    track_id: str
    feature_id: str
    rendered_text: str
    generation_method: str
    model_id: str
    prompt_hash: str
    grounding_passed: bool
    created_at: datetime
