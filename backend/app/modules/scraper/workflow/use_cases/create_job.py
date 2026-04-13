from __future__ import annotations

from uuid import uuid4

from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.scraper.db.job_repository import ScraperJobRepository
from app.modules.scraper.url.target_url_resolver import resolve_target_url
from app.modules.scraper.workflow.state_machine import validate_state


def create_job(
    *,
    backlog_item_id: str,
    max_depth: int,
    max_pages: int,
    same_origin_only: bool,
    backlog_repo: Agent1BacklogRepository,
    job_repo: ScraperJobRepository,
) -> dict:
    backlog_item = backlog_repo.get_item(backlog_item_id)
    if backlog_item is None:
        raise ValueError(f"Backlog item '{backlog_item_id}' not found")

    runtime_context = job_repo.get_story_runtime_context(backlog_item_id)
    target_url = resolve_target_url(
        backlog_item=backlog_item,
        runtime_context=runtime_context,
    )

    config = {
        "max_depth": max_depth,
        "max_pages": max_pages,
        "same_origin_only": same_origin_only,
    }
    job_id = str(uuid4())
    job = job_repo.create_job(
        job_id=job_id,
        backlog_item_id=backlog_item_id,
        target_url=target_url,
        state=validate_state("created"),
        stage="phase-0-contract",
        config=config,
    )

    job_repo.upsert_story_runtime_context(
        story_id=backlog_item_id,
        target_url=target_url,
        context_bundle={
            "target_url": target_url,
            "source": "scraper_phase0_auto_resolve",
        },
    )
    return job
