from __future__ import annotations

from uuid import uuid4

from app.core.container import AppContainer
from app.infrastructure.store import store
from app.modules.agent3.contracts.models import Agent3HandoffEnvelope


def _seed_agent2_source() -> str:
    run_id = f"agent2-run-{uuid4().hex[:10]}"
    msg_id = f"a2-msg-{uuid4().hex[:10]}"
    trace = f"trace-{uuid4().hex[:10]}"

    store.upsert_agent2_inbox(
        message_id=msg_id,
        source_agent1_run_id=f"agent1-{uuid4().hex[:8]}",
        trace_id=trace,
        contract_version="v1",
        task_type="generate_steps",
        payload={
            "scraper_context_pack": {
                "llm_input": {
                    "evidence_pages": [
                        {
                            "url": "https://www.amazon.com/",
                            "depth": 0,
                            "status_code": 200,
                            "title": "Amazon.com",
                            "text_excerpt": "Search Cart Add to Cart filters available",
                            "sample_links": ["https://www.amazon.com/s?k=wireless+mouse"],
                        }
                    ]
                }
            }
        },
        intake_status="accepted",
    )
    store.create_agent2_run_from_inbox(
        run_id=run_id,
        inbox_message_id=msg_id,
        source_agent1_run_id=f"agent1-{uuid4().hex[:8]}",
        trace_id=trace,
        state="review_pending",
        stage="review",
    )
    store.add_agent2_artifact(
        run_id=run_id,
        source_agent1_run_id=f"agent1-{uuid4().hex[:8]}",
        artifact_version=1,
        artifact={
            "story_id": "story_site_001",
            "generated_steps": {
                "test_cases": [
                    {
                        "id": "TC001",
                        "title": "Search works",
                        "expected_result": "results shown",
                        "steps": [
                            {"number": 1, "action": "Type wireless mouse in search input"},
                            {"number": 2, "action": "Click search button and verify results"},
                        ],
                    }
                ]
            },
        },
    )
    return run_id


def main() -> None:
    source_agent2_run_id = _seed_agent2_source()

    container = AppContainer()
    orchestrator = container.get_agent3_orchestrator()

    envelope = Agent3HandoffEnvelope(
        message_id=f"a3-msg-{uuid4().hex[:8]}",
        run_id=source_agent2_run_id,
        trace_id=f"trace-{uuid4().hex[:8]}",
        from_agent="agent_2",
        to_agent="agent_3",
        stage_id="reasoning",
        task_type="reason_over_steps",
        contract_version="v1",
        retry_count=0,
        dedupe_key=f"dedupe-{uuid4().hex[:8]}",
        payload={"note": "phase4 smoke"},
    )

    orchestrator.consume_handoff(envelope)
    created = orchestrator.create_run_from_inbox(envelope.message_id)
    run_id = (created.get("run") or {}).get("run_id")
    if not run_id:
        raise RuntimeError("Agent3 run not created")

    orchestrator.assemble_context(run_id)
    orchestrator.submit_phase3_gate(
        run_id=run_id,
        decision="approve",
        gate_mode="quick",
        reviewer_id="phase4_smoke",
        reason_code=None,
        auto_retry=True,
    )

    generated = orchestrator.generate_phase4_selectors(run_id)
    run = generated.get("run") or {}
    artifact = (generated.get("selector_artifact") or {}).get("artifact") or {}

    print("RUN_ID", run_id)
    print("RUN_STATE", run.get("state"))
    print("STAGE", run.get("stage"))
    print("SELECTOR_STEPS", artifact.get("selector_steps_count"))
    print("UNRESOLVED", artifact.get("unresolved_count"))
    print("READY_FOR_HANDOFF", artifact.get("ready_for_handoff"))


if __name__ == "__main__":
    main()
