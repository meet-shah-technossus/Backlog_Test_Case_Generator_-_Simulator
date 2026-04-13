from __future__ import annotations

import pathlib
import sys
import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure backend package imports resolve when running tests from workspace root.
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

retry_router_module = importlib.import_module("app.api.routes.retry_governance.router")
from app.infrastructure.store.core import Store
from app.modules.retry_governance import RetryGovernancePolicyService
import app.modules.retry_governance.policy_service as policy_service_module


OPERATOR_HEADERS = {"X-Retry-Role": "operator"}
REVIEWER_HEADERS = {"X-Retry-Role": "reviewer"}


def build_retry_client(tmp_path, monkeypatch) -> TestClient:
    test_store = Store(db_path=tmp_path / "phase2_retry_governance.db")
    monkeypatch.setattr(retry_router_module, "store", test_store)
    monkeypatch.setattr(policy_service_module, "store", test_store)
    monkeypatch.setattr(retry_router_module, "policy_service", RetryGovernancePolicyService())

    app = FastAPI()
    app.include_router(retry_router_module.router)
    return TestClient(app)


def test_phase2_manual_assignment_enforced_for_reviewer(tmp_path, monkeypatch) -> None:
    client = build_retry_client(tmp_path, monkeypatch)

    created = client.post(
        "/retry-governance/agent2/run-21/request",
        headers=OPERATOR_HEADERS,
        json={
            "requested_by": "qa-user",
            "reason_code": "needs_retry",
            "reason_text": "Retry requested after failed evidence upload",
        },
    )
    assert created.status_code == 200
    request_id = created.json()["request"]["request_id"]

    assigned = client.post(
        f"/retry-governance/requests/{request_id}/assign",
        headers=OPERATOR_HEADERS,
        json={
            "reviewer_id": "agent2-reviewer",
            "assigned_by": "lead-reviewer",
            "reason": "Owner assignment",
        },
    )
    assert assigned.status_code == 200
    assert assigned.json()["request"]["assigned_reviewer_id"] == "agent2-reviewer"

    wrong_reviewer_review = client.post(
        f"/retry-governance/requests/{request_id}/review",
        headers=REVIEWER_HEADERS,
        json={
            "reviewer_id": "agent3-reviewer",
            "decision": "approve",
            "comment": "Looks good",
        },
    )
    assert wrong_reviewer_review.status_code == 400
    assert "Only assigned reviewer" in wrong_reviewer_review.json()["detail"]


def test_phase2_auto_assignment_conflict_escalates(tmp_path, monkeypatch) -> None:
    client = build_retry_client(tmp_path, monkeypatch)

    created = client.post(
        "/retry-governance/agent2/run-22/request",
        headers=OPERATOR_HEADERS,
        json={
            "requested_by": "agent2-reviewer",
            "reason_code": "retry_policy",
            "reason_text": "Re-run after policy check",
        },
    )
    assert created.status_code == 200
    request_id = created.json()["request"]["request_id"]

    auto_assigned = client.post(
        f"/retry-governance/requests/{request_id}/assign/auto",
        headers=OPERATOR_HEADERS,
        json={"assigned_by": "system"},
    )

    assert auto_assigned.status_code == 200
    body = auto_assigned.json()["request"]
    assert body["assigned_reviewer_id"] == "platform-reviewer"
    assert body["assignment_mode"] == "auto_escalated"
    assert body["escalation_status"] == "escalated_reviewer_conflict"


def test_phase2_self_approval_blocked_even_when_assigned(tmp_path, monkeypatch) -> None:
    client = build_retry_client(tmp_path, monkeypatch)

    created = client.post(
        "/retry-governance/agent3/run-23/request",
        headers=OPERATOR_HEADERS,
        json={
            "requested_by": "agent3-reviewer",
            "reason_code": "retry_policy",
            "reason_text": "Needs second pass",
        },
    )
    assert created.status_code == 200
    request_id = created.json()["request"]["request_id"]

    assigned = client.post(
        f"/retry-governance/requests/{request_id}/assign",
        headers=OPERATOR_HEADERS,
        json={
            "reviewer_id": "agent3-reviewer",
            "assigned_by": "lead-reviewer",
            "reason": "Temporary assignment",
        },
    )
    assert assigned.status_code == 200

    review = client.post(
        f"/retry-governance/requests/{request_id}/review",
        headers=REVIEWER_HEADERS,
        json={
            "reviewer_id": "agent3-reviewer",
            "decision": "approve",
            "comment": "Self approve should fail",
        },
    )
    assert review.status_code == 400
    assert "Self-approval is not allowed" in review.json()["detail"]


def test_phase2_audit_endpoint_returns_events(tmp_path, monkeypatch) -> None:
    client = build_retry_client(tmp_path, monkeypatch)

    created = client.post(
        "/retry-governance/agent1/run-24/request",
        headers=OPERATOR_HEADERS,
        json={
            "requested_by": "qa-user",
            "reason_code": "retry_policy",
            "reason_text": "Evidence mismatch",
        },
    )
    request_id = created.json()["request"]["request_id"]

    client.post(
        f"/retry-governance/requests/{request_id}/assign",
        headers=OPERATOR_HEADERS,
        json={
            "reviewer_id": "agent1-reviewer",
            "assigned_by": "lead-reviewer",
            "reason": "Default owner",
        },
    )

    audit = client.get(f"/retry-governance/requests/{request_id}/audit", headers=REVIEWER_HEADERS)
    assert audit.status_code == 200
    events = audit.json()["events"]
    actions = {event["action"] for event in events}
    assert "retry_requested" in actions
    assert "reviewer_assigned" in actions


def test_phase2_role_authorization_blocks_invalid_role(tmp_path, monkeypatch) -> None:
    client = build_retry_client(tmp_path, monkeypatch)

    created = client.post(
        "/retry-governance/agent1/run-25/request",
        headers=OPERATOR_HEADERS,
        json={
            "requested_by": "qa-user",
            "reason_code": "retry_policy",
            "reason_text": "Role check",
        },
    )
    request_id = created.json()["request"]["request_id"]

    denied = client.post(
        f"/retry-governance/requests/{request_id}/assign",
        headers=REVIEWER_HEADERS,
        json={
            "reviewer_id": "agent1-reviewer",
            "assigned_by": "reviewer",
            "reason": "Should fail",
        },
    )
    assert denied.status_code == 403


def test_phase3_approve_and_run_endpoint_executes(tmp_path, monkeypatch) -> None:
    client = build_retry_client(tmp_path, monkeypatch)

    created = client.post(
        "/retry-governance/agent1/run-26/request",
        headers=OPERATOR_HEADERS,
        json={
            "requested_by": "qa-user",
            "reason_code": "retry_policy",
            "reason_text": "Phase3 execution",
        },
    )
    request_id = created.json()["request"]["request_id"]

    client.post(
        f"/retry-governance/requests/{request_id}/assign",
        headers=OPERATOR_HEADERS,
        json={
            "reviewer_id": "agent1-reviewer",
            "assigned_by": "lead-reviewer",
            "reason": "Owner",
        },
    )

    class FakeExecutionService:
        async def execute_approved_retry(self, *, request_id: str, actor: str, container):
            return {
                "request": {
                    "request_id": request_id,
                    "status": "retry_completed",
                },
                "run_scope": "agent1",
                "run_id": "run-26",
                "result": {"ok": True, "actor": actor},
            }

    monkeypatch.setattr(retry_router_module, "execution_service", FakeExecutionService())

    res = client.post(
        f"/retry-governance/requests/{request_id}/approve-and-run",
        headers=REVIEWER_HEADERS,
        json={
            "reviewer_id": "agent1-reviewer",
            "comment": "Approved and execute",
        },
    )

    assert res.status_code == 200
    body = res.json()
    assert body["request"]["status"] == "retry_completed"
    assert body["result"]["ok"] is True
