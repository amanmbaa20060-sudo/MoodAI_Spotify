"""Shared configuration for phased implementations."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


PRODUCT_MOODS = (
    "ENERGISED",
    "FOCUSED",
    "LOW_KEY",
    "ADVENTUROUS",
    "NOSTALGIC",
    "SAD",
)


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL", "postgresql://app:app@localhost:5432/discovery"
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    llm_provider: str = os.getenv("LLM_PROVIDER", "groq")
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    groq_base_url: str = os.getenv(
        "GROQ_BASE_URL", "https://api.groq.com/openai/v1"
    ).rstrip("/")
    default_mood: str = os.getenv("DEFAULT_MOOD", "LOW_KEY")
    drop_size: int = int(os.getenv("DROP_SIZE", "10"))
    mood_gateway_enabled: bool = os.getenv(
        "MOOD_GATEWAY_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    visual_search_enabled: bool = os.getenv(
        "VISUAL_SEARCH_ENABLED", "true"
    ).lower() in {"1", "true", "yes", "on"}
    push_notifications_enabled: bool = os.getenv(
        "PUSH_NOTIFICATIONS_ENABLED", "false"
    ).lower() in {"1", "true", "yes", "on"}
    home_cache_ttl_seconds: int = int(os.getenv("HOME_CACHE_TTL_SECONDS", "60"))
    smart_mood_default_enabled: bool = os.getenv(
        "SMART_MOOD_DEFAULT_ENABLED", "false"
    ).lower() in {"1", "true", "yes", "on"}
    adaptive_drop_size: int = int(os.getenv("ADAPTIVE_DROP_SIZE", "10"))
    drop_partitions: int = int(os.getenv("DROP_PARTITIONS", "4"))
    llm_token_budget_per_day: int = int(os.getenv("LLM_TOKEN_BUDGET_PER_DAY", "12000"))
    cors_origins: str = os.getenv("CORS_ORIGINS", "")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
