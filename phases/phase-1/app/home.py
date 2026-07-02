"""Home feed composition for the Phase 1 MVP."""

from __future__ import annotations

from datetime import date

from phases.common.config import PRODUCT_MOODS

from .orchestrator import DiscoveryOrchestrator
from .ranker import MoodAwareRanker
from .repository import Phase1Repository


class HomeFeedComposer:
    def __init__(
        self,
        repository: Phase1Repository,
        orchestrator: DiscoveryOrchestrator,
        ranker: MoodAwareRanker,
    ):
        self.repository = repository
        self.orchestrator = orchestrator
        self.ranker = ranker

    def compose(self, user_id: str, active_mood: str, mood_gateway_enabled: bool) -> dict:
        drop = self.repository.list_drop(user_id, date.today())
        if drop is None:
            drop = self.orchestrator.generate_drop(user_id, active_mood)

        fresh_candidates = self.repository.fetch_candidates(active_mood, limit=60)
        fresh_tracks = self.ranker.score(fresh_candidates, active_mood)[:20]

        return {
            "user_id": user_id,
            "mood_options": list(PRODUCT_MOODS),
            "active_mood": active_mood,
            "feature_flags": {
                "mood_gateway_enabled": mood_gateway_enabled,
                "discovery_drop_enabled": True,
                "explanations_enabled": True,
                "llm_explanations_enabled": True,
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
                                "reason_text": f"Fits your {active_mood.title()} session",
                                "reason_feature_id": "MOOD_MATCH",
                                "reason_method": "TEMPLATE",
                                "score": track["score"],
                            }
                            for track in fresh_tracks
                        ]
                    },
                },
            ],
        }
