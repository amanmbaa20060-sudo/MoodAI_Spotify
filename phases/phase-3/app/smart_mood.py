"""Smart mood default — time-of-day + listening signals."""

from __future__ import annotations

from datetime import datetime, timezone

from phases.common.config import PRODUCT_MOODS


class SmartMoodDefaultService:
    TIME_MOOD_MAP = {
        (5, 11): "ENERGISED",
        (11, 17): "FOCUSED",
        (17, 22): "LOW_KEY",
        (22, 24): "NOSTALGIC",
        (0, 5): "SAD",
    }

    def __init__(self, repository, enabled: bool):
        self.repository = repository
        self.enabled = enabled

    def suggest(self, user_id: str) -> dict:
        if not self.enabled:
            return {"suggested_mood": "LOW_KEY", "source": "default", "confidence": 0.0}

        hour = datetime.now(timezone.utc).hour
        time_mood = "LOW_KEY"
        for (start, end), mood in self.TIME_MOOD_MAP.items():
            if start <= hour < end:
                time_mood = mood
                break

        history_mood = self.repository.get_dominant_play_mood(user_id)
        if history_mood and history_mood in PRODUCT_MOODS:
            return {
                "suggested_mood": history_mood,
                "source": "listening_history",
                "confidence": 0.72,
                "time_of_day_mood": time_mood,
            }

        return {
            "suggested_mood": time_mood,
            "source": "time_of_day",
            "confidence": 0.55,
        }
