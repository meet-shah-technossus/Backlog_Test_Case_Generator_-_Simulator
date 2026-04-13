from __future__ import annotations

from app.infrastructure.store import store


class Agent5RunStoreMCPService:
    def create_run(self, **kwargs) -> dict:
        return store.create_agent5_run(**kwargs)

    def update_state(self, **kwargs) -> None:
        store.update_agent5_run_state(**kwargs)

    def set_payloads(self, **kwargs) -> None:
        store.set_agent5_run_payloads(**kwargs)

    def get_run(self, agent5_run_id: str) -> dict | None:
        return store.get_agent5_run(agent5_run_id)

    def list_runs_for_agent4_run(self, source_agent4_run_id: str, limit: int = 50) -> list[dict]:
        return store.list_agent5_runs_for_agent4_run(source_agent4_run_id=source_agent4_run_id, limit=limit)

    def list_runs_by_states(
        self,
        *,
        states: list[str],
        older_than_seconds: int,
        limit: int = 100,
    ) -> list[dict]:
        return store.list_agent5_runs_by_states(
            states=states,
            older_than_seconds=older_than_seconds,
            limit=limit,
        )

    def add_artifact(self, **kwargs) -> None:
        store.add_agent5_artifact(**kwargs)

    def get_artifacts(self, agent5_run_id: str) -> list[dict]:
        return store.get_agent5_artifacts(agent5_run_id)

    def get_next_artifact_version(self, agent5_run_id: str) -> int:
        return store.get_agent5_next_artifact_version(agent5_run_id)

    def add_timeline_event(self, **kwargs) -> None:
        store.add_agent5_timeline_event(**kwargs)

    def list_timeline_events(self, agent5_run_id: str, *, ascending: bool = True) -> list[dict]:
        return store.get_agent5_timeline_events(agent5_run_id, ascending=ascending)
