from __future__ import annotations

from app.modules.agent2.db.run_repository import Agent2RunRepository
from app.modules.agent2.review.review_service import Agent2ReviewService


def get_run_snapshot(*, run_id: str, run_repo: Agent2RunRepository) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent2 run '{run_id}' not found")

    review_service = Agent2ReviewService()
    artifacts = run_repo.list_artifacts(run_id)

    return {
        "run": run,
        "latest_artifact": run_repo.get_latest_artifact(run_id),
        "artifacts": artifacts,
        "reviews": run_repo.list_reviews(run_id),
        "handoffs": run_repo.list_handoffs(run_id),
        "review_diff": review_service.build_review_diff(artifacts=artifacts),
        "timeline": run_repo.get_audit_events(run_id),
    }
