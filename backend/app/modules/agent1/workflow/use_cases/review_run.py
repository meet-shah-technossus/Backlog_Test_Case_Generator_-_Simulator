from __future__ import annotations

from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.agent1.db.run_repository import Agent1RunRepository
from app.modules.agent1.workflow.services.review_edit_service import persist_human_edited_artifact
from app.modules.agent1.workflow.state_machine import validate_state


def submit_review(
    *,
    run_id: str,
    decision: str,
    reviewer_id: str,
    reason_code: str | None,
    edited_payload: dict | None,
    backlog_repo: Agent1BacklogRepository,
    run_repo: Agent1RunRepository,
) -> None:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Run '{run_id}' not found")

    current_state = run.get("state")
    if current_state == "handoff_emitted":
        raise ValueError(
            f"Run '{run_id}' is locked after handoff emission and cannot be reviewed"
        )

    decision_to_state = {
        "approve": "review_approved",
        "edit_approve": "review_approved",
        "reject": "review_rejected",
        "retry": "review_retry_requested",
    }
    if decision not in decision_to_state:
        raise ValueError(f"Unsupported decision '{decision}'")

    if decision in {"reject", "retry"} and current_state in {"review_approved", "handoff_pending", "handoff_emitted"}:
        raise ValueError(
            f"Run '{run_id}' is already approved and cannot transition to '{decision}'"
        )

    backlog_item_id = run["backlog_item_id"]
    trace_id = run["trace_id"]
    source_type = run.get("source_type")
    source_ref = run.get("source_ref")

    if decision == "edit_approve":
        persist_human_edited_artifact(
            run_id=run_id,
            backlog_item_id=backlog_item_id,
            reviewer_id=reviewer_id,
            edited_payload=edited_payload,
            backlog_repo=backlog_repo,
            run_repo=run_repo,
        )

    run_repo.add_review(
        run_id=run_id,
        stage="agent1_review",
        decision=decision,
        reason_code=reason_code,
        reviewer_id=reviewer_id,
        edited_payload=edited_payload,
    )

    target_state = validate_state(decision_to_state[decision])
    run_repo.update_state(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        trace_id=trace_id,
        state=target_state,
        source_type=source_type,
        source_ref=source_ref,
    )

    run_repo.add_audit_event(
        run_id=run_id,
        stage="review",
        action=f"decision_{decision}",
        actor=reviewer_id,
        metadata={"reason_code": reason_code},
    )

    if decision in {"approve", "edit_approve"}:
        run_repo.update_state(
            run_id=run_id,
            backlog_item_id=backlog_item_id,
            trace_id=trace_id,
            state=validate_state("handoff_pending"),
            source_type=source_type,
            source_ref=source_ref,
        )
