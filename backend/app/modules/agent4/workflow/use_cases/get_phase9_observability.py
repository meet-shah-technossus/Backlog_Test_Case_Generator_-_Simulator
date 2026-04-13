from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository


def _artifact_type_counts(artifacts: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        artifact_type = "unknown"
        if isinstance(artifact, dict):
            artifact_type = str(artifact.get("artifact_type") or "unknown")
        counts[artifact_type] = counts.get(artifact_type, 0) + 1
    return counts


def _feedback_outcome_counts(artifacts: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if not isinstance(artifact, dict):
            continue
        if artifact.get("artifact_type") != "phase8_execution_feedback":
            continue
        outcome = str(artifact.get("outcome") or "unknown")
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


def get_phase9_observability(*, run_id: str, run_repo: Agent4RunRepository) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")

    artifacts = run_repo.get_artifacts(run_id)
    timeline = run_repo.get_timeline_events(run_id, ascending=False)

    action_counts: dict[str, int] = {}
    stage_counts: dict[str, int] = {}
    generated_script_total = 0

    for event in timeline:
        action = str(event.get("action") or "unknown")
        stage = str(event.get("stage") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_generated_script_bundle":
            generated_script_total += int(artifact.get("script_count") or 0)

    return {
        "run": run,
        "counters": {
            "artifacts_total": len(artifacts),
            "audit_events_total": len(timeline),
            "artifact_type_counts": _artifact_type_counts(artifacts),
            "audit_action_counts": action_counts,
            "audit_stage_counts": stage_counts,
            "generated_script_total": generated_script_total,
            "feedback_outcome_counts": _feedback_outcome_counts(artifacts),
        },
    }
