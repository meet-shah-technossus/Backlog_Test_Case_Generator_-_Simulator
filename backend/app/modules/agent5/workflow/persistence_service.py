from __future__ import annotations

from uuid import uuid4

from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent5.db.run_repository import Agent5RunRepository
from app.modules.execution.db.execution_run_repository import ExecutionRunRepository


class Agent5PersistenceService:
    def __init__(
        self,
        run_repo: Agent5RunRepository,
        agent4_run_repo: Agent4RunRepository,
        execution_repo: ExecutionRunRepository,
    ) -> None:
        self._run_repo = run_repo
        self._agent4_run_repo = agent4_run_repo
        self._execution_repo = execution_repo

    def create_run(
        self,
        *,
        source_agent4_run_id: str,
        source_execution_run_id: str | None,
        created_by: str,
        reason: str | None = None,
    ) -> dict:
        agent4_run = self._agent4_run_repo.get_run(source_agent4_run_id)
        if not agent4_run:
            raise ValueError(f"Agent4 run '{source_agent4_run_id}' not found")

        execution_snapshot = None
        if source_execution_run_id:
            execution_snapshot = self._execution_repo.get_run(source_execution_run_id)
            if not execution_snapshot:
                raise ValueError(f"Execution run '{source_execution_run_id}' not found")
            linked_agent4_run = str(execution_snapshot.get("source_agent4_run_id") or "")
            if linked_agent4_run != source_agent4_run_id:
                raise ValueError("Execution run does not belong to the selected Agent4 run")

        run_id = str(uuid4())
        trace_id = str(agent4_run.get("trace_id") or f"agent5-{source_agent4_run_id}")

        request_payload = {
            "created_by": created_by,
            "reason": reason,
            "source_agent4_run_id": source_agent4_run_id,
            "source_execution_run_id": source_execution_run_id,
        }

        initial_state, initial_stage = self._resolve_initial_lifecycle_state(execution_snapshot)
        created = self._run_repo.create_run(
            agent5_run_id=run_id,
            source_agent4_run_id=source_agent4_run_id,
            source_execution_run_id=source_execution_run_id,
            backlog_item_id=None,
            trace_id=trace_id,
            state=initial_state,
            stage=initial_stage,
            request_payload=request_payload,
        )

        self._run_repo.add_timeline_event(
            agent5_run_id=run_id,
            stage="a5_persistence_initialized",
            action="run_created",
            actor=created_by,
            metadata={
                "reason": reason,
                "source_agent4_run_id": source_agent4_run_id,
                "source_execution_run_id": source_execution_run_id,
            },
        )

        if execution_snapshot is not None:
            self.persist_execution_snapshot(
                agent5_run_id=run_id,
                execution_snapshot=execution_snapshot,
                actor=created_by,
            )

        return self.get_run_snapshot(run_id)

    def persist_execution_snapshot(
        self,
        *,
        agent5_run_id: str,
        execution_snapshot: dict,
        actor: str,
    ) -> dict:
        raw_result = execution_snapshot.get("result")
        result = raw_result if isinstance(raw_result, dict) else {}

        raw_summary = result.get("summary")
        summary = raw_summary if isinstance(raw_summary, dict) else {}

        raw_integrity = result.get("integrity")
        integrity = raw_integrity if isinstance(raw_integrity, dict) else {}

        raw_evidence_manifest = result.get("evidence")
        evidence_manifest = raw_evidence_manifest if isinstance(raw_evidence_manifest, dict) else {}

        raw_step_evidence = execution_snapshot.get("evidence")
        step_evidence = raw_step_evidence if isinstance(raw_step_evidence, list) else []

        execution_summary = {
            "execution_run_id": execution_snapshot.get("execution_run_id"),
            "state": execution_snapshot.get("state"),
            "stage": execution_snapshot.get("stage"),
            "summary": summary,
            "integrity": integrity,
            "evidence_manifest": evidence_manifest,
            "captured_at": execution_snapshot.get("updated_at"),
        }

        self._run_repo.set_payloads(
            agent5_run_id=agent5_run_id,
            execution_summary=execution_summary,
            step_evidence_refs=step_evidence,
        )
        self._run_repo.add_artifact(
            agent5_run_id=agent5_run_id,
            artifact_type="execution_snapshot",
            artifact={
                "execution_summary": execution_summary,
                "step_evidence_refs": step_evidence,
            },
        )
        self._run_repo.add_timeline_event(
            agent5_run_id=agent5_run_id,
            stage="a5_execution_snapshot_persisted",
            action="execution_snapshot_persisted",
            actor=actor,
            metadata={
                "execution_run_id": execution_snapshot.get("execution_run_id"),
                "step_count": len(step_evidence),
            },
        )
        return self.get_run_snapshot(agent5_run_id)

    def persist_stage7_analysis(self, *, agent5_run_id: str, analysis: dict, actor: str) -> dict:
        self._assert_run_exists(agent5_run_id)
        self._run_repo.set_payloads(agent5_run_id=agent5_run_id, stage7_analysis=analysis)
        self._run_repo.add_artifact(agent5_run_id=agent5_run_id, artifact_type="stage7_analysis", artifact=analysis)
        self._run_repo.add_timeline_event(
            agent5_run_id=agent5_run_id,
            stage="stage7_analysis",
            action="analysis_persisted",
            actor=actor,
            metadata={"keys": sorted(analysis.keys())},
        )
        return self.get_run_snapshot(agent5_run_id)

    def persist_gate7_decision(self, *, agent5_run_id: str, decision: dict, actor: str) -> dict:
        self._assert_run_exists(agent5_run_id)
        self._run_repo.set_payloads(agent5_run_id=agent5_run_id, gate7_decision=decision)
        self._run_repo.add_artifact(agent5_run_id=agent5_run_id, artifact_type="gate7_decision", artifact=decision)
        self._run_repo.add_timeline_event(
            agent5_run_id=agent5_run_id,
            stage="gate7",
            action="decision_persisted",
            actor=actor,
            metadata={"decision": decision.get("decision")},
        )
        return self.get_run_snapshot(agent5_run_id)

    def persist_stage8_writeback(self, *, agent5_run_id: str, writeback: dict, actor: str) -> dict:
        self._assert_run_exists(agent5_run_id)
        self._run_repo.set_payloads(agent5_run_id=agent5_run_id, stage8_writeback=writeback)
        self._run_repo.add_artifact(agent5_run_id=agent5_run_id, artifact_type="stage8_writeback", artifact=writeback)
        self._run_repo.add_timeline_event(
            agent5_run_id=agent5_run_id,
            stage="stage8_writeback",
            action="writeback_persisted",
            actor=actor,
            metadata={"keys": sorted(writeback.keys())},
        )
        return self.get_run_snapshot(agent5_run_id)

    def persist_gate8_decision(self, *, agent5_run_id: str, decision: dict, actor: str) -> dict:
        self._assert_run_exists(agent5_run_id)
        self._run_repo.set_payloads(agent5_run_id=agent5_run_id, gate8_decision=decision)
        self._run_repo.add_artifact(agent5_run_id=agent5_run_id, artifact_type="gate8_decision", artifact=decision)
        self._run_repo.add_timeline_event(
            agent5_run_id=agent5_run_id,
            stage="gate8",
            action="decision_persisted",
            actor=actor,
            metadata={"decision": decision.get("decision")},
        )
        return self.get_run_snapshot(agent5_run_id)

    def get_run_snapshot(self, agent5_run_id: str) -> dict:
        run = self._run_repo.get_run(agent5_run_id)
        if not run:
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")
        return {
            "run": run,
            "artifacts": self._run_repo.get_artifacts(agent5_run_id),
            "timeline": self._run_repo.get_timeline_events(agent5_run_id, ascending=True),
        }

    def list_runs_for_agent4_run(self, source_agent4_run_id: str, limit: int = 50) -> list[dict]:
        return self._run_repo.list_runs_for_agent4_run(source_agent4_run_id=source_agent4_run_id, limit=limit)

    def _assert_run_exists(self, agent5_run_id: str) -> None:
        if not self._run_repo.get_run(agent5_run_id):
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")

    @staticmethod
    def _resolve_initial_lifecycle_state(execution_snapshot: dict | None) -> tuple[str, str]:
        if not execution_snapshot:
            return ("queued", "a5_persistence_initialized")

        execution_state = str(execution_snapshot.get("state") or "").strip().lower()
        mapping = {
            "queued": ("queued", "a5_persistence_initialized"),
            "running": ("running", "a5_execution_running"),
            "paused": ("paused", "a5_execution_paused"),
            "completed": ("execution_completed", "a5_execution_completed"),
            "failed": ("failed", "a5_failed"),
            "canceled": ("canceled", "a5_canceled"),
        }
        return mapping.get(execution_state, ("execution_completed", "a5_execution_completed"))
