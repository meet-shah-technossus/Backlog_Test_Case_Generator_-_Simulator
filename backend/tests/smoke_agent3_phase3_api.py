from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.infrastructure.store import store
from app.main import app


def _seed_agent2_source(*, run_id: str, message_id: str, trace_id: str, step_action: str) -> None:
    store.upsert_agent2_inbox(
        message_id=message_id,
        source_agent1_run_id=f"agent1-{uuid4().hex[:8]}",
        trace_id=trace_id,
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
        inbox_message_id=message_id,
        source_agent1_run_id=f"agent1-{uuid4().hex[:8]}",
        trace_id=trace_id,
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
                        "title": "Step mapping",
                        "expected_result": "action completed",
                        "steps": [
                            {"number": 1, "action": step_action},
                            {"number": 2, "action": "Click search button and verify results"},
                        ],
                    }
                ]
            },
        },
    )


def _consume_create_assemble(client: TestClient, *, source_run_id: str, suffix: str) -> str:
    message_id = f"a3-msg-{suffix}"
    consume = client.post(
        "/agent3/inbox/consume",
        json={
            "message_id": message_id,
            "run_id": source_run_id,
            "trace_id": f"trace-{suffix}",
            "from_agent": "agent_2",
            "to_agent": "agent_3",
            "stage_id": "reasoning",
            "task_type": "reason_over_steps",
            "contract_version": "v1",
            "retry_count": 0,
            "dedupe_key": f"dedupe-{suffix}",
            "payload": {"note": "phase3 api smoke"},
        },
    )
    assert consume.status_code == 200, consume.text

    create = client.post(f"/agent3/inbox/{message_id}/runs")
    assert create.status_code == 200, create.text
    run_id = create.json()["run"]["run_id"]

    assembled = client.post(f"/agent3/runs/{run_id}/phase3/assemble-context")
    assert assembled.status_code == 200, assembled.text
    return run_id


def main() -> None:
    client = TestClient(app)

    # Flow A: high confidence path accepts quick gate and approves.
    source_run_a = f"agent2-run-{uuid4().hex[:10]}"
    source_msg_a = f"a2-msg-{uuid4().hex[:10]}"
    trace_a = f"trace-{uuid4().hex[:10]}"
    _seed_agent2_source(
        run_id=source_run_a,
        message_id=source_msg_a,
        trace_id=trace_a,
        step_action="Type wireless mouse in search input",
    )

    run_a = _consume_create_assemble(client, source_run_id=source_run_a, suffix=uuid4().hex[:8])
    approve_a = client.post(
        f"/agent3/runs/{run_a}/phase3/gate",
        json={
            "decision": "approve",
            "gate_mode": "quick",
            "reviewer_id": "phase3_api_smoke",
            "reason_code": None,
            "auto_retry": True,
        },
    )
    assert approve_a.status_code == 200, approve_a.text
    state_a = approve_a.json()["run"]["state"]

    # Flow B: non-high confidence requires deep mode; retry auto-orchestrates and increments retry order.
    source_run_b = f"agent2-run-{uuid4().hex[:10]}"
    source_msg_b = f"a2-msg-{uuid4().hex[:10]}"
    trace_b = f"trace-{uuid4().hex[:10]}"
    _seed_agent2_source(
        run_id=source_run_b,
        message_id=source_msg_b,
        trace_id=trace_b,
        step_action="Open the homepage and continue",
    )

    run_b = _consume_create_assemble(client, source_run_id=source_run_b, suffix=uuid4().hex[:8])

    quick_rejected = client.post(
        f"/agent3/runs/{run_b}/phase3/gate",
        json={
            "decision": "retry",
            "gate_mode": "quick",
            "reviewer_id": "phase3_api_smoke",
            "reason_code": "confidence_too_low",
            "auto_retry": True,
        },
    )
    assert quick_rejected.status_code == 400, quick_rejected.text

    deep_retry = client.post(
        f"/agent3/runs/{run_b}/phase3/gate",
        json={
            "decision": "retry",
            "gate_mode": "deep",
            "reviewer_id": "phase3_api_smoke",
            "reason_code": "confidence_too_low",
            "auto_retry": True,
        },
    )
    assert deep_retry.status_code == 200, deep_retry.text

    artifact_b = (deep_retry.json().get("context_artifact") or {}).get("artifact") or {}
    retry_count_b = artifact_b.get("retry_count")
    state_b = deep_retry.json()["run"]["state"]

    approve_b = client.post(
        f"/agent3/runs/{run_b}/phase3/gate",
        json={
            "decision": "approve",
            "gate_mode": "deep",
            "reviewer_id": "phase3_api_smoke",
            "reason_code": None,
            "auto_retry": True,
        },
    )
    assert approve_b.status_code == 200, approve_b.text
    final_state_b = approve_b.json()["run"]["state"]

    print("FLOW_A_STATE", state_a)
    print("FLOW_B_STATE_AFTER_RETRY", state_b)
    print("FLOW_B_RETRY_COUNT", retry_count_b)
    print("FLOW_B_FINAL_STATE", final_state_b)


if __name__ == "__main__":
    main()
