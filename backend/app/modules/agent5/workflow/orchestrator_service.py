from __future__ import annotations

from app.modules.agent5.db.run_repository import Agent5RunRepository
from app.modules.agent5.state_machine import AGENT5_COMMAND_TRANSITIONS, Agent5StateMachine
from app.modules.agent5.workflow.persistence_service import Agent5PersistenceService


STATE_TO_STAGE = {
    "queued": "a5_persistence_initialized",
    "running": "a5_execution_running",
    "paused": "a5_execution_paused",
    "canceled": "a5_canceled",
    "execution_completed": "a5_execution_completed",
    "analysis_pending": "a5_analysis_pending",
    "gate7_pending": "a5_gate7_pending",
    "gate7_approved": "a5_gate7_approved",
    "writeback_pending": "a5_writeback_pending",
    "gate8_pending": "a5_gate8_pending",
    "completed": "a5_completed",
    "failed": "a5_failed",
}


class Agent5OrchestratorService:
    def __init__(
        self,
        run_repo: Agent5RunRepository,
        persistence_service: Agent5PersistenceService,
    ) -> None:
        self._run_repo = run_repo
        self._persistence_service = persistence_service
        self._state_machine = Agent5StateMachine()

    def get_orchestration_snapshot(self, *, agent5_run_id: str) -> dict:
        run = self._run_repo.get_run(agent5_run_id)
        if not run:
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")

        commands = self._commands_for_state(str(run.get("state") or ""))
        blocked_reasons = self._blocked_command_reasons(run=run)
        available_commands = [command for command in commands if command not in blocked_reasons]
        blocked_commands = [
            {
                "command": command,
                "reason": blocked_reasons[command],
            }
            for command in commands
            if command in blocked_reasons
        ]

        return {
            "agent5_run_id": str(run.get("agent5_run_id") or ""),
            "state": str(run.get("state") or ""),
            "stage": str(run.get("stage") or ""),
            "available_commands": available_commands,
            "blocked_commands": blocked_commands,
            "can_advance_to_gate7_pending": str(run.get("state") or "") in {"execution_completed", "analysis_pending", "gate7_pending"},
            "phase": "A5.5",
        }

    def apply_command(
        self,
        *,
        agent5_run_id: str,
        command: str,
        actor: str,
        context: dict | None = None,
    ) -> dict:
        run = self._run_repo.get_run(agent5_run_id)
        if not run:
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")

        from_state = str(run.get("state") or "")
        if self._is_duplicate_command(
            agent5_run_id=agent5_run_id,
            command=command,
            from_state=from_state,
            actor=actor,
        ):
            return self._persistence_service.get_run_snapshot(agent5_run_id)

        check = self._state_machine.validate_transition(
            from_state=from_state,
            command=command,
            actor=actor,
            context=context,
        )
        if not check.allowed:
            raise ValueError(f"Transition rejected: {check.reason}")

        blocked_reasons = self._blocked_command_reasons(run=run)
        if check.command in blocked_reasons:
            raise ValueError(f"Transition rejected: {blocked_reasons[check.command]}")

        next_stage = STATE_TO_STAGE.get(check.to_state, run.get("stage") or "a5_unknown")
        self._run_repo.update_state(
            agent5_run_id=agent5_run_id,
            state=check.to_state,
            stage=str(next_stage),
        )
        self._run_repo.add_artifact(
            agent5_run_id=agent5_run_id,
            artifact_type="state_transition_audit",
            artifact=check.audit_event,
        )
        self._run_repo.add_timeline_event(
            agent5_run_id=agent5_run_id,
            stage=str(next_stage),
            action="command_applied",
            actor=actor,
            metadata={
                "command": check.command,
                "from_state": check.from_state,
                "to_state": check.to_state,
                "context": context or {},
            },
        )
        return self._persistence_service.get_run_snapshot(agent5_run_id)

    def advance_to_gate7_pending(
        self,
        *,
        agent5_run_id: str,
        actor: str,
        context: dict | None = None,
    ) -> dict:
        run = self._run_repo.get_run(agent5_run_id)
        if not run:
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")

        state = str(run.get("state") or "")
        if state == "gate7_pending":
            return self._persistence_service.get_run_snapshot(agent5_run_id)

        sequence_map = {
            "execution_completed": ("begin_analysis", "submit_gate7"),
            "analysis_pending": ("submit_gate7",),
        }
        commands = sequence_map.get(state)
        if not commands:
            raise ValueError(
                "advance_to_gate7_pending requires state 'execution_completed' or 'analysis_pending'"
            )

        snapshot: dict | None = None
        for command in commands:
            snapshot = self.apply_command(
                agent5_run_id=agent5_run_id,
                command=command,
                actor=actor,
                context=context,
            )
        return snapshot or self._persistence_service.get_run_snapshot(agent5_run_id)

    def _commands_for_state(self, state: str) -> list[str]:
        allowed_commands: list[str] = []
        for command, mapping in AGENT5_COMMAND_TRANSITIONS.items():
            if state in mapping:
                allowed_commands.append(command)
        return allowed_commands

    def _blocked_command_reasons(self, *, run: dict) -> dict[str, str]:
        blocked: dict[str, str] = {}

        stage7_analysis = run.get("stage7_analysis") if isinstance(run.get("stage7_analysis"), dict) else {}
        gate7_decision = run.get("gate7_decision") if isinstance(run.get("gate7_decision"), dict) else {}
        stage8_writeback = run.get("stage8_writeback") if isinstance(run.get("stage8_writeback"), dict) else {}
        gate8_decision = run.get("gate8_decision") if isinstance(run.get("gate8_decision"), dict) else {}

        if not stage7_analysis:
            blocked["submit_gate7"] = "stage7_analysis payload is required before submit_gate7"

        gate7_value = str(gate7_decision.get("decision") or "").strip().lower()
        if gate7_value not in {"approve", "approved", "gate7_approved"}:
            blocked["gate7_approve"] = "gate7_decision.decision must indicate approval before gate7_approve"
            blocked["start_writeback"] = "gate7_decision approval is required before start_writeback"

        if not stage8_writeback:
            blocked["submit_gate8"] = "stage8_writeback payload is required before submit_gate8"

        gate8_value = str(gate8_decision.get("decision") or "").strip().lower()
        if gate8_value not in {"confirm", "confirmed", "approve", "approved", "gate8_confirmed"}:
            blocked["gate8_confirm"] = "gate8_decision.decision must indicate confirmation before gate8_confirm"

        return blocked

    def _is_duplicate_command(
        self,
        *,
        agent5_run_id: str,
        command: str,
        from_state: str,
        actor: str,
    ) -> bool:
        events = self._run_repo.get_timeline_events(agent5_run_id, ascending=False)
        if not events:
            return False

        latest = events[0]
        if str(latest.get("action") or "") != "command_applied":
            return False

        metadata = latest.get("metadata") if isinstance(latest.get("metadata"), dict) else {}
        latest_command = str(metadata.get("command") or "")
        latest_from_state = str(metadata.get("from_state") or "")
        latest_actor = str(latest.get("actor") or "") or str(latest.get("actor") or "")

        return latest_command == str(command) and latest_from_state == str(from_state) and (
            latest_actor == str(actor) or not latest_actor
        )