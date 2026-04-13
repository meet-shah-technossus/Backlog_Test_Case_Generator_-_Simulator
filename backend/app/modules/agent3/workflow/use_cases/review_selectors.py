from __future__ import annotations

from app.modules.agent3.db.run_repository import Agent3RunRepository
from app.modules.agent3.review.selector_review_service import Agent3SelectorReviewService
from app.modules.agent3.workflow.state_machine import validate_state


def _find_latest_selector_artifact(artifacts: list[dict]) -> dict | None:
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase4_selector_plan":
            return row
    return None


def submit_selector_review(
    *,
    run_id: str,
    decision: str,
    reviewer_id: str,
    reason_code: str | None,
    edited_selector_steps: list[dict] | None,
    run_repo: Agent3RunRepository,
    review_service: Agent3SelectorReviewService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent3 run '{run_id}' not found")

    if run.get("state") not in {"review_pending", "review_rejected", "handoff_pending"}:
        raise ValueError(
            f"Agent3 run '{run_id}' not eligible for Phase 5 review from state '{run.get('state')}'"
        )

    selector_row = _find_latest_selector_artifact(run_repo.get_artifacts(run_id))
    if selector_row is None:
        raise ValueError(f"Agent3 run '{run_id}' has no Phase 4 selector artifact")

    selector_artifact = selector_row.get("artifact") or {}

    review_service.validate_review_request(
        decision=decision,
        reason_code=reason_code,
        edited_selector_steps=edited_selector_steps,
        selector_artifact=selector_artifact,
    )

    latest_artifact_for_return = selector_row
    if decision == "edit_approve":
        next_artifact = review_service.build_edited_artifact(
            base_artifact=selector_artifact,
            edited_selector_steps=edited_selector_steps or [],
        )
        run_repo.add_artifact(run_id=run_id, artifact=next_artifact)
        latest_artifact_for_return = run_repo.get_latest_artifact(run_id) or selector_row
    elif decision == "approve" and not bool(selector_artifact.get("ready_for_handoff")):
        next_artifact = review_service.build_approved_override_artifact(
            base_artifact=selector_artifact,
            reason_code=reason_code,
        )
        run_repo.add_artifact(run_id=run_id, artifact=next_artifact)
        latest_artifact_for_return = run_repo.get_latest_artifact(run_id) or selector_row

    if decision in {"approve", "edit_approve"}:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("handoff_pending"),
            stage="phase-5-review-approved",
            last_error_code=None,
            last_error_message=None,
        )
    else:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("review_rejected"),
            stage="phase-5-review-rejected",
            last_error_code="A3_SELECTOR_REVIEW_REJECTED",
            last_error_message=reason_code,
        )

    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-5-review",
        action=f"selector_review_{decision}",
        actor=reviewer_id,
        metadata={
            "reason_code": reason_code,
            "edited": decision == "edit_approve",
        },
    )

    return {
        "run": run_repo.get_run(run_id) or run,
        "selector_artifact": latest_artifact_for_return,
    }
