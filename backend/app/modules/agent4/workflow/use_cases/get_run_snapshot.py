from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository


def get_run_snapshot(*, run_id: str, run_repo: Agent4RunRepository) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")
    artifacts = run_repo.get_artifacts(run_id)

    return {
        "run": run,
        "latest_artifact": artifacts[0] if artifacts else None,
        "artifacts": artifacts,
        "timeline": run_repo.get_timeline_events(run_id, ascending=False),
    }
