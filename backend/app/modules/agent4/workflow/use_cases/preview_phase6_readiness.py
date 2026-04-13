from __future__ import annotations

from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.review.script_review_service import Agent4ScriptReviewService


def _find_latest_phase5_script_bundle(artifacts: list[dict]) -> dict | None:
    for artifact_row in artifacts:
        artifact = artifact_row.get("artifact") if isinstance(artifact_row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_generated_script_bundle":
            return artifact_row
    return None


def preview_phase6_readiness(
    *,
    run_id: str,
    run_repo: Agent4RunRepository,
    review_service: Agent4ScriptReviewService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")

    script_row = _find_latest_phase5_script_bundle(run_repo.get_artifacts(run_id))
    if script_row is None:
        raise ValueError(f"Agent4 run '{run_id}' has no Phase 5 script bundle artifact")

    script_bundle = script_row.get("artifact") if isinstance(script_row, dict) else {}
    script_bundle = script_bundle if isinstance(script_bundle, dict) else {}

    readiness = review_service.assess_script_bundle_readiness(script_bundle=script_bundle)
    recommended_decision = "approve" if readiness.get("ready") else "retry"

    return {
        "run": run,
        "readiness": readiness,
        "recommended_decision": recommended_decision,
        "reason_code_options": review_service.reason_code_catalog(),
    }
