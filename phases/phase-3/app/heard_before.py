"""Heard-before feedback loop for novelty correction."""

from __future__ import annotations

import uuid
from typing import Any


class HeardBeforeService:
    def __init__(self, repository):
        self.repository = repository

    def report(self, user_id: str, track_id: str, drop_id: str | None = None) -> dict[str, Any]:
        report_id = self.repository.record_heard_before(user_id, track_id, drop_id)
        excluded = self.repository.get_heard_before_track_ids(user_id)
        return {
            "report_id": report_id,
            "user_id": user_id,
            "track_id": track_id,
            "excluded_count": len(excluded),
            "message": "Track will be excluded from future drops for this user.",
        }
