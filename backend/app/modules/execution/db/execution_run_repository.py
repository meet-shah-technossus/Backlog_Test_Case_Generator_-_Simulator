from __future__ import annotations

from app.modules.execution.mcp.execution_store_mcp_service import ExecutionStoreMCPService


class ExecutionRunRepository:
    def __init__(self, mcp_store: ExecutionStoreMCPService | None = None):
        self._mcp_store = mcp_store or ExecutionStoreMCPService()

    def create_run(
        self,
        *,
        execution_run_id: str,
        source_agent4_run_id: str,
        backlog_item_id: str | None,
        trace_id: str,
        state: str,
        stage: str,
        request_payload: dict | None,
        runtime_policy: dict | None,
        max_attempts: int = 1,
    ) -> dict:
        return self._mcp_store.create_execution_run(
            execution_run_id=execution_run_id,
            source_agent4_run_id=source_agent4_run_id,
            backlog_item_id=backlog_item_id,
            trace_id=trace_id,
            state=state,
            stage=stage,
            request_payload=request_payload,
            runtime_policy=runtime_policy,
            max_attempts=max_attempts,
        )

    def mark_running(self, *, execution_run_id: str, stage: str = "phase10_execution_running") -> None:
        self._mcp_store.mark_execution_run_running(
            execution_run_id=execution_run_id,
            stage=stage,
        )

    def update_state(
        self,
        *,
        execution_run_id: str,
        state: str,
        stage: str,
        result_payload: dict | None = None,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        self._mcp_store.update_execution_run_state(
            execution_run_id=execution_run_id,
            state=state,
            stage=stage,
            result_payload=result_payload,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
        )

    def get_run(self, execution_run_id: str) -> dict | None:
        return self._mcp_store.get_execution_run(execution_run_id)

    def list_for_agent4_run(self, source_agent4_run_id: str, limit: int = 50) -> list[dict]:
        return self._mcp_store.list_execution_runs_for_agent4_run(
            source_agent4_run_id=source_agent4_run_id,
            limit=limit,
        )

    def claim_next_queued(self) -> dict | None:
        return self._mcp_store.claim_next_queued_execution_run()

    def recover_stale_runs(self, *, ttl_seconds: int) -> list[str]:
        return self._mcp_store.recover_stale_execution_runs(ttl_seconds=ttl_seconds)

    def expire_pending_runs(self, *, ttl_seconds: int) -> list[str]:
        return self._mcp_store.expire_pending_execution_runs(ttl_seconds=ttl_seconds)
