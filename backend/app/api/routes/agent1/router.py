from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.dependencies import AppContainer, get_container
from app.api.routes.agent1.models import (
    Agent1RunContractV1Response,
    Agent1RunSnapshotResponse,
    Agent1StoryRunsResponse,
    Agent1TimelineResponse,
    CreateRunRequest,
    GenerateRunRequest,
    ReviewRunRequest,
    RetryRunRequest,
)
from app.infrastructure.store import store
from app.modules.agent1.mcp.contracts import MCPBacklogIntakeRequest

router = APIRouter(prefix="/agent1", tags=["Agent1"])


@router.post("/intake/load")
async def load_backlog_via_mcp(
    request: MCPBacklogIntakeRequest,
    container: AppContainer = Depends(get_container),
):
    svc = container.get_agent1_mcp_backlog_intake_service()
    try:
        return await svc.load(request)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/runs")
async def create_agent1_run(
    request: CreateRunRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    try:
        return orchestrator.create_run(backlog_item_id=request.backlog_item_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/runs/{run_id}/generate")
async def generate_agent1_artifact(
    run_id: str,
    request: GenerateRunRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    try:
        return await orchestrator.generate(run_id=run_id, model=request.model)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/runs/{run_id}/generate/stream")
async def generate_agent1_artifact_stream(
    run_id: str,
    request: GenerateRunRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()

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


@router.get("/runs/{run_id}", response_model=Agent1RunSnapshotResponse)
async def get_agent1_run(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    try:
        return orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/runs/{run_id}/contract/v1", response_model=Agent1RunContractV1Response)
async def get_agent1_run_contract_v1(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    try:
        snapshot = orchestrator.get_run_snapshot(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    run = snapshot.get("run") or {}
    latest_artifact = snapshot.get("latest_artifact") or {}
    reviews = snapshot.get("reviews") or []
    latest_review = reviews[0] if reviews else {}

    retry_requests = store.list_retry_governance_requests(
        run_scope="agent1",
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

    return Agent1RunContractV1Response(
        contract_version="v1",
        run_scope="agent1",
        internal_id=str(run.get("run_id") or run_id),
        business_id=run.get("business_id"),
        current_revision=current_revision,
        retry_status=retry_status,
        review_status=review_status,
        run=run,
    )


@router.get("/stories/{backlog_item_id}/runs", response_model=Agent1StoryRunsResponse)
async def list_agent1_runs_for_story(
    backlog_item_id: str,
    limit: int = 50,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    return {
        "backlog_item_id": backlog_item_id,
        "runs": orchestrator.list_runs_for_backlog_item(backlog_item_id, limit=limit),
    }


@router.post("/runs/{run_id}/review")
async def submit_agent1_review(
    run_id: str,
    request: ReviewRunRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    try:
        return orchestrator.submit_review(
            run_id=run_id,
            decision=request.decision,
            reviewer_id=request.reviewer_id,
            reason_code=request.reason_code,
            edited_payload=request.edited_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/runs/{run_id}/retry")
async def retry_agent1_run(
    run_id: str,
    request: RetryRunRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    try:
        return orchestrator.retry(
            run_id=run_id,
            reason_code=request.reason_code,
            actor=request.actor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/runs/{run_id}/handoff")
async def handoff_agent1_run(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    try:
        return orchestrator.emit_handoff(run_id=run_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/runs/{run_id}/timeline", response_model=Agent1TimelineResponse)
async def get_agent1_timeline(
    run_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_agent1_orchestrator()
    try:
        snap = orchestrator.get_run_snapshot(run_id)
        return {
            "run_id": run_id,
            "timeline": snap["timeline"],
        }
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
