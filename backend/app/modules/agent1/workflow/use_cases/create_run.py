from __future__ import annotations

from uuid import uuid4

from app.infrastructure.telemetry_service import new_trace_id
from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.agent1.db.run_repository import Agent1RunRepository
from app.modules.agent1.workflow.state_machine import validate_state


def create_run(*, backlog_item_id: str, backlog_repo: Agent1BacklogRepository, run_repo: Agent1RunRepository) -> str:
    item = backlog_repo.get_item(backlog_item_id)
    if item is None:
        raise ValueError(f"Backlog item '{backlog_item_id}' not found")

    run_id = str(uuid4())
    trace_id = new_trace_id("agent1")
    state = validate_state("intake_ready")
    run_repo.create_run(
        run_id=run_id,
        backlog_item_id=item.backlog_item_id,
        trace_id=trace_id,
        state=state,
        source_type=item.source_type,
        source_ref=item.source_ref,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="intake",
        action="run_created",
        actor="system",
        metadata={"backlog_item_id": item.backlog_item_id, "source_type": item.source_type},
    )
    return run_id
