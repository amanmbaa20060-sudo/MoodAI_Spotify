"""Dataset mood bucketing rules — docs/architecture.md §6.5"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

DATASET_MOODS = ("ENERGISED", "FOCUSED", "LOW_KEY", "NOSTALGIC", "SAD")
MOOD_PRIORITY = {m: i for i, m in enumerate(DATASET_MOODS)}

AUDIO_FEATURES = ("energy", "valence", "tempo", "instrumentalness")


@dataclass(frozen=True)
class Threshold:
    check: Optional[Callable[[float], bool]]
    active: bool = True

    @staticmethod
    def gt(value: float) -> "Threshold":
        return Threshold(check=lambda x: x > value)

    @staticmethod
    def gte(value: float) -> "Threshold":
        return Threshold(check=lambda x: x >= value)

    @staticmethod
    def lt(value: float) -> "Threshold":
        return Threshold(check=lambda x: x < value)

    @staticmethod
    def between(low: float, high: float) -> "Threshold":
        return Threshold(check=lambda x: low <= x <= high)

    @staticmethod
    def none() -> "Threshold":
        return Threshold(check=None, active=False)


# Bucketing thresholds (numeric only; ADVENTUROUS excluded)
MOOD_THRESHOLDS: dict[str, dict[str, Threshold]] = {
    "ENERGISED": {
        "energy": Threshold.gt(0.7),
        "valence": Threshold.gt(0.6),
        "tempo": Threshold.gt(120),
        "instrumentalness": Threshold.none(),
    },
    "FOCUSED": {
        "energy": Threshold.between(0.3, 0.6),
        "valence": Threshold.between(0.4, 0.6),
        "tempo": Threshold.between(80, 110),
        "instrumentalness": Threshold.gt(0.5),
    },
    "LOW_KEY": {
        "energy": Threshold.lt(0.4),
        "valence": Threshold.between(0.3, 0.6),
        "tempo": Threshold.lt(100),
        "instrumentalness": Threshold.none(),
    },
    "NOSTALGIC": {
        "energy": Threshold.between(0.3, 0.6),
        "valence": Threshold.between(0.4, 0.7),
        "tempo": Threshold.none(),
        "instrumentalness": Threshold.none(),
    },
    "SAD": {
        "energy": Threshold.lt(0.35),
        "valence": Threshold.lt(0.35),
        "tempo": Threshold.lt(100),
        "instrumentalness": Threshold.none(),
    },
}


def mood_matches(track: dict, mood: str) -> bool:
    rules = MOOD_THRESHOLDS[mood]
    for feature in AUDIO_FEATURES:
        threshold = rules[feature]
        if not threshold.active or threshold.check is None:
            continue
        if not threshold.check(float(track[feature])):
            return False
    return True


def active_constraint_count(mood: str) -> int:
    return sum(1 for f in AUDIO_FEATURES if MOOD_THRESHOLDS[mood][f].active)


def assign_dataset_moods(track: dict) -> tuple[Optional[str], list[str]]:
    eligible = [m for m in DATASET_MOODS if mood_matches(track, m)]
    if not eligible:
        return None, []

    def sort_key(mood: str) -> tuple:
        return (-active_constraint_count(mood), MOOD_PRIORITY[mood])

    primary = sorted(eligible, key=sort_key)[0]
    return primary, eligible
