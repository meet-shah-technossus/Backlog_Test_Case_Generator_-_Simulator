from __future__ import annotations

from app.modules.agent2.contracts.models import Agent2HandoffEnvelope
from app.modules.agent2.mcp.inbox_store_mcp_service import Agent2InboxStoreMCPService

class Agent2InboxRepository:
    """Agent2 inbox persistence and idempotent consume-by-message-id."""

    def __init__(self, mcp_store: Agent2InboxStoreMCPService | None = None):
        self._mcp_store = mcp_store or Agent2InboxStoreMCPService()

    def consume(self, envelope: Agent2HandoffEnvelope) -> tuple[dict, bool]:
        return self._mcp_store.upsert_inbox(
            message_id=envelope.message_id,
            source_agent1_run_id=envelope.run_id,
            trace_id=envelope.trace_id,
            contract_version=envelope.contract_version,
            task_type=envelope.task_type,
            payload=envelope.payload,
            intake_status="accepted",
        )

    def get_by_message_id(self, message_id: str) -> dict | None:
        return self._mcp_store.get_inbox(message_id)
