from __future__ import annotations

from app.domain.models import GeneratedTestSuite, TestCase
from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.agent1.db.run_repository import Agent1RunRepository


def persist_human_edited_artifact(
    *,
    run_id: str,
    backlog_item_id: str,
    reviewer_id: str,
    edited_payload: dict | None,
    backlog_repo: Agent1BacklogRepository,
    run_repo: Agent1RunRepository,
) -> int:
    if not edited_payload:
        raise ValueError("edit_approve requires edited_payload with test_cases")

    raw_cases = edited_payload.get("test_cases")
    if not isinstance(raw_cases, list):
        raise ValueError("edited_payload.test_cases must be a list")

    item = backlog_repo.get_item(backlog_item_id)
    if item is None:
        raise ValueError(f"Backlog item '{backlog_item_id}' not found")

    try:
        parsed_cases = [TestCase(**tc) for tc in raw_cases]
    except Exception as exc:
        raise ValueError(f"Invalid edited test_cases payload: {exc}") from exc

    suite = GeneratedTestSuite(
        story_id=backlog_item_id,
        story_title=item.title,
        feature_title=item.feature_title,
        epic_title=item.epic_title,
        model_used="human_edited",
        test_cases=parsed_cases,
    )

    artifact = {
        "run_id": run_id,
        "backlog_item_id": backlog_item_id,
        "story_title": suite.story_title,
        "test_cases": [tc.model_dump() for tc in suite.test_cases],
        "model_used": suite.model_used,
        "edited_by": reviewer_id,
        "review_edit": True,
    }
    version = run_repo.add_artifact(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        artifact=artifact,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="review",
        action="edited_artifact_saved",
        actor=reviewer_id,
        metadata={"artifact_version": version, "test_case_count": len(parsed_cases)},
    )
    return version
