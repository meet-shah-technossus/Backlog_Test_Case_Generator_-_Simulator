from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.core import config
from app.api.dependencies import AppContainer, get_container
from app.infrastructure.store import store
from app.api.security.operator_auth import (
    require_operator_action,
    require_operator_admin,
    require_operator_view,
    resolve_operator_identity,
)
from app.api.security.operator_incident_policy import operator_incident_policy_service
from app.api.routes.agent4.models import (
    Agent4BlueprintResponse,
    Agent4ConsumeHandoffRequest,
    Agent4CreateRunFromInboxResponse,
    Agent4GateReasonCodesResponse,
    Agent4InboxConsumeResponse,
    Agent4Phase3GateRequest,
    Agent4Phase3GateResponse,
    Agent4Phase3ReadinessResponse,
    Agent4Phase4PlanScriptsResponse,
    Agent4Phase5GenerateScriptsResponse,
    Agent4Phase6ReadinessResponse,
    Agent4Phase6ReviewReasonCodesResponse,
    Agent4Phase6ReviewRequest,
    Agent4Phase6ReviewResponse,
    Agent4Phase7EmitHandoffResponse,
    Agent4Phase8FeedbackReasonCodesResponse,
    Agent4Phase8FeedbackRequest,
    Agent4Phase8FeedbackResponse,
    Agent4Phase9IntegrityResponse,
    Agent4Phase9ObservabilityResponse,
    Agent4Phase10ProfileResponse,
    Agent4Phase10RuntimeCheckResponse,
    Agent4Phase10ExecutionStartRequest,
    Agent4Phase10ExecutionRunRequest,
    Agent4Phase10DispatchRequest,
    Agent4Phase10ExecutionSnapshotResponse,
    Agent4Phase10ExecutionListResponse,
    Agent4Phase10DispatchResponse,
    Agent4Phase10DispatcherStatusResponse,
    Agent4Phase10RecoveryResponse,
    Agent4Phase11QueueProfileResponse,
    Agent4Phase11QueueSnapshotResponse,
    Agent4Phase11QueueItemsResponse,
    Agent4Phase12QueueHealthResponse,
    Agent4Phase12QueueExpireResponse,
    Agent4Phase14QueueAuditResponse,
    Agent4Phase15OperatorWhoAmIResponse,
    Agent4Phase15QueueAuditVerifyResponse,
    Agent4Phase16OperatorSecurityStatusResponse,
    Agent4Phase16OperatorSecurityEventsResponse,
    Agent4Phase17OperatorSecurityHistoryResponse,
    Agent4Phase17OperatorSecuritySummaryResponse,
    Agent4Phase17OperatorAlertTestResponse,
    Agent4Phase19OpenIncidentsResponse,
    Agent4Phase19IncidentLifecycleResponse,
    Agent4Phase20SecurityExportResponse,
    Agent4Phase20SecurityReadinessResponse,
    Agent4RunHistoryResponse,
    Agent4RunSnapshotResponse,
    Agent4StartFromAgent3RunResponse,
)
from app.modules.agent4.contracts.models import Agent4HandoffEnvelope
from app.modules.execution.contracts.models import Phase10Scope

router = APIRouter(prefix="/agent4", tags=["Agent4"])


def _ensure_run_ready_for_phase5(orchestrator, run_id: str) -> None:
    snapshot = orchestrator.get_run_snapshot(run_id)
    run = snapshot.get("run") if isinstance(snapshot, dict) else {}
    state = str((run or {}).get("state") or "")

    if state == "intake_ready":
        orchestrator.submit_phase3_gate(
            run_id=run_id,
            decision="approve",
            gate_mode="quick",
            reviewer_id="system-auto",
            reason_code="manual_override_confirmed",
            auto_retry=True,
        )

    # Phase 4 planning is idempotent and reuses existing blueprint when available.
    orchestrator.plan_phase4_scripts(run_id)


def _find_latest_phase5_script_bundle(snapshot: dict) -> dict | None:
    artifacts = snapshot.get("artifacts") if isinstance(snapshot, dict) else []
    if not isinstance(artifacts, list):
        return None
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_generated_script_bundle":
            return artifact
    return None


def _tokenize_script_bundle(script_bundle: dict) -> list[str]:
    scripts = script_bundle.get("scripts") if isinstance(script_bundle, dict) else []
    if not isinstance(scripts, list):
        return []

    chunks: list[str] = []

    def _chunk_text(value: str, chunk_size: int = 22) -> list[str]:
        text = value or ""
        if not text:
            return []
        return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

    for script in scripts:
        if not isinstance(script, dict):
            continue
        path = str(script.get("path") or "generated.py")
        content = str(script.get("content") or "")
        header = f"\n# FILE: {path}\n"
        body = content if content.endswith("\n") else f"{content}\n"
        chunks.extend(_chunk_text(header, 18))
        chunks.extend(_chunk_text(body, 22))
    return chunks


def _find_latest_phase5_handoff_envelope(snapshot: dict) -> dict | None:
    artifacts = snapshot.get("artifacts") if isinstance(snapshot, dict) else []
    if not isinstance(artifacts, list):
        return None
    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase5_handoff_envelope":
            envelope = artifact.get("envelope")
            if isinstance(envelope, dict):
                return envelope
    return None


@router.get("/blueprint", response_model=Agent4BlueprintResponse)
async def get_agent4_blueprint(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent4_orchestrator()
    return orchestrator.get_blueprint()


@router.post("/inbox/consume", response_model=Agent4InboxConsumeResponse)
async def consume_agent3_handoff(
    request: Agent4ConsumeHandoffRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    envelope = Agent4HandoffEnvelope(
        message_id=request.message_id,
        run_id=request.run_id,
        trace_id=request.trace_id,
        from_agent="agent_3",
        to_agent="agent_4",
        stage_id=request.stage_id,
        task_type="generate_test_scripts",
        contract_version=request.contract_version,
        retry_count=request.retry_count,
        dedupe_key=request.dedupe_key,
        payload=request.payload,
    )
    try:
        return orchestrator.consume_handoff(envelope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/inbox/{message_id}/runs", response_model=Agent4CreateRunFromInboxResponse)
async def create_agent4_run_from_inbox(
    message_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.create_run_from_inbox(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{run_id}", response_model=Agent4RunSnapshotResponse)
async def get_agent4_run_snapshot(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs", response_model=Agent4RunHistoryResponse)
async def list_agent4_runs_for_backlog_item(
    backlog_item_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    return orchestrator.list_runs_for_backlog_item(backlog_item_id, limit=limit)


@router.post("/runs/{run_id}/phase3/gate", response_model=Agent4Phase3GateResponse)
async def submit_agent4_phase3_gate(
    run_id: str,
    request: Agent4Phase3GateRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.submit_phase3_gate(
            run_id=run_id,
            decision=request.decision,
            gate_mode=request.gate_mode,
            reviewer_id=request.reviewer_id,
            reason_code=request.reason_code,
            auto_retry=request.auto_retry,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/phase3/gate/reason-codes", response_model=Agent4GateReasonCodesResponse)
async def get_agent4_gate_reason_codes(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent4_orchestrator()
    return {"codes": orchestrator.gate_reason_codes()}


@router.get("/runs/{run_id}/phase3/readiness", response_model=Agent4Phase3ReadinessResponse)
async def preview_agent4_phase3_readiness(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.preview_phase3_gate_readiness(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/phase4/plan-scripts", response_model=Agent4Phase4PlanScriptsResponse)
async def plan_agent4_phase4_scripts(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.plan_phase4_scripts(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/phase5/generate-scripts", response_model=Agent4Phase5GenerateScriptsResponse)
async def generate_agent4_phase5_scripts(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        _ensure_run_ready_for_phase5(orchestrator, run_id)
        return orchestrator.generate_phase5_scripts(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/phase5/generate-scripts/stream")
async def generate_agent4_phase5_scripts_stream(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()

    async def event_stream():
        try:
            _ensure_run_ready_for_phase5(orchestrator, run_id)
            orchestrator.generate_phase5_scripts(run_id)
            snapshot = orchestrator.get_run_snapshot(run_id)
            script_bundle = _find_latest_phase5_script_bundle(snapshot) or {}

            for token in _tokenize_script_bundle(script_bundle):
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
                await asyncio.sleep(0.04)

            yield f"data: {json.dumps({'type': 'done', 'snapshot': snapshot})}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/runs/{run_id}/phase6/readiness", response_model=Agent4Phase6ReadinessResponse)
async def preview_agent4_phase6_readiness(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.preview_phase6_readiness(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/phase6/review", response_model=Agent4Phase6ReviewResponse)
async def submit_agent4_phase6_review(
    run_id: str,
    request: Agent4Phase6ReviewRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.submit_phase6_review(
            run_id=run_id,
            decision=request.decision,
            reviewer_id=request.reviewer_id,
            reason_code=request.reason_code,
            edited_scripts=request.edited_scripts,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/phase6/review/reason-codes", response_model=Agent4Phase6ReviewReasonCodesResponse)
async def get_agent4_phase6_review_reason_codes(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent4_orchestrator()
    return {"codes": orchestrator.phase6_review_reason_codes()}


@router.post("/runs/{run_id}/phase7/handoff", response_model=Agent4Phase7EmitHandoffResponse)
async def emit_agent4_phase7_handoff(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.emit_phase7_handoff(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/phase8/feedback", response_model=Agent4Phase8FeedbackResponse)
async def apply_agent4_phase8_feedback(
    run_id: str,
    request: Agent4Phase8FeedbackRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.apply_phase8_feedback(
            run_id=run_id,
            message_id=request.message_id,
            source_agent5_run_id=request.source_agent5_run_id,
            outcome=request.outcome,
            recommended_action=request.recommended_action,
            step_results=request.step_results,
            summary=request.summary,
            metadata=request.metadata,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/phase8/feedback/reason-codes", response_model=Agent4Phase8FeedbackReasonCodesResponse)
async def get_agent4_phase8_feedback_reason_codes(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent4_orchestrator()
    return {"codes": orchestrator.phase8_feedback_reason_codes()}


@router.get("/runs/{run_id}/phase9/observability", response_model=Agent4Phase9ObservabilityResponse)
async def get_agent4_phase9_observability(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.get_phase9_observability(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/runs/{run_id}/phase9/integrity", response_model=Agent4Phase9IntegrityResponse)
async def get_agent4_phase9_integrity(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent4_orchestrator()
    try:
        return orchestrator.get_phase9_integrity_report(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/phase10/profile", response_model=Agent4Phase10ProfileResponse)
async def get_agent4_phase10_profile(
    container: AppContainer = Depends(get_container),
):
    runtime_service = container.get_execution_runtime_service()
    scope = Phase10Scope(
        guarantees=[
            "Execution defaults to visual headed mode for easier debugging.",
            "Default playback speed is slow_mo=1000ms.",
            "Default parallelism is sequential (single worker).",
            "No behavioral change to existing Agent4 generation/review/handoff flow.",
        ],
        non_goals=[
            "No full Agent5 execution orchestration in phase10.0/10.1.",
            "No frontend execution board in phase10.0/10.1.",
        ],
    )
    return {
        "scope": scope.model_dump(),
        "policy": runtime_service.get_execution_policy().model_dump(),
    }


@router.get("/phase10/runtime/check", response_model=Agent4Phase10RuntimeCheckResponse)
async def get_agent4_phase10_runtime_check(
    launch_probe: bool = Query(default=False),
    container: AppContainer = Depends(get_container),
):
    runtime_service = container.get_execution_runtime_service()
    result = await runtime_service.check_runtime(launch_probe=launch_probe)
    return result.model_dump()


@router.post("/runs/{run_id}/phase10/executions", response_model=Agent4Phase10ExecutionSnapshotResponse)
async def start_agent4_phase10_execution(
    run_id: str,
    request: Agent4Phase10ExecutionStartRequest,
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    try:
        execution = lifecycle.enqueue_execution(
            agent4_run_id=run_id,
            requested_by=request.requested_by,
            reason=request.reason,
            max_attempts=request.max_attempts,
            target_url=request.target_url,
            max_scripts=request.max_scripts,
            early_stop_after_failures=request.early_stop_after_failures,
            parallel_workers=request.parallel_workers,
            selected_script_paths=request.selected_script_paths,
            use_smoke_probe_script=request.use_smoke_probe_script,
        )
        return {"execution": execution}
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/phase10/executions/{execution_run_id}/run", response_model=Agent4Phase10ExecutionSnapshotResponse)
async def run_agent4_phase10_execution(
    execution_run_id: str,
    request: Agent4Phase10ExecutionRunRequest,
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    try:
        execution = await lifecycle.process_execution(execution_run_id, started_by=request.started_by)
        return {"execution": execution}
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/phase10/executions/{execution_run_id}/run/stream")
async def run_agent4_phase10_execution_stream(
    execution_run_id: str,
    started_by: str = Query(default="operator"),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()

    async def event_stream():
        try:
            async for event in lifecycle.run_execution_stream(execution_run_id, started_by=started_by):
                yield f"data: {json.dumps(event)}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/phase10/dispatch/next", response_model=Agent4Phase10DispatchResponse)
async def dispatch_agent4_phase10_next(
    request: Agent4Phase10DispatchRequest,
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    execution = await lifecycle.dispatch_next_queued_execution(started_by=request.started_by)
    return {"execution": execution}


@router.get("/phase10/dispatcher/status", response_model=Agent4Phase10DispatcherStatusResponse)
async def get_agent4_phase10_dispatcher_status(
    container: AppContainer = Depends(get_container),
):
    dispatcher = container.get_execution_dispatcher_service()
    return {"dispatcher": dispatcher.status()}


@router.post("/phase10/dispatcher/start", response_model=Agent4Phase10DispatcherStatusResponse)
async def start_agent4_phase10_dispatcher(
    container: AppContainer = Depends(get_container),
):
    dispatcher = container.get_execution_dispatcher_service()
    await dispatcher.start()
    return {"dispatcher": dispatcher.status()}


@router.post("/phase10/dispatcher/stop", response_model=Agent4Phase10DispatcherStatusResponse)
async def stop_agent4_phase10_dispatcher(
    _: None = Depends(require_operator_action),
    container: AppContainer = Depends(get_container),
):
    dispatcher = container.get_execution_dispatcher_service()
    await dispatcher.stop()
    return {"dispatcher": dispatcher.status()}


@router.post("/phase10/dispatcher/recover-stale", response_model=Agent4Phase10RecoveryResponse)
async def recover_agent4_phase10_stale_executions(
    ttl_seconds: int = Query(default=config.EXECUTION_PENDING_TTL_SECONDS, ge=1, le=86_400),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    recovery = lifecycle.recover_stale_executions(ttl_seconds=ttl_seconds)
    return {"recovery": recovery}


@router.get("/phase10/executions/{execution_run_id}/stream")
async def stream_agent4_phase10_execution(
    execution_run_id: str,
    poll_ms: int = Query(default=500, ge=100, le=5000),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()

    async def event_stream():
        terminal_states = {"completed", "failed", "canceled"}
        while True:
            try:
                snapshot = lifecycle.get_execution(execution_run_id)
            except ValueError as exc:
                yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
                return

            yield f"data: {json.dumps({'type': 'status', 'execution': snapshot})}\n\n"

            if str(snapshot.get("state") or "") in terminal_states:
                yield f"data: {json.dumps({'type': 'done', 'execution': snapshot})}\n\n"
                return

            await asyncio.sleep(poll_ms / 1000.0)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/runs/{run_id}/phase10/executions", response_model=Agent4Phase10ExecutionListResponse)
async def list_agent4_phase10_executions(
    run_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    executions = lifecycle.list_for_agent4_run(run_id, limit=limit)
    return {"run_id": run_id, "executions": executions}


@router.get("/phase10/executions/{execution_run_id}", response_model=Agent4Phase10ExecutionSnapshotResponse)
async def get_agent4_phase10_execution(
    execution_run_id: str,
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    try:
        execution = lifecycle.get_execution(execution_run_id)
        return {"execution": execution}
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/phase10/executions/{execution_run_id}/normalized")
async def get_agent4_phase10_execution_normalized(
    execution_run_id: str,
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    try:
        execution = lifecycle.get_execution(execution_run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)

    result = execution.get("result") if isinstance(execution.get("result"), dict) else {}
    normalized = {
        "execution_run_id": execution.get("execution_run_id"),
        "source_agent4_run_id": execution.get("source_agent4_run_id"),
        "state": execution.get("state"),
        "summary": result.get("summary") if isinstance(result, dict) else {},
        "per_script_status": result.get("per_script_status") if isinstance(result, dict) else [],
        "step_results": result.get("step_results") if isinstance(result, dict) else [],
        "evidence": result.get("evidence") if isinstance(result, dict) else {},
        "integrity": result.get("integrity") if isinstance(result, dict) else {},
        "recommended_next_action": "agent5_handoff_ready"
        if execution.get("state") in {"completed", "failed"}
        else "wait_for_completion",
    }
    return {"execution": normalized}


@router.post("/phase10/executions/{execution_run_id}/cancel", response_model=Agent4Phase10ExecutionSnapshotResponse)
async def cancel_agent4_phase10_execution(
    execution_run_id: str,
    canceled_by: str = Query(default="operator"),
    _: None = Depends(require_operator_action),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    try:
        execution = lifecycle.cancel_execution(execution_run_id, canceled_by=canceled_by)
        return {"execution": execution}
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/phase10/executions/{execution_run_id}/pause", response_model=Agent4Phase10ExecutionSnapshotResponse)
async def pause_agent4_phase10_execution(
    execution_run_id: str,
    paused_by: str = Query(default="operator"),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    try:
        execution = lifecycle.pause_execution(execution_run_id, paused_by=paused_by)
        return {"execution": execution}
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/phase10/executions/{execution_run_id}/resume", response_model=Agent4Phase10ExecutionSnapshotResponse)
async def resume_agent4_phase10_execution(
    execution_run_id: str,
    resumed_by: str = Query(default="operator"),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    try:
        execution = lifecycle.resume_execution(execution_run_id, resumed_by=resumed_by)
        return {"execution": execution}
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/phase11/queue/profile", response_model=Agent4Phase11QueueProfileResponse)
async def get_agent4_phase11_queue_profile():
    return {
        "phase": "phase11",
        "strategy": "queue_backpressure_hardening",
        "limits": {
            "max_queue_size": config.EXECUTION_MAX_QUEUE_SIZE,
            "poll_ms": config.EXECUTION_QUEUE_POLL_MS,
            "dispatcher_workers": max(1, config.EXECUTION_DISPATCHER_WORKERS),
        },
        "protections": [
            "Queue rejects new items when max_queue_size reached.",
            "Dispatcher performs stale-running recovery sweeps.",
            "Phase11 queue-cancel endpoint allows queued items only.",
        ],
    }


@router.get("/phase11/queue/snapshot", response_model=Agent4Phase11QueueSnapshotResponse)
async def get_agent4_phase11_queue_snapshot(
    window_limit: int = Query(default=1000, ge=10, le=5000),
    container: AppContainer = Depends(get_container),
):
    dispatcher = container.get_execution_dispatcher_service()
    runs = store.list_execution_runs(limit=window_limit)

    counts = {
        "queued": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "canceled": 0,
        "other": 0,
    }
    for run in runs:
        state = str(run.get("state") or "").lower()
        if state in counts:
            counts[state] += 1
        else:
            counts["other"] += 1

    queue_size = counts["queued"]
    max_size = max(1, int(config.EXECUTION_MAX_QUEUE_SIZE))
    utilization = min(100.0, (queue_size / max_size) * 100.0)
    pressure = "normal"
    if utilization >= 90:
        pressure = "high"
    elif utilization >= 70:
        pressure = "elevated"

    return {
        "snapshot": {
            "counts": counts,
            "queue_size": queue_size,
            "max_queue_size": max_size,
            "queue_utilization_pct": round(utilization, 2),
            "pressure": pressure,
            "dispatcher": dispatcher.status(),
            "window_limit": window_limit,
            "window_run_count": len(runs),
        }
    }


@router.get("/phase11/queue/items", response_model=Agent4Phase11QueueItemsResponse)
async def list_agent4_phase11_queue_items(
    limit: int = Query(default=200, ge=1, le=500),
):
    runs = store.list_execution_runs(limit=limit)
    items: list[dict] = []
    for run in runs:
        items.append(
            {
                "execution_run_id": run.get("execution_run_id"),
                "business_id": run.get("business_id"),
                "source_agent4_run_id": run.get("source_agent4_run_id"),
                "backlog_item_id": run.get("backlog_item_id"),
                "state": run.get("state"),
                "stage": run.get("stage"),
                "attempt_count": run.get("attempt_count"),
                "max_attempts": run.get("max_attempts"),
                "queue_position": run.get("queue_position"),
                "updated_at": run.get("updated_at"),
                "created_at": run.get("created_at"),
            }
        )
    return {"limit": limit, "items": items}


@router.delete("/phase11/queue/{execution_run_id}", response_model=Agent4Phase10ExecutionSnapshotResponse)
async def cancel_agent4_phase11_queue_item(
    execution_run_id: str,
    canceled_by: str = Query(default="operator"),
    _: None = Depends(require_operator_action),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    try:
        snapshot = lifecycle.get_execution(execution_run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)

    state = str(snapshot.get("state") or "").lower()
    if state != "queued":
        raise HTTPException(
            status_code=409,
            detail=(
                "Only queued executions can be cancelled via phase11 queue endpoint. "
                "Use execution stop controls for running items."
            ),
        )

    execution = lifecycle.cancel_execution(execution_run_id, canceled_by=canceled_by)
    return {"execution": execution}


@router.get("/phase12/queue/health", response_model=Agent4Phase12QueueHealthResponse)
async def get_agent4_phase12_queue_health(
    window_limit: int = Query(default=2000, ge=10, le=10000),
    container: AppContainer = Depends(get_container),
):
    dispatcher = container.get_execution_dispatcher_service()
    runs = store.list_execution_runs(limit=window_limit)

    counts = {
        "queued": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "canceled": 0,
        "other": 0,
    }
    timed_out = 0
    oldest_pending_age_seconds = 0
    now = datetime.now(timezone.utc)

    for run in runs:
        state = str(run.get("state") or "").lower()
        if state in counts:
            counts[state] += 1
        else:
            counts["other"] += 1

        if str(run.get("last_error_code") or "").lower() == "execution_timeout":
            timed_out += 1

        if state == "queued":
            created_at = str(run.get("created_at") or "").strip().replace(" ", "T")
            if created_at:
                try:
                    age = int((now - datetime.fromisoformat(created_at).replace(tzinfo=timezone.utc)).total_seconds())
                    if age > oldest_pending_age_seconds:
                        oldest_pending_age_seconds = max(age, 0)
                except ValueError:
                    pass

    max_size = max(1, int(config.EXECUTION_MAX_QUEUE_SIZE))
    saturation = min(1.0, counts["queued"] / max_size)

    health = {
        "saturation": round(saturation, 4),
        "in_flight": {
            "queued": counts["queued"],
            "running": counts["running"],
        },
        "oldest_pending_age_seconds": oldest_pending_age_seconds,
        "queue_totals": {
            "enqueued": len(runs),
            "completed": counts["completed"],
            "failed": counts["failed"],
            "cancelled": counts["canceled"],
            "timed_out": timed_out,
        },
        "window_limit": window_limit,
        "dispatcher": dispatcher.status(),
    }
    return {"health": health}


@router.post("/phase12/queue/expire-pending", response_model=Agent4Phase12QueueExpireResponse)
async def expire_agent4_phase12_pending_queue_items(
    ttl_seconds: int = Query(default=config.EXECUTION_PENDING_TTL_SECONDS, ge=1, le=86_400),
    _: None = Depends(require_operator_action),
    container: AppContainer = Depends(get_container),
):
    lifecycle = container.get_execution_lifecycle_service()
    expiration = lifecycle.expire_pending_executions(ttl_seconds=ttl_seconds)
    return {"expiration": expiration}


@router.get("/phase14/queue/audit", response_model=Agent4Phase14QueueAuditResponse)
async def get_agent4_phase14_queue_audit(
    limit: int = Query(default=200, ge=1, le=1000),
    stage: str | None = Query(default=None),
    status: str | None = Query(default=None),
    story_id: str | None = Query(default=None),
    _: None = Depends(require_operator_action),
):
    normalized_status = str(status or "").strip().lower() or None
    if normalized_status not in {None, "ok", "error"}:
        raise HTTPException(status_code=400, detail="status must be one of: ok, error")

    events = store.get_queue_events(
        limit=limit,
        stage=stage,
        status=normalized_status,
        story_id=story_id,
    )
    return {
        "limit": limit,
        "stage": stage,
        "status": normalized_status,
        "story_id": story_id,
        "events": events,
    }


@router.get("/phase15/operator/whoami", response_model=Agent4Phase15OperatorWhoAmIResponse)
async def get_agent4_phase15_operator_whoami(
    identity: dict = Depends(resolve_operator_identity),
):
    return {"identity": identity}


@router.get("/phase15/queue/audit/verify", response_model=Agent4Phase15QueueAuditVerifyResponse)
async def verify_agent4_phase15_queue_audit(
    limit: int = Query(default=500, ge=1, le=1000),
    story_id: str | None = Query(default=None),
    _: None = Depends(require_operator_view),
):
    events = store.get_queue_events(limit=limit, story_id=story_id)

    signing_secret = str(config.AUDIT_SIGNING_SECRET or "")
    secret_configured = bool(signing_secret)
    invalid_event_ids: list[int] = []

    for event in events:
        event_id = int(event.get("event_id") or 0)
        prev_signature = str(event.get("prev_signature") or "")
        event_signature = str(event.get("event_signature") or "")

        if not secret_configured:
            continue

        if not prev_signature or not event_signature:
            invalid_event_ids.append(event_id)
            continue

        metadata = event.get("metadata") if isinstance(event.get("metadata"), dict) else {}
        metadata_json = json.dumps(metadata, sort_keys=True, separators=(",", ":")) if metadata else None
        canonical_payload = {
            "trace_id": event.get("trace_id"),
            "run_id": event.get("run_id"),
            "story_id": event.get("story_id"),
            "stage": event.get("stage"),
            "status": event.get("status"),
            "model_provider": event.get("model_provider"),
            "model_name": event.get("model_name"),
            "prompt_template": event.get("prompt_template"),
            "prompt_chars": event.get("prompt_chars"),
            "response_chars": event.get("response_chars"),
            "duration_ms": event.get("duration_ms"),
            "error_code": event.get("error_code"),
            "error_message": event.get("error_message"),
            "metadata_json": metadata_json,
        }
        canonical = json.dumps(canonical_payload, sort_keys=True, separators=(",", ":"))
        expected = hmac.new(
            signing_secret.encode("utf-8"),
            f"{prev_signature}|{canonical}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if expected != event_signature:
            invalid_event_ids.append(event_id)

    verification = {
        "checked_events": len(events),
        "secret_configured": secret_configured,
        "valid": secret_configured and len(invalid_event_ids) == 0,
        "invalid_event_ids": invalid_event_ids,
        "story_id": story_id,
        "limit": limit,
    }
    return {"verification": verification}


@router.get("/phase16/operator/security/status", response_model=Agent4Phase16OperatorSecurityStatusResponse)
async def get_agent4_phase16_operator_security_status(
    _: None = Depends(require_operator_view),
):
    return {"security": operator_incident_policy_service.get_status()}


@router.get("/phase16/operator/security/events", response_model=Agent4Phase16OperatorSecurityEventsResponse)
async def get_agent4_phase16_operator_security_events(
    limit: int = Query(default=100, ge=1, le=500),
    _: None = Depends(require_operator_view),
):
    events = operator_incident_policy_service.get_events(limit=limit)
    return {
        "limit": limit,
        "events": events,
    }


@router.get("/phase17/operator/security/history", response_model=Agent4Phase17OperatorSecurityHistoryResponse)
async def get_agent4_phase17_operator_security_history(
    limit: int = Query(default=100, ge=1, le=500),
    _: None = Depends(require_operator_view),
):
    events = operator_incident_policy_service.get_history(limit=limit)
    return {
        "limit": limit,
        "events": events,
    }


@router.get("/phase17/operator/security/summary", response_model=Agent4Phase17OperatorSecuritySummaryResponse)
async def get_agent4_phase17_operator_security_summary(
    window_limit: int = Query(default=1000, ge=1, le=5000),
    _: None = Depends(require_operator_view),
):
    return {"summary": operator_incident_policy_service.get_summary(window_limit=window_limit)}


@router.post("/phase17/operator/security/alerts/test", response_model=Agent4Phase17OperatorAlertTestResponse)
async def post_agent4_phase17_operator_security_alert_test(
    source: str = Query(default="operator-test"),
    _: None = Depends(require_operator_admin),
):
    return {"alert_test": operator_incident_policy_service.send_test_alert(source=source)}


@router.get("/phase19/operator/security/incidents/open", response_model=Agent4Phase19OpenIncidentsResponse)
async def get_agent4_phase19_operator_security_open_incidents(
    limit: int = Query(default=200, ge=1, le=500),
    _: None = Depends(require_operator_view),
):
    incidents = operator_incident_policy_service.get_open_incidents(limit=limit)
    return {
        "limit": limit,
        "incidents": incidents,
    }


@router.post("/phase19/operator/security/incidents/{incident_id}/ack", response_model=Agent4Phase19IncidentLifecycleResponse)
async def post_agent4_phase19_operator_security_incident_ack(
    incident_id: str,
    acked_by: str = Query(default="operator"),
    _: None = Depends(require_operator_action),
):
    incident = operator_incident_policy_service.acknowledge_incident(incident_id, acked_by=acked_by)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"incident": incident}


@router.post("/phase19/operator/security/incidents/{incident_id}/resolve", response_model=Agent4Phase19IncidentLifecycleResponse)
async def post_agent4_phase19_operator_security_incident_resolve(
    incident_id: str,
    resolved_by: str = Query(default="operator"),
    resolution_note: str | None = Query(default=None),
    _: None = Depends(require_operator_action),
):
    incident = operator_incident_policy_service.resolve_incident(
        incident_id,
        resolved_by=resolved_by,
        resolution_note=resolution_note,
    )
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"incident": incident}


@router.get("/phase20/operator/security/export", response_model=Agent4Phase20SecurityExportResponse)
async def get_agent4_phase20_operator_security_export(
    limit: int = Query(default=500, ge=1, le=5000),
    state: str | None = Query(default=None),
    _: None = Depends(require_operator_view),
):
    normalized_state = str(state or "").strip().lower() or None
    if normalized_state not in {None, "open", "acknowledged", "resolved"}:
        raise HTTPException(status_code=400, detail="state must be one of: open, acknowledged, resolved")

    payload = store.export_operator_security_events(limit=limit, state=normalized_state)
    return {"export": payload}


@router.get("/phase20/operator/security/readiness", response_model=Agent4Phase20SecurityReadinessResponse)
async def get_agent4_phase20_operator_security_readiness(
    _: None = Depends(require_operator_view),
):
    open_incidents = operator_incident_policy_service.get_open_incidents(limit=200)
    open_threshold = max(0, int(config.OPERATOR_SECURITY_OPEN_INCIDENT_THRESHOLD or 0))

    checks = {
        "operator_auth_enabled": bool(config.OPERATOR_REQUIRE_API_KEY),
        "audit_signing_enabled": bool(str(config.AUDIT_SIGNING_SECRET or "").strip()),
        "webhook_configured": bool(str(config.OPERATOR_ALERT_WEBHOOK_URL or "").strip()),
        "open_incidents_within_threshold": len(open_incidents) <= open_threshold,
    }
    readiness = {
        "ready": all(bool(value) for value in checks.values()),
        "checks": checks,
        "open_incident_count": len(open_incidents),
        "open_incident_threshold": open_threshold,
    }
    return {"readiness": readiness}


@router.post("/agent3-runs/{run_id}/start", response_model=Agent4StartFromAgent3RunResponse)
async def start_agent4_from_agent3_run(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    agent3_orchestrator = container.get_agent3_orchestrator()
    agent4_orchestrator = container.get_agent4_orchestrator()

    try:
        snapshot = agent3_orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)

    handoff_emitted = False
    handoff = _find_latest_phase5_handoff_envelope(snapshot)

    if handoff is None and (snapshot.get("run") or {}).get("state") == "handoff_pending":
        handoff_result = agent3_orchestrator.emit_phase5_handoff(run_id)
        handoff_emitted = bool(handoff_result.get("created"))
        snapshot = agent3_orchestrator.get_run_snapshot(run_id)
        handoff = _find_latest_phase5_handoff_envelope(snapshot)

    if handoff is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Agent3 run '{run_id}' has no Agent3->Agent4 handoff. "
                "Run Agent3 handoff first or move the run to 'handoff_pending'."
            ),
        )

    payload = handoff.get("payload") if isinstance(handoff, dict) else {}
    payload = payload if isinstance(payload, dict) else {}
    source_run = snapshot.get("run") or {}
    message_id = str(handoff.get("message_id") or "")
    trace_id = str(payload.get("trace_id") or source_run.get("trace_id") or f"agent3-{run_id}")
    artifact_version = payload.get("artifact_version")
    dedupe_key = str(uuid5(NAMESPACE_URL, f"agent3-agent4:{run_id}:{artifact_version}"))

    envelope = Agent4HandoffEnvelope(
        message_id=message_id,
        run_id=run_id,
        trace_id=trace_id,
        from_agent="agent_3",
        to_agent="agent_4",
        stage_id="script_generation",
        task_type="generate_test_scripts",
        contract_version=str(handoff.get("contract_version") or "v1"),
        retry_count=0,
        dedupe_key=dedupe_key,
        payload=payload,
    )

    consume = agent4_orchestrator.consume_handoff(envelope)
    create = agent4_orchestrator.create_run_from_inbox(message_id)
    agent4_run_id = (create.get("run") or {}).get("run_id")
    agent4_snapshot = agent4_orchestrator.get_run_snapshot(agent4_run_id) if agent4_run_id else None

    return {
        "agent3_run_id": run_id,
        "handoff_emitted": handoff_emitted,
        "message_id": message_id,
        "consume": consume,
        "create": create,
        "agent4_snapshot": agent4_snapshot,
    }
