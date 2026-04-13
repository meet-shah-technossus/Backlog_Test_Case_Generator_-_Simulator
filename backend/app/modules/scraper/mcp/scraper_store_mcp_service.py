from __future__ import annotations

from app.infrastructure.store import store


class ScraperStoreMCPService:
    def create_job(
        self,
        *,
        job_id: str,
        backlog_item_id: str,
        target_url: str,
        state: str,
        stage: str,
        config: dict,
    ) -> dict:
        return store.create_scraper_job(
            job_id=job_id,
            backlog_item_id=backlog_item_id,
            target_url=target_url,
            state=state,
            stage=stage,
            config=config,
        )

    def get_job(self, job_id: str) -> dict | None:
        return store.get_scraper_job(job_id)

    def list_jobs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        return store.list_scraper_jobs_for_backlog_item(backlog_item_id, limit=limit)

    def update_job_state(
        self,
        *,
        job_id: str,
        state: str,
        stage: str,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> dict | None:
        return store.update_scraper_job_state(
            job_id=job_id,
            state=state,
            stage=stage,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
        )

    def upsert_scraper_page(
        self,
        *,
        job_id: str,
        url: str,
        depth: int,
        parent_url: str | None,
        page_title: str | None,
        text_excerpt: str | None,
        source: str | None,
        status_code: int | None,
        content_type: str | None,
        links: list[str],
        errors: list[str],
    ) -> None:
        store.upsert_scraper_page(
            job_id=job_id,
            url=url,
            depth=depth,
            parent_url=parent_url,
            page_title=page_title,
            text_excerpt=text_excerpt,
            source=source,
            status_code=status_code,
            content_type=content_type,
            links=links,
            errors=errors,
        )

    def list_scraper_pages(self, job_id: str, limit: int = 500) -> list[dict]:
        return store.list_scraper_pages(job_id, limit=limit)

    def delete_scraper_pages_for_job(self, job_id: str) -> int:
        return store.delete_scraper_pages_for_job(job_id)

    def upsert_story_runtime_context(
        self,
        *,
        story_id: str,
        target_url: str,
        context_bundle: dict | None = None,
    ) -> None:
        store.upsert_story_runtime_context(
            story_id=story_id,
            target_url=target_url,
            context_bundle=context_bundle,
        )

    def get_story_runtime_context(self, story_id: str) -> dict | None:
        return store.get_story_runtime_context(story_id)
