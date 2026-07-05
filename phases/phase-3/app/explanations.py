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
        track_count = len(tracks)
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
                        f"reasons must be an array of exactly {track_count} strings, "
                        "one per track in the same order. "
                        "Each reason must be under 60 characters and mention only "
                        "the artist, genre, or mood from that track."
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
                "User-Agent": "MoodAI/1.0",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=45) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("Groq request failed") from exc

        content = raw["choices"][0]["message"]["content"]
        result = json.loads(content)
        if "header" not in result or "reasons" not in result:
            raise RuntimeError("Invalid Groq response shape")
        return result


def _batched(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


class ExplanationService:
    def __init__(self, repository: Phase1Repository, settings: Settings, token_budget=None):
        self.repository = repository
        self.settings = settings
        self.gateway = GroqLLMGateway(settings)
        self.token_budget = token_budget

    def _generate_explanations(self, mood: str, tracks: list[dict[str, Any]]) -> dict[str, Any]:
        if len(tracks) <= 5:
            result = self.gateway.generate_drop_explanations(mood, tracks)
            if len(result.get("reasons", [])) != len(tracks):
                raise RuntimeError("Unexpected reason count")
            return result

        header = ""
        reasons: list[Any] = []
        for batch in _batched(tracks, 5):
            result = self.gateway.generate_drop_explanations(mood, batch)
            batch_reasons = result.get("reasons", [])
            if len(batch_reasons) != len(batch):
                raise RuntimeError("Unexpected reason count")
            if not header:
                header = str(result.get("header") or "")
            reasons.extend(batch_reasons)
        return {"header": header, "reasons": reasons}

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

    @staticmethod
    def _normalize_reason(raw: Any) -> str:
        if raw is None:
            return ""
        if isinstance(raw, str):
            text = raw.strip()
            if text.startswith("{") and text.endswith("}"):
                try:
                    import ast

                    parsed = ast.literal_eval(text)
                    if isinstance(parsed, dict):
                        return ExplanationService._normalize_reason(parsed)
                except (ValueError, SyntaxError):
                    pass
            return text
        if isinstance(raw, dict):
            for key in ("reason", "text", "explanation", "message"):
                value = raw.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return str(raw).strip()

    @staticmethod
    def _is_grounded(track: dict[str, Any], mood: str, reason_text: str) -> bool:
        text = reason_text.lower()
        if not text:
            return False
        mood_label = mood.lower().replace("_", " ")
        if mood_label in text or mood.lower() in text:
            return True
        genre = track.get("genre")
        if genre and str(genre).lower() in text:
            return True
        artist = track.get("artist_name")
        if artist:
            artist_lower = str(artist).lower()
            if artist_lower in text or text in artist_lower:
                return True
            lead_artist = artist_lower.split(";")[0].strip()
            if lead_artist and (lead_artist in text or text in lead_artist):
                return True
        return False

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

        estimated_tokens = min(len(tracks) * 80, 2400)
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
            result = self._generate_explanations(mood, tracks)
            reasons = result["reasons"]
            enriched: list[dict[str, Any]] = []
            llm_count = 0
            for track, reason in zip(tracks, reasons):
                reason_text = self._normalize_reason(reason)
                feature_id, payload = self._feature_from_track(track, mood)
                grounded = self._is_grounded(track, mood, reason_text)
                if not reason_text or not grounded or len(reason_text) > 60:
                    reason_text = self._template_text(feature_id, payload)
                    method = "TEMPLATE"
                    grounded = True
                else:
                    method = "LLM"
                    llm_count += 1
                enriched.append(
                    {
                        **track,
                        "reason_text": reason_text,
                        "reason_feature_id": feature_id,
                        "reason_method": method,
                    }
                )
                self.repository.insert_explanation_audit_log(
                    recommendation_id=str(uuid.uuid4()),
                    user_id=user_id,
                    track_id=track["track_id"],
                    feature_id=feature_id,
                    rendered_text=reason_text,
                    generation_method=method,
                    model_id=self.settings.groq_model,
                    prompt_hash=prompt_hash,
                    grounding_passed=grounded,
                )
            header = str(result.get("header") or "")[:120] or f"Fresh picks for your {mood.title()} mood"
            if self.token_budget:
                self.token_budget.record(user_id, estimated_tokens)
            header_method = "LLM" if llm_count else "TEMPLATE"
            return header, header_method, enriched
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
