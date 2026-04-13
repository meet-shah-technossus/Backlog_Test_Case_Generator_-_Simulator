from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.infrastructure.openai_client import OpenAIClient
from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.agent1.db.run_repository import Agent1RunRepository
from app.modules.agent1.workflow.services.case_generation_service import generate_suite_from_backlog_item
from app.modules.agent1.workflow.state_machine import validate_state


async def generate_run(
    *,
    run_id: str,
    backlog_repo: Agent1BacklogRepository,
    run_repo: Agent1RunRepository,
    openai_client: OpenAIClient,
    model: str | None = None,
    on_token: Callable[[str], Awaitable[None] | None] | None = None,
) -> None:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Run '{run_id}' not found")

    backlog_item_id = run["backlog_item_id"]
    trace_id = run["trace_id"]
    source_type = run.get("source_type")
    source_ref = run.get("source_ref")

    run_repo.update_state(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        trace_id=trace_id,
        state=validate_state("agent1_generating"),
        source_type=source_type,
        source_ref=source_ref,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="agent1",
        action="generation_started",
        actor="system",
        metadata={"model": model},
    )

    try:
        suite = await generate_suite_from_backlog_item(
            backlog_item_id=backlog_item_id,
            backlog_repo=backlog_repo,
            openai_client=openai_client,
            model=model,
            on_token=on_token,
        )
    except Exception as exc:
        run_repo.update_state(
            run_id=run_id,
            backlog_item_id=backlog_item_id,
            trace_id=trace_id,
            state=validate_state("failed"),
            source_type=source_type,
            source_ref=source_ref,
            last_error_code="GENERATION_FAILED",
            last_error_message=str(exc),
        )
        run_repo.add_audit_event(
            run_id=run_id,
            stage="agent1",
            action="generation_failed",
            actor="system",
            metadata={"reason": str(exc)},
        )
        raise

    artifact = {
        "run_id": run_id,
        "backlog_item_id": backlog_item_id,
        "story_title": suite.story_title,
        "test_cases": [tc.model_dump() for tc in suite.test_cases],
        "model_used": suite.model_used,
    }
    version = run_repo.add_artifact(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        artifact=artifact,
    )

    run_repo.update_state(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        trace_id=trace_id,
        state=validate_state("review_pending"),
        source_type=source_type,
        source_ref=source_ref,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="agent1",
        action="generation_completed",
        actor="system",
        metadata={"artifact_version": version, "test_case_count": len(suite.test_cases)},
    )
