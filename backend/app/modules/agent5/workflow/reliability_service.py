from __future__ import annotations

from app.modules.agent5.db.run_repository import Agent5RunRepository
from app.modules.agent5.workflow.persistence_service import Agent5PersistenceService


NON_TERMINAL_RECOVERY_STATES = [
    "running",
    "paused",
    "execution_completed",
    "analysis_pending",
    "gate7_pending",
    "gate7_approved",
    "writeback_pending",
    "gate8_pending",
]


class Agent5ReliabilityService:
    def __init__(
        self,
        run_repo: Agent5RunRepository,
        persistence_service: Agent5PersistenceService,
    ) -> None:
        self._run_repo = run_repo
        self._persistence_service = persistence_service

    def recover_stale_runs(
        self,
        *,
        actor: str,
        older_than_seconds: int,
        limit: int = 100,
    ) -> dict:
        stale_runs = self._run_repo.list_runs_by_states(
            states=NON_TERMINAL_RECOVERY_STATES,
            older_than_seconds=max(60, int(older_than_seconds)),
            limit=max(1, int(limit)),
        )

        recovered: list[dict] = []
        for run in stale_runs:
            run_id = str(run.get("agent5_run_id") or "")
            if not run_id:
                continue

            self._run_repo.update_state(
                agent5_run_id=run_id,
                state="failed",
                stage="a5_recovered_stale",
                last_error_code="stale_run_timeout",
                last_error_message=f"Recovered stale non-terminal run older than {older_than_seconds} seconds",
            )
            self._run_repo.add_timeline_event(
                agent5_run_id=run_id,
                stage="a5_recovered_stale",
                action="stale_recovered",
                actor=actor,
                metadata={
                    "older_than_seconds": older_than_seconds,
                    "previous_state": str(run.get("state") or ""),
                    "phase": "A5.12",
                },
            )
            recovered.append({
                "agent5_run_id": run_id,
                "previous_state": str(run.get("state") or ""),
                "new_state": "failed",
                "new_stage": "a5_recovered_stale",
            })

        return {
            "phase": "A5.12",
            "recovered_count": len(recovered),
            "recovered_runs": recovered,
        }

    def retry_failed_run(self, *, agent5_run_id: str, actor: str) -> dict:
        run = self._run_repo.get_run(agent5_run_id)
        if not run:
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")

        state = str(run.get("state") or "")
        if state != "failed":
            raise ValueError("Retry is allowed only when run state is failed")

        stage = str(run.get("stage") or "")
        next_state, next_stage = self._retry_target(stage=stage)
        self._run_repo.update_state(
            agent5_run_id=agent5_run_id,
            state=next_state,
            stage=next_stage,
            last_error_code=None,
            last_error_message=None,
        )
        self._run_repo.add_timeline_event(
            agent5_run_id=agent5_run_id,
            stage=next_stage,
            action="retry_requested",
            actor=actor,
            metadata={
                "previous_stage": stage,
                "next_state": next_state,
                "phase": "A5.12",
            },
        )
        return self._persistence_service.get_run_snapshot(agent5_run_id)

    @staticmethod
    def _retry_target(*, stage: str) -> tuple[str, str]:
        normalized = str(stage or "").strip().lower()
        if "execution" in normalized:
            return ("running", "a5_execution_running")
        if "analysis" in normalized:
            return ("analysis_pending", "a5_analysis_pending")
        if "gate7" in normalized:
            return ("gate7_pending", "a5_gate7_pending")
        if "writeback" in normalized:
            return ("writeback_pending", "a5_writeback_pending")
        if "gate8" in normalized:
            return ("gate8_pending", "a5_gate8_pending")
        return ("analysis_pending", "a5_analysis_pending")
