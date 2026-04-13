from __future__ import annotations

from uuid import uuid4

from app.modules.agent2.db.run_repository import Agent2RunRepository
from app.modules.agent2.intake.handoff_inbox_service import Agent2HandoffInboxService
from app.modules.agent2.workflow.state_machine import validate_state


def create_run_from_inbox(
    *,
    message_id: str,
    inbox_service: Agent2HandoffInboxService,
    run_repo: Agent2RunRepository,
) -> dict:
    inbox = inbox_service.get(message_id)
    if inbox is None:
        raise ValueError(f"Inbox message '{message_id}' not found")

    run_id = str(uuid4())
    run_record, created = run_repo.create_from_inbox(
        run_id=run_id,
        inbox_message_id=message_id,
        source_agent1_run_id=inbox["source_agent1_run_id"],
        trace_id=inbox["trace_id"],
        state=validate_state("intake_ready"),
        stage="intake",
    )

    run_repo.add_audit_event(
        run_id=run_record["run_id"],
        stage="intake",
        action="run_created_from_inbox" if created else "run_reused_from_inbox",
        actor="system",
        metadata={"message_id": message_id},
    )

    return {
        "created": created,
        "run": run_record,
    }
