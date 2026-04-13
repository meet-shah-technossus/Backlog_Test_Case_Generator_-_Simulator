import asyncio

from app.core.container import AppContainer
from app.modules.agent2.contracts.models import Agent2HandoffEnvelope


async def main() -> None:
    container = AppContainer()
    scraper = container.get_scraper_orchestrator()
    agent2 = container.get_agent2_orchestrator()

    job = scraper.create_job(
        backlog_item_id="story_site_001",
        max_depth=1,
        max_pages=2,
        same_origin_only=True,
    )
    await scraper.run_job(
        job_id=job["job_id"],
        mode="http",
        timeout_seconds=15,
        force_restart=True,
    )

    context_pack = scraper.build_context_pack(job_id=job["job_id"], max_pages=2)
    message_id = f"smoke-phase6-{job['job_id']}"
    trace_id = f"scraper-{job['job_id']}"

    envelope = Agent2HandoffEnvelope(
        message_id=message_id,
        run_id=job["job_id"],
        trace_id=trace_id,
        from_agent="scraper",
        to_agent="agent_2",
        task_type="generate_steps",
        contract_version="v1",
        payload={
            "run_id": job["job_id"],
            "trace_id": trace_id,
            "task": "generate_steps",
            "source": "scraper_phase6",
            "backlog_item_id": job.get("backlog_item_id"),
            "scraper_job_id": job["job_id"],
            "scraper_context_pack": context_pack,
        },
    )

    consume = agent2.consume_handoff(envelope)
    create = agent2.create_run_from_inbox(message_id)
    run_id = (create.get("run") or {}).get("run_id")
    snapshot = agent2.get_run_snapshot(run_id) if run_id else {}

    print("SCRAPER_JOB_ID", job["job_id"])
    print("CONSUME_CREATED", consume.get("created"))
    print("CREATE_CREATED", create.get("created"))
    print("AGENT2_RUN_ID", run_id)
    print("AGENT2_STATE", (snapshot.get("run") or {}).get("state"))
    print("AGENT2_STAGE", (snapshot.get("run") or {}).get("stage"))


if __name__ == "__main__":
    asyncio.run(main())
