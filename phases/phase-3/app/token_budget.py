"""LLM token budget enforcement per user per day."""

from __future__ import annotations

from datetime import date


class TokenBudgetService:
    def __init__(self, repository, daily_budget: int):
        self.repository = repository
        self.daily_budget = daily_budget

    def can_spend(self, user_id: str, tokens: int) -> bool:
        used = self.repository.get_llm_tokens_used(user_id, date.today())
        return used + tokens <= self.daily_budget

    def record(self, user_id: str, tokens: int) -> int:
        return self.repository.add_llm_token_usage(user_id, date.today(), tokens)
