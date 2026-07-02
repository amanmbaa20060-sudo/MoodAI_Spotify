"""Mood-aware scoring for candidate tracks."""

from __future__ import annotations

from phases.common.mood_rules import MOOD_WEIGHT_VECTORS, normalize_feature


class MoodAwareRanker:
    def score(self, candidates: list[dict], mood: str) -> list[dict]:
        weights = MOOD_WEIGHT_VECTORS[mood]
        ranked: list[dict] = []
        for candidate in candidates:
            novelty_score = 1.0 if mood == "ADVENTUROUS" else 0.4
            if candidate.get("primary_mood") == mood:
                novelty_score += 0.1
            feature_sum = 0.0
            for feature, weight in weights.items():
                if feature == "novelty":
                    value = novelty_score
                else:
                    value = normalize_feature(feature, float(candidate.get(feature) or 0.0))
                feature_sum += value * weight

            genre_bonus = 0.05 if candidate.get("genre") else 0.0
            mood_bonus = 0.08 if candidate.get("primary_mood") == mood else 0.03
            final_score = float(candidate.get("base_rec_score") or 0.0) + feature_sum + genre_bonus + mood_bonus
            ranked.append({**candidate, "score": round(final_score, 4)})

        return sorted(ranked, key=lambda item: item["score"], reverse=True)
