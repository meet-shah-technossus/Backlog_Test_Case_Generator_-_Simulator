from __future__ import annotations

import asyncio
import json
from uuid import NAMESPACE_URL, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.api.dependencies import AppContainer, get_container
from app.api.routes.agent2.models import (
    Agent2ApprovedAgent1RunsResponse,
    Agent2BlueprintResponse,
    Agent2ConsumeHandoffRequest,
    Agent2CreateRunFromInboxResponse,
    Agent2EmitHandoffResponse,
    Agent2GenerateRunRequest,
    Agent2InboxConsumeResponse,
    Agent2ObservabilityCountersResponse,
    Agent2ReviewDiffResponse,
    Agent2ReviewReasonCodesResponse,
    Agent2ReviewRunRequest,
    Agent2RunContractV1Response,
    Agent2RunHistoryResponse,
    Agent2RunSnapshotResponse,
    Agent2StartAgent3Response,
    Agent2StartFromAgent1RunResponse,
    Agent2TimelineResponse,
)
from app.modules.agent2.contracts.models import Agent2HandoffEnvelope
from app.modules.agent3.contracts.models import Agent3HandoffEnvelope
from app.infrastructure.store import store

router = APIRouter(prefix="/agent2", tags=["Agent2"])


@router.get("/blueprint", response_model=Agent2BlueprintResponse)
async def get_agent2_blueprint(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent2_orchestrator()
    return orchestrator.get_blueprint()


@router.post("/inbox/consume", response_model=Agent2InboxConsumeResponse)
async def consume_agent1_handoff(
    request: Agent2ConsumeHandoffRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    envelope = Agent2HandoffEnvelope(
        message_id=request.message_id,
        run_id=request.run_id,
        trace_id=request.trace_id,
        from_agent="agent_1",
        to_agent="agent_2",
        task_type="generate_steps",
        contract_version=request.contract_version,
        payload=request.payload,
    )
    try:
        return orchestrator.consume_handoff(envelope)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/agent1-runs/{agent1_run_id}/consume", response_model=Agent2InboxConsumeResponse)
async def consume_agent1_handoff_from_mcp(
    agent1_run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return orchestrator.consume_agent1_handoff(agent1_run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() or "no agent1 handoff" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/agent1/approved-runs", response_model=Agent2ApprovedAgent1RunsResponse)
async def list_agent1_approved_runs_for_agent2(
    backlog_item_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    handoff_only: bool = Query(default=True),
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    return orchestrator.list_approved_agent1_runs(
        backlog_item_id,
        limit=limit,
        handoff_only=handoff_only,
    )


@router.post("/agent1-runs/{agent1_run_id}/start", response_model=Agent2StartFromAgent1RunResponse)
async def start_agent2_from_agent1_run(
    agent1_run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return orchestrator.start_from_agent1_run(agent1_run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/inbox/{message_id}/runs", response_model=Agent2CreateRunFromInboxResponse)
async def create_agent2_run_from_inbox(
    message_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return orchestrator.create_run_from_inbox(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{run_id}", response_model=Agent2RunSnapshotResponse)
async def get_agent2_run_snapshot(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{run_id}/contract/v1", response_model=Agent2RunContractV1Response)
async def get_agent2_run_contract_v1(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        snapshot = orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    run = snapshot.get("run") or {}
    latest_artifact = snapshot.get("latest_artifact") or {}
    reviews = snapshot.get("reviews") or []
    latest_review = reviews[0] if reviews else {}

    retry_requests = store.list_retry_governance_requests(
        run_scope="agent2",
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
        "latest_decision": latest_review.get("decision"),
        "latest_reviewer_id": latest_review.get("reviewer_id"),
        "latest_reviewed_at": latest_review.get("created_at"),
        "total_reviews": len(reviews),
    }

    return Agent2RunContractV1Response(
        contract_version="v1",
        run_scope="agent2",
        internal_id=str(run.get("run_id") or run_id),
        business_id=run.get("business_id"),
        current_revision=current_revision,
        retry_status=retry_status,
        review_status=review_status,
        run=run,
    )


@router.get("/runs", response_model=Agent2RunHistoryResponse)
async def list_agent2_runs_for_backlog_item(
    backlog_item_id: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=200),
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    return orchestrator.list_runs_for_backlog_item(backlog_item_id, limit=limit)


@router.get("/runs/{run_id}/timeline", response_model=Agent2TimelineResponse)
async def get_agent2_timeline(
    run_id: str,
    order: str = Query(default='asc', pattern='^(asc|desc)$'),
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return orchestrator.get_timeline(run_id, order=order)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/observability/counters", response_model=Agent2ObservabilityCountersResponse)
async def get_agent2_observability_counters(
    backlog_item_id: str | None = Query(default=None),
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    return orchestrator.get_observability_counters(backlog_item_id=backlog_item_id)


@router.post("/runs/{run_id}/generate", response_model=Agent2RunSnapshotResponse)
async def generate_agent2_run(
    run_id: str,
    request: Agent2GenerateRunRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return await orchestrator.generate(run_id=run_id, model=request.model)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/generate/stream")
async def generate_agent2_run_stream(
    run_id: str,
    request: Agent2GenerateRunRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()

    async def event_stream():
        queue: asyncio.Queue[str] = asyncio.Queue()

        async def on_token(token: str):
            await queue.put(token)

        task = asyncio.create_task(
            orchestrator.generate_stream(run_id=run_id, model=request.model, on_token=on_token)
        )

        while True:
            if task.done() and queue.empty():
                break
            try:
                token = await asyncio.wait_for(queue.get(), timeout=0.2)
                yield f"data: {json.dumps({'type': 'token', 'token': token})}\n\n"
            except TimeoutError:
                continue

        try:
            snapshot = await task
            yield f"data: {json.dumps({'type': 'done', 'snapshot': snapshot})}\n\n"
        except ValueError as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/runs/{run_id}/review", response_model=Agent2RunSnapshotResponse)
async def review_agent2_run(
    run_id: str,
    request: Agent2ReviewRunRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return orchestrator.review(
            run_id=run_id,
            decision=request.decision,
            reviewer_id=request.reviewer_id,
            reason_code=request.reason_code,
            edited_payload=request.edited_payload,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/runs/{run_id}/review-diff", response_model=Agent2ReviewDiffResponse)
async def get_agent2_review_diff(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return orchestrator.review_diff(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/review/reason-codes", response_model=Agent2ReviewReasonCodesResponse)
async def get_agent2_review_reason_codes(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_agent2_orchestrator()
    return {"codes": orchestrator.review_reason_codes()}


@router.post("/runs/{run_id}/handoff", response_model=Agent2EmitHandoffResponse)
async def emit_agent2_handoff(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent2_orchestrator()
    try:
        return orchestrator.handoff(run_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/runs/{run_id}/agent3/start", response_model=Agent2StartAgent3Response)
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
