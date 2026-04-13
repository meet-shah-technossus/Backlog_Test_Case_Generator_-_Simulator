from __future__ import annotations

import hashlib
import json

from app.modules.agent3.db.run_repository import Agent3RunRepository
from app.modules.agent3.feedback.execution_feedback_service import Agent3ExecutionFeedbackService
from app.modules.agent3.workflow.state_machine import validate_state


def _find_latest_selector_artifact(artifacts: list[dict]) -> dict | None:
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase4_selector_plan":
            return row
    return None


def _find_existing_feedback_artifact(artifacts: list[dict], message_id: str) -> dict | None:
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if not isinstance(artifact, dict):
            continue
        if artifact.get("artifact_type") != "phase6_execution_feedback":
            continue
        if str(artifact.get("message_id") or "") == message_id:
            return row
    return None


def apply_execution_feedback(
    *,
    run_id: str,
    message_id: str,
    source_agent4_run_id: str,
    outcome: str,
    recommended_action: str,
    step_results: list[dict],
    summary: dict,
    metadata: dict,
    run_repo: Agent3RunRepository,
    feedback_service: Agent3ExecutionFeedbackService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent3 run '{run_id}' not found")

    if run.get("state") not in {"handoff_emitted", "handoff_pending", "review_pending", "review_retry_requested"}:
        raise ValueError(
            f"Agent3 run '{run_id}' not eligible for Phase 6 feedback from state '{run.get('state')}'"
        )

    feedback_service.validate_feedback_request(
        outcome=outcome,
        recommended_action=recommended_action,
        step_results=step_results,
    )

    artifacts = run_repo.get_artifacts(run_id)
    existing_feedback = _find_existing_feedback_artifact(artifacts, message_id)
    if existing_feedback is not None:
        run_repo.add_audit_event(
            run_id=run_id,
            stage="phase-6-feedback",
            action="execution_feedback_reused",
            actor="agent_4",
            metadata={"message_id": message_id},
        )
        return {
            "created": False,
            "run": run_repo.get_run(run_id) or run,
            "feedback_artifact": existing_feedback,
        }

    selector_artifact_row = _find_latest_selector_artifact(artifacts)
    if selector_artifact_row is None:
        raise ValueError(f"Agent3 run '{run_id}' has no selector artifact to correlate feedback")

    computed = feedback_service.summarize(step_results=step_results)
    transition = feedback_service.derive_transition(
        outcome=outcome,
        recommended_action=recommended_action,
        failed_steps=int(computed.get("failed_steps") or 0),
    )

    feedback_artifact = {
        "artifact_type": "phase6_execution_feedback",
        "run_id": run_id,
        "message_id": message_id,
        "source_agent4_run_id": source_agent4_run_id,
        "outcome": outcome,
        "recommended_action": recommended_action,
        "selector_artifact_version": int(selector_artifact_row.get("artifact_version") or 0),
        "summary": summary or {},
        "computed": computed,
        "step_results": step_results,
        "metadata": metadata or {},
        "integrity": {
            "step_results_sha256": hashlib.sha256(
                json.dumps(step_results, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        },
    }

    run_repo.add_artifact(run_id=run_id, artifact=feedback_artifact)
    run_repo.update_state(
        run_id=run_id,
        state=validate_state(str(transition["state"])),
        stage=str(transition["stage"]),
        last_error_code=transition.get("last_error_code"),
        last_error_message=transition.get("last_error_message"),
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-6-feedback",
        action=str(transition["action"]),
        actor="agent_4",
        metadata={
            "message_id": message_id,
            "source_agent4_run_id": source_agent4_run_id,
            "outcome": outcome,
            "recommended_action": recommended_action,
            "failed_steps": computed.get("failed_steps"),
        },
    )

    return {
        "created": True,
        "run": run_repo.get_run(run_id) or run,
        "feedback_artifact": run_repo.get_latest_artifact(run_id),
    }
