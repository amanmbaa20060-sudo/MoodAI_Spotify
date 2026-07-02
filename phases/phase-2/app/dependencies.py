"""FastAPI dependencies for demo auth and shared services."""

from __future__ import annotations

from fastapi import Header


def get_user_id(x_user_id: str | None = Header(default=None)) -> str:
    return (x_user_id or "demo-user").strip() or "demo-user"
