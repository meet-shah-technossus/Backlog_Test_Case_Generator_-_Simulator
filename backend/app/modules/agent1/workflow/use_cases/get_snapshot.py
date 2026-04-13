from __future__ import annotations

from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.agent1.db.run_repository import Agent1RunRepository
from app.modules.agent1.workflow.services.review_diff_service import build_review_diff


def get_run_snapshot(*, run_id: str, backlog_repo: Agent1BacklogRepository, run_repo: Agent1RunRepository) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Run '{run_id}' not found")

    item = backlog_repo.get_item(run["backlog_item_id"])
    artifacts = run_repo.list_artifacts(run_id)

    return {
        "run": run,
        "backlog_item": item.model_dump() if item else None,
        "latest_artifact": artifacts[0] if artifacts else None,
        "review_diff": build_review_diff(artifacts),
        "reviews": run_repo.list_reviews(run_id),
        "handoffs": run_repo.list_handoffs(run_id),
        "timeline": run_repo.list_audit_events(run_id),
    }
