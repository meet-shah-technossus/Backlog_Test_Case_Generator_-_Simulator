from __future__ import annotations

from app.core.container import AppContainer
from app.infrastructure.store import store


SUPPORTED_RETRY_EXECUTION_SCOPES = {"agent1", "agent2", "agent3", "agent4", "agent5"}


class RetryGovernanceExecutionService:
    async def execute_approved_retry(
        self,
        *,
        request_id: str,
        actor: str,
        container: AppContainer,
    ) -> dict:
        request = store.get_retry_governance_request(request_id)
        if not request:
            raise ValueError(f"Retry request '{request_id}' not found")

        if str(request.get("status") or "") != "retry_approved":
            raise ValueError("Retry request must be approved before execution")

        run_scope = str(request.get("run_scope") or "").strip().lower()
        run_id = str(request.get("run_id") or "").strip()
        if not run_scope or not run_id:
            raise ValueError("Retry request is missing run scope or run id")

        store.update_retry_governance_status(
            request_id=request_id,
            status="retry_running",
            actor=actor,
            action="retry_execution_started",
            metadata={"run_scope": run_scope, "run_id": run_id},
        )

        try:
            result = await self._execute_scope_retry(
                run_scope=run_scope,
                run_id=run_id,
                container=container,
            )
            store.update_retry_governance_status(
                request_id=request_id,
                status="retry_completed",
                actor=actor,
                action="retry_execution_completed",
                metadata={"run_scope": run_scope, "run_id": run_id},
            )
            return {
                "request": store.get_retry_governance_request(request_id) or {},
                "run_scope": run_scope,
                "run_id": run_id,
                "result": result,
            }
        except Exception as exc:
            store.update_retry_governance_status(
                request_id=request_id,
                status="retry_failed",
                actor=actor,
                action="retry_execution_failed",
                metadata={
                    "run_scope": run_scope,
                    "run_id": run_id,
                    "error": str(exc),
                },
            )
            raise

    async def _execute_scope_retry(self, *, run_scope: str, run_id: str, container: AppContainer) -> dict:
        if run_scope == "agent1":
            orchestrator = container.get_agent1_orchestrator()
            return await orchestrator.generate(run_id=run_id, model=None)

        if run_scope == "agent2":
            orchestrator = container.get_agent2_orchestrator()
            return await orchestrator.generate(run_id=run_id, model=None)

        if run_scope == "agent3":
            orchestrator = container.get_agent3_orchestrator()
            context_result = orchestrator.assemble_context(run_id)
            selector_result = orchestrator.generate_phase4_selectors(run_id)
            return {
                "context": context_result,
                "selectors": selector_result,
            }

        if run_scope == "agent4":
            orchestrator = container.get_agent4_orchestrator()
            plan_result = orchestrator.plan_phase4_scripts(run_id)
            generate_result = orchestrator.generate_phase5_scripts(run_id)
            return {
                "plan": plan_result,
                "generate": generate_result,
            }

        if run_scope == "agent5":
            reliability_service = container.get_agent5_reliability_service()
            persistence_service = container.get_agent5_persistence_service()
            analysis_service = container.get_agent5_analysis_service()
            writeback_service = container.get_agent5_writeback_service()

            snapshot = persistence_service.get_run_snapshot(run_id)
            run = snapshot.get("run") or {}
            state = str(run.get("state") or "")

            if state == "failed":
                snapshot = reliability_service.retry_failed_run(agent5_run_id=run_id, actor="retry-governance")
                run = snapshot.get("run") or {}
                state = str(run.get("state") or "")

            result: dict = {
                "recovered": state != "failed",
                "state": state,
            }

            if state in {"analysis_pending", "execution_completed", "gate7_pending"}:
                snapshot = analysis_service.generate_stage7_analysis(
                    agent5_run_id=run_id,
                    actor="retry-governance",
                    force_regenerate=True,
                )
                result["analysis"] = snapshot

            latest_run = (snapshot or {}).get("run") or {}
            latest_state = str(latest_run.get("state") or state)
            if latest_state in {"writeback_pending", "gate8_pending", "gate7_approved"}:
                snapshot = writeback_service.generate_writeback(
                    agent5_run_id=run_id,
                    actor="retry-governance",
                    idempotency_key=f"retry-governance:{run_id}",
                    force_regenerate=True,
                )
                result["writeback"] = snapshot

            return result

        raise ValueError(f"Unsupported run scope '{run_scope}' for retry execution")
