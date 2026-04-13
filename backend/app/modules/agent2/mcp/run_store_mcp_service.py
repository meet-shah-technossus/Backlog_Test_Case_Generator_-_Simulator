from __future__ import annotations

from app.infrastructure.store import store


class Agent2RunStoreMCPService:
    """MCP data-plane adapter for Agent2 run, artifact, review, handoff persistence."""

    def create_run_from_inbox(self, **kwargs) -> tuple[dict, bool]:
        return store.create_agent2_run_from_inbox(**kwargs)

    def get_run(self, run_id: str) -> dict | None:
        return store.get_agent2_run(run_id)

    def list_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        return store.list_agent2_runs_for_backlog_item(backlog_item_id, limit=limit)

    def get_observability_counters(self, backlog_item_id: str | None = None) -> dict:
        return store.get_agent2_observability_counters(backlog_item_id=backlog_item_id)

    def update_state(self, **kwargs) -> None:
        store.upsert_agent2_run_state(**kwargs)

    def add_artifact(self, *, run_id: str, source_agent1_run_id: str, artifact: dict) -> int:
        version = store.get_agent2_next_artifact_version(run_id)
        store.add_agent2_artifact(
            run_id=run_id,
            source_agent1_run_id=source_agent1_run_id,
            artifact_version=version,
            artifact=artifact,
        )
        return version

    def get_latest_artifact(self, run_id: str) -> dict | None:
        return store.get_agent2_latest_artifact(run_id)

    def list_artifacts(self, run_id: str) -> list[dict]:
        return store.get_agent2_artifacts(run_id)

    def add_review(self, **kwargs) -> None:
        store.add_agent2_review(**kwargs)

    def list_reviews(self, run_id: str) -> list[dict]:
        return store.get_agent2_reviews(run_id)

    def add_handoff(self, **kwargs) -> tuple[dict, bool]:
        return store.create_agent2_handoff(**kwargs)

    def list_handoffs(self, run_id: str) -> list[dict]:
        return store.get_agent2_handoffs(run_id)

    def add_audit_event(self, **kwargs) -> None:
        store.add_agent2_audit_event(**kwargs)

    def list_audit_events(self, run_id: str) -> list[dict]:
        return store.get_agent2_audit_events(run_id)

    def list_timeline_events(self, run_id: str, *, ascending: bool = True) -> list[dict]:
        return store.get_agent2_audit_events(run_id, ascending=ascending)

    def get_agent1_latest_artifact(self, run_id: str) -> dict | None:
        return store.get_agent1_latest_artifact(run_id)

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
            run_scope="agent2",
            run_id=run_id,
            requested_by=requested_by,
            reason_code=reason_code,
            reason_text=reason_text,
        )

    def list_retry_requests(self, run_id: str, limit: int = 20) -> list[dict]:
        return store.list_retry_governance_requests(run_scope="agent2", run_id=run_id, limit=limit)

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
