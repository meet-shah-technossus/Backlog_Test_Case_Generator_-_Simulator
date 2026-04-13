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
    message_id = f"scraper-{scraper_job['job_id']}-phase6-v1"
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
            "source": "scraper_phase8_complete",
            "backlog_item_id": scraper_job.get("backlog_item_id"),
            "scraper_job_id": scraper_job["job_id"],
            "scraper_context_pack": context_pack,
        },
    )

    consume = agent2.consume_handoff(envelope)
    create = agent2.create_run_from_inbox(message_id)
    run_id = (create.get("run") or {}).get("run_id")
    if not run_id:
        raise RuntimeError("Failed to create Agent2 run")

    snapshot = agent2.get_run_snapshot(run_id)
    state = (snapshot.get("run") or {}).get("state")

    generated = False
    auto_approved = False
    handoff_emitted = False

    if state in {"intake_ready", "review_retry_requested"}:
        snapshot = await agent2.generate(run_id=run_id, model="gpt-4o-mini")
        generated = True
        state = (snapshot.get("run") or {}).get("state")

    if state == "review_pending":
        snapshot = agent2.review(
            run_id=run_id,
            decision="approve",
            reviewer_id="scraper_phase8_auto",
            reason_code=None,
            edited_payload=None,
        )
        auto_approved = True
        state = (snapshot.get("run") or {}).get("state")

    if state == "handoff_pending":
        handoff = agent2.handoff(run_id)
        snapshot = handoff.get("snapshot") or {}
        handoff_emitted = bool(handoff.get("created"))

    final_state = (snapshot.get("run") or {}).get("state")

    print("SCRAPER_JOB_ID", scraper_job["job_id"])
    print("AGENT2_RUN_ID", run_id)
    print("CONSUME_CREATED", consume.get("created"))
    print("CREATE_CREATED", create.get("created"))
    print("GENERATED", generated)
    print("AUTO_APPROVED", auto_approved)
    print("HANDOFF_EMITTED", handoff_emitted)
    print("FINAL_STATE", final_state)


if __name__ == "__main__":
    asyncio.run(main())
