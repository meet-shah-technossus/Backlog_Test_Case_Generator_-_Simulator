from __future__ import annotations

from app.modules.agent3.contracts.models import Agent3HandoffEnvelope
from app.modules.agent3.mcp.inbox_store_mcp_service import Agent3InboxStoreMCPService


class Agent3InboxRepository:
    """Agent3 inbox persistence and idempotent consume-by-message-id."""

    def __init__(self, mcp_store: Agent3InboxStoreMCPService | None = None):
        self._mcp_store = mcp_store or Agent3InboxStoreMCPService()

    def consume(self, envelope: Agent3HandoffEnvelope) -> tuple[dict, bool]:
        payload = dict(envelope.payload or {})
        payload.setdefault(
            "_a2a",
            {
                "stage_id": envelope.stage_id,
                "retry_count": envelope.retry_count,
                "dedupe_key": envelope.dedupe_key,
            },
        )
        return self._mcp_store.upsert_inbox(
            message_id=envelope.message_id,
            source_agent2_run_id=envelope.run_id,
            trace_id=envelope.trace_id,
            contract_version=envelope.contract_version,
            task_type=envelope.task_type,
            payload=payload,
            intake_status="accepted",
        )

    def get_by_message_id(self, message_id: str) -> dict | None:
        return self._mcp_store.get_inbox(message_id)
