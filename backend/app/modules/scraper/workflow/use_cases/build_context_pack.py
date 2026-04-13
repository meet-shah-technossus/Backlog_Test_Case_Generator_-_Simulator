from __future__ import annotations

from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.scraper.db.job_repository import ScraperJobRepository


def build_context_pack(
    *,
    job_id: str,
    max_pages: int,
    backlog_repo: Agent1BacklogRepository,
    job_repo: ScraperJobRepository,
) -> dict:
    job = job_repo.get_job(job_id)
    if job is None:
        raise ValueError(f"Scraper job '{job_id}' not found")

    backlog_item_id = job.get("backlog_item_id") or ""
    story = backlog_repo.get_item(backlog_item_id)
    if story is None:
        raise ValueError(f"Backlog item '{backlog_item_id}' not found")

    pages = job_repo.list_scraper_pages(job_id, limit=max(max_pages, 1))
    compact_pages = [
        {
            "url": p.get("url"),
            "depth": p.get("depth"),
            "parent_url": p.get("parent_url"),
            "title": p.get("page_title") or "",
            "text_excerpt": p.get("text_excerpt") or "",
            "status_code": p.get("status_code"),
            "content_type": p.get("content_type"),
            "source": p.get("source"),
            "links_count": len(p.get("links") or []),
            "error_count": len(p.get("errors") or []),
            "sample_links": (p.get("links") or [])[:5],
        }
        for p in pages
    ]

    prompt_lines = [
        f"Story ID: {story.backlog_item_id}",
        f"Story Title: {story.title}",
        f"Target URL: {job.get('target_url')}",
        "Acceptance Criteria:",
    ]
    prompt_lines.extend([f"- {ac}" for ac in story.acceptance_criteria])
    prompt_lines.append("Observed Pages:")
    for page in compact_pages:
        title = page["title"] or "(no-title)"
        excerpt = page["text_excerpt"] or "(no-text-excerpt)"
        prompt_lines.append(
            f"- depth={page['depth']} status={page['status_code']} source={page['source']} url={page['url']} links={page['links_count']} errors={page['error_count']}"
        )
        prompt_lines.append(f"  title: {title}")
        prompt_lines.append(f"  excerpt: {excerpt}")

    return {
        "job_id": job_id,
        "phase": "phase-5-context-pack",
        "story": {
            "backlog_item_id": story.backlog_item_id,
            "title": story.title,
            "description": story.description,
            "acceptance_criteria": story.acceptance_criteria,
            "target_url": job.get("target_url"),
        },
        "crawl": {
            "job_state": job.get("state"),
            "job_stage": job.get("stage"),
            "max_pages_requested": max_pages,
            "pages_included": len(compact_pages),
            "pages": compact_pages,
        },
        "llm_input": {
            "prompt_text": "\n".join(prompt_lines),
            "evidence_pages": compact_pages,
        },
    }
