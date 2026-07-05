"""Discovery Drop orchestration pipeline."""

from __future__ import annotations

from datetime import date

from .explanations import ExplanationService
from .novelty import NoveltyFilterService
from .ranker import MoodAwareRanker
from .repository import Phase1Repository


class DiscoveryOrchestrator:
    def __init__(
        self,
        repository: Phase1Repository,
        ranker: MoodAwareRanker,
        novelty_filter: NoveltyFilterService,
        explanations: ExplanationService,
        drop_size: int,
        on_drop_ready=None,
    ):
        self.repository = repository
        self.ranker = ranker
        self.novelty_filter = novelty_filter
        self.explanations = explanations
        self.drop_size = drop_size
        self.on_drop_ready = on_drop_ready

    def generate_drop(self, user_id: str, mood: str, drop_date: date | None = None) -> dict:
        effective_date = drop_date or date.today()
        existing = self.repository.list_drop(user_id, effective_date)
        if existing and existing.get("tracks") and existing.get("mood_at_generation") == mood:
            return existing

        candidates = self.repository.fetch_candidates(mood, limit=500)
        scored = self.ranker.score(candidates, mood)
        novel = self.novelty_filter.exclude_played(user_id, scored)
        selected = self.novelty_filter.select_diverse(novel, count=self.drop_size)
        header, header_method, explained = self.explanations.attach(user_id, mood, selected)
        saved = self.repository.save_drop(
            user_id=user_id,
            active_mood=mood,
            header=header,
            header_method=header_method,
            tracks=explained,
            drop_date=effective_date,
        )
        if self.on_drop_ready and saved.get("drop_id"):
            self.on_drop_ready(user_id, saved["drop_id"], header)
        return saved
