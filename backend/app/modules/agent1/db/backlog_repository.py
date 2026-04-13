from __future__ import annotations

from app.modules.agent1.mcp.backlog_store_mcp_service import Agent1BacklogStoreMCPService
from app.modules.agent1.mcp.contracts import BacklogItemCanonical


class Agent1BacklogRepository:
    def __init__(self, mcp_store: Agent1BacklogStoreMCPService | None = None):
        self._mcp_store = mcp_store or Agent1BacklogStoreMCPService()

    def list_items(self, *, source_type: str | None = None, limit: int = 2000) -> list[BacklogItemCanonical]:
        rows = self._mcp_store.list_items(source_type=source_type, limit=limit)
        return [self._to_contract(row) for row in rows]

    def get_item(self, backlog_item_id: str) -> BacklogItemCanonical | None:
        row = self._mcp_store.get_item(backlog_item_id)
        if row is None:
            return None
        return self._to_contract(row)

    def _to_contract(self, row: dict) -> BacklogItemCanonical:
        return BacklogItemCanonical(
            backlog_item_id=row["backlog_item_id"],
            title=row.get("story_title") or "",
            description=row.get("story_description") or "",
            acceptance_criteria=row.get("acceptance_criteria") or [],
            target_url=row.get("target_url"),
            epic_id=row.get("epic_id"),
            epic_title=row.get("epic_title"),
            feature_id=row.get("feature_id"),
            feature_title=row.get("feature_title"),
            source_type=row.get("source_type") or "sample_db",
            source_ref=row.get("source_ref"),
        )
