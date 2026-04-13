from __future__ import annotations

from collections import deque

from app.modules.scraper.db.job_repository import ScraperJobRepository
from app.modules.scraper.fetch.fetch_service import ScraperFetchService
from app.modules.scraper.url.policy import canonicalize_url, scope_reason
from app.modules.scraper.workflow.state_machine import validate_state


async def run_job(
    *,
    job_id: str,
    mode: str,
    timeout_seconds: int,
    force_restart: bool,
    job_repo: ScraperJobRepository,
    fetch_service: ScraperFetchService,
) -> dict:
    job = job_repo.get_job(job_id)
    if job is None:
        raise ValueError(f"Scraper job '{job_id}' not found")

    root_url = canonicalize_url(job.get("target_url"))
    if not root_url:
        raise ValueError(f"Scraper job '{job_id}' has invalid target_url")

    config = job.get("config") or {}
    max_depth = int(config.get("max_depth") or 0)
    max_pages = int(config.get("max_pages") or 0)
    same_origin_only = bool(config.get("same_origin_only", True))

    job_repo.update_job_state(
        job_id=job_id,
        state=validate_state("running"),
        stage="phase-4-run-loop",
        last_error_code=None,
        last_error_message=None,
    )

    cleared_count = 0
    if force_restart:
        cleared_count = job_repo.delete_scraper_pages_for_job(job_id)

    existing_pages = job_repo.list_scraper_pages(job_id, limit=max(max_pages, 500))
    seen: set[str] = set()
    queue: deque[dict] = deque()
    queued: set[str] = set()

    for page in existing_pages:
        page_url = canonicalize_url(page.get("url"))
        if page_url:
            seen.add(page_url)

    def _try_enqueue(candidate_url: str, depth: int, parent_url: str | None) -> bool:
        if candidate_url in seen or candidate_url in queued:
            return False
        if depth > max_depth:
            return False
        if len(seen) + len(queue) >= max_pages:
            return False
        if scope_reason(root_url=root_url, candidate_url=candidate_url, same_origin_only=same_origin_only):
            return False
        queue.append(
            {
                "url": candidate_url,
                "depth": depth,
                "parent_url": parent_url,
            }
        )
        queued.add(candidate_url)
        return True

    resume_enqueued = 0
    for page in existing_pages:
        parent_url = canonicalize_url(page.get("url"))
        if not parent_url:
            continue
        parent_depth = int(page.get("depth") or 0)
        child_depth = parent_depth + 1
        if child_depth > max_depth:
            continue
        for raw_link in page.get("links") or []:
            candidate = canonicalize_url(raw_link)
            if not candidate:
                continue
            if _try_enqueue(candidate, child_depth, parent_url):
                resume_enqueued += 1

    if not existing_pages:
        _try_enqueue(root_url, 0, None)
    elif root_url not in seen:
        _try_enqueue(root_url, 0, None)

    start_seen_count = len(seen)
    rejected_total: int = 0
    fetch_errors: list[str] = []

    while queue and len(seen) < max_pages:
        current = queue.popleft()
        current_url = current["url"]
        current_depth = int(current["depth"])
        current_parent = current.get("parent_url")

        if current_url in seen:
            continue
        seen.add(current_url)
        queued.discard(current_url)

        try:
            fetched = await fetch_service.fetch_page(
                url=current_url,
                mode=mode,
                timeout_seconds=timeout_seconds,
            )
            page_links = fetched.get("links") or []
            page_errors = fetched.get("errors") or []
            fetch_errors.extend(page_errors)

            job_repo.upsert_scraper_page(
                job_id=job_id,
                url=current_url,
                depth=current_depth,
                parent_url=current_parent,
                page_title=fetched.get("title") or "",
                text_excerpt=fetched.get("text_excerpt") or "",
                source=fetched.get("source"),
                status_code=int(fetched.get("status_code") or 0),
                content_type=fetched.get("content_type") or "",
                links=page_links,
                errors=page_errors,
            )

            if current_depth >= max_depth:
                continue

            for raw_link in page_links:
                candidate = canonicalize_url(raw_link)
                if not candidate:
                    rejected_total += 1
                    continue
                if not _try_enqueue(candidate, current_depth + 1, current_url):
                    rejected_total += 1
        except Exception as exc:
            fetch_errors.append(f"{current_url}: {exc}")
            job_repo.upsert_scraper_page(
                job_id=job_id,
                url=current_url,
                depth=current_depth,
                parent_url=current_parent,
                page_title="",
                text_excerpt="",
                source=mode,
                status_code=0,
                content_type="",
                links=[],
                errors=[str(exc)],
            )

    final_state = validate_state("partial_success" if fetch_errors else "success")
    final_job = job_repo.update_job_state(
        job_id=job_id,
        state=final_state,
        stage="phase-4-complete",
        last_error_code="crawl_partial" if fetch_errors else None,
        last_error_message=(fetch_errors[-1] if fetch_errors else None),
    )

    pages_after = job_repo.list_scraper_pages(job_id, limit=max(max_pages, 500))

    summary = {
        "job_id": job_id,
        "target_url": root_url,
        "mode": mode,
        "force_restart": force_restart,
        "cleared_count": cleared_count,
        "max_depth": max_depth,
        "max_pages": max_pages,
        "same_origin_only": same_origin_only,
        "resumed": bool(existing_pages),
        "existing_count_before": start_seen_count,
        "resume_queue_seeded": resume_enqueued,
        "newly_fetched_count": max(0, len(pages_after) - start_seen_count),
        "visited_count": len(pages_after),
        "rejected_count": rejected_total,
        "error_count": len(fetch_errors),
    }

    job_repo.upsert_story_runtime_context(
        story_id=job.get("backlog_item_id") or "",
        target_url=root_url,
        context_bundle={
            "target_url": root_url,
            "scraper_phase4": summary,
        },
    )

    return {
        "job": final_job,
        "summary": summary,
        "pages": pages_after,
    }
