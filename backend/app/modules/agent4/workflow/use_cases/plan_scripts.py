from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.intake.handoff_inbox_service import Agent4HandoffInboxService
from app.modules.agent4.planning.script_blueprint_service import Agent4ScriptBlueprintService
from app.modules.agent4.workflow.state_machine import validate_state


def _find_latest_phase4_blueprint_artifact(artifacts: list[dict]) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase4_script_blueprint":
            return artifact_row
    return None


def plan_phase4_scripts(
    *,
    run_id: str,
    run_repo: Agent4RunRepository,
    inbox_service: Agent4HandoffInboxService,
    planning_service: Agent4ScriptBlueprintService,
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
            f"Agent4 run '{run_id}' not eligible for Phase 4 planning from state '{run.get('state')}'"
        )

    inbox_message_id = str(run.get("inbox_message_id") or "")
    inbox = inbox_service.get(inbox_message_id) if inbox_message_id else None
    if inbox is None:
        raise ValueError(f"Agent4 run '{run_id}' has no intake inbox message")

    if str(inbox.get("task_type") or "") not in {"generate_test_scripts", "execute_selectors"}:
        raise ValueError(
            f"Agent4 run '{run_id}' has unsupported intake task_type '{inbox.get('task_type')}'"
        )

    artifacts = run_repo.get_artifacts(run_id)
    latest_phase4 = _find_latest_phase4_blueprint_artifact(artifacts)
    latest_phase4_artifact = (latest_phase4 or {}).get("artifact") if isinstance(latest_phase4, dict) else {}
    if isinstance(latest_phase4_artifact, dict):
        same_source_message = str(latest_phase4_artifact.get("source_message_id") or "") == inbox_message_id
        if same_source_message and run.get("state") in {"generation_ready", "generation_completed", "review_pending", "review_approved", "handoff_pending", "handoff_emitted"}:
            run_repo.add_audit_event(
                run_id=run_id,
                stage="phase-4-script-planning",
                action="script_blueprint_reused",
                actor="system",
                metadata={"source_message_id": inbox_message_id},
            )
            return {
                "created": False,
                "run": run_repo.get_run(run_id) or run,
                "blueprint_artifact": latest_phase4,
            }

    run_repo.update_state(
        run_id=run_id,
        state=validate_state("generation_ready"),
        stage="phase-4-script-planning",
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-4-script-planning",
        action="script_blueprint_planning_started",
        actor="system",
        metadata={"source_message_id": inbox_message_id},
    )

    payload = inbox.get("payload") or {}
    try:
        blueprint_artifact = planning_service.build_phase4_blueprint(
            run_id=run_id,
            source_agent3_run_id=str(run.get("source_agent3_run_id") or ""),
            inbox_message_id=inbox_message_id,
            payload=payload,
        )
    except Exception as exc:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("failed"),
            stage="phase-4-script-planning",
            last_error_code="A4_SCRIPT_BLUEPRINT_FAILED",
            last_error_message=str(exc),
        )
        run_repo.add_audit_event(
            run_id=run_id,
            stage="phase-4-script-planning",
            action="script_blueprint_planning_failed",
            actor="system",
            metadata={"error": str(exc)},
        )
        raise

    run_repo.add_artifact(run_id=run_id, artifact=blueprint_artifact)
    run_repo.update_state(
        run_id=run_id,
        state=validate_state("generation_ready"),
        stage="phase-4-script-blueprint-ready",
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-4-script-planning",
        action="script_blueprint_planning_completed",
        actor="system",
        metadata={
            "script_suite_count": blueprint_artifact.get("script_suite_count", 0),
            "selector_step_count": blueprint_artifact.get("selector_step_count", 0),
            "needs_human_review": blueprint_artifact.get("needs_human_review", False),
        },
    )

    return {
        "created": True,
        "run": run_repo.get_run(run_id) or run,
        "blueprint_artifact": run_repo.get_latest_artifact(run_id),
    }
