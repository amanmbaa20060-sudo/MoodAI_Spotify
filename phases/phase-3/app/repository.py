"""Database access helpers for the Phase 1 MVP."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from phases.common.db import fetch_all_dicts, fetch_one_dict, get_connection


class Phase3Repository:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def get_active_mood(self, user_id: str, default_mood: str) -> str:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT active_mood
                FROM user_mood_preferences
                WHERE user_id = %s
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else default_mood

    def set_active_mood(self, user_id: str, mood: str, persist: bool) -> None:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_mood_preferences (user_id, active_mood, persist, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET active_mood = EXCLUDED.active_mood,
                    persist = EXCLUDED.persist,
                    updated_at = NOW()
                """,
                (user_id, mood, persist),
            )
            conn.commit()

    def fetch_candidates(self, mood: str, limit: int = 300) -> list[dict[str, Any]]:
        comparator = "m.primary_mood = %s OR %s = ANY(m.mood_tags)"
        params: tuple[Any, ...]
        if mood == "ADVENTUROUS":
            comparator = "TRUE"
            params = (limit,)
        else:
            params = (mood, mood, limit)

        sql = f"""
            SELECT
                t.track_id,
                t.name AS title,
                t.artist_name,
                t.album_name,
                t.genre,
                m.primary_mood,
                m.mood_tags,
                m.energy,
                m.valence,
                m.tempo,
                m.instrumentalness,
                CASE
                    WHEN m.primary_mood = %s THEN 0.85
                    WHEN %s = ANY(m.mood_tags) THEN 0.70
                    ELSE 0.45
                END AS base_rec_score
            FROM tracks t
            JOIN track_mood_tags m ON m.track_id = t.track_id
            WHERE {comparator}
            ORDER BY t.track_id
            LIMIT %s
        """

        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            if mood == "ADVENTUROUS":
                cur.execute(
                    """
                    SELECT
                        t.track_id,
                        t.name AS title,
                        t.artist_name,
                        t.album_name,
                        t.genre,
                        m.primary_mood,
                        m.mood_tags,
                        m.energy,
                        m.valence,
                        m.tempo,
                        m.instrumentalness,
                        0.55 AS base_rec_score
                    FROM tracks t
                    JOIN track_mood_tags m ON m.track_id = t.track_id
                    ORDER BY t.track_id
                    LIMIT %s
                    """,
                    params,
                )
            else:
                cur.execute(sql, (mood, mood, *params))
            return fetch_all_dicts(cur)

    def get_played_track_ids(self, user_id: str) -> set[str]:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT track_id FROM play_history WHERE user_id = %s",
                (user_id,),
            )
            return {row[0] for row in cur.fetchall()}

    def get_recent_drop_track_ids(self, user_id: str, days: int = 7) -> set[str]:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT dt.track_id
                FROM discovery_drop dd
                JOIN drop_track dt ON dt.drop_id = dd.drop_id
                WHERE dd.user_id = %s
                  AND dd.drop_date >= CURRENT_DATE - %s::INT
                """,
                (user_id, days),
            )
            return {row[0] for row in cur.fetchall()}

    def list_drop(self, user_id: str, drop_date: date) -> dict[str, Any] | None:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT drop_id, user_id, drop_date, mood_at_generation, drop_header,
                       header_method, track_count, status, created_at
                FROM discovery_drop
                WHERE user_id = %s AND drop_date = %s
                """,
                (user_id, drop_date),
            )
            drop = fetch_one_dict(cur)
            if drop is None:
                return None

            cur.execute(
                """
                SELECT
                    dt.position,
                    dt.track_id,
                    t.name AS title,
                    t.artist_name,
                    t.album_name,
                    t.genre,
                    dt.reason_text,
                    dt.reason_feature_id,
                    dt.reason_method,
                    dt.base_score
                FROM drop_track dt
                JOIN tracks t ON t.track_id = dt.track_id
                WHERE dt.drop_id = %s
                ORDER BY dt.position ASC
                """,
                (drop["drop_id"],),
            )
            drop["tracks"] = fetch_all_dicts(cur)
            return drop

    def save_drop(
        self,
        user_id: str,
        active_mood: str,
        header: str,
        header_method: str,
        tracks: list[dict[str, Any]],
        drop_date: date,
    ) -> dict[str, Any]:
        drop_id = str(uuid.uuid4())
        status = "READY" if len(tracks) == 10 else "PARTIAL"
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO discovery_drop
                    (drop_id, user_id, drop_date, mood_at_generation, drop_header,
                     header_method, track_count, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (user_id, drop_date) DO UPDATE
                SET mood_at_generation = EXCLUDED.mood_at_generation,
                    drop_header = EXCLUDED.drop_header,
                    header_method = EXCLUDED.header_method,
                    track_count = EXCLUDED.track_count,
                    status = EXCLUDED.status,
                    created_at = NOW()
                RETURNING drop_id
                """,
                (
                    drop_id,
                    user_id,
                    drop_date,
                    active_mood,
                    header,
                    header_method,
                    len(tracks),
                    status,
                ),
            )
            stored_drop_id = cur.fetchone()[0]
            cur.execute("DELETE FROM drop_track WHERE drop_id = %s", (stored_drop_id,))
            for position, track in enumerate(tracks, start=1):
                cur.execute(
                    """
                    INSERT INTO drop_track
                        (drop_id, position, track_id, reason_text, reason_feature_id,
                         reason_method, base_score)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        stored_drop_id,
                        position,
                        track["track_id"],
                        track["reason_text"],
                        track["reason_feature_id"],
                        track["reason_method"],
                        track["score"],
                    ),
                )
            conn.commit()

        return self.list_drop(user_id, drop_date) or {}

    def insert_explanation_audit_log(
        self,
        *,
        recommendation_id: str,
        user_id: str,
        track_id: str,
        feature_id: str,
        rendered_text: str,
        generation_method: str,
        model_id: str,
        prompt_hash: str,
        grounding_passed: bool,
    ) -> None:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO explanation_audit_log
                    (recommendation_id, user_id, track_id, feature_id, rendered_text,
                     generation_method, model_id, prompt_hash, grounding_passed, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    recommendation_id,
                    user_id,
                    track_id,
                    feature_id,
                    rendered_text,
                    generation_method,
                    model_id,
                    prompt_hash,
                    grounding_passed,
                ),
            )
            conn.commit()

    def list_known_users(self) -> list[str]:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT DISTINCT user_id FROM user_mood_preferences
                UNION
                SELECT DISTINCT user_id FROM play_history
                ORDER BY user_id
                """
            )
            users = [row[0] for row in cur.fetchall()]
            return users or ["demo-user"]

    @staticmethod
    def next_refresh_at() -> datetime:
        tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)

    def search_artists(self, query: str, limit: int = 24) -> list[dict[str, Any]]:
        pattern = f"%{query.strip()}%"
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    MD5(LOWER(COALESCE(t.artist_name, 'unknown'))) AS artist_id,
                    t.artist_name,
                    MAX(t.artist_image_url) AS artist_image_url,
                    COUNT(*)::INT AS track_count,
                    MODE() WITHIN GROUP (ORDER BY t.genre) AS top_genre
                FROM tracks t
                WHERE t.artist_name ILIKE %s
                GROUP BY t.artist_name
                ORDER BY track_count DESC, t.artist_name ASC
                LIMIT %s
                """,
                (pattern, limit),
            )
            return fetch_all_dicts(cur)

    def get_artist_with_tracks(
        self, artist_id: str, limit: int = 100
    ) -> dict[str, Any] | None:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    MD5(LOWER(COALESCE(t.artist_name, 'unknown'))) AS artist_id,
                    t.artist_name,
                    MAX(t.artist_image_url) AS artist_image_url,
                    COUNT(*)::INT AS track_count,
                    MODE() WITHIN GROUP (ORDER BY t.genre) AS top_genre
                FROM tracks t
                WHERE MD5(LOWER(COALESCE(t.artist_name, 'unknown'))) = %s
                GROUP BY t.artist_name
                """,
                (artist_id,),
            )
            artist = fetch_one_dict(cur)
            if artist is None:
                return None

            cur.execute(
                """
                SELECT
                    track_id,
                    name AS title,
                    artist_name,
                    album_name,
                    genre
                FROM tracks
                WHERE MD5(LOWER(COALESCE(artist_name, 'unknown'))) = %s
                ORDER BY name ASC
                LIMIT %s
                """,
                (artist_id, limit),
            )
            artist["tracks"] = fetch_all_dicts(cur)
            return artist

    def record_heard_before(
        self, user_id: str, track_id: str, drop_id: str | None
    ) -> str:
        report_id = str(uuid.uuid4())
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO heard_before_reports (report_id, user_id, track_id, drop_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, track_id) DO UPDATE
                SET reported_at = NOW(),
                    drop_id = EXCLUDED.drop_id
                RETURNING report_id
                """,
                (report_id, user_id, track_id, drop_id),
            )
            stored = cur.fetchone()[0]
            conn.commit()
            return str(stored)

    def get_heard_before_track_ids(self, user_id: str) -> set[str]:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT track_id FROM heard_before_reports WHERE user_id = %s",
                (user_id,),
            )
            return {row[0] for row in cur.fetchall()}

    def upsert_push_subscription(self, user_id: str, endpoint: str) -> None:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO push_subscriptions (user_id, endpoint, enabled, subscribed_at)
                VALUES (%s, %s, TRUE, NOW())
                ON CONFLICT (user_id) DO UPDATE
                SET endpoint = EXCLUDED.endpoint,
                    enabled = TRUE,
                    subscribed_at = NOW()
                """,
                (user_id, endpoint),
            )
            conn.commit()

    def get_push_subscription(self, user_id: str) -> dict[str, Any] | None:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT user_id, endpoint, enabled, subscribed_at
                FROM push_subscriptions
                WHERE user_id = %s
                """,
                (user_id,),
            )
            return fetch_one_dict(cur)

    def log_push_notification(
        self,
        notification_id: str,
        user_id: str,
        event_type: str,
        payload: str,
    ) -> None:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO push_notification_log
                    (notification_id, user_id, event_type, payload, sent_at)
                VALUES (%s, %s, %s, %s::jsonb, NOW())
                """,
                (notification_id, user_id, event_type, payload),
            )
            conn.commit()

    def list_explanation_audit(self, user_id: str, limit: int = 50) -> list[dict[str, Any]]:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT recommendation_id, user_id, track_id, feature_id, rendered_text,
                       generation_method, model_id, prompt_hash, grounding_passed, created_at
                FROM explanation_audit_log
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return fetch_all_dicts(cur)

    def get_dominant_play_mood(self, user_id: str) -> str | None:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.primary_mood, COUNT(*) AS plays
                FROM play_history ph
                JOIN track_mood_tags m ON m.track_id = ph.track_id
                WHERE ph.user_id = %s AND m.primary_mood IS NOT NULL
                GROUP BY m.primary_mood
                ORDER BY plays DESC
                LIMIT 1
                """,
                (user_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None

    def get_experiment_variant(self, user_id: str, flag_name: str, default: str) -> str:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT variant FROM experiment_assignments
                WHERE user_id = %s AND flag_name = %s
                """,
                (user_id, flag_name),
            )
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                """
                INSERT INTO experiment_assignments (user_id, flag_name, variant)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, flag_name) DO NOTHING
                """,
                (user_id, flag_name, default),
            )
            conn.commit()
            return default

    def get_llm_tokens_used(self, user_id: str, usage_date: date) -> int:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT tokens_used FROM llm_token_usage
                WHERE user_id = %s AND usage_date = %s
                """,
                (user_id, usage_date),
            )
            row = cur.fetchone()
            return int(row[0]) if row else 0

    def add_llm_token_usage(self, user_id: str, usage_date: date, tokens: int) -> int:
        with get_connection(self.database_url) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_token_usage (user_id, usage_date, tokens_used)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, usage_date) DO UPDATE
                SET tokens_used = llm_token_usage.tokens_used + EXCLUDED.tokens_used
                RETURNING tokens_used
                """,
                (user_id, usage_date, tokens),
            )
            total = int(cur.fetchone()[0])
            conn.commit()
            return total


# Backward-compatible aliases for copied modules
Phase2Repository = Phase3Repository
Phase1Repository = Phase3Repository
