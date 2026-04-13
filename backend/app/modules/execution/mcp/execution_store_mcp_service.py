from __future__ import annotations

from app.infrastructure.store import store


class ExecutionStoreMCPService:
    def create_execution_run(self, **kwargs) -> dict:
        return store.create_execution_run(**kwargs)

    def update_execution_run_state(self, **kwargs) -> None:
        store.update_execution_run_state(**kwargs)

    def mark_execution_run_running(self, **kwargs) -> None:
        store.mark_execution_run_running(**kwargs)

    def get_execution_run(self, execution_run_id: str) -> dict | None:
        return store.get_execution_run(execution_run_id)

    def list_execution_runs_for_agent4_run(self, source_agent4_run_id: str, limit: int = 50) -> list[dict]:
        return store.list_execution_runs_for_agent4_run(source_agent4_run_id=source_agent4_run_id, limit=limit)

    def claim_next_queued_execution_run(self) -> dict | None:
        return store.claim_next_queued_execution_run()

    def recover_stale_execution_runs(self, *, ttl_seconds: int) -> list[str]:
        return store.recover_stale_execution_runs(ttl_seconds=ttl_seconds)

    def expire_pending_execution_runs(self, *, ttl_seconds: int) -> list[str]:
        return store.expire_pending_execution_runs(ttl_seconds=ttl_seconds)
