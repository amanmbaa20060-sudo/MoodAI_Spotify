"""Database access helpers for the Phase 1 MVP."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

from phases.common.db import fetch_all_dicts, fetch_one_dict, get_connection


class Phase1Repository:
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
