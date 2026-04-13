from __future__ import annotations

from app.modules.agent2.db.inbox_repository import Agent2InboxRepository
from app.modules.agent2.contracts.models import Agent2HandoffEnvelope


class Agent2HandoffInboxService:
    """Phase 2 intake service for validation and idempotent inbox persistence."""

    def __init__(self, inbox_repo: Agent2InboxRepository):
        self._inbox_repo = inbox_repo

    def consume(self, envelope: Agent2HandoffEnvelope) -> tuple[dict, bool]:
        # Pydantic contract validation has already been applied by request parsing.
        return self._inbox_repo.consume(envelope)

    def get(self, message_id: str) -> dict | None:
        return self._inbox_repo.get_by_message_id(message_id)
