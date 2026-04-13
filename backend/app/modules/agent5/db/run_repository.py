from __future__ import annotations

from app.modules.agent5.mcp.run_store_mcp_service import Agent5RunStoreMCPService


class Agent5RunRepository:
    def __init__(self, mcp_store: Agent5RunStoreMCPService | None = None):
        self._mcp_store = mcp_store or Agent5RunStoreMCPService()

    def create_run(
        self,
        *,
        agent5_run_id: str,
        source_agent4_run_id: str,
        source_execution_run_id: str | None,
        backlog_item_id: str | None,
        trace_id: str,
        state: str,
        stage: str,
        request_payload: dict | None = None,
    ) -> dict:
        return self._mcp_store.create_run(
            agent5_run_id=agent5_run_id,
            source_agent4_run_id=source_agent4_run_id,
            source_execution_run_id=source_execution_run_id,
            backlog_item_id=backlog_item_id,
            trace_id=trace_id,
            state=state,
            stage=stage,
            request_payload=request_payload,
        )

    def update_state(
        self,
        *,
        agent5_run_id: str,
        state: str,
        stage: str,
        last_error_code: str | None = None,
        last_error_message: str | None = None,
    ) -> None:
        self._mcp_store.update_state(
            agent5_run_id=agent5_run_id,
            state=state,
            stage=stage,
            last_error_code=last_error_code,
            last_error_message=last_error_message,
        )

    def set_payloads(
        self,
        *,
        agent5_run_id: str,
        execution_summary: dict | None = None,
        step_evidence_refs: list[dict] | None = None,
        stage7_analysis: dict | None = None,
        gate7_decision: dict | None = None,
        stage8_writeback: dict | None = None,
        gate8_decision: dict | None = None,
    ) -> None:
        self._mcp_store.set_payloads(
            agent5_run_id=agent5_run_id,
            execution_summary=execution_summary,
            step_evidence_refs=step_evidence_refs,
            stage7_analysis=stage7_analysis,
            gate7_decision=gate7_decision,
            stage8_writeback=stage8_writeback,
            gate8_decision=gate8_decision,
        )

    def get_run(self, agent5_run_id: str) -> dict | None:
        return self._mcp_store.get_run(agent5_run_id)

    def list_runs_for_agent4_run(self, source_agent4_run_id: str, limit: int = 50) -> list[dict]:
        return self._mcp_store.list_runs_for_agent4_run(source_agent4_run_id=source_agent4_run_id, limit=limit)

    def list_runs_by_states(
        self,
        *,
        states: list[str],
        older_than_seconds: int,
        limit: int = 100,
    ) -> list[dict]:
        return self._mcp_store.list_runs_by_states(
            states=states,
            older_than_seconds=older_than_seconds,
            limit=limit,
        )

    def add_artifact(self, *, agent5_run_id: str, artifact_type: str, artifact: dict) -> int:
        version = self._mcp_store.get_next_artifact_version(agent5_run_id)
        self._mcp_store.add_artifact(
            agent5_run_id=agent5_run_id,
            artifact_version=version,
            artifact_type=artifact_type,
            artifact=artifact,
        )
        return version

    def get_artifacts(self, agent5_run_id: str) -> list[dict]:
        return self._mcp_store.get_artifacts(agent5_run_id)

    def add_timeline_event(
        self,
        *,
        agent5_run_id: str,
        stage: str,
        action: str,
        actor: str,
        metadata: dict | None = None,
    ) -> None:
        self._mcp_store.add_timeline_event(
            agent5_run_id=agent5_run_id,
            stage=stage,
            action=action,
            actor=actor,
            metadata=metadata,
        )

    def get_timeline_events(self, agent5_run_id: str, *, ascending: bool = True) -> list[dict]:
        return self._mcp_store.list_timeline_events(agent5_run_id, ascending=ascending)
