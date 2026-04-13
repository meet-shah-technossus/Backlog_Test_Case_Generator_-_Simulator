from __future__ import annotations

from datetime import datetime, timezone

from app.modules.agent5.db.run_repository import Agent5RunRepository
from app.modules.agent5.workflow.orchestrator_service import Agent5OrchestratorService
from app.modules.agent5.workflow.persistence_service import Agent5PersistenceService


class Agent5Gate8Service:
    def __init__(
        self,
        run_repo: Agent5RunRepository,
        persistence_service: Agent5PersistenceService,
        orchestrator_service: Agent5OrchestratorService,
    ) -> None:
        self._run_repo = run_repo
        self._persistence_service = persistence_service
        self._orchestrator_service = orchestrator_service

    def submit_gate8_decision(
        self,
        *,
        agent5_run_id: str,
        reviewer_id: str,
        decision: str,
        reason_code: str,
        comment: str | None,
    ) -> dict:
        run = self._run_repo.get_run(agent5_run_id)
        if not run:
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")

        state = str(run.get("state") or "")
        if state != "gate8_pending":
            raise ValueError("Gate8 decision can be submitted only when state is gate8_pending")

        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in {"confirm", "followup", "reject"}:
            raise ValueError("Gate8 decision must be one of: confirm, followup, reject")

        payload = {
            "agent5_run_id": agent5_run_id,
            "decision": normalized_decision,
            "reviewer_id": str(reviewer_id or "").strip() or "operator",
            "reason_code": str(reason_code or "unspecified").strip() or "unspecified",
            "comment": str(comment or "").strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "A5.10",
        }

        self._persistence_service.persist_gate8_decision(
            agent5_run_id=agent5_run_id,
            decision=payload,
            actor=payload["reviewer_id"],
        )

        if normalized_decision == "confirm":
            command = "gate8_confirm"
        elif normalized_decision == "followup":
            command = "gate8_followup"
        else:
            command = "fail_gate8"

        return self._orchestrator_service.apply_command(
            agent5_run_id=agent5_run_id,
            command=command,
            actor=payload["reviewer_id"],
            context={
                "phase": "A5.10",
                "decision": normalized_decision,
                "reason_code": payload["reason_code"],
                "comment": payload["comment"],
            },
        )
