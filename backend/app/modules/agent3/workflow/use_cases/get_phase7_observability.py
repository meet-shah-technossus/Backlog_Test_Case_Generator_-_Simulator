from __future__ import annotations

from app.modules.agent3.db.run_repository import Agent3RunRepository


def _artifact_type_counts(artifacts: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        artifact_type = "unknown"
        if isinstance(artifact, dict):
            artifact_type = str(artifact.get("artifact_type") or "phase3_context")
        counts[artifact_type] = counts.get(artifact_type, 0) + 1
    return counts


def _feedback_outcome_counts(artifacts: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if not isinstance(artifact, dict):
            continue
        if artifact.get("artifact_type") != "phase6_execution_feedback":
            continue
        outcome = str(artifact.get("outcome") or "unknown")
        counts[outcome] = counts.get(outcome, 0) + 1
    return counts


def get_phase7_observability(*, run_id: str, run_repo: Agent3RunRepository) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent3 run '{run_id}' not found")

    artifacts = run_repo.get_artifacts(run_id)
    timeline = run_repo.get_timeline_events(run_id, ascending=False)

    action_counts: dict[str, int] = {}
    stage_counts: dict[str, int] = {}
    quality_blocked_total = 0

    for event in timeline:
        action = str(event.get("action") or "unknown")
        stage = str(event.get("stage") or "unknown")
        action_counts[action] = action_counts.get(action, 0) + 1
        stage_counts[stage] = stage_counts.get(stage, 0) + 1

    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase4_selector_plan":
            quality_blocked_total += int(artifact.get("quality_blocked_count") or 0)

    return {
        "run": run,
        "counters": {
            "artifacts_total": len(artifacts),
            "audit_events_total": len(timeline),
            "artifact_type_counts": _artifact_type_counts(artifacts),
            "audit_action_counts": action_counts,
            "audit_stage_counts": stage_counts,
            "selector_quality_blocked_total": quality_blocked_total,
            "feedback_outcome_counts": _feedback_outcome_counts(artifacts),
        },
    }
