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


def main() -> None:
    client = TestClient(app)

    suffix = uuid4().hex[:10]
    backlog_item_id = f"story-phase21-{suffix}"
    run_id = f"agent1-phase21-{suffix}"

    store.upsert_agent1_run(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        trace_id=f"trace-phase21-{suffix}",
        state="completed",
        source_type="manual",
        source_ref=None,
    )
    store.add_agent1_artifact(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        artifact_version=1,
        artifact={
            "backlog_item_id": backlog_item_id,
            "test_cases": [{"id": "TC-PHASE21-1", "title": "Phase 21 contract sanity"}],
        },
    )
    store.add_agent1_review(
        run_id=run_id,
        stage="phase21_foundation",
        decision="approve",
        reason_code=None,
        reviewer_id="phase21_sanity",
        edited_payload=None,
    )

    run_resp = client.get(f"/agent1/runs/{run_id}")
    contract_resp = client.get(f"/agent1/runs/{run_id}/contract/v1")
    timeline_resp = client.get(f"/agent1/runs/{run_id}/timeline")
    history_resp = client.get(f"/agent1/stories/{backlog_item_id}/runs?limit=10")

    assert run_resp.status_code == 200, run_resp.text
    assert contract_resp.status_code == 200, contract_resp.text
    assert timeline_resp.status_code == 200, timeline_resp.text
    assert history_resp.status_code == 200, history_resp.text

    run_payload = run_resp.json() or {}
    contract_payload = contract_resp.json() or {}
    timeline_payload = timeline_resp.json() or {}
    history_payload = history_resp.json() or {}

    assert isinstance(run_payload.get("run"), dict), run_payload
    assert isinstance(run_payload.get("timeline"), list), run_payload
    assert isinstance(run_payload.get("reviews"), list), run_payload

    assert contract_payload.get("contract_version") == "v1", contract_payload
    assert contract_payload.get("run_scope") == "agent1", contract_payload
    assert contract_payload.get("internal_id") == run_id, contract_payload

    assert timeline_payload.get("run_id") == run_id, timeline_payload
    assert isinstance(timeline_payload.get("timeline"), list), timeline_payload

    assert history_payload.get("backlog_item_id") == backlog_item_id, history_payload
    runs = history_payload.get("runs") or []
    assert isinstance(runs, list) and runs, history_payload
    assert any((row or {}).get("run_id") == run_id for row in runs), history_payload

    print(
        {
            "run_id": run_id,
            "contract_version": contract_payload.get("contract_version"),
            "history_count": len(runs),
            "timeline_events": len(timeline_payload.get("timeline") or []),
        }
    )


if __name__ == "__main__":
    main()
