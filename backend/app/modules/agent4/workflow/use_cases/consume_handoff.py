from __future__ import annotations

from app.modules.agent4.contracts.models import Agent4HandoffEnvelope
from app.modules.agent4.intake.handoff_inbox_service import Agent4HandoffInboxService


def consume_handoff(
    *,
    envelope: Agent4HandoffEnvelope,
    inbox_service: Agent4HandoffInboxService,
) -> dict:
    record, created = inbox_service.consume(envelope)
    return {
        "created": created,
        "inbox": record,
    }
