from __future__ import annotations

from app.modules.agent3.context.context_source_service import Agent3ContextSourceService
from app.modules.agent3.context.policy import TokenSafeCrawlContextPolicy
from app.modules.agent3.db.run_repository import Agent3RunRepository
from app.modules.agent3.intake.handoff_inbox_service import Agent3HandoffInboxService
from app.modules.agent3.review.review_service import AGENT3_MAX_RETRIES, Agent3ReviewService
from app.modules.agent3.workflow.state_machine import validate_state
from app.modules.agent3.workflow.use_cases.assemble_context import assemble_context_for_run


def _derive_retry_count(
    *,
    run: dict,
    inbox_service: Agent3HandoffInboxService,
    run_repo: Agent3RunRepository,
) -> int:
    inbox = inbox_service.get(str(run.get("inbox_message_id") or "")) or {}
    payload = inbox.get("payload") if isinstance(inbox, dict) else {}
    a2a = (payload or {}).get("_a2a") if isinstance(payload, dict) else {}
    base_retry = int((a2a or {}).get("retry_count") or 0)

    events = run_repo.get_timeline_events(str(run.get("run_id") or ""), ascending=False)
    local_retries = sum(1 for ev in events if ev.get("action") == "gate_retry_requested")
    return base_retry + local_retries


def submit_gate_decision(
    *,
    run_id: str,
    decision: str,
    gate_mode: str,
    reviewer_id: str,
    reason_code: str | None,
    auto_retry: bool,
    run_repo: Agent3RunRepository,
    inbox_service: Agent3HandoffInboxService,
    review_service: Agent3ReviewService,
    context_source: Agent3ContextSourceService,
    policy: TokenSafeCrawlContextPolicy,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent3 run '{run_id}' not found")

    if run.get("state") not in {"review_pending", "review_retry_requested", "review_rejected"}:
        raise ValueError(
            f"Agent3 run '{run_id}' cannot be gated in state '{run.get('state')}'"
        )

    latest_artifact = run_repo.get_latest_artifact(run_id)
    artifact = (latest_artifact or {}).get("artifact") if isinstance(latest_artifact, dict) else None
    if not isinstance(artifact, dict):
        raise ValueError(f"Agent3 run '{run_id}' has no Phase 3 artifact to review")

    gate_requirements = artifact.get("gate_requirements") if isinstance(artifact, dict) else {}
    required_mode = str((gate_requirements or {}).get("required_mode") or "deep")

    review_service.validate_gate_request(
        decision=decision,
        gate_mode=gate_mode,
        required_mode=required_mode,
        reason_code=reason_code,
    )

    retry_count_before = _derive_retry_count(
        run=run,
        inbox_service=inbox_service,
        run_repo=run_repo,
    )

    if decision == "approve":
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("review_approved"),
            stage="phase-3-gate-approved",
            last_error_code=None,
            last_error_message=None,
        )
    elif decision == "reject":
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("review_rejected"),
            stage="phase-3-gate-rejected",
            last_error_code="A3_GATE_REJECTED",
            last_error_message=reason_code,
        )
    else:
        next_retry = retry_count_before + 1
        if next_retry > AGENT3_MAX_RETRIES:
            run_repo.update_state(
                run_id=run_id,
                state=validate_state("failed"),
                stage="phase-3-retry-limit-exceeded",
                last_error_code="AGENT3_RETRY_LIMIT_EXCEEDED",
                last_error_message=(
                    f"Retry limit exceeded ({AGENT3_MAX_RETRIES}) for Agent3 run '{run_id}'"
                ),
            )
            run_repo.add_audit_event(
                run_id=run_id,
                stage="phase-3-gate",
                action="retry_limit_exceeded",
                actor="system",
                metadata={
                    "retry_count_before": retry_count_before,
                    "retry_count_after": next_retry,
                    "max_retries": AGENT3_MAX_RETRIES,
                },
            )
            raise ValueError(
                f"Retry limit exceeded ({AGENT3_MAX_RETRIES}) for Agent3 run '{run_id}'"
            )

        run_repo.update_state(
            run_id=run_id,
            state=validate_state("review_retry_requested"),
            stage="phase-3-gate-retry-requested",
            last_error_code=None,
            last_error_message=None,
        )

    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-3-gate",
        action=f"decision_{decision}",
        actor=reviewer_id,
        metadata={
            "gate_mode": gate_mode,
            "required_mode": required_mode,
            "reason_code": reason_code,
            "retry_count_before": retry_count_before,
            "auto_retry": auto_retry,
        },
    )

    if decision == "retry":
        run_repo.create_retry_request(
            run_id=run_id,
            requested_by=reviewer_id,
            reason_code=reason_code,
            reason_text=reason_code,
        )

    if decision == "retry" and auto_retry:
        run_repo.add_audit_event(
            run_id=run_id,
            stage="phase-3-retry",
            action="gate_retry_requested",
            actor="system",
            metadata={
                "retry_count_before": retry_count_before,
                "retry_count_after": retry_count_before + 1,
            },
        )
        assemble_context_for_run(
            run_id=run_id,
            run_repo=run_repo,
            context_source=context_source,
            policy=policy,
            retry_count=retry_count_before + 1,
        )

    return {
        "run": run_repo.get_run(run_id) or run,
        "context_artifact": run_repo.get_latest_artifact(run_id),
    }
