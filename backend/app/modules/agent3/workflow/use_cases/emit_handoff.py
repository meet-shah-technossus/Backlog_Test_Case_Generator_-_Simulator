from __future__ import annotations

from app.modules.agent3.db.run_repository import Agent3RunRepository
from app.modules.agent3.handoff.handoff_service import Agent3HandoffService
from app.modules.agent3.review.selector_review_service import Agent3SelectorReviewService
from app.modules.agent3.workflow.state_machine import validate_state


def _find_latest_selector_artifact(artifacts: list[dict]) -> dict | None:
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase4_selector_plan":
            return row
    return None


def _find_existing_handoff_artifact(artifacts: list[dict], message_id: str) -> dict | None:
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_handoff_envelope":
            envelope = artifact.get("envelope") if isinstance(artifact, dict) else {}
            if isinstance(envelope, dict) and envelope.get("message_id") == message_id:
                return row
    return None


def emit_phase5_handoff(
    *,
    run_id: str,
    run_repo: Agent3RunRepository,
    handoff_service: Agent3HandoffService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent3 run '{run_id}' not found")

    if run.get("state") not in {"handoff_pending", "handoff_emitted"}:
        raise ValueError(
            f"Agent3 run '{run_id}' not eligible for handoff from state '{run.get('state')}'"
        )

    artifacts = run_repo.get_artifacts(run_id)
    selector_row = _find_latest_selector_artifact(artifacts)
    if selector_row is None:
        raise ValueError(f"Agent3 run '{run_id}' has no selector artifact for handoff")

    selector_artifact = selector_row.get("artifact") or {}
    if not bool(selector_artifact.get("ready_for_handoff")):
        if run.get("state") == "handoff_pending":
            # Compatibility fallback for legacy approved runs where state advanced
            # but latest selector artifact was not materialized as handoff-ready.
            review_service = Agent3SelectorReviewService()
            compat_artifact = review_service.build_approved_override_artifact(
                base_artifact=selector_artifact,
                reason_code="manual_override_confirmed",
            )
            run_repo.add_artifact(run_id=run_id, artifact=compat_artifact)
            selector_row = run_repo.get_latest_artifact(run_id) or selector_row
            selector_artifact = selector_row.get("artifact") or {}
            run_repo.add_audit_event(
                run_id=run_id,
                stage="phase-5-handoff",
                action="legacy_handoff_self_heal",
                actor="system",
                metadata={"reason": "stale_selector_artifact_in_handoff_pending"},
            )

        if not bool(selector_artifact.get("ready_for_handoff")):
            raise ValueError(
                f"Agent3 run '{run_id}' selector artifact is not ready for handoff; complete Phase 5 review first"
            )

    envelope = handoff_service.build_envelope(run=run, selector_artifact_row=selector_row)
    existing = _find_existing_handoff_artifact(artifacts, envelope["message_id"])
    created = existing is None

    if created:
        run_repo.add_artifact(
            run_id=run_id,
            artifact={
                "artifact_type": "phase5_handoff_envelope",
                "envelope": envelope,
            },
        )

    run_repo.update_state(
        run_id=run_id,
        state=validate_state("handoff_emitted"),
        stage="phase-5-handoff-emitted",
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-5-handoff",
        action="a2a_emitted" if created else "a2a_emit_reused",
        actor="system",
        metadata={"message_id": envelope["message_id"]},
    )

    return {
        "created": created,
        "message_id": envelope["message_id"],
        "run": run_repo.get_run(run_id) or run,
        "handoff_artifact": run_repo.get_latest_artifact(run_id),
    }
