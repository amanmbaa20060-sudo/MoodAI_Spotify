"""Push notification consumer for DiscoveryDropReady events."""

from __future__ import annotations

import json
import uuid
from typing import Any


class PushNotificationService:
    def __init__(self, repository, enabled: bool):
        self.repository = repository
        self.enabled = enabled

    def subscribe(self, user_id: str, endpoint: str) -> dict[str, Any]:
        self.repository.upsert_push_subscription(user_id, endpoint)
        return {"user_id": user_id, "endpoint": endpoint, "enabled": True}

    def notify_drop_ready(self, user_id: str, drop_id: str, header: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        subscription = self.repository.get_push_subscription(user_id)
        if subscription is None or not subscription.get("enabled"):
            return None

        payload = {
            "title": "Your Discovery Drop is ready",
            "body": header,
            "drop_id": drop_id,
        }
        notification_id = str(uuid.uuid4())
        self.repository.log_push_notification(
            notification_id=notification_id,
            user_id=user_id,
            event_type="DiscoveryDropReady",
            payload=json.dumps(payload),
        )
        return {"notification_id": notification_id, "payload": payload, "status": "queued"}
