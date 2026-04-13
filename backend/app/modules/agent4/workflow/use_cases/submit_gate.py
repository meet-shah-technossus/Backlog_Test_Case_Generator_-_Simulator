from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.intake.handoff_inbox_service import Agent4HandoffInboxService
from app.modules.agent4.review.review_service import Agent4ReviewService
from app.modules.agent4.workflow.state_machine import validate_state


def submit_phase3_gate(
    *,
    run_id: str,
    decision: str,
    gate_mode: str,
    reviewer_id: str,
    reason_code: str | None,
    auto_retry: bool,
    run_repo: Agent4RunRepository,
    inbox_service: Agent4HandoffInboxService,
    review_service: Agent4ReviewService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")

    if run.get("state") not in {"intake_ready", "context_assembled", "review_pending", "review_rejected"}:
        raise ValueError(
            f"Agent4 run '{run_id}' cannot be gated in state '{run.get('state')}'"
        )

    inbox_message_id = str(run.get("inbox_message_id") or "")
    inbox = inbox_service.get(inbox_message_id) if inbox_message_id else None
    if inbox is None:
        raise ValueError(f"Agent4 run '{run_id}' has no intake inbox message")

    payload = inbox.get("payload") or {}
    readiness = review_service.assess_payload_readiness(payload=payload)
    review_service.validate_gate_request(
        decision=decision,
        gate_mode=gate_mode,
        reason_code=reason_code,
        readiness=readiness,
    )

    gate_artifact = {
        "artifact_type": "phase3_gate_assessment",
        "decision": decision,
        "gate_mode": gate_mode,
        "reason_code": reason_code,
        "auto_retry": auto_retry,
        "readiness": readiness,
    }
    run_repo.add_artifact(run_id=run_id, artifact=gate_artifact)

    if decision == "approve":
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("generation_ready"),
            stage="phase-3-gate-approved",
            last_error_code=None,
            last_error_message=None,
        )
    elif decision == "retry":
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("intake_ready"),
            stage="phase-3-gate-retry-requested",
            last_error_code="A4_GATE_RETRY_REQUESTED",
            last_error_message=reason_code,
        )
        if auto_retry:
            run_repo.add_audit_event(
                run_id=run_id,
                stage="phase-3-gate",
                action="gate_auto_retry_scheduled",
                actor="system",
                metadata={"reason_code": reason_code},
            )
    else:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("review_rejected"),
            stage="phase-3-gate-rejected",
            last_error_code="A4_GATE_REJECTED",
            last_error_message=reason_code,
        )

    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-3-gate",
        action=f"gate_{decision}",
        actor=reviewer_id,
        metadata={
            "gate_mode": gate_mode,
            "reason_code": reason_code,
            "auto_retry": auto_retry,
            "ready": readiness.get("ready"),
            "missing_keys": readiness.get("missing_keys", []),
        },
    )

    return {
        "run": run_repo.get_run(run_id) or run,
        "gate_artifact": run_repo.get_latest_artifact(run_id),
    }
