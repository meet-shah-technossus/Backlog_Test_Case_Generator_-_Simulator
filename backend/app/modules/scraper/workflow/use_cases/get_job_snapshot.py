from __future__ import annotations

from app.modules.scraper.db.job_repository import ScraperJobRepository


def get_job_snapshot(*, job_id: str, job_repo: ScraperJobRepository) -> dict:
    job = job_repo.get_job(job_id)
    if job is None:
        raise ValueError(f"Scraper job '{job_id}' not found")
    return job
