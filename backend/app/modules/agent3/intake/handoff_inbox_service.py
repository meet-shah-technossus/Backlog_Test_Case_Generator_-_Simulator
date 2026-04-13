from __future__ import annotations

from app.modules.agent3.contracts.models import Agent3HandoffEnvelope
from app.modules.agent3.db.inbox_repository import Agent3InboxRepository


class Agent3HandoffInboxService:
    """Phase 2 intake service for validation and idempotent inbox persistence."""

    def __init__(self, inbox_repo: Agent3InboxRepository):
        self._inbox_repo = inbox_repo

    def consume(self, envelope: Agent3HandoffEnvelope) -> tuple[dict, bool]:
        return self._inbox_repo.consume(envelope)

    def get(self, message_id: str) -> dict | None:
        return self._inbox_repo.get_by_message_id(message_id)
