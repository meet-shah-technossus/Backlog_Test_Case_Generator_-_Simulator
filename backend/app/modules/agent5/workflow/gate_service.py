from __future__ import annotations

from datetime import datetime, timezone

from app.modules.agent5.db.run_repository import Agent5RunRepository
from app.modules.agent5.workflow.orchestrator_service import Agent5OrchestratorService
from app.modules.agent5.workflow.persistence_service import Agent5PersistenceService


class Agent5GateService:
    def __init__(
        self,
        run_repo: Agent5RunRepository,
        persistence_service: Agent5PersistenceService,
        orchestrator_service: Agent5OrchestratorService,
    ) -> None:
        self._run_repo = run_repo
        self._persistence_service = persistence_service
        self._orchestrator_service = orchestrator_service

    def submit_gate7_decision(
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
        if state != "gate7_pending":
            raise ValueError("Gate7 decision can be submitted only when state is gate7_pending")

        normalized_decision = str(decision or "").strip().lower()
        if normalized_decision not in {"approve", "request_revision", "reject"}:
            raise ValueError("Gate7 decision must be one of: approve, request_revision, reject")

        payload = {
            "agent5_run_id": agent5_run_id,
            "decision": normalized_decision,
            "reviewer_id": str(reviewer_id or "").strip() or "operator",
            "reason_code": str(reason_code or "unspecified").strip() or "unspecified",
            "comment": str(comment or "").strip(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "phase": "A5.8",
        }

        self._persistence_service.persist_gate7_decision(
            agent5_run_id=agent5_run_id,
            decision=payload,
            actor=payload["reviewer_id"],
        )

        if normalized_decision == "approve":
            command = "gate7_approve"
        elif normalized_decision == "request_revision":
            command = "gate7_request_revision"
        else:
            command = "fail_gate7"

        return self._orchestrator_service.apply_command(
            agent5_run_id=agent5_run_id,
            command=command,
            actor=payload["reviewer_id"],
            context={
                "reason_code": payload["reason_code"],
                "comment": payload["comment"],
                "decision": normalized_decision,
                "phase": "A5.8",
            },
        )
