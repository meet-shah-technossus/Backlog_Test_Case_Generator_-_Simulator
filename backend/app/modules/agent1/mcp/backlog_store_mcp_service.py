from __future__ import annotations

from app.infrastructure.store import store


class Agent1BacklogStoreMCPService:
    """MCP data-plane adapter for Agent1 backlog persistence reads/writes."""

    def list_items(self, *, source_type: str | None = None, limit: int = 2000) -> list[dict]:
        return store.get_backlog_items(source_type=source_type, limit=limit)

    def get_item(self, backlog_item_id: str) -> dict | None:
        return store.get_backlog_item(backlog_item_id)

    def upsert_backlog_items(self, *, backlog, source_type: str, source_ref: str | None = None) -> None:
        store.upsert_backlog_items(backlog=backlog, source_type=source_type, source_ref=source_ref)

    def get_backlog_data_by_source(self, source_type: str):
        return store.get_backlog_data_by_source(source_type)
