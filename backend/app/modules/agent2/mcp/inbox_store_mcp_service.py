from __future__ import annotations

from app.infrastructure.store import store


class Agent2InboxStoreMCPService:
    """MCP data-plane adapter for Agent2 intake inbox persistence."""

    def upsert_inbox(self, **kwargs) -> tuple[dict, bool]:
        return store.upsert_agent2_inbox(**kwargs)

    def get_inbox(self, message_id: str) -> dict | None:
        return store.get_agent2_inbox(message_id)
