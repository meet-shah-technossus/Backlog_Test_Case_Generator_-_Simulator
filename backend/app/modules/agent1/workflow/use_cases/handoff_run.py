from __future__ import annotations

from uuid import uuid4

from app.modules.agent1.db.run_repository import Agent1RunRepository
from app.modules.agent1.workflow.state_machine import validate_state


def emit_handoff(*, run_id: str, run_repo: Agent1RunRepository) -> None:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Run '{run_id}' not found")

    if run["state"] not in {"handoff_pending", "handoff_emitted"}:
        raise ValueError(f"Run '{run_id}' not eligible for handoff from state '{run['state']}'")

    message_id = str(uuid4())
    payload = {
        "run_id": run_id,
        "backlog_item_id": run["backlog_item_id"],
        "trace_id": run["trace_id"],
        "task": "generate_steps",
    }
    run_repo.add_handoff(
        run_id=run_id,
        message_id=message_id,
        from_agent="agent_1",
        to_agent="agent_2",
        task_type="generate_steps",
        contract_version="v1",
        payload=payload,
        delivery_status="queued",
    )

    run_repo.update_state(
        run_id=run_id,
        backlog_item_id=run["backlog_item_id"],
        trace_id=run["trace_id"],
        state=validate_state("handoff_emitted"),
        source_type=run.get("source_type"),
        source_ref=run.get("source_ref"),
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="handoff",
        action="a2a_emitted",
        actor="system",
        metadata={"message_id": message_id},
    )
