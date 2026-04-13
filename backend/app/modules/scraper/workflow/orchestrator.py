from __future__ import annotations

from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.scraper.db.job_repository import ScraperJobRepository
from app.modules.scraper.fetch.fetch_service import ScraperFetchService
from app.modules.scraper.workflow.use_cases.build_context_pack import build_context_pack
from app.modules.scraper.workflow.use_cases.create_job import create_job
from app.modules.scraper.workflow.use_cases.fetch_target_preview import fetch_target_preview
from app.modules.scraper.workflow.use_cases.get_blueprint import get_scraper_blueprint
from app.modules.scraper.workflow.use_cases.get_job_snapshot import get_job_snapshot
from app.modules.scraper.workflow.use_cases.preview_frontier import preview_frontier
from app.modules.scraper.workflow.use_cases.run_job import run_job


class ScraperOrchestrator:
    def __init__(
        self,
        *,
        backlog_repo: Agent1BacklogRepository,
        job_repo: ScraperJobRepository,
        fetch_service: ScraperFetchService,
    ):
        self._backlog_repo = backlog_repo
        self._job_repo = job_repo
        self._fetch_service = fetch_service

    def get_blueprint(self) -> dict:
        return get_scraper_blueprint()

    def create_job(
        self,
        *,
        backlog_item_id: str,
        max_depth: int = 2,
        max_pages: int = 100,
        same_origin_only: bool = True,
    ) -> dict:
        return create_job(
            backlog_item_id=backlog_item_id,
            max_depth=max_depth,
            max_pages=max_pages,
            same_origin_only=same_origin_only,
            backlog_repo=self._backlog_repo,
            job_repo=self._job_repo,
        )

    def get_job_snapshot(self, job_id: str) -> dict:
        return get_job_snapshot(job_id=job_id, job_repo=self._job_repo)

    def list_jobs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> dict:
        return {
            "backlog_item_id": backlog_item_id,
            "jobs": self._job_repo.list_jobs_for_backlog_item(backlog_item_id, limit=limit),
        }

    async def fetch_target_preview(
        self,
        *,
        job_id: str,
        mode: str = "auto",
        timeout_seconds: int = 20,
    ) -> dict:
        return await fetch_target_preview(
            job_id=job_id,
            mode=mode,
            timeout_seconds=timeout_seconds,
            job_repo=self._job_repo,
            fetch_service=self._fetch_service,
        )

    async def run_job(
        self,
        *,
        job_id: str,
        mode: str = "auto",
        timeout_seconds: int = 20,
        force_restart: bool = False,
    ) -> dict:
        return await run_job(
            job_id=job_id,
            mode=mode,
            timeout_seconds=timeout_seconds,
            force_restart=force_restart,
            job_repo=self._job_repo,
            fetch_service=self._fetch_service,
        )

    def preview_frontier(
        self,
        *,
        job_id: str,
        discovered_links: list[str],
        source_url: str | None = None,
        source_depth: int = 0,
    ) -> dict:
        return preview_frontier(
            job_id=job_id,
            discovered_links=discovered_links,
            source_url=source_url,
            source_depth=source_depth,
            job_repo=self._job_repo,
        )

    def build_context_pack(self, *, job_id: str, max_pages: int = 50) -> dict:
        return build_context_pack(
            job_id=job_id,
            max_pages=max_pages,
            backlog_repo=self._backlog_repo,
            job_repo=self._job_repo,
        )
