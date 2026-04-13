from __future__ import annotations

import json
from uuid import uuid4
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from app.infrastructure.store import store

BASE = "http://127.0.0.1:8011"


def _request(method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = Request(
        url=f"{BASE}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=10) as response:
            raw = response.read().decode("utf-8")
            return response.status, (json.loads(raw) if raw else {})
    except HTTPError as exc:
        raw = exc.read().decode("utf-8")
        data = json.loads(raw) if raw else {}
        return exc.code, data


def seed_source(step_action: str) -> str:
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
    return run_id


def smoke() -> None:
    health_status, health_data = _request("GET", "/health")
    assert health_status == 200, health_data

    source_run = seed_source("Open the homepage and continue")
    suffix = uuid4().hex[:8]
    consume_status, consume_data = _request(
        "POST",
        "/agent3/inbox/consume",
        {
            "message_id": f"a3-msg-{suffix}",
            "run_id": source_run,
            "trace_id": f"trace-{suffix}",
            "stage_id": "reasoning",
            "task_type": "reason_over_steps",
            "contract_version": "v1",
            "retry_count": 0,
            "dedupe_key": f"dedupe-{suffix}",
            "payload": {"note": "phase3 http smoke"},
        },
    )
    assert consume_status == 200, consume_data

    message_id = consume_data["inbox"]["message_id"]
    create_status, create_data = _request("POST", f"/agent3/inbox/{message_id}/runs")
    assert create_status == 200, create_data
    run_id = create_data["run"]["run_id"]

    assemble_status, assemble_data = _request("POST", f"/agent3/runs/{run_id}/phase3/assemble-context")
    assert assemble_status == 200, assemble_data

    wrong_mode_status, wrong_mode_data = _request(
        "POST",
        f"/agent3/runs/{run_id}/phase3/gate",
        {
            "decision": "retry",
            "gate_mode": "quick",
            "reviewer_id": "phase3_http_smoke",
            "reason_code": "confidence_too_low",
            "auto_retry": True,
        },
    )
    assert wrong_mode_status == 400, wrong_mode_data

    deep_retry_status, deep_retry_data = _request(
        "POST",
        f"/agent3/runs/{run_id}/phase3/gate",
        {
            "decision": "retry",
            "gate_mode": "deep",
            "reviewer_id": "phase3_http_smoke",
            "reason_code": "confidence_too_low",
            "auto_retry": True,
        },
    )
    assert deep_retry_status == 200, deep_retry_data

    final_status, final_data = _request(
        "POST",
        f"/agent3/runs/{run_id}/phase3/gate",
        {
            "decision": "approve",
            "gate_mode": "deep",
            "reviewer_id": "phase3_http_smoke",
            "reason_code": None,
            "auto_retry": True,
        },
    )
    assert final_status == 200, final_data

    print("HEALTH", health_status)
    print("RUN_ID", run_id)
    print("WRONG_MODE_STATUS", wrong_mode_status)
    print("RETRY_STATE", deep_retry_data["run"]["state"])
    print("FINAL_STATE", final_data["run"]["state"])


if __name__ == "__main__":
    smoke()
