"""Home feed composition — Phase 2 with expanded explanations."""

from __future__ import annotations

from datetime import date

from phases.common.config import PRODUCT_MOODS

from .explanations import ExplanationService
from .orchestrator import DiscoveryOrchestrator
from .ranker import MoodAwareRanker
from .repository import Phase2Repository


class HomeFeedComposer:
    def __init__(
        self,
        repository: Phase2Repository,
        orchestrator: DiscoveryOrchestrator,
        ranker: MoodAwareRanker,
        explanations: ExplanationService | None = None,
    ):
        self.repository = repository
        self.orchestrator = orchestrator
        self.ranker = ranker
        self.explanations = explanations

    def compose(
        self,
        user_id: str,
        active_mood: str,
        mood_gateway_enabled: bool,
        visual_search_enabled: bool = True,
    ) -> dict:
        drop = self.repository.list_drop(user_id, date.today())
        if drop is None:
            drop = self.orchestrator.generate_drop(user_id, active_mood)

        fresh_candidates = self.repository.fetch_candidates(active_mood, limit=60)
        fresh_scored = self.ranker.score(fresh_candidates, active_mood)[:20]
        if self.explanations:
            _, _, fresh_tracks = self.explanations.attach(user_id, active_mood, fresh_scored)
        else:
            fresh_tracks = [
                {
                    **track,
                    "reason_text": f"Fits your {active_mood.title()} session",
                    "reason_feature_id": "MOOD_MATCH",
                    "reason_method": "TEMPLATE",
                }
                for track in fresh_scored
            ]

        return {
            "user_id": user_id,
            "mood_options": list(PRODUCT_MOODS),
            "active_mood": active_mood,
            "feature_flags": {
                "mood_gateway_enabled": mood_gateway_enabled,
                "discovery_drop_enabled": True,
                "explanations_enabled": True,
                "llm_explanations_enabled": True,
                "visual_search_enabled": visual_search_enabled,
                "heard_before_enabled": True,
                "push_notifications_enabled": False,
            },
            "modules": [
                {
                    "type": "mood_gateway",
                    "data": {
                        "active_mood": active_mood,
                        "options": list(PRODUCT_MOODS),
                    },
                },
                {
                    "type": "discovery_drop",
                    "data": {
                        "drop_id": drop["drop_id"],
                        "drop_date": str(drop["drop_date"]),
                        "header": drop["drop_header"],
                        "header_method": drop["header_method"],
                        "status": drop["status"],
                        "tracks": [
                            {
                                "track_id": track["track_id"],
                                "title": track["title"],
                                "artists": [track["artist_name"]] if track.get("artist_name") else [],
                                "album_name": track.get("album_name"),
                                "genre": track.get("genre"),
                                "reason_text": track["reason_text"],
                                "reason_feature_id": track["reason_feature_id"],
                                "reason_method": track["reason_method"],
                                "score": float(track["base_score"]),
                            }
                            for track in drop["tracks"]
                        ],
                    },
                },
                {
                    "type": "fresh_picks",
                    "data": {
                        "tracks": [
                            {
                                "track_id": track["track_id"],
                                "title": track["title"],
                                "artists": [track["artist_name"]] if track.get("artist_name") else [],
                                "genre": track.get("genre"),
                                "reason_text": track["reason_text"],
                                "reason_feature_id": track["reason_feature_id"],
                                "reason_method": track["reason_method"],
                                "score": track.get("score", 0.0),
                            }
                            for track in fresh_tracks
                        ]
                    },
                },
            ],
        }
