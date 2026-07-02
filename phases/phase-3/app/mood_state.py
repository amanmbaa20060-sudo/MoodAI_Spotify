"""Mood state service for Phase 1."""

from __future__ import annotations

from phases.common.mood_rules import validate_product_mood

from .repository import Phase1Repository


class MoodStateService:
    def __init__(self, repository: Phase1Repository, default_mood: str):
        self.repository = repository
        self.default_mood = default_mood

    def get_active_mood(self, user_id: str) -> str:
        return self.repository.get_active_mood(user_id, self.default_mood)

    def set_active_mood(self, user_id: str, mood: str, persist: bool) -> str:
        normalized = validate_product_mood(mood)
        self.repository.set_active_mood(user_id, normalized, persist)
        return normalized
