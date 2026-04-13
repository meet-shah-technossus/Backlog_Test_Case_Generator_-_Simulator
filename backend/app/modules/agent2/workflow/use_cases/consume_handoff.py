from __future__ import annotations

from app.modules.agent2.contracts.models import Agent2HandoffEnvelope
from app.modules.agent2.intake.handoff_inbox_service import Agent2HandoffInboxService


def consume_handoff(
    *,
    envelope: Agent2HandoffEnvelope,
    inbox_service: Agent2HandoffInboxService,
) -> dict:
    record, created = inbox_service.consume(envelope)
    return {
        "created": created,
        "inbox": record,
    }
