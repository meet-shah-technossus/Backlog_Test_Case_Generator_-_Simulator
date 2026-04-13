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
                        "title": "Phase8",
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
    container = AppContainer()
    orchestrator = container.get_agent3_orchestrator()

    envelope = Agent3HandoffEnvelope(
        message_id=f"a3-msg-{uuid4().hex[:8]}",
        run_id=_seed_agent2_source(),
        trace_id=f"trace-{uuid4().hex[:8]}",
        from_agent="agent_2",
        to_agent="agent_3",
        stage_id="reasoning",
        task_type="reason_over_steps",
        contract_version="v1",
        retry_count=0,
        dedupe_key=f"dedupe-{uuid4().hex[:8]}",
        payload={"note": "phase8 smoke"},
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
        reviewer_id="phase8_smoke",
        reason_code=None,
        auto_retry=True,
    )
    orchestrator.generate_phase4_selectors(run_id)
    orchestrator.emit_phase5_handoff(run_id)

    feedback_message = f"a4-feedback-{uuid4().hex[:8]}"
    first = orchestrator.apply_phase6_feedback(
        run_id=run_id,
        message_id=feedback_message,
        source_agent4_run_id=f"agent4-run-{uuid4().hex[:8]}",
        outcome="passed",
        recommended_action="none",
        step_results=[
            {"step_id": "TC001-S1", "status": "passed"},
            {"step_id": "TC001-S2", "status": "passed"},
        ],
        summary={"browser": "chromium"},
        metadata={"env": "smoke"},
    )
    second = orchestrator.apply_phase6_feedback(
        run_id=run_id,
        message_id=feedback_message,
        source_agent4_run_id=f"agent4-run-{uuid4().hex[:8]}",
        outcome="passed",
        recommended_action="none",
        step_results=[
            {"step_id": "TC001-S1", "status": "passed"},
            {"step_id": "TC001-S2", "status": "passed"},
        ],
        summary={"browser": "chromium"},
        metadata={"env": "smoke"},
    )

    integrity = orchestrator.get_phase8_integrity_report(run_id)

    print("RUN_ID", run_id)
    print("FIRST_CREATED", first.get("created"))
    print("SECOND_CREATED", second.get("created"))
    print("INTEGRITY_TIMELINE_SHA", (integrity.get("integrity") or {}).get("timeline_sha256"))
    print("DUP_FEEDBACK_IDS", (integrity.get("integrity") or {}).get("duplicate_feedback_message_ids"))


if __name__ == "__main__":
    main()
