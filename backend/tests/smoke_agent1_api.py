from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


client = TestClient(app)


def run_smoke() -> dict:
    summary: dict = {}

    # 1) Sample backlog intake via MCP
    resp = client.post(
        "/agent1/intake/load",
        json={"source_type": "sample_db", "source_ref": "smoke-test"},
    )
    summary["sample_intake_status"] = resp.status_code
    resp.raise_for_status()

    items = resp.json().get("items", [])
    summary["sample_item_count"] = len(items)
    if not items:
        raise AssertionError("No sample backlog items returned")

    backlog_item_id = items[0]["backlog_item_id"]
    summary["sample_backlog_item_id"] = backlog_item_id

    # 2) Agent1 run lifecycle
    resp = client.post("/agent1/runs", json={"backlog_item_id": backlog_item_id})
    summary["create_run_status"] = resp.status_code
    resp.raise_for_status()

    run_snapshot = resp.json()
    run = run_snapshot["run"]
    run_id = run["run_id"]
    summary["run_id"] = run_id
    summary["state_after_create"] = run["state"]

    resp = client.post(f"/agent1/runs/{run_id}/generate", json={"model": "smoke-model"})
    summary["generate_status"] = resp.status_code
    resp.raise_for_status()

    run_snapshot = resp.json()
    run = run_snapshot["run"]
    summary["state_after_generate"] = run["state"]
    summary["artifact_versions_after_generate"] = 1 if run_snapshot.get("latest_artifact") else 0

    resp = client.post(
        f"/agent1/runs/{run_id}/review",
        json={
            "decision": "approve",
            "reviewer_id": "qa-smoke",
            "reason_code": "smoke_approved",
        },
    )
    summary["review_status"] = resp.status_code
    resp.raise_for_status()

    run_snapshot = resp.json()
    run = run_snapshot["run"]
    summary["state_after_review"] = run["state"]

    resp = client.post(f"/agent1/runs/{run_id}/handoff")
    summary["handoff_status"] = resp.status_code
    resp.raise_for_status()

    run_snapshot = resp.json()
    run = run_snapshot["run"]
    summary["state_after_handoff"] = run["state"]
    summary["handoff_count"] = len(run_snapshot.get("handoffs", []))

    resp = client.get(f"/agent1/runs/{run_id}/timeline")
    summary["timeline_status"] = resp.status_code
    resp.raise_for_status()
    summary["timeline_events"] = len(resp.json().get("timeline", []))

    resp = client.get(f"/agent1/stories/{backlog_item_id}/runs")
    summary["run_history_status"] = resp.status_code
    resp.raise_for_status()
    summary["run_history_count"] = len(resp.json().get("runs", []))

    # 3) API backlog intake capability check (environment-config dependent)
    api_resp = client.post(
        "/agent1/intake/load",
        json={"source_type": "api", "source_ref": "smoke-test-api"},
    )
    summary["api_intake_status"] = api_resp.status_code
    if api_resp.status_code == 200:
        summary["api_item_count"] = len(api_resp.json().get("items", []))
    else:
        summary["api_intake_error"] = api_resp.json().get("detail")

    return summary


if __name__ == "__main__":
    print(run_smoke())
