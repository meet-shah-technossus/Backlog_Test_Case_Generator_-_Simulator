import asyncio

from app.core.container import AppContainer


async def main() -> None:
    container = AppContainer()
    orchestrator = container.get_scraper_orchestrator()
    job = orchestrator.create_job(
        backlog_item_id="story_site_001",
        max_depth=1,
        max_pages=2,
        same_origin_only=True,
    )
    await orchestrator.run_job(
        job_id=job["job_id"],
        mode="http",
        timeout_seconds=15,
        force_restart=True,
    )

    pack = orchestrator.build_context_pack(job_id=job["job_id"], max_pages=2)
    pages = pack["crawl"]["pages"]
    first = pages[0] if pages else {}

    print("JOB_ID", job["job_id"])
    print("PAGES_INCLUDED", pack["crawl"]["pages_included"])
    print("FIRST_HAS_TITLE", bool(first.get("title")))
    print("FIRST_EXCERPT_LEN", len(first.get("text_excerpt") or ""))
    print("PROMPT_CONTAINS_TITLE", "title:" in pack["llm_input"]["prompt_text"])
    print("PROMPT_CONTAINS_EXCERPT", "excerpt:" in pack["llm_input"]["prompt_text"])


if __name__ == "__main__":
    asyncio.run(main())
