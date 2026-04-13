from __future__ import annotations

from app.infrastructure.store import store


class Agent3InboxStoreMCPService:
    """MCP data-plane adapter for Agent3 intake inbox persistence."""

    def upsert_inbox(self, **kwargs) -> tuple[dict, bool]:
        return store.upsert_agent3_inbox(**kwargs)

    def get_inbox(self, message_id: str) -> dict | None:
        return store.get_agent3_inbox(message_id)
