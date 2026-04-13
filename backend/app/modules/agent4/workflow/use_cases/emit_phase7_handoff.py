from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.handoff.handoff_service import Agent4HandoffService
from app.modules.agent4.workflow.state_machine import validate_state


def _find_latest_phase5_script_bundle(artifacts: list[dict]) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_generated_script_bundle":
            return artifact_row
    return None


def _find_existing_handoff_artifact(artifacts: list[dict], message_id: str) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase7_handoff_envelope":
            envelope = artifact.get("envelope") if isinstance(artifact, dict) else {}
            if isinstance(envelope, dict) and envelope.get("message_id") == message_id:
                return artifact_row
    return None


def emit_phase7_handoff(
    *,
    run_id: str,
    run_repo: Agent4RunRepository,
    handoff_service: Agent4HandoffService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")

    if run.get("state") not in {"handoff_pending", "handoff_emitted"}:
        raise ValueError(
            f"Agent4 run '{run_id}' not eligible for handoff from state '{run.get('state')}'"
        )

    artifacts = run_repo.get_artifacts(run_id)
    script_bundle_row = _find_latest_phase5_script_bundle(artifacts)
    if script_bundle_row is None:
        raise ValueError(f"Agent4 run '{run_id}' has no Phase 5 script bundle artifact")

    script_bundle = script_bundle_row.get("artifact") if isinstance(script_bundle_row, dict) else {}
    script_bundle = script_bundle if isinstance(script_bundle, dict) else {}
    if int(script_bundle.get("script_count") or 0) <= 0:
        raise ValueError(
            f"Agent4 run '{run_id}' cannot emit handoff with empty script bundle; complete Phase 5 generation first"
        )

    envelope = handoff_service.build_envelope(
        run=run,
        script_bundle_row=script_bundle_row,
    )

    existing = _find_existing_handoff_artifact(artifacts, envelope["message_id"])
    created = existing is None

    if created:
        run_repo.add_artifact(
            run_id=run_id,
            artifact={
                "artifact_type": "phase7_handoff_envelope",
                "envelope": envelope,
            },
        )

    run_repo.update_state(
        run_id=run_id,
        state=validate_state("handoff_emitted"),
        stage="phase-7-handoff-emitted",
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-7-handoff",
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
