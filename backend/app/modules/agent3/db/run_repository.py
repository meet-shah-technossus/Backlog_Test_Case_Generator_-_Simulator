from __future__ import annotations

from uuid import uuid4

from app.modules.agent3.mcp.run_store_mcp_service import Agent3RunStoreMCPService


class Agent3RunRepository:
    """Agent3 run persistence for intake phase."""

    def __init__(self, mcp_store: Agent3RunStoreMCPService | None = None):
        self._mcp_store = mcp_store or Agent3RunStoreMCPService()

    def create_from_inbox(
        self,
        *,
        run_id: str,
        inbox_message_id: str,
        source_agent2_run_id: str,
        trace_id: str,
        state: str,
        stage: str,
    ) -> tuple[dict, bool]:
        return self._mcp_store.create_run_from_inbox(
            run_id=run_id,
            inbox_message_id=inbox_message_id,
            source_agent2_run_id=source_agent2_run_id,
            trace_id=trace_id,
            state=state,
            stage=stage,
        )

    def get_run(self, run_id: str) -> dict | None:
        return self._mcp_store.get_run(run_id)

    def list_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        return self._mcp_store.list_runs_for_backlog_item(backlog_item_id, limit=limit)

    def update_state(
        self,
        *,
        run_id: str,
        state: str,
        stage: str,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        self._mcp_store.update_state(
            run_id=run_id,
            state=state,
            stage=stage,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
        )

    def add_artifact(self, *, run_id: str, artifact: dict) -> int:
        version = self._mcp_store.get_next_artifact_version(run_id)
        self._mcp_store.add_artifact(
            run_id=run_id,
            artifact_version=version,
            artifact=artifact,
        )
        return version

    def get_latest_artifact(self, run_id: str) -> dict | None:
        return self._mcp_store.get_latest_artifact(run_id)

    def get_artifacts(self, run_id: str) -> list[dict]:
        return self._mcp_store.get_artifacts(run_id)

    def get_next_artifact_version(self, run_id: str) -> int:
        return self._mcp_store.get_next_artifact_version(run_id)

    def add_audit_event(
        self,
        *,
        run_id: str,
        stage: str,
        action: str,
        actor: str,
        metadata: dict | None = None,
    ) -> None:
        self._mcp_store.add_audit_event(
            run_id=run_id,
            stage=stage,
            action=action,
            actor=actor,
            metadata=metadata,
        )

    def get_timeline_events(self, run_id: str, *, ascending: bool = True) -> list[dict]:
        return self._mcp_store.list_audit_events(run_id, ascending=ascending)

    def create_retry_request(
        self,
        *,
        run_id: str,
        requested_by: str,
        reason_code: str | None,
        reason_text: str | None = None,
    ) -> dict:
        return self._mcp_store.create_retry_request(
            request_id=str(uuid4()),
            run_id=run_id,
            requested_by=requested_by,
            reason_code=reason_code,
            reason_text=reason_text,
        )

    def list_retry_requests(self, run_id: str, limit: int = 20) -> list[dict]:
        return self._mcp_store.list_retry_requests(run_id, limit=limit)

    def review_retry_request(
        self,
        *,
        request_id: str,
        reviewer_id: str,
        reviewer_decision: str,
        reviewer_comment: str | None = None,
    ) -> dict | None:
        return self._mcp_store.review_retry_request(
            request_id=request_id,
            reviewer_id=reviewer_id,
            reviewer_decision=reviewer_decision,
            reviewer_comment=reviewer_comment,
        )
