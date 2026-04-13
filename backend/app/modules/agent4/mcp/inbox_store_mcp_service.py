from __future__ import annotations

from app.infrastructure.store import store


class Agent4InboxStoreMCPService:
    """MCP data-plane adapter for Agent4 intake inbox persistence."""

    def upsert_inbox(self, **kwargs) -> tuple[dict, bool]:
        return store.upsert_agent4_inbox(**kwargs)

    def get_inbox(self, message_id: str) -> dict | None:
        return store.get_agent4_inbox(message_id)
