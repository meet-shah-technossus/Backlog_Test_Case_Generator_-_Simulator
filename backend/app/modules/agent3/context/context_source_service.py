from __future__ import annotations

from app.infrastructure.store import store


class Agent3ContextSourceService:
    """Read-only source adapter for Phase 3 context assembly."""

    def get_agent2_run(self, run_id: str) -> dict | None:
        return store.get_agent2_run(run_id)

    def get_agent2_latest_artifact(self, run_id: str) -> dict | None:
        return store.get_agent2_latest_artifact(run_id)

    def get_agent2_inbox(self, message_id: str) -> dict | None:
        return store.get_agent2_inbox(message_id)
