from __future__ import annotations

import pathlib
import sys
from unittest.mock import Mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure backend package imports resolve when running tests from workspace root.
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.api.dependencies import get_container
from app.api.routes.agent5.router import router as agent5_router


class FakeContainer:
    def __init__(self) -> None:
        self._observability = Mock()
        self._gate8 = Mock()
        self._reliability = Mock()

    def get_agent5_observability_service(self):
        return self._observability

    def get_agent5_gate8_service(self):
        return self._gate8

    def get_agent5_reliability_service(self):
        return self._reliability


def build_client(container: FakeContainer) -> TestClient:
    app = FastAPI()
    app.include_router(agent5_router)
    app.dependency_overrides[get_container] = lambda: container
    return TestClient(app)


class TestAgent5A510A512Router:
    def test_get_observability_returns_payload_wrapper(self) -> None:
        container = FakeContainer()
        container._observability.get_run_observability.return_value = {
            "agent5_run_id": "run-1",
            "phase": "A5.11",
            "stage_durations": [],
            "payload_checksums": {},
        }
        client = build_client(container)

        res = client.get("/agent5/runs/run-1/observability")

        assert res.status_code == 200
        body = res.json()
        assert "observability" in body
        assert body["observability"]["phase"] == "A5.11"

    def test_submit_gate8_decision_maps_state_error_to_409(self) -> None:
        container = FakeContainer()
        container._gate8.submit_gate8_decision.side_effect = ValueError(
            "Gate8 decision can be submitted only when state is gate8_pending"
        )
        client = build_client(container)

        res = client.post(
            "/agent5/runs/run-1/gate8/decision",
            json={
                "reviewer_id": "agent5-ui",
                "decision": "confirm",
                "reason_code": "ok",
                "comment": "",
            },
        )

        assert res.status_code == 409

    def test_recover_stale_returns_recovery_object(self) -> None:
        container = FakeContainer()
        container._reliability.recover_stale_runs.return_value = {
            "phase": "A5.12",
            "recovered_count": 1,
            "recovered_runs": [{"agent5_run_id": "run-2"}],
        }
        client = build_client(container)

        res = client.post(
            "/agent5/reliability/recover-stale",
            json={"actor": "ops", "older_than_seconds": 1800, "limit": 10},
        )

        assert res.status_code == 200
        body = res.json()
        assert body["recovery"]["phase"] == "A5.12"
        assert body["recovery"]["recovered_count"] == 1

    def test_retry_failed_maps_not_found_to_404(self) -> None:
        container = FakeContainer()
        container._reliability.retry_failed_run.side_effect = ValueError("Agent5 run 'x' not found")
        client = build_client(container)

        res = client.post("/agent5/runs/x/reliability/retry", json={"actor": "agent5-ui"})

        assert res.status_code == 404
