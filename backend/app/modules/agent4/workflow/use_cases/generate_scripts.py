from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.generation.script_generation_service import Agent4ScriptGenerationService
from app.modules.agent4.intake.handoff_inbox_service import Agent4HandoffInboxService
from app.modules.agent4.workflow.state_machine import validate_state


def _find_latest_phase4_blueprint_artifact(artifacts: list[dict]) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase4_script_blueprint":
            return artifact_row
    return None


def _find_latest_phase5_script_bundle(artifacts: list[dict]) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_generated_script_bundle":
            return artifact_row
    return None


def generate_phase5_scripts(
    *,
    run_id: str,
    run_repo: Agent4RunRepository,
    inbox_service: Agent4HandoffInboxService,
    generation_service: Agent4ScriptGenerationService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")

    if run.get("state") not in {
        "generation_ready",
        "generation_completed",
        "review_pending",
        "review_approved",
        "handoff_pending",
        "handoff_emitted",
    }:
        raise ValueError(
            f"Agent4 run '{run_id}' not eligible for Phase 5 generation from state '{run.get('state')}'"
        )

    inbox_message_id = str(run.get("inbox_message_id") or "")
    inbox = inbox_service.get(inbox_message_id) if inbox_message_id else None
    if inbox is None:
        raise ValueError(f"Agent4 run '{run_id}' has no intake inbox message")

    artifacts = run_repo.get_artifacts(run_id)
    phase4_blueprint = _find_latest_phase4_blueprint_artifact(artifacts)
    if phase4_blueprint is None:
        raise ValueError(f"Agent4 run '{run_id}' has no Phase 4 blueprint artifact")

    latest_phase5 = _find_latest_phase5_script_bundle(artifacts)
    latest_phase5_artifact = (latest_phase5 or {}).get("artifact") if isinstance(latest_phase5, dict) else {}
    if isinstance(latest_phase5_artifact, dict):
        same_blueprint_version = int(
            latest_phase5_artifact.get("source_blueprint_artifact_version") or -1
        ) == int(phase4_blueprint.get("artifact_version") or -2)
        if same_blueprint_version and run.get("state") in {
            "generation_completed",
            "review_pending",
            "review_approved",
            "handoff_pending",
            "handoff_emitted",
        }:
            run_repo.add_audit_event(
                run_id=run_id,
                stage="phase-5-script-generation",
                action="script_generation_reused",
                actor="system",
                metadata={
                    "source_blueprint_artifact_version": phase4_blueprint.get("artifact_version"),
                },
            )
            return {
                "created": False,
                "run": run_repo.get_run(run_id) or run,
                "script_bundle_artifact": latest_phase5,
            }

    run_repo.update_state(
        run_id=run_id,
        state=validate_state("generation_ready"),
        stage="phase-5-script-generation",
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-5-script-generation",
        action="script_generation_started",
        actor="system",
        metadata={
            "source_blueprint_artifact_version": phase4_blueprint.get("artifact_version"),
            "source_message_id": inbox_message_id,
        },
    )

    payload = inbox.get("payload") or {}
    try:
        script_bundle = generation_service.build_phase5_script_bundle(
            run_id=run_id,
            source_agent3_run_id=str(run.get("source_agent3_run_id") or ""),
            source_message_id=inbox_message_id,
            source_blueprint_artifact_version=int(phase4_blueprint.get("artifact_version") or 0),
            payload=payload,
            blueprint_artifact=phase4_blueprint,
        )
    except Exception as exc:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("failed"),
            stage="phase-5-script-generation",
            last_error_code="A4_SCRIPT_GENERATION_FAILED",
            last_error_message=str(exc),
        )
        run_repo.add_audit_event(
            run_id=run_id,
            stage="phase-5-script-generation",
            action="script_generation_failed",
            actor="system",
            metadata={"error": str(exc)},
        )
        raise

    run_repo.add_artifact(run_id=run_id, artifact=script_bundle)
    run_repo.update_state(
        run_id=run_id,
        state=validate_state("generation_completed"),
        stage="phase-5-script-generated",
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-5-script-generation",
        action="script_generation_completed",
        actor="system",
        metadata={
            "script_count": script_bundle.get("script_count", 0),
            "framework": script_bundle.get("framework"),
            "language": script_bundle.get("language"),
        },
    )

    return {
        "created": True,
        "run": run_repo.get_run(run_id) or run,
        "script_bundle_artifact": run_repo.get_latest_artifact(run_id),
    }
