from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.review.script_review_service import Agent4ScriptReviewService
from app.modules.agent4.workflow.state_machine import validate_state


def _find_latest_phase5_script_bundle(artifacts: list[dict]) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_generated_script_bundle":
            return artifact_row
    return None


def submit_phase6_review(
    *,
    run_id: str,
    decision: str,
    reviewer_id: str,
    reason_code: str | None,
    edited_scripts: list[dict] | None,
    run_repo: Agent4RunRepository,
    review_service: Agent4ScriptReviewService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")

    if run.get("state") not in {"generation_completed", "review_pending", "review_rejected", "handoff_pending"}:
        raise ValueError(
            f"Agent4 run '{run_id}' not eligible for Phase 6 review from state '{run.get('state')}'"
        )

    script_row = _find_latest_phase5_script_bundle(run_repo.get_artifacts(run_id))
    if script_row is None:
        raise ValueError(f"Agent4 run '{run_id}' has no Phase 5 script bundle artifact")

    script_artifact = script_row.get("artifact") if isinstance(script_row, dict) else {}
    script_artifact = script_artifact if isinstance(script_artifact, dict) else {}

    readiness = review_service.assess_script_bundle_readiness(script_bundle=script_artifact)
    review_service.validate_review_request(
        decision=decision,
        reason_code=reason_code,
        edited_scripts=edited_scripts,
        readiness=readiness,
    )

    latest_artifact_for_return = script_row
    if decision == "edit_approve":
        edited_artifact = review_service.build_edited_artifact(
            base_artifact=script_artifact,
            edited_scripts=edited_scripts or [],
        )
        run_repo.add_artifact(run_id=run_id, artifact=edited_artifact)
        latest_artifact_for_return = run_repo.get_latest_artifact(run_id) or script_row
    elif decision == "approve" and not bool(readiness.get("ready")):
        override_artifact = review_service.build_approved_override_artifact(
            base_artifact=script_artifact,
            reason_code=reason_code,
        )
        run_repo.add_artifact(run_id=run_id, artifact=override_artifact)
        latest_artifact_for_return = run_repo.get_latest_artifact(run_id) or script_row

    if decision in {"approve", "edit_approve"}:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("handoff_pending"),
            stage="phase-6-review-approved",
            last_error_code=None,
            last_error_message=None,
        )
    elif decision == "retry":
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("generation_ready"),
            stage="phase-6-review-retry-requested",
            last_error_code="A4_PHASE6_RETRY_REQUESTED",
            last_error_message=reason_code,
        )
    else:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("review_rejected"),
            stage="phase-6-review-rejected",
            last_error_code="A4_PHASE6_REVIEW_REJECTED",
            last_error_message=reason_code,
        )

    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-6-readiness-review",
        action=f"phase6_review_{decision}",
        actor=reviewer_id,
        metadata={
            "reason_code": reason_code,
            "edited": decision == "edit_approve",
            "ready": readiness.get("ready"),
            "script_count": readiness.get("script_count", 0),
            "empty_script_count": readiness.get("empty_script_count", 0),
        },
    )

    return {
        "run": run_repo.get_run(run_id) or run,
        "script_bundle_artifact": latest_artifact_for_return,
    }
