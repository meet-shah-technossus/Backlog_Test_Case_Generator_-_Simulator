from __future__ import annotations

from app.infrastructure.store import store


class Agent4RunStoreMCPService:
    """MCP data-plane adapter for Agent4 run and audit persistence."""

    def create_run_from_inbox(self, **kwargs) -> tuple[dict, bool]:
        return store.create_agent4_run_from_inbox(**kwargs)

    def get_run(self, run_id: str) -> dict | None:
        return store.get_agent4_run(run_id)

    def list_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        return store.list_agent4_runs_for_backlog_item(backlog_item_id, limit=limit)

    def update_state(self, **kwargs) -> None:
        store.upsert_agent4_run_state(**kwargs)

    def add_artifact(self, *, run_id: str, artifact_version: int, artifact: dict) -> None:
        store.add_agent4_artifact(
            run_id=run_id,
            artifact_version=artifact_version,
            artifact=artifact,
        )

    def get_latest_artifact(self, run_id: str) -> dict | None:
        return store.get_agent4_latest_artifact(run_id)

    def get_artifacts(self, run_id: str) -> list[dict]:
        return store.get_agent4_artifacts(run_id)

    def get_next_artifact_version(self, run_id: str) -> int:
        return store.get_agent4_next_artifact_version(run_id)

    def add_audit_event(self, **kwargs) -> None:
        store.add_agent4_audit_event(**kwargs)

    def list_audit_events(self, run_id: str, *, ascending: bool = False) -> list[dict]:
        return store.get_agent4_audit_events(run_id, ascending=ascending)
