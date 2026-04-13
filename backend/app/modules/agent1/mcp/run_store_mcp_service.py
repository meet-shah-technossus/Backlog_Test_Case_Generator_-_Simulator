from __future__ import annotations

from app.infrastructure.store import store


class Agent1RunStoreMCPService:
    """MCP data-plane adapter for Agent1 run persistence operations."""

    def upsert_run(self, **kwargs) -> None:
        store.upsert_agent1_run(**kwargs)

    def get_run(self, run_id: str) -> dict | None:
        return store.get_agent1_run(run_id)

    def list_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        return store.list_agent1_runs_for_backlog_item(backlog_item_id, limit=limit)

    def add_artifact(self, *, run_id: str, backlog_item_id: str, artifact: dict) -> int:
        version = store.get_agent1_next_artifact_version(run_id)
        store.add_agent1_artifact(
            run_id=run_id,
            backlog_item_id=backlog_item_id,
            artifact_version=version,
            artifact=artifact,
        )
        return version

    def get_latest_artifact(self, run_id: str) -> dict | None:
        return store.get_agent1_latest_artifact(run_id)

    def list_artifacts(self, run_id: str) -> list[dict]:
        return store.get_agent1_artifacts(run_id)

    def add_review(self, **kwargs) -> None:
        store.add_agent1_review(**kwargs)

    def list_reviews(self, run_id: str) -> list[dict]:
        return store.get_agent1_reviews(run_id)

    def add_handoff(self, **kwargs) -> None:
        store.add_agent1_handoff(**kwargs)

    def list_handoffs(self, run_id: str) -> list[dict]:
        return store.get_agent1_handoffs(run_id)

    def add_audit_event(self, **kwargs) -> None:
        store.add_agent1_audit_event(**kwargs)

    def list_audit_events(self, run_id: str) -> list[dict]:
        return store.get_agent1_audit_events(run_id)

    def create_retry_request(
        self,
        *,
        request_id: str,
        run_id: str,
        requested_by: str,
        reason_code: str | None,
        reason_text: str | None,
    ) -> dict:
        return store.add_retry_governance_request(
            request_id=request_id,
            run_scope="agent1",
            run_id=run_id,
            requested_by=requested_by,
            reason_code=reason_code,
            reason_text=reason_text,
        )

    def list_retry_requests(self, run_id: str, limit: int = 20) -> list[dict]:
        return store.list_retry_governance_requests(run_scope="agent1", run_id=run_id, limit=limit)

    def review_retry_request(
        self,
        *,
        request_id: str,
        reviewer_id: str,
        reviewer_decision: str,
        reviewer_comment: str | None,
    ) -> dict | None:
        return store.review_retry_governance_request(
            request_id=request_id,
            reviewer_id=reviewer_id,
            reviewer_decision=reviewer_decision,
            reviewer_comment=reviewer_comment,
        )
