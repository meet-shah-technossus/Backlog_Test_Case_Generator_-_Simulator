from __future__ import annotations

from uuid import uuid4

from app.modules.agent1.mcp.run_store_mcp_service import Agent1RunStoreMCPService


class Agent1RunRepository:
    def __init__(self, mcp_store: Agent1RunStoreMCPService | None = None):
        self._mcp_store = mcp_store or Agent1RunStoreMCPService()

    def create_run(
        self,
        *,
        run_id: str,
        backlog_item_id: str,
        trace_id: str,
        state: str,
        source_type: str | None,
        source_ref: str | None,
    ) -> None:
        self._mcp_store.upsert_run(
            run_id=run_id,
            backlog_item_id=backlog_item_id,
            trace_id=trace_id,
            state=state,
            source_type=source_type,
            source_ref=source_ref,
        )

    def update_state(
        self,
        *,
        run_id: str,
        backlog_item_id: str,
        trace_id: str,
        state: str,
        source_type: str | None,
        source_ref: str | None,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        self._mcp_store.upsert_run(
            run_id=run_id,
            backlog_item_id=backlog_item_id,
            trace_id=trace_id,
            state=state,
            source_type=source_type,
            source_ref=source_ref,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
        )

    def get_run(self, run_id: str) -> dict | None:
        return self._mcp_store.get_run(run_id)

    def list_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        return self._mcp_store.list_runs_for_backlog_item(backlog_item_id, limit=limit)

    def add_artifact(self, *, run_id: str, backlog_item_id: str, artifact: dict) -> int:
        return self._mcp_store.add_artifact(
            run_id=run_id,
            backlog_item_id=backlog_item_id,
            artifact=artifact,
        )

    def get_latest_artifact(self, run_id: str) -> dict | None:
        return self._mcp_store.get_latest_artifact(run_id)

    def list_artifacts(self, run_id: str) -> list[dict]:
        return self._mcp_store.list_artifacts(run_id)

    def add_review(
        self,
        *,
        run_id: str,
        stage: str,
        decision: str,
        reason_code: str | None,
        reviewer_id: str,
        edited_payload: dict | None = None,
    ) -> None:
        self._mcp_store.add_review(
            run_id=run_id,
            stage=stage,
            decision=decision,
            reason_code=reason_code,
            reviewer_id=reviewer_id,
            edited_payload=edited_payload,
        )

    def list_reviews(self, run_id: str) -> list[dict]:
        return self._mcp_store.list_reviews(run_id)

    def add_handoff(
        self,
        *,
        run_id: str,
        message_id: str,
        from_agent: str,
        to_agent: str,
        task_type: str,
        contract_version: str,
        payload: dict,
        delivery_status: str,
    ) -> None:
        self._mcp_store.add_handoff(
            run_id=run_id,
            message_id=message_id,
            from_agent=from_agent,
            to_agent=to_agent,
            task_type=task_type,
            contract_version=contract_version,
            payload=payload,
            delivery_status=delivery_status,
        )

    def list_handoffs(self, run_id: str) -> list[dict]:
        return self._mcp_store.list_handoffs(run_id)

    def get_latest_handoff(self, run_id: str) -> dict | None:
        handoffs = self.list_handoffs(run_id)
        return handoffs[0] if handoffs else None

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

    def list_audit_events(self, run_id: str) -> list[dict]:
        return self._mcp_store.list_audit_events(run_id)

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
