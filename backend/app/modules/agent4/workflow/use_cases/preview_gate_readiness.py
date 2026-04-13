from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.intake.handoff_inbox_service import Agent4HandoffInboxService
from app.modules.agent4.review.review_service import Agent4ReviewService


def preview_phase3_gate_readiness(
    *,
    run_id: str,
    run_repo: Agent4RunRepository,
    inbox_service: Agent4HandoffInboxService,
    review_service: Agent4ReviewService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")

    inbox_message_id = str(run.get("inbox_message_id") or "")
    inbox = inbox_service.get(inbox_message_id) if inbox_message_id else None
    if inbox is None:
        raise ValueError(f"Agent4 run '{run_id}' has no intake inbox message")

    payload = inbox.get("payload") or {}
    readiness = review_service.assess_payload_readiness(payload=payload)

    recommended_decision = "approve" if readiness.get("ready") else "retry"
    missing_keys = readiness.get("missing_keys", []) or []

    return {
        "run": run,
        "readiness": readiness,
        "recommended_decision": recommended_decision,
        "missing_keys": missing_keys,
        "reason_code_options": review_service.reason_code_catalog(),
    }
