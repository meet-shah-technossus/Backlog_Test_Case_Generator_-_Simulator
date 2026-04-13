from __future__ import annotations

from app.modules.scraper.db.job_repository import ScraperJobRepository
from app.modules.scraper.url.policy import canonicalize_url, scope_reason


def preview_frontier(
    *,
    job_id: str,
    discovered_links: list[str],
    source_url: str | None,
    source_depth: int,
    job_repo: ScraperJobRepository,
) -> dict:
    job = job_repo.get_job(job_id)
    if job is None:
        raise ValueError(f"Scraper job '{job_id}' not found")

    config = job.get("config") or {}
    max_depth = int(config.get("max_depth") or 0)
    max_pages = int(config.get("max_pages") or 0)
    same_origin_only = bool(config.get("same_origin_only", True))

    root_url = canonicalize_url(job.get("target_url"))
    if not root_url:
        raise ValueError(f"Scraper job '{job_id}' has invalid target_url")

    normalized_source = canonicalize_url(source_url) if source_url else root_url
    if not normalized_source:
        normalized_source = root_url

    next_depth = source_depth + 1
    accepted: list[dict] = []
    rejected: list[dict] = []
    seen: set[str] = set()

    for raw_link in discovered_links:
        candidate = canonicalize_url(raw_link)
        if not candidate:
            rejected.append({"url": raw_link, "reason": "invalid_url"})
            continue

        if candidate in seen:
            rejected.append({"url": candidate, "reason": "duplicate"})
            continue
        seen.add(candidate)

        scope_error = scope_reason(
            root_url=root_url,
            candidate_url=candidate,
            same_origin_only=same_origin_only,
        )
        if scope_error:
            rejected.append({"url": candidate, "reason": scope_error})
            continue

        if next_depth > max_depth:
            rejected.append({"url": candidate, "reason": "max_depth_exceeded"})
            continue

        if len(accepted) >= max_pages:
            rejected.append({"url": candidate, "reason": "max_pages_exceeded"})
            continue

        accepted.append(
            {
                "url": candidate,
                "depth": next_depth,
                "parent_url": normalized_source,
            }
        )

    return {
        "job_id": job_id,
        "target_url": root_url,
        "source_url": normalized_source,
        "source_depth": source_depth,
        "accepted": accepted,
        "rejected": rejected,
        "summary": {
            "accepted_count": len(accepted),
            "rejected_count": len(rejected),
            "same_origin_only": same_origin_only,
            "max_depth": max_depth,
            "max_pages": max_pages,
        },
    }
