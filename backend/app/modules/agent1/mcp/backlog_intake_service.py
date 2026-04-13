from __future__ import annotations

from pathlib import Path

from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.agent1.mcp.contracts import MCPBacklogIntakeRequest, MCPBacklogIntakeResponse
from app.modules.agent1.services.backlog_service import BacklogService


class MCPBacklogIntakeService:
    """
    MCP-facing intake service for Agent 1 backlog acquisition.

    Phase 3 scope:
    - normalize and persist API backlog into DB
    - normalize and persist sample backlog into DB
    - return canonical backlog item records for workflow input
    """

    def __init__(self, backlog_service: BacklogService, backlog_repo: Agent1BacklogRepository):
        self._backlog_service = backlog_service
        self._backlog_repo = backlog_repo

    async def load(self, request: MCPBacklogIntakeRequest) -> MCPBacklogIntakeResponse:
        source_type = request.source_type

        if source_type == "api":
            await self._backlog_service.fetch()
            items = self._backlog_repo.list_items(source_type="api", limit=2000)
            return MCPBacklogIntakeResponse(
                source_type="api",
                source_ref=request.source_ref,
                item_count=len(items),
                items=items,
            )

        sample_backlog = self._backlog_service.get_sample_from_db()
        if sample_backlog is None:
            sample_path = Path(__file__).resolve().parents[5] / "tests" / "sample_backlog.json"
            self._backlog_service.load_from_file(sample_path)

        items = self._backlog_repo.list_items(source_type="sample_db", limit=2000)
        return MCPBacklogIntakeResponse(
            source_type="sample_db",
            source_ref=request.source_ref,
            item_count=len(items),
            items=items,
        )
