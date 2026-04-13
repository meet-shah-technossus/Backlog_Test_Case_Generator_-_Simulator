from __future__ import annotations

from uuid import uuid4

from app.core.container import AppContainer
from app.infrastructure.store import store
from app.modules.agent3.contracts.models import Agent3HandoffEnvelope


def _seed_agent2_source(step_action: str) -> str:
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
                        "title": "Selector quality",
                        "expected_result": "results shown",
                        "steps": [
                            {"number": 1, "action": step_action},
                            {"number": 2, "action": "Click search button and verify results"},
                        ],
                    }
                ]
            },
        },
    )
    return run_id


def _run_to_phase4(step_action: str, gate_mode: str) -> tuple[dict, dict]:
    container = AppContainer()
    orchestrator = container.get_agent3_orchestrator()

    envelope = Agent3HandoffEnvelope(
        message_id=f"a3-msg-{uuid4().hex[:8]}",
        run_id=_seed_agent2_source(step_action),
        trace_id=f"trace-{uuid4().hex[:8]}",
        from_agent="agent_2",
        to_agent="agent_3",
        stage_id="reasoning",
        task_type="reason_over_steps",
        contract_version="v1",
        retry_count=0,
        dedupe_key=f"dedupe-{uuid4().hex[:8]}",
        payload={"note": "phase4 quality smoke"},
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
        gate_mode=gate_mode,
        reviewer_id="phase4_quality_smoke",
        reason_code=None,
        auto_retry=True,
    )

    generated = orchestrator.generate_phase4_selectors(run_id)
    run = generated.get("run") or {}
    artifact = (generated.get("selector_artifact") or {}).get("artifact") or {}
    return run, artifact


def main() -> None:
    run_ok, artifact_ok = _run_to_phase4(
        step_action="Type wireless mouse in search input",
        gate_mode="quick",
    )
    print("PASS_STATE", run_ok.get("state"))
    print("PASS_READY", artifact_ok.get("ready_for_handoff"))
    print("PASS_QUALITY_BLOCKED", artifact_ok.get("quality_blocked_count"))

    run_blocked, artifact_blocked = _run_to_phase4(
        step_action="Open the homepage and continue",
        gate_mode="deep",
    )
    print("BLOCKED_STATE", run_blocked.get("state"))
    print("BLOCKED_STAGE", run_blocked.get("stage"))
    print("BLOCKED_ERROR", run_blocked.get("last_error_code"))
    print("BLOCKED_READY", artifact_blocked.get("ready_for_handoff"))
    print("BLOCKED_QUALITY_BLOCKED", artifact_blocked.get("quality_blocked_count"))


if __name__ == "__main__":
    main()
