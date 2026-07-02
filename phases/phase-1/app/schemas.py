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
    feature_flags: dict[str, bool]
    modules: list[HomeModule]


class MoodUpdateResponse(BaseModel):
    user_id: str
    active_mood: str
    persist: bool
    home: HomeResponse
