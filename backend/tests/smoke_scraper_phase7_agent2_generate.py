import asyncio

from app.core.container import AppContainer
from app.modules.agent2.contracts.models import Agent2HandoffEnvelope


async def main() -> None:
    container = AppContainer()
    scraper = container.get_scraper_orchestrator()
    agent2 = container.get_agent2_orchestrator()

    scraper_job = scraper.create_job(
        backlog_item_id="story_site_001",
        max_depth=1,
        max_pages=2,
        same_origin_only=True,
    )
    await scraper.run_job(
        job_id=scraper_job["job_id"],
        mode="http",
        timeout_seconds=15,
        force_restart=True,
    )
    context_pack = scraper.build_context_pack(job_id=scraper_job["job_id"], max_pages=2)

    message_id = f"smoke-phase7-{scraper_job['job_id']}"
    trace_id = f"scraper-{scraper_job['job_id']}"
    envelope = Agent2HandoffEnvelope(
        message_id=message_id,
        run_id=scraper_job["job_id"],
        trace_id=trace_id,
        from_agent="scraper",
        to_agent="agent_2",
        task_type="generate_steps",
        contract_version="v1",
        payload={
            "run_id": scraper_job["job_id"],
            "trace_id": trace_id,
            "task": "generate_steps",
            "source": "scraper_phase6",
            "backlog_item_id": scraper_job.get("backlog_item_id"),
            "scraper_job_id": scraper_job["job_id"],
            "scraper_context_pack": context_pack,
        },
    )

    agent2.consume_handoff(envelope)
    created = agent2.create_run_from_inbox(message_id)
    run_id = (created.get("run") or {}).get("run_id")
    if not run_id:
        raise RuntimeError("Phase7 smoke failed to create Agent2 run")

    await agent2.generate(run_id=run_id, model="gpt-4o-mini")
    snapshot = agent2.get_run_snapshot(run_id)
    latest_artifact = snapshot.get("latest_artifact") or {}
    generated = (latest_artifact.get("artifact") or {}).get("generated_steps") or {}

    print("SCRAPER_JOB_ID", scraper_job["job_id"])
    print("AGENT2_RUN_ID", run_id)
    print("AGENT2_STATE", (snapshot.get("run") or {}).get("state"))
    print("ARTIFACT_PRESENT", bool(latest_artifact))
    print("GENERATED_CASES", len(generated.get("test_cases") or []))


if __name__ == "__main__":
    asyncio.run(main())
