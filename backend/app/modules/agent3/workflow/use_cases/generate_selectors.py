from __future__ import annotations

from app.modules.agent3.db.run_repository import Agent3RunRepository
from app.modules.agent3.generation.selector_generation_service import Agent3SelectorGenerationService
from app.modules.agent3.workflow.state_machine import validate_state


def _find_latest_phase3_artifact(artifacts: list[dict]) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and isinstance(artifact.get("output_steps"), list):
            return artifact_row
    return None


def _find_latest_phase4_selector_artifact(artifacts: list[dict]) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase4_selector_plan":
            return artifact_row
    return None


def generate_selectors_for_run(
    *,
    run_id: str,
    run_repo: Agent3RunRepository,
    generation_service: Agent3SelectorGenerationService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent3 run '{run_id}' not found")

    if run.get("state") not in {"review_approved", "reasoning_generated", "handoff_pending"}:
        raise ValueError(
            f"Agent3 run '{run_id}' not eligible for Phase 4 generation from state '{run.get('state')}'"
        )

    artifacts = run_repo.get_artifacts(run_id)
    phase3_source = _find_latest_phase3_artifact(artifacts)
    if phase3_source is None:
        raise ValueError(f"Agent3 run '{run_id}' has no Phase 3 context artifact")

    latest_phase4 = _find_latest_phase4_selector_artifact(artifacts)
    latest_phase4_artifact = (latest_phase4 or {}).get("artifact") if isinstance(latest_phase4, dict) else {}
    if isinstance(latest_phase4_artifact, dict):
        same_source_version = int(latest_phase4_artifact.get("source_context_artifact_version") or -1) == int(
            phase3_source.get("artifact_version") or -2
        )
        if same_source_version and run.get("state") in {"reasoning_generated", "handoff_pending", "handoff_emitted"}:
            run_repo.add_audit_event(
                run_id=run_id,
                stage="phase-4-selector-generation",
                action="selector_generation_reused",
                actor="system",
                metadata={"source_context_artifact_version": phase3_source.get("artifact_version")},
            )
            return {
                "created": False,
                "run": run_repo.get_run(run_id) or run,
                "selector_artifact": latest_phase4,
            }

    phase3_artifact = phase3_source.get("artifact") or {}
    output_steps = phase3_artifact.get("output_steps") or []
    if not isinstance(output_steps, list) or not output_steps:
        raise ValueError(f"Agent3 run '{run_id}' has empty Phase 3 output_steps")

    run_repo.update_state(
        run_id=run_id,
        state=validate_state("reasoning_generating"),
        stage="phase-4-selector-generation",
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-4-selector-generation",
        action="selector_generation_started",
        actor="system",
        metadata={"source_context_artifact_version": phase3_source.get("artifact_version")},
    )

    try:
        selector_artifact = generation_service.build_selector_artifact(
            run_id=run_id,
            source_agent2_run_id=str(run.get("source_agent2_run_id") or ""),
            source_context_artifact_version=int(phase3_source.get("artifact_version") or 0),
            output_steps=output_steps,
        )
    except Exception as exc:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("failed"),
            stage="phase-4-selector-generation",
            last_error_code="A3_SELECTOR_GENERATION_FAILED",
            last_error_message=str(exc),
        )
        run_repo.add_audit_event(
            run_id=run_id,
            stage="phase-4-selector-generation",
            action="selector_generation_failed",
            actor="system",
            metadata={"error": str(exc)},
        )
        raise

    run_repo.add_artifact(run_id=run_id, artifact=selector_artifact)
    run_repo.update_state(
        run_id=run_id,
        state=validate_state("reasoning_generated"),
        stage="phase-4-selector-generated",
        last_error_code=None,
        last_error_message=None,
    )
    ready_for_handoff = bool(selector_artifact.get("ready_for_handoff"))
    if ready_for_handoff:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("handoff_pending"),
            stage="phase-4-handoff-pending",
            last_error_code=None,
            last_error_message=None,
        )
    else:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("review_pending"),
            stage="phase-4-quality-review-required",
            last_error_code="A3_SELECTOR_QUALITY_REVIEW_REQUIRED",
            last_error_message=(
                "Selector quality checks failed (stability/ambiguity thresholds); manual review required"
            ),
        )
        run_repo.add_audit_event(
            run_id=run_id,
            stage="phase-4-selector-generation",
            action="selector_quality_blocked",
            actor="system",
            metadata={
                "quality_blocked_count": selector_artifact.get("quality_blocked_count", 0),
                "unresolved_count": selector_artifact.get("unresolved_count", 0),
            },
        )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-4-selector-generation",
        action="selector_generation_completed",
        actor="system",
        metadata={
            "selector_steps_count": selector_artifact.get("selector_steps_count", 0),
            "unresolved_count": selector_artifact.get("unresolved_count", 0),
            "ready_for_handoff": selector_artifact.get("ready_for_handoff", False),
            "quality_blocked_count": selector_artifact.get("quality_blocked_count", 0),
        },
    )

    return {
        "created": True,
        "run": run_repo.get_run(run_id) or run,
        "selector_artifact": run_repo.get_latest_artifact(run_id),
    }
