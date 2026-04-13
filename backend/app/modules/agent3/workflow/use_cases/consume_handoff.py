from __future__ import annotations

from app.modules.agent3.contracts.models import Agent3HandoffEnvelope
from app.modules.agent3.intake.handoff_inbox_service import Agent3HandoffInboxService


def consume_handoff(
    *,
    envelope: Agent3HandoffEnvelope,
    inbox_service: Agent3HandoffInboxService,
) -> dict:
    record, created = inbox_service.consume(envelope)
    return {
        "created": created,
        "inbox": record,
    }
