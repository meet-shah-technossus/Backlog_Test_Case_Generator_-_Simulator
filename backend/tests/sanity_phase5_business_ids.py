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
    auth_headers = {'X-Retry-Role': 'reviewer'}

    suffix = uuid4().hex[:10]

    agent1_run_id = f"agent1-phase5-bid-{suffix}"
    backlog_item_id = f"story-phase5-bid-{suffix}"
    trace_id = f"trace-phase5-bid-{suffix}"

    store.upsert_agent1_run(
        run_id=agent1_run_id,
        backlog_item_id=backlog_item_id,
        trace_id=trace_id,
        state="completed",
        source_type="manual",
        source_ref=None,
    )
    store.add_agent1_artifact(
        run_id=agent1_run_id,
        backlog_item_id=backlog_item_id,
        artifact_version=1,
        artifact={"test_cases": [{"id": "TC001", "title": "Business ID sanity"}]},
    )

    artifacts = store.get_agent1_artifacts(agent1_run_id)
    assert artifacts, "Expected at least one Agent1 artifact"
    artifact_business_id = artifacts[0].get("business_id")
    assert isinstance(artifact_business_id, str) and artifact_business_id.startswith("TC-"), (
        f"Unexpected artifact business_id: {artifact_business_id}"
    )

    execution_run_id = f"exe-phase5-bid-{suffix}"
    store.create_execution_run(
        execution_run_id=execution_run_id,
        source_agent4_run_id=f"agent4-phase5-bid-{suffix}",
        backlog_item_id=backlog_item_id,
        trace_id=trace_id,
        state="queued",
        stage="phase10_execution_queued",
        request_payload={"script_path": "tests/generated/sample.spec.ts"},
        runtime_policy={"headless": True},
        max_attempts=1,
    )
    store.update_execution_run_state(
        execution_run_id=execution_run_id,
        state="completed",
        stage="phase10_execution_completed",
        result_payload={
            "status": "passed",
            "step_results": [
                {
                    "step_index": 1,
                    "status": "passed",
                    "duration_ms": 12,
                    "screenshot_path": "execution_artifacts/shot.png",
                }
            ],
        },
    )

    evidence = store.get_execution_evidence(execution_run_id)
    assert evidence, "Expected at least one execution evidence item"
    evidence_business_id = evidence[0].get("business_id")
    assert isinstance(evidence_business_id, str) and evidence_business_id.startswith("EVD-"), (
        f"Unexpected evidence business_id: {evidence_business_id}"
    )

    artifact_lookup = client.get(f"/business-ids/{artifact_business_id}", headers=auth_headers)
    assert artifact_lookup.status_code == 200, artifact_lookup.text
    artifact_payload = artifact_lookup.json()
    assert artifact_payload.get("table") == "agent1_artifacts", artifact_payload
    assert artifact_payload.get("key_value") == artifacts[0].get("id"), artifact_payload

    evidence_lookup = client.get(f"/business-ids/{evidence_business_id}", headers=auth_headers)
    assert evidence_lookup.status_code == 200, evidence_lookup.text
    evidence_payload = evidence_lookup.json()
    assert evidence_payload.get("table") == "execution_evidence", evidence_payload
    assert evidence_payload.get("key_value") == evidence[0].get("id"), evidence_payload

    not_found = client.get("/business-ids/UNKNOWN-BID-999999", headers=auth_headers)
    assert not_found.status_code == 404, not_found.text

    print(
        {
            "artifact_business_id": artifact_business_id,
            "evidence_business_id": evidence_business_id,
            "artifact_lookup_table": artifact_payload.get("table"),
            "evidence_lookup_table": evidence_payload.get("table"),
            "unknown_status": not_found.status_code,
        }
    )


if __name__ == "__main__":
    main()
