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
                        "title": "Selector review",
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


def _start_agent3(container: AppContainer, source_run_id: str, gate_mode: str) -> str:
    orchestrator = container.get_agent3_orchestrator()
    envelope = Agent3HandoffEnvelope(
        message_id=f"a3-msg-{uuid4().hex[:8]}",
        run_id=source_run_id,
        trace_id=f"trace-{uuid4().hex[:8]}",
        from_agent="agent_2",
        to_agent="agent_3",
        stage_id="reasoning",
        task_type="reason_over_steps",
        contract_version="v1",
        retry_count=0,
        dedupe_key=f"dedupe-{uuid4().hex[:8]}",
        payload={"note": "phase5 smoke"},
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
        reviewer_id="phase5_smoke",
        reason_code=None,
        auto_retry=True,
    )
    orchestrator.generate_phase4_selectors(run_id)
    return run_id


def main() -> None:
    container = AppContainer()
    orchestrator = container.get_agent3_orchestrator()

    # Path A: quality-pass selectors -> direct Phase 5 handoff.
    run_ok = _start_agent3(
        container,
        _seed_agent2_source("Type wireless mouse in search input"),
        gate_mode="quick",
    )
    handoff_ok = orchestrator.emit_phase5_handoff(run_ok)
    print("PATH_A_RUN", run_ok)
    print("PATH_A_HANDOFF_CREATED", handoff_ok.get("created"))
    print("PATH_A_STATE", (handoff_ok.get("run") or {}).get("state"))

    # Path B: quality-blocked selectors -> edit_approve review -> handoff.
    run_blocked = _start_agent3(
        container,
        _seed_agent2_source("Open the homepage and continue"),
        gate_mode="deep",
    )

    edited_selector_steps = [
        {
            "step_id": "manual-S1",
            "selected": {"selector": "#twotabsearchtextbox", "action": "type"},
            "alternates": [{"selector": "input[type='search']", "action": "type"}],
            "confidence": {"score": 0.93, "band": "high_confidence"},
            "rationale": "Manual selector normalization from reviewer",
            "failure_reason_code": None,
            "quality": {"pass": True},
            "requires_manual_resolution": False,
        },
        {
            "step_id": "manual-S2",
            "selected": {"selector": "input[id='nav-search-submit-button']", "action": "click"},
            "alternates": [{"selector": "[aria-label*='Search']", "action": "click"}],
            "confidence": {"score": 0.9, "band": "high_confidence"},
            "rationale": "Manual submit selector",
            "failure_reason_code": None,
            "quality": {"pass": True},
            "requires_manual_resolution": False,
        },
    ]

    reviewed = orchestrator.review_phase5_selectors(
        run_id=run_blocked,
        decision="edit_approve",
        reviewer_id="phase5_smoke",
        reason_code=None,
        edited_selector_steps=edited_selector_steps,
    )
    handoff_blocked = orchestrator.emit_phase5_handoff(run_blocked)

    print("PATH_B_RUN", run_blocked)
    print("PATH_B_REVIEW_STATE", (reviewed.get("run") or {}).get("state"))
    print("PATH_B_HANDOFF_CREATED", handoff_blocked.get("created"))
    print("PATH_B_HANDOFF_STATE", (handoff_blocked.get("run") or {}).get("state"))


if __name__ == "__main__":
    main()
