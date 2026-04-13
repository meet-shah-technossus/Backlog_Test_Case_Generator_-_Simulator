from __future__ import annotations

from dataclasses import dataclass

AGENT5_STATES = (
    "queued",
    "running",
    "paused",
    "canceled",
    "execution_completed",
    "analysis_pending",
    "gate7_pending",
    "gate7_approved",
    "writeback_pending",
    "gate8_pending",
    "completed",
    "failed",
)

AGENT5_TERMINAL_STATES = ("canceled", "completed", "failed")

AGENT5_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "queued": ("running", "canceled"),
    "running": ("paused", "canceled", "execution_completed", "failed"),
    "paused": ("running", "canceled"),
    "execution_completed": ("analysis_pending",),
    "analysis_pending": ("gate7_pending", "failed"),
    "gate7_pending": ("gate7_approved", "analysis_pending", "failed"),
    "gate7_approved": ("writeback_pending",),
    "writeback_pending": ("gate8_pending", "failed"),
    "gate8_pending": ("completed", "writeback_pending", "failed"),
}

AGENT5_COMMAND_TRANSITIONS: dict[str, dict[str, str]] = {
    "start_execution": {"queued": "running"},
    "pause_execution": {"running": "paused"},
    "resume_execution": {"paused": "running"},
    "cancel_execution": {"queued": "canceled", "running": "canceled", "paused": "canceled"},
    "execution_finished": {"running": "execution_completed"},
    "begin_analysis": {"execution_completed": "analysis_pending"},
    "submit_gate7": {"analysis_pending": "gate7_pending"},
    "gate7_approve": {"gate7_pending": "gate7_approved"},
    "gate7_request_revision": {"gate7_pending": "analysis_pending"},
    "start_writeback": {"gate7_approved": "writeback_pending"},
    "submit_gate8": {"writeback_pending": "gate8_pending"},
    "gate8_confirm": {"gate8_pending": "completed"},
    "gate8_followup": {"gate8_pending": "writeback_pending"},
    "fail_execution": {"running": "failed"},
    "fail_analysis": {"analysis_pending": "failed"},
    "fail_gate7": {"gate7_pending": "failed"},
    "fail_writeback": {"writeback_pending": "failed"},
    "fail_gate8": {"gate8_pending": "failed"},
}


@dataclass(frozen=True)
class TransitionCheck:
    allowed: bool
    from_state: str
    to_state: str
    command: str
    reason: str
    audit_event: dict


class Agent5StateMachine:
    def validate_transition(
        self,
        *,
        from_state: str,
        command: str,
        actor: str,
        context: dict | None = None,
    ) -> TransitionCheck:
        source = str(from_state or "").strip()
        op = str(command or "").strip()
        who = str(actor or "system").strip() or "system"

        if source not in AGENT5_STATES:
            return TransitionCheck(
                allowed=False,
                from_state=source,
                to_state=source,
                command=op,
                reason=f"Unknown from_state '{source}'",
                audit_event=self._build_event(
                    from_state=source,
                    to_state=source,
                    command=op,
                    actor=who,
                    allowed=False,
                    reason=f"unknown_state:{source}",
                    context=context,
                ),
            )

        if source in AGENT5_TERMINAL_STATES:
            return TransitionCheck(
                allowed=False,
                from_state=source,
                to_state=source,
                command=op,
                reason=f"State '{source}' is terminal",
                audit_event=self._build_event(
                    from_state=source,
                    to_state=source,
                    command=op,
                    actor=who,
                    allowed=False,
                    reason=f"terminal_state:{source}",
                    context=context,
                ),
            )

        command_map = AGENT5_COMMAND_TRANSITIONS.get(op)
        if not command_map:
            return TransitionCheck(
                allowed=False,
                from_state=source,
                to_state=source,
                command=op,
                reason=f"Unknown command '{op}'",
                audit_event=self._build_event(
                    from_state=source,
                    to_state=source,
                    command=op,
                    actor=who,
                    allowed=False,
                    reason=f"unknown_command:{op}",
                    context=context,
                ),
            )

        destination = command_map.get(source)
        if destination is None:
            return TransitionCheck(
                allowed=False,
                from_state=source,
                to_state=source,
                command=op,
                reason=f"Command '{op}' is not allowed from state '{source}'",
                audit_event=self._build_event(
                    from_state=source,
                    to_state=source,
                    command=op,
                    actor=who,
                    allowed=False,
                    reason=f"invalid_command_for_state:{op}:{source}",
                    context=context,
                ),
            )

        if destination not in AGENT5_TRANSITIONS.get(source, ()):
            return TransitionCheck(
                allowed=False,
                from_state=source,
                to_state=destination,
                command=op,
                reason=f"Transition '{source} -> {destination}' is not declared",
                audit_event=self._build_event(
                    from_state=source,
                    to_state=destination,
                    command=op,
                    actor=who,
                    allowed=False,
                    reason=f"undeclared_transition:{source}:{destination}",
                    context=context,
                ),
            )

        return TransitionCheck(
            allowed=True,
            from_state=source,
            to_state=destination,
            command=op,
            reason="ok",
            audit_event=self._build_event(
                from_state=source,
                to_state=destination,
                command=op,
                actor=who,
                allowed=True,
                reason="ok",
                context=context,
            ),
        )

    @staticmethod
    def _build_event(
        *,
        from_state: str,
        to_state: str,
        command: str,
        actor: str,
        allowed: bool,
        reason: str,
        context: dict | None,
    ) -> dict:
        return {
            "event_type": "agent5.state_transition",
            "from_state": from_state,
            "to_state": to_state,
            "command": command,
            "actor": actor,
            "allowed": allowed,
            "reason": reason,
            "context": context or {},
        }
