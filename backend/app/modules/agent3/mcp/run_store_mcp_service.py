from __future__ import annotations

from app.infrastructure.store import store


class Agent3RunStoreMCPService:
    """MCP data-plane adapter for Agent3 run and audit persistence."""

    def create_run_from_inbox(self, **kwargs) -> tuple[dict, bool]:
        return store.create_agent3_run_from_inbox(**kwargs)

    def get_run(self, run_id: str) -> dict | None:
        return store.get_agent3_run(run_id)

    def list_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        return store.list_agent3_runs_for_backlog_item(backlog_item_id, limit=limit)

    def update_state(self, **kwargs) -> None:
        store.upsert_agent3_run_state(**kwargs)

    def add_artifact(self, *, run_id: str, artifact_version: int, artifact: dict) -> None:
        store.add_agent3_artifact(
            run_id=run_id,
            artifact_version=artifact_version,
            artifact=artifact,
        )

    def get_latest_artifact(self, run_id: str) -> dict | None:
        return store.get_agent3_latest_artifact(run_id)

    def get_artifacts(self, run_id: str) -> list[dict]:
        return store.get_agent3_artifacts(run_id)

    def get_next_artifact_version(self, run_id: str) -> int:
        return store.get_agent3_next_artifact_version(run_id)

    def add_audit_event(self, **kwargs) -> None:
        store.add_agent3_audit_event(**kwargs)

    def list_audit_events(self, run_id: str, *, ascending: bool = False) -> list[dict]:
        return store.get_agent3_audit_events(run_id, ascending=ascending)

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
            run_scope="agent3",
            run_id=run_id,
            requested_by=requested_by,
            reason_code=reason_code,
            reason_text=reason_text,
        )

    def list_retry_requests(self, run_id: str, limit: int = 20) -> list[dict]:
        return store.list_retry_governance_requests(run_scope="agent3", run_id=run_id, limit=limit)

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
