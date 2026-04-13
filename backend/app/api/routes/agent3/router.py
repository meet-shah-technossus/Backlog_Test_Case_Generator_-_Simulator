from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import AppContainer, get_container
from app.api.routes.agent3.models import (
    Agent3AssembleContextResponse,
    Agent3BlueprintResponse,
    Agent3ConsumeHandoffRequest,
    Agent3CreateRunFromInboxResponse,
    Agent3GateReasonCodesResponse,
    Agent3InboxConsumeResponse,
    Agent3Phase4GenerateResponse,
    Agent3Phase5EmitHandoffResponse,
    Agent3Phase5ReviewReasonCodesResponse,
    Agent3Phase5ReviewRequest,
    Agent3Phase5ReviewResponse,
    Agent3Phase6FeedbackReasonCodesResponse,
    Agent3Phase6FeedbackRequest,
    Agent3Phase6FeedbackResponse,
    Agent3Phase7ObservabilityResponse,
    Agent3Phase8IntegrityResponse,
    Agent3Phase3GateRequest,
    Agent3Phase3GateResponse,
    Agent3StartFromAgent2RunResponse,
    Agent3RunSnapshotResponse,
    Agent3RunContractV1Response,
    Agent3RunHistoryResponse,
)
from app.modules.agent4.contracts.models import Agent4HandoffEnvelope
from app.modules.agent3.contracts.models import Agent3HandoffEnvelope
from app.infrastructure.store import store

router = APIRouter(prefix="/agent3", tags=["Agent3"])


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


@router.get("/blueprint", response_model=Agent3BlueprintResponse)
async def get_agent3_blueprint(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent3_orchestrator()
    return orchestrator.get_blueprint()


@router.post("/inbox/consume", response_model=Agent3InboxConsumeResponse)
async def consume_agent2_handoff(
    request: Agent3ConsumeHandoffRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    envelope = Agent3HandoffEnvelope(
        message_id=request.message_id,
        run_id=request.run_id,
        trace_id=request.trace_id,
        from_agent="agent_2",
        to_agent="agent_3",
        stage_id=request.stage_id,
        task_type="reason_over_steps",
        contract_version=request.contract_version,
        retry_count=request.retry_count,
        dedupe_key=request.dedupe_key,
        payload=request.payload,
    )
    try:
        return orchestrator.consume_handoff(envelope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/inbox/{message_id}/runs", response_model=Agent3CreateRunFromInboxResponse)
async def create_agent3_run_from_inbox(
    message_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.create_run_from_inbox(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{run_id}", response_model=Agent3RunSnapshotResponse)
async def get_agent3_run_snapshot(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{run_id}/contract/v1", response_model=Agent3RunContractV1Response)
async def get_agent3_run_contract_v1(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        snapshot = orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    run = snapshot.get("run") or {}
    latest_artifact = snapshot.get("latest_artifact") or {}
    timeline = snapshot.get("timeline") or []

    latest_review_event = next(
        (
            event
            for event in timeline
            if str(event.get("action") or "").startswith("phase5_review_")
        ),
        {},
    )

    retry_requests = store.list_retry_governance_requests(
        run_scope="agent3",
        run_id=run_id,
        limit=20,
    )
    latest_retry = retry_requests[0] if retry_requests else {}

    current_revision = {
        "internal_id": latest_artifact.get("id"),
        "business_id": latest_artifact.get("business_id"),
        "artifact_version": latest_artifact.get("artifact_version"),
        "created_at": latest_artifact.get("created_at"),
    }
    retry_status = {
        "latest_request_id": latest_retry.get("request_id"),
        "latest_status": latest_retry.get("status"),
        "total_requests": len(retry_requests),
    }
    review_status = {
        "latest_decision": latest_review_event.get("action"),
        "latest_reviewer_id": latest_review_event.get("actor"),
        "latest_reviewed_at": latest_review_event.get("created_at"),
        "total_reviews": sum(1 for event in timeline if str(event.get("action") or "").startswith("phase5_review_")),
    }

    return Agent3RunContractV1Response(
        contract_version="v1",
        run_scope="agent3",
        internal_id=str(run.get("run_id") or run_id),
        business_id=run.get("business_id"),
        current_revision=current_revision,
        retry_status=retry_status,
        review_status=review_status,
        run=run,
    )


@router.get("/runs", response_model=Agent3RunHistoryResponse)
async def list_agent3_runs_for_backlog_item(
    backlog_item_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    return orchestrator.list_runs_for_backlog_item(backlog_item_id, limit=limit)


@router.post("/runs/{run_id}/phase3/assemble-context", response_model=Agent3AssembleContextResponse)
async def assemble_agent3_context(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.assemble_context(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/phase3/gate", response_model=Agent3Phase3GateResponse)
async def submit_agent3_phase3_gate(
    run_id: str,
    request: Agent3Phase3GateRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
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


@router.get("/phase3/gate/reason-codes", response_model=Agent3GateReasonCodesResponse)
async def get_agent3_gate_reason_codes(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent3_orchestrator()
    return {"codes": orchestrator.gate_reason_codes()}


@router.post("/runs/{run_id}/phase4/generate-selectors", response_model=Agent3Phase4GenerateResponse)
async def generate_agent3_phase4_selectors(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.generate_phase4_selectors(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/phase5/review", response_model=Agent3Phase5ReviewResponse)
async def review_agent3_phase5_selectors(
    run_id: str,
    request: Agent3Phase5ReviewRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.review_phase5_selectors(
            run_id=run_id,
            decision=request.decision,
            reviewer_id=request.reviewer_id,
            reason_code=request.reason_code,
            edited_selector_steps=request.edited_selector_steps,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/phase5/review/reason-codes", response_model=Agent3Phase5ReviewReasonCodesResponse)
async def get_agent3_phase5_review_reason_codes(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent3_orchestrator()
    return {"codes": orchestrator.phase5_review_reason_codes()}


@router.post("/runs/{run_id}/phase5/handoff", response_model=Agent3Phase5EmitHandoffResponse)
async def emit_agent3_phase5_handoff(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.emit_phase5_handoff(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/phase6/feedback", response_model=Agent3Phase6FeedbackResponse)
async def apply_agent3_phase6_feedback(
    run_id: str,
    request: Agent3Phase6FeedbackRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.apply_phase6_feedback(
            run_id=run_id,
            message_id=request.message_id,
            source_agent4_run_id=request.source_agent4_run_id,
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


@router.get("/phase6/feedback/reason-codes", response_model=Agent3Phase6FeedbackReasonCodesResponse)
async def get_agent3_phase6_feedback_reason_codes(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent3_orchestrator()
    return {"codes": orchestrator.phase6_feedback_reason_codes()}


@router.get("/runs/{run_id}/phase7/observability", response_model=Agent3Phase7ObservabilityResponse)
async def get_agent3_phase7_observability(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.get_phase7_observability(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/runs/{run_id}/phase8/integrity", response_model=Agent3Phase8IntegrityResponse)
async def get_agent3_phase8_integrity(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent3_orchestrator()
    try:
        return orchestrator.get_phase8_integrity_report(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/agent2-runs/{run_id}/start", response_model=Agent3StartFromAgent2RunResponse)
async def start_agent3_from_agent2_run(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    agent2_orchestrator = container.get_agent2_orchestrator()
    agent3_orchestrator = container.get_agent3_orchestrator()

    try:
        snapshot = agent2_orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)

    handoff_emitted = False
    handoffs = snapshot.get("handoffs") or []
    if not handoffs and (snapshot.get("run") or {}).get("state") == "handoff_pending":
        handoff_result = agent2_orchestrator.handoff(run_id)
        handoff_emitted = bool(handoff_result.get("created"))
        snapshot = handoff_result.get("snapshot") or snapshot
        handoffs = snapshot.get("handoffs") or []

    if not handoffs:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Agent2 run '{run_id}' has no Agent2->Agent3 handoff. "
                "Run Agent2 handoff first or move the run to 'handoff_pending'."
            ),
        )

    handoff = handoffs[0]
    payload = handoff.get("payload") or {}
    source_run = snapshot.get("run") or {}
    message_id = str(handoff.get("message_id") or "")
    trace_id = str(payload.get("trace_id") or source_run.get("trace_id") or f"agent2-{run_id}")
    artifact_version = payload.get("artifact_version")
    dedupe_key = str(uuid5(NAMESPACE_URL, f"agent2-agent3:{run_id}:{artifact_version}"))

    envelope = Agent3HandoffEnvelope(
        message_id=message_id,
        run_id=run_id,
        trace_id=trace_id,
        from_agent="agent_2",
        to_agent="agent_3",
        stage_id="reasoning",
        task_type="reason_over_steps",
        contract_version=str(handoff.get("contract_version") or "v1"),
        retry_count=0,
        dedupe_key=dedupe_key,
        payload=payload,
    )

    consume = agent3_orchestrator.consume_handoff(envelope)
    create = agent3_orchestrator.create_run_from_inbox(message_id)
    agent3_run_id = (create.get("run") or {}).get("run_id")
    agent3_snapshot = agent3_orchestrator.get_run_snapshot(agent3_run_id) if agent3_run_id else None

    return {
        "agent2_run_id": run_id,
        "handoff_emitted": handoff_emitted,
        "message_id": message_id,
        "consume": consume,
        "create": create,
        "agent3_snapshot": agent3_snapshot,
    }


@router.post("/runs/{run_id}/agent4/start")
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
