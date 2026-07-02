"""Explanation service and Groq gateway with template fallback."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any
from urllib import error, request

from phases.common.config import Settings

from .repository import Phase1Repository


class GroqLLMGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    def generate_drop_explanations(
        self, mood: str, tracks: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if self.settings.llm_provider.lower() != "groq" or not self.settings.groq_api_key:
            raise RuntimeError("Groq is not configured")

        prompt_payload = {
            "mood": mood,
            "tracks": [
                {
                    "track_id": track["track_id"],
                    "title": track["title"],
                    "artist_name": track.get("artist_name"),
                    "genre": track.get("genre"),
                    "primary_mood": track.get("primary_mood"),
                }
                for track in tracks
            ],
        }
        body = {
            "model": self.settings.groq_model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You write short grounded music recommendation explanations. "
                        "Return strict JSON with keys header and reasons. "
                        "Each reason must be under 60 characters and use only artist, genre, or mood from input."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt_payload),
                },
            ],
        }
        payload = json.dumps(body).encode("utf-8")
        req = request.Request(
            url=f"{self.settings.groq_base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.settings.groq_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=15) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("Groq request failed") from exc

        content = raw["choices"][0]["message"]["content"]
        result = json.loads(content)
        if "header" not in result or "reasons" not in result:
            raise RuntimeError("Invalid Groq response shape")
        return result


class ExplanationService:
    def __init__(self, repository: Phase1Repository, settings: Settings, token_budget=None):
        self.repository = repository
        self.settings = settings
        self.gateway = GroqLLMGateway(settings)
        self.token_budget = token_budget

    @staticmethod
    def _feature_from_track(track: dict[str, Any], mood: str) -> tuple[str, dict[str, str]]:
        if track.get("genre"):
            return "TASTE_GENRE", {"genre": str(track["genre"])}
        if track.get("artist_name"):
            return "TASTE_ARTIST", {"artist": str(track["artist_name"])}
        return "MOOD_MATCH", {"mood": mood.title().replace("_", "-")}

    @staticmethod
    def _template_text(feature_id: str, payload: dict[str, str]) -> str:
        templates = {
            "TASTE_ARTIST": "Because you love {artist}",
            "TASTE_GENRE": "Because you love {genre}",
            "MOOD_MATCH": "Matches your {mood} vibe",
        }
        return templates[feature_id].format(**payload)[:60]

    def _fallback(self, mood: str, tracks: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
        header = f"10 fresh picks for your {mood.title().replace('_', '-')} mood"
        enriched: list[dict[str, Any]] = []
        for track in tracks:
            feature_id, payload = self._feature_from_track(track, mood)
            enriched.append(
                {
                    **track,
                    "reason_text": self._template_text(feature_id, payload),
                    "reason_feature_id": feature_id,
                    "reason_method": "TEMPLATE",
                }
            )
        return header[:120], enriched

    def attach(self, user_id: str, mood: str, tracks: list[dict[str, Any]]) -> tuple[str, str, list[dict[str, Any]]]:
        prompt_hash = hashlib.sha256(
            json.dumps(
                {
                    "mood": mood,
                    "track_ids": [track["track_id"] for track in tracks],
                    "model": self.settings.groq_model,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()

        estimated_tokens = len(tracks) * 120
        if self.token_budget and not self.token_budget.can_spend(user_id, estimated_tokens):
            header, enriched = self._fallback(mood, tracks)
            for track in enriched:
                self.repository.insert_explanation_audit_log(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    track_id=track["track_id"],
                    feature_id=track["reason_feature_id"],
                    rendered_text=track["reason_text"],
                    generation_method="TEMPLATE",
                    model_id=self.settings.groq_model,
                    prompt_hash=prompt_hash,
                    grounding_passed=True,
                )
            return header, "TEMPLATE", enriched

        try:
            result = self.gateway.generate_drop_explanations(mood, tracks)
            reasons = result["reasons"]
            if len(reasons) != len(tracks):
                raise RuntimeError("Unexpected reason count")

            enriched: list[dict[str, Any]] = []
            for track, reason in zip(tracks, reasons):
                feature_id, payload = self._feature_from_track(track, mood)
                grounded_values = [str(value).lower() for value in payload.values()]
                grounded = any(value in str(reason).lower() for value in grounded_values)
                if not grounded or len(str(reason)) > 60:
                    reason = self._template_text(feature_id, payload)
                    method = "TEMPLATE"
                    grounded = True
                else:
                    method = "LLM"
                enriched.append(
                    {
                        **track,
                        "reason_text": str(reason),
                        "reason_feature_id": feature_id,
                        "reason_method": method,
                    }
                )
                self.repository.insert_explanation_audit_log(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    track_id=track["track_id"],
                    feature_id=feature_id,
                    rendered_text=str(reason),
                    generation_method=method,
                    model_id=self.settings.groq_model,
                    prompt_hash=prompt_hash,
                    grounding_passed=grounded,
                )
            header = str(result.get("header") or "")[:120] or f"Fresh picks for your {mood.title()} mood"
            if self.token_budget:
                self.token_budget.record(user_id, estimated_tokens)
            return header, "LLM", enriched
        except Exception:
            header, enriched = self._fallback(mood, tracks)
            for track in enriched:
                self.repository.insert_explanation_audit_log(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    track_id=track["track_id"],
                    feature_id=track["reason_feature_id"],
                    rendered_text=track["reason_text"],
                    generation_method="TEMPLATE",
                    model_id=self.settings.groq_model,
                    prompt_hash=prompt_hash,
                    grounding_passed=True,
                )
            return header, "TEMPLATE", enriched
