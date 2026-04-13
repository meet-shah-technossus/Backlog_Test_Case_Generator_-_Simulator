from __future__ import annotations

import pathlib
import sys

# Ensure backend package imports resolve when running tests from workspace root.
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.infrastructure.store.core import Store


def test_phase0_business_id_is_assigned_for_agent5_run(tmp_path) -> None:
    db_path = tmp_path / "phase0_business_id.db"
    store = Store(db_path=db_path)

    store.create_agent5_run(
        agent5_run_id="run-internal-1",
        source_agent4_run_id="agent4-internal-1",
        source_execution_run_id=None,
        backlog_item_id=None,
        trace_id="trace-1",
        state="queued",
        stage="a5_persistence_initialized",
        request_payload={"created_by": "test"},
    )

    row = store.get_agent5_run("run-internal-1")
    assert row is not None
    assert str(row.get("business_id") or "").startswith("AG5-RUN-")


def test_phase1_retry_governance_request_and_review(tmp_path) -> None:
    db_path = tmp_path / "phase1_retry_governance.db"
    store = Store(db_path=db_path)

    created = store.add_retry_governance_request(
        request_id="req-1",
        run_scope="agent2",
        run_id="run-2",
        requested_by="qa-user",
        reason_code="needs_retry",
        reason_text="Prompt drift observed",
    )
    assert created["status"] == "retry_review_pending"

    reviewed = store.review_retry_governance_request(
        request_id="req-1",
        reviewer_id="lead-reviewer",
        reviewer_decision="approve",
        reviewer_comment="Approved for rerun",
    )

    assert reviewed is not None
    assert reviewed["status"] == "retry_approved"
    assert reviewed["reviewer_id"] == "lead-reviewer"
