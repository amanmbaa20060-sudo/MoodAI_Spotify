"""Horizontal sharding helpers for drop generator workers."""

from __future__ import annotations

import hashlib


def user_partition(user_id: str, partitions: int) -> int:
    if partitions <= 1:
        return 0
    digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % partitions


def users_for_partition(user_ids: list[str], partition: int, partitions: int) -> list[str]:
    return [uid for uid in user_ids if user_partition(uid, partitions) == partition]
