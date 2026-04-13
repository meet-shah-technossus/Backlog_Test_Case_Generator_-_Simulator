from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.store import store
from app.main import app


def seed_agent1_handoff_ready_run(run_id: str, backlog_item_id: str, suffix: str) -> None:
    store.upsert_agent1_run(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        trace_id=f"trace-phase22-{suffix}",
        state="handoff_pending",
        source_type="manual",
        source_ref="phase22_sanity",
    )
    store.add_agent1_artifact(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        artifact_version=1,
        artifact={
            "backlog_item_id": backlog_item_id,
            "test_cases": [{"id": "TC-PHASE22-1", "title": "Phase 22 handoff seed"}],
        },
    )
    store.add_agent1_review(
        run_id=run_id,
        stage="phase22_foundation",
        decision="approve",
        reason_code=None,
        reviewer_id="phase22_sanity",
        edited_payload=None,
    )


def main() -> None:
    client = TestClient(app)

    suffix = uuid4().hex[:10]
    backlog_item_id = f"story-phase22-{suffix}"
    agent1_run_id = f"agent1-phase22-{suffix}"

    seed_agent1_handoff_ready_run(agent1_run_id, backlog_item_id, suffix)

    handoff_resp = client.post(f"/agent1/runs/{agent1_run_id}/handoff")
    assert handoff_resp.status_code == 200, handoff_resp.text

    start_resp = client.post(f"/agent2/agent1-runs/{agent1_run_id}/start")
    assert start_resp.status_code == 200, start_resp.text
    start_payload = start_resp.json() or {}

    agent2_run_id = (((start_payload.get("snapshot") or {}).get("run") or {}).get("run_id"))
    assert isinstance(agent2_run_id, str) and agent2_run_id, start_payload

    snapshot_resp = client.get(f"/agent2/runs/{agent2_run_id}")
    contract_resp = client.get(f"/agent2/runs/{agent2_run_id}/contract/v1")
    timeline_resp = client.get(f"/agent2/runs/{agent2_run_id}/timeline?order=asc")
    history_resp = client.get(f"/agent2/runs?backlog_item_id={backlog_item_id}&limit=10")

    assert snapshot_resp.status_code == 200, snapshot_resp.text
    assert contract_resp.status_code == 200, contract_resp.text
    assert timeline_resp.status_code == 200, timeline_resp.text
    assert history_resp.status_code == 200, history_resp.text

    snapshot_payload = snapshot_resp.json() or {}
    contract_payload = contract_resp.json() or {}
    timeline_payload = timeline_resp.json() or {}
    history_payload = history_resp.json() or {}

    assert ((snapshot_payload.get("run") or {}).get("run_id")) == agent2_run_id, snapshot_payload
    assert isinstance(snapshot_payload.get("timeline"), list), snapshot_payload

    assert contract_payload.get("contract_version") == "v1", contract_payload
    assert contract_payload.get("run_scope") == "agent2", contract_payload
    assert contract_payload.get("internal_id") == agent2_run_id, contract_payload

    current_revision = contract_payload.get("current_revision") or {}
    retry_status = contract_payload.get("retry_status") or {}
    review_status = contract_payload.get("review_status") or {}

    assert set(current_revision.keys()) >= {
        "internal_id",
        "business_id",
        "artifact_version",
        "created_at",
    }, current_revision
    assert set(retry_status.keys()) >= {
        "latest_request_id",
        "latest_status",
        "total_requests",
    }, retry_status
    assert set(review_status.keys()) >= {
        "latest_decision",
        "latest_reviewer_id",
        "latest_reviewed_at",
        "total_reviews",
    }, review_status

    assert timeline_payload.get("run_id") == agent2_run_id, timeline_payload
    assert timeline_payload.get("order") == "asc", timeline_payload
    assert isinstance(timeline_payload.get("events"), list), timeline_payload

    assert history_payload.get("backlog_item_id") == backlog_item_id, history_payload
    runs = history_payload.get("runs") or []
    assert isinstance(runs, list) and runs, history_payload
    assert any((row or {}).get("run_id") == agent2_run_id for row in runs), history_payload

    print(
        {
            "agent1_run_id": agent1_run_id,
            "agent2_run_id": agent2_run_id,
            "contract_version": contract_payload.get("contract_version"),
            "timeline_events": len(timeline_payload.get("events") or []),
            "history_count": len(runs),
        }
    )


if __name__ == "__main__":
    main()
