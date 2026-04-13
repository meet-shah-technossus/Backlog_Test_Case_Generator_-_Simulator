from __future__ import annotations

from app.modules.agent1.db.run_repository import Agent1RunRepository
from app.modules.agent1.workflow.state_machine import validate_state


def retry_run(*, run_id: str, reason_code: str | None, actor: str, run_repo: Agent1RunRepository) -> None:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Run '{run_id}' not found")

    current_state = run.get("state")
    if current_state == "handoff_emitted":
        raise ValueError(
            f"Run '{run_id}' is locked after handoff emission and cannot be retried"
        )
    if current_state in {"review_approved", "handoff_pending"}:
        raise ValueError(
            f"Run '{run_id}' is already approved and cannot transition to 'retry'"
        )

    run_repo.add_review(
        run_id=run_id,
        stage="agent1_review",
        decision="retry",
        reason_code=reason_code,
        reviewer_id=actor,
        edited_payload=None,
    )

    backlog_item_id = run["backlog_item_id"]
    trace_id = run["trace_id"]
    source_type = run.get("source_type")
    source_ref = run.get("source_ref")
    run_repo.update_state(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        trace_id=trace_id,
        state=validate_state("review_retry_requested"),
        source_type=source_type,
        source_ref=source_ref,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="review",
        action="retry_requested",
        actor=actor,
        metadata={"reason_code": reason_code},
    )
    run_repo.create_retry_request(
        run_id=run_id,
        requested_by=actor,
        reason_code=reason_code,
        reason_text=reason_code,
    )
