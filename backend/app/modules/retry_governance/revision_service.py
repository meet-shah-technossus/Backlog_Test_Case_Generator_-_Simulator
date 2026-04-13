from __future__ import annotations

from app.infrastructure.store import store


class RetryRevisionService:
    def get_revisions(self, *, run_scope: str, run_id: str, include_history: bool) -> dict:
        normalized_scope = str(run_scope or "").strip().lower()
        active = self._get_active_artifact(normalized_scope, run_id)
        if active is None:
            raise ValueError(f"No artifacts found for scope '{normalized_scope}' and run '{run_id}'")

        history = self._list_artifacts(normalized_scope, run_id) if include_history else []
        return {
            "run_scope": normalized_scope,
            "run_id": run_id,
            "active_revision": active,
            "history": history,
        }

    def promote_revision(
        self,
        *,
        run_scope: str,
        run_id: str,
        artifact_version: int,
        actor: str,
        reason: str | None,
    ) -> dict:
        normalized_scope = str(run_scope or "").strip().lower()
        promoted = self._promote_artifact(normalized_scope, run_id, artifact_version)
        if promoted is None:
            raise ValueError(
                f"Artifact version '{artifact_version}' not found for scope '{normalized_scope}' and run '{run_id}'"
            )

        return {
            "run_scope": normalized_scope,
            "run_id": run_id,
            "active_revision": promoted,
            "actor": actor,
            "reason": reason,
        }

    @staticmethod
    def _get_active_artifact(run_scope: str, run_id: str) -> dict | None:
        if run_scope == "agent1":
            return store.get_agent1_latest_artifact(run_id)
        if run_scope == "agent2":
            return store.get_agent2_latest_artifact(run_id)
        if run_scope == "agent3":
            return store.get_agent3_latest_artifact(run_id)
        if run_scope == "agent4":
            return store.get_agent4_latest_artifact(run_id)
        if run_scope == "agent5":
            artifacts = store.get_agent5_artifacts(run_id)
            return artifacts[0] if artifacts else None
        raise ValueError(f"Unsupported run scope '{run_scope}'")

    @staticmethod
    def _list_artifacts(run_scope: str, run_id: str) -> list[dict]:
        if run_scope == "agent1":
            return store.get_agent1_artifacts(run_id)
        if run_scope == "agent2":
            return store.get_agent2_artifacts(run_id)
        if run_scope == "agent3":
            return store.get_agent3_artifacts(run_id)
        if run_scope == "agent4":
            return store.get_agent4_artifacts(run_id)
        if run_scope == "agent5":
            return store.get_agent5_artifacts(run_id)
        raise ValueError(f"Unsupported run scope '{run_scope}'")

    @staticmethod
    def _promote_artifact(run_scope: str, run_id: str, artifact_version: int) -> dict | None:
        version = int(artifact_version)
        if run_scope == "agent1":
            return store.set_agent1_active_artifact_version(run_id=run_id, artifact_version=version)
        if run_scope == "agent2":
            return store.set_agent2_active_artifact_version(run_id=run_id, artifact_version=version)
        if run_scope == "agent3":
            return store.set_agent3_active_artifact_version(run_id=run_id, artifact_version=version)
        if run_scope == "agent4":
            return store.set_agent4_active_artifact_version(run_id=run_id, artifact_version=version)
        if run_scope == "agent5":
            return store.set_agent5_active_artifact_version(agent5_run_id=run_id, artifact_version=version)
        raise ValueError(f"Unsupported run scope '{run_scope}'")
