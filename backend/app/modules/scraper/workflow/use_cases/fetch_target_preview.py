from __future__ import annotations

from app.modules.scraper.db.job_repository import ScraperJobRepository
from app.modules.scraper.fetch.fetch_service import ScraperFetchService
from app.modules.scraper.url.policy import canonicalize_url


async def fetch_target_preview(
    *,
    job_id: str,
    mode: str,
    timeout_seconds: int,
    job_repo: ScraperJobRepository,
    fetch_service: ScraperFetchService,
) -> dict:
    job = job_repo.get_job(job_id)
    if job is None:
        raise ValueError(f"Scraper job '{job_id}' not found")

    target_url = canonicalize_url(job.get("target_url"))
    if not target_url:
        raise ValueError(f"Scraper job '{job_id}' has invalid target_url")

    fetched = await fetch_service.fetch_page(
        url=target_url,
        mode=mode,
        timeout_seconds=timeout_seconds,
    )

    return {
        "job_id": job_id,
        "requested_url": target_url,
        "fetch_mode": mode,
        "fetch_result": {
            "source": fetched.get("source"),
            "status_code": fetched.get("status_code"),
            "final_url": fetched.get("final_url"),
            "content_type": fetched.get("content_type"),
            "links_count": len(fetched.get("links") or []),
            "sample_links": (fetched.get("links") or [])[:20],
            "errors": fetched.get("errors") or [],
        },
    }
