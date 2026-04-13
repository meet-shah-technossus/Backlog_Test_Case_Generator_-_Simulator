from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import AppContainer, get_container
from app.api.routes.agent5.models import (
    Agent5AdvanceToGate7PendingRequest,
    Agent5OrchestrationResponse,
    Agent5CommandRequest,
    Agent5ContractResponse,
    Agent5CreateRunRequest,
    Agent5Gate7DecisionRequest,
    Agent5Gate8DecisionRequest,
    Agent5ObservabilityResponse,
    Agent5PersistPayloadRequest,
    Agent5RecoverStaleRequest,
    Agent5RecoverStaleResponse,
    Agent5RetryFailedRequest,
    Agent5Stage7AnalyzeRequest,
    Agent5Stage8WritebackRequest,
    Agent5RunListResponse,
    Agent5RunSnapshotResponse,
    Agent5StateMachineResponse,
    Agent5TransitionValidationRequest,
    Agent5TransitionValidationResponse,
)
from app.modules.agent5.contracts import get_agent5_contract_spec, get_agent5_state_machine_spec
from app.modules.agent5.state_machine import Agent5StateMachine

router = APIRouter(prefix="/agent5", tags=["Agent5"])


@router.get("/contract", response_model=Agent5ContractResponse)
async def get_agent5_contract() -> Agent5ContractResponse:
    return Agent5ContractResponse(contract=get_agent5_contract_spec())


@router.get("/state-machine", response_model=Agent5StateMachineResponse)
async def get_agent5_state_machine() -> Agent5StateMachineResponse:
    return Agent5StateMachineResponse(state_machine=get_agent5_state_machine_spec())


@router.post("/state-machine/validate-transition", response_model=Agent5TransitionValidationResponse)
async def validate_agent5_transition(
    request: Agent5TransitionValidationRequest,
) -> Agent5TransitionValidationResponse:
    machine = Agent5StateMachine()
    check = machine.validate_transition(
        from_state=request.from_state,
        command=request.command,
        actor=request.actor,
        context=request.context,
    )
    return Agent5TransitionValidationResponse(
        validation={
            "allowed": check.allowed,
            "from_state": check.from_state,
            "to_state": check.to_state,
            "command": check.command,
            "reason": check.reason,
            "audit_event": check.audit_event,
        }
    )


@router.post("/runs", response_model=Agent5RunSnapshotResponse)
async def create_agent5_run(
    request: Agent5CreateRunRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_persistence_service()
    try:
        snapshot = service.create_run(
            source_agent4_run_id=request.source_agent4_run_id,
            source_execution_run_id=request.source_execution_run_id,
            created_by=request.created_by,
            reason=request.reason,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/runs/{agent5_run_id}", response_model=Agent5RunSnapshotResponse)
async def get_agent5_run(
    agent5_run_id: str,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_persistence_service()
    try:
        snapshot = service.get_run_snapshot(agent5_run_id)
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{agent5_run_id}/orchestration", response_model=Agent5OrchestrationResponse)
async def get_agent5_orchestration(
    agent5_run_id: str,
    container: AppContainer = Depends(get_container),
) -> Agent5OrchestrationResponse:
    service = container.get_agent5_orchestrator_service()
    try:
        payload = service.get_orchestration_snapshot(agent5_run_id=agent5_run_id)
        return Agent5OrchestrationResponse(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{agent5_run_id}/observability", response_model=Agent5ObservabilityResponse)
async def get_agent5_observability(
    agent5_run_id: str,
    container: AppContainer = Depends(get_container),
) -> Agent5ObservabilityResponse:
    service = container.get_agent5_observability_service()
    try:
        payload = service.get_run_observability(agent5_run_id=agent5_run_id)
        return Agent5ObservabilityResponse(observability=payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/runs/{agent5_run_id}/commands", response_model=Agent5RunSnapshotResponse)
async def apply_agent5_command(
    agent5_run_id: str,
    request: Agent5CommandRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_orchestrator_service()
    try:
        snapshot = service.apply_command(
            agent5_run_id=agent5_run_id,
            command=request.command,
            actor=request.actor,
            context=request.context,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        message = str(exc)
        lowered = message.lower()
        if "not found" in lowered:
            raise HTTPException(status_code=404, detail=message)
        if "rejected" in lowered:
            raise HTTPException(status_code=409, detail=message)
        raise HTTPException(status_code=400, detail=message)


@router.post("/runs/{agent5_run_id}/advance-to-gate7-pending", response_model=Agent5RunSnapshotResponse)
async def advance_agent5_to_gate7_pending(
    agent5_run_id: str,
    request: Agent5AdvanceToGate7PendingRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_orchestrator_service()
    try:
        snapshot = service.advance_to_gate7_pending(
            agent5_run_id=agent5_run_id,
            actor=request.actor,
            context=request.context,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        message = str(exc)
        lowered = message.lower()
        if "not found" in lowered:
            raise HTTPException(status_code=404, detail=message)
        if "requires state" in lowered:
            raise HTTPException(status_code=409, detail=message)
        raise HTTPException(status_code=400, detail=message)


@router.get("/runs", response_model=Agent5RunListResponse)
async def list_agent5_runs(
    source_agent4_run_id: str,
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_container),
) -> Agent5RunListResponse:
    service = container.get_agent5_persistence_service()
    runs = service.list_runs_for_agent4_run(source_agent4_run_id=source_agent4_run_id, limit=max(1, min(200, int(limit))))
    return Agent5RunListResponse(source_agent4_run_id=source_agent4_run_id, runs=runs)


@router.post("/runs/{agent5_run_id}/stage7-analysis", response_model=Agent5RunSnapshotResponse)
async def persist_agent5_stage7_analysis(
    agent5_run_id: str,
    request: Agent5PersistPayloadRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_persistence_service()
    try:
        snapshot = service.persist_stage7_analysis(
            agent5_run_id=agent5_run_id,
            analysis=request.payload,
            actor=request.actor,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/runs/{agent5_run_id}/stage7-analysis/generate", response_model=Agent5RunSnapshotResponse)
async def generate_agent5_stage7_analysis(
    agent5_run_id: str,
    request: Agent5Stage7AnalyzeRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_analysis_service()
    try:
        snapshot = service.generate_stage7_analysis(
            agent5_run_id=agent5_run_id,
            actor=request.actor,
            force_regenerate=bool(request.force_regenerate),
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{agent5_run_id}/gate7-decision", response_model=Agent5RunSnapshotResponse)
async def persist_agent5_gate7_decision(
    agent5_run_id: str,
    request: Agent5PersistPayloadRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_persistence_service()
    try:
        snapshot = service.persist_gate7_decision(
            agent5_run_id=agent5_run_id,
            decision=request.payload,
            actor=request.actor,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/runs/{agent5_run_id}/gate7/decision", response_model=Agent5RunSnapshotResponse)
async def submit_agent5_gate7_decision(
    agent5_run_id: str,
    request: Agent5Gate7DecisionRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_gate_service()
    try:
        snapshot = service.submit_gate7_decision(
            agent5_run_id=agent5_run_id,
            reviewer_id=request.reviewer_id,
            decision=request.decision,
            reason_code=request.reason_code,
            comment=request.comment,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        message = str(exc)
        lowered = message.lower()
        if "not found" in lowered:
            raise HTTPException(status_code=404, detail=message)
        if "only when state" in lowered or "must be" in lowered or "blocked" in lowered:
            raise HTTPException(status_code=409, detail=message)
        raise HTTPException(status_code=400, detail=message)


@router.post("/runs/{agent5_run_id}/stage8-writeback", response_model=Agent5RunSnapshotResponse)
async def persist_agent5_stage8_writeback(
    agent5_run_id: str,
    request: Agent5PersistPayloadRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_persistence_service()
    try:
        snapshot = service.persist_stage8_writeback(
            agent5_run_id=agent5_run_id,
            writeback=request.payload,
            actor=request.actor,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/runs/{agent5_run_id}/stage8-writeback/generate", response_model=Agent5RunSnapshotResponse)
async def generate_agent5_stage8_writeback(
    agent5_run_id: str,
    request: Agent5Stage8WritebackRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_writeback_service()
    try:
        snapshot = service.generate_writeback(
            agent5_run_id=agent5_run_id,
            actor=request.actor,
            idempotency_key=request.idempotency_key,
            force_regenerate=bool(request.force_regenerate),
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        message = str(exc)
        lowered = message.lower()
        if "not found" in lowered:
            raise HTTPException(status_code=404, detail=message)
        if "requires state" in lowered or "blocked" in lowered:
            raise HTTPException(status_code=409, detail=message)
        raise HTTPException(status_code=400, detail=message)


@router.post("/runs/{agent5_run_id}/gate8-decision", response_model=Agent5RunSnapshotResponse)
async def persist_agent5_gate8_decision(
    agent5_run_id: str,
    request: Agent5PersistPayloadRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_persistence_service()
    try:
        snapshot = service.persist_gate8_decision(
            agent5_run_id=agent5_run_id,
            decision=request.payload,
            actor=request.actor,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/runs/{agent5_run_id}/gate8/decision", response_model=Agent5RunSnapshotResponse)
async def submit_agent5_gate8_decision(
    agent5_run_id: str,
    request: Agent5Gate8DecisionRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_gate8_service()
    try:
        snapshot = service.submit_gate8_decision(
            agent5_run_id=agent5_run_id,
            reviewer_id=request.reviewer_id,
            decision=request.decision,
            reason_code=request.reason_code,
            comment=request.comment,
        )
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        message = str(exc)
        lowered = message.lower()
        if "not found" in lowered:
            raise HTTPException(status_code=404, detail=message)
        if "only when state" in lowered or "must be" in lowered:
            raise HTTPException(status_code=409, detail=message)
        raise HTTPException(status_code=400, detail=message)


@router.post("/reliability/recover-stale", response_model=Agent5RecoverStaleResponse)
async def recover_agent5_stale_runs(
    request: Agent5RecoverStaleRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RecoverStaleResponse:
    service = container.get_agent5_reliability_service()
    recovery = service.recover_stale_runs(
        actor=request.actor,
        older_than_seconds=request.older_than_seconds,
        limit=request.limit,
    )
    return Agent5RecoverStaleResponse(recovery=recovery)


@router.post("/runs/{agent5_run_id}/reliability/retry", response_model=Agent5RunSnapshotResponse)
async def retry_agent5_failed_run(
    agent5_run_id: str,
    request: Agent5RetryFailedRequest,
    container: AppContainer = Depends(get_container),
) -> Agent5RunSnapshotResponse:
    service = container.get_agent5_reliability_service()
    try:
        snapshot = service.retry_failed_run(agent5_run_id=agent5_run_id, actor=request.actor)
        return Agent5RunSnapshotResponse(**snapshot)
    except ValueError as exc:
        message = str(exc)
        if "not found" in message.lower():
            raise HTTPException(status_code=404, detail=message)
        raise HTTPException(status_code=409, detail=message)
