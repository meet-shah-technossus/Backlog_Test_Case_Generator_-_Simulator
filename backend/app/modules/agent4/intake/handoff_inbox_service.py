from __future__ import annotations

from app.modules.agent4.contracts.models import Agent4HandoffEnvelope
from app.modules.agent4.db.inbox_repository import Agent4InboxRepository


class Agent4HandoffInboxService:
    """Phase 1 intake service for validation and idempotent inbox persistence."""

    def __init__(self, inbox_repo: Agent4InboxRepository):
        self._inbox_repo = inbox_repo

    def consume(self, envelope: Agent4HandoffEnvelope) -> tuple[dict, bool]:
        return self._inbox_repo.consume(envelope)

    def get(self, message_id: str) -> dict | None:
        return self._inbox_repo.get_by_message_id(message_id)
