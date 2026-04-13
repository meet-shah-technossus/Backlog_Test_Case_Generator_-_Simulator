from __future__ import annotations

import importlib
import pathlib
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure backend package imports resolve when running tests from workspace root.
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

retry_router_module = importlib.import_module("app.api.routes.retry_governance.router")
from app.infrastructure.store.core import Store
import app.modules.retry_governance.policy_service as policy_service_module
import app.modules.retry_governance.revision_service as revision_service_module


OPERATOR_HEADERS = {"X-Retry-Role": "operator"}
REVIEWER_HEADERS = {"X-Retry-Role": "reviewer"}


def build_client(tmp_path, monkeypatch) -> tuple[TestClient, Store]:
    test_store = Store(db_path=tmp_path / "phase4_active_revisions.db")
    monkeypatch.setattr(retry_router_module, "store", test_store)
    monkeypatch.setattr(policy_service_module, "store", test_store)
    monkeypatch.setattr(revision_service_module, "store", test_store)

    app = FastAPI()
    app.include_router(retry_router_module.router)
    return TestClient(app), test_store


def test_phase4_new_artifact_becomes_active_and_promotion_switches_active(tmp_path) -> None:
    store = Store(db_path=tmp_path / "phase4_store_active.db")

    store.upsert_agent1_run(
        run_id="run-1",
        backlog_item_id="story-1",
        trace_id="trace-1",
        state="review_pending",
        source_type="sample",
        source_ref="local",
    )

    store.add_agent1_artifact(
        run_id="run-1",
        backlog_item_id="story-1",
        artifact_version=1,
        artifact={"artifact_type": "suite", "name": "v1"},
    )
    store.add_agent1_artifact(
        run_id="run-1",
        backlog_item_id="story-1",
        artifact_version=2,
        artifact={"artifact_type": "suite", "name": "v2"},
    )

    latest = store.get_agent1_latest_artifact("run-1")
    assert latest is not None
    assert latest["artifact_version"] == 2
    assert latest["is_active"] is True

    promoted = store.set_agent1_active_artifact_version(run_id="run-1", artifact_version=1)
    assert promoted is not None
    assert promoted["artifact_version"] == 1
    assert promoted["is_active"] is True

    artifacts = store.get_agent1_artifacts("run-1")
    active_versions = [row["artifact_version"] for row in artifacts if row.get("is_active")]
    assert active_versions == [1]


def test_phase4_revision_api_active_default_and_history_optional(tmp_path, monkeypatch) -> None:
    client, store = build_client(tmp_path, monkeypatch)

    store.upsert_agent1_run(
        run_id="run-2",
        backlog_item_id="story-2",
        trace_id="trace-2",
        state="review_pending",
        source_type="sample",
        source_ref="local",
    )
    store.add_agent1_artifact(
        run_id="run-2",
        backlog_item_id="story-2",
        artifact_version=1,
        artifact={"artifact_type": "suite", "name": "v1"},
    )
    store.add_agent1_artifact(
        run_id="run-2",
        backlog_item_id="story-2",
        artifact_version=2,
        artifact={"artifact_type": "suite", "name": "v2"},
    )

    without_history = client.get(
        "/retry-governance/revisions/agent1/run-2",
        headers=REVIEWER_HEADERS,
    )
    assert without_history.status_code == 200
    body = without_history.json()
    assert body["active_revision"]["artifact_version"] == 2
    assert body["history"] == []

    with_history = client.get(
        "/retry-governance/revisions/agent1/run-2?include_history=true",
        headers=REVIEWER_HEADERS,
    )
    assert with_history.status_code == 200
    history = with_history.json()["history"]
    assert len(history) == 2
    assert history[0]["is_active"] is True


def test_phase4_revision_promote_endpoint_changes_active_revision(tmp_path, monkeypatch) -> None:
    client, store = build_client(tmp_path, monkeypatch)

    store.upsert_agent1_run(
        run_id="run-3",
        backlog_item_id="story-3",
        trace_id="trace-3",
        state="review_pending",
        source_type="sample",
        source_ref="local",
    )
    store.add_agent1_artifact(
        run_id="run-3",
        backlog_item_id="story-3",
        artifact_version=1,
        artifact={"artifact_type": "suite", "name": "v1"},
    )
    store.add_agent1_artifact(
        run_id="run-3",
        backlog_item_id="story-3",
        artifact_version=2,
        artifact={"artifact_type": "suite", "name": "v2"},
    )

    promote = client.post(
        "/retry-governance/revisions/agent1/run-3/promote",
        headers=OPERATOR_HEADERS,
        json={"artifact_version": 1, "actor": "operator", "reason": "revert"},
    )
    assert promote.status_code == 200
    assert promote.json()["active_revision"]["artifact_version"] == 1

    latest = store.get_agent1_latest_artifact("run-3")
    assert latest is not None
    assert latest["artifact_version"] == 1

    denied = client.post(
        "/retry-governance/revisions/agent1/run-3/promote",
        headers=REVIEWER_HEADERS,
        json={"artifact_version": 2, "actor": "reviewer", "reason": "should fail"},
    )
    assert denied.status_code == 403
