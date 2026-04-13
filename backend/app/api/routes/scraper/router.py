from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import AppContainer, get_container
from app.api.routes.scraper.models import (
    ScraperBlueprintResponse,
    ScraperPhase8CompleteRequest,
    ScraperPhase8CompleteResponse,
    ScraperPhase6StartAgent2Request,
    ScraperPhase6StartAgent2Response,
    ScraperContextPackRequest,
    ScraperContextPackResponse,
    ScraperCreateJobRequest,
    ScraperFetchPreviewRequest,
    ScraperFetchPreviewResponse,
    ScraperFrontierPreviewRequest,
    ScraperFrontierPreviewResponse,
    ScraperJobListResponse,
    ScraperJobResponse,
    ScraperRunJobRequest,
    ScraperRunJobResponse,
)
from app.modules.agent2.contracts.models import Agent2HandoffEnvelope

router = APIRouter(prefix="/scraper", tags=["Scraper"])


@router.get("/blueprint", response_model=ScraperBlueprintResponse)
async def get_scraper_blueprint(container: AppContainer = Depends(get_container)):
    orchestrator = container.get_scraper_orchestrator()
    return orchestrator.get_blueprint()


@router.post("/jobs", response_model=ScraperJobResponse)
async def create_scraper_job(
    request: ScraperCreateJobRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_scraper_orchestrator()
    try:
        job = orchestrator.create_job(
            backlog_item_id=request.backlog_item_id,
            max_depth=request.max_depth,
            max_pages=request.max_pages,
            same_origin_only=request.same_origin_only,
        )
        return {"job": job}
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/jobs/{job_id}/phase5/context-pack", response_model=ScraperContextPackResponse)
async def build_scraper_context_pack(
    job_id: str,
    request: ScraperContextPackRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_scraper_orchestrator()
    try:
        return orchestrator.build_context_pack(job_id=job_id, max_pages=request.max_pages)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/jobs/{job_id}/phase6/agent2/start", response_model=ScraperPhase6StartAgent2Response)
async def start_agent2_from_scraper_job(
    job_id: str,
    request: ScraperPhase6StartAgent2Request,
    container: AppContainer = Depends(get_container),
):
    scraper_orchestrator = container.get_scraper_orchestrator()
    agent2_orchestrator = container.get_agent2_orchestrator()

    try:
        job = scraper_orchestrator.get_job_snapshot(job_id)
        context_pack = scraper_orchestrator.build_context_pack(
            job_id=job_id,
            max_pages=request.max_pages,
        )

        trace_id = f"scraper-{job_id}"
        message_id = f"scraper-{job_id}-{uuid4()}"
        envelope = Agent2HandoffEnvelope(
            message_id=message_id,
            run_id=job_id,
            trace_id=trace_id,
            from_agent="scraper",
            to_agent="agent_2",
            task_type="generate_steps",
            contract_version="v1",
            payload={
                "run_id": job_id,
                "trace_id": trace_id,
                "task": "generate_steps",
                "source": "scraper_phase6",
                "backlog_item_id": job.get("backlog_item_id"),
                "scraper_job_id": job_id,
                "scraper_context_pack": context_pack,
            },
        )

        consume = agent2_orchestrator.consume_handoff(envelope)
        create = agent2_orchestrator.create_run_from_inbox(message_id)
        run_id = (create.get("run") or {}).get("run_id")
        snapshot = agent2_orchestrator.get_run_snapshot(run_id) if run_id else None

        return {
            "scraper_job_id": job_id,
            "message_id": message_id,
            "consume": consume,
            "create": create,
            "snapshot": snapshot,
        }
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/jobs/{job_id}/phase8/complete", response_model=ScraperPhase8CompleteResponse)
async def complete_scraper_pipeline(
    job_id: str,
    request: ScraperPhase8CompleteRequest,
    container: AppContainer = Depends(get_container),
):
    scraper_orchestrator = container.get_scraper_orchestrator()
    agent2_orchestrator = container.get_agent2_orchestrator()

    try:
        job = scraper_orchestrator.get_job_snapshot(job_id)
        context_pack = scraper_orchestrator.build_context_pack(
            job_id=job_id,
            max_pages=request.max_pages,
        )

        trace_id = f"scraper-{job_id}"
        message_id = f"scraper-{job_id}-phase6-v1"
        envelope = Agent2HandoffEnvelope(
            message_id=message_id,
            run_id=job_id,
            trace_id=trace_id,
            from_agent="scraper",
            to_agent="agent_2",
            task_type="generate_steps",
            contract_version="v1",
            payload={
                "run_id": job_id,
                "trace_id": trace_id,
                "task": "generate_steps",
                "source": "scraper_phase8_complete",
                "backlog_item_id": job.get("backlog_item_id"),
                "scraper_job_id": job_id,
                "scraper_context_pack": context_pack,
            },
        )

        consume = agent2_orchestrator.consume_handoff(envelope)
        create = agent2_orchestrator.create_run_from_inbox(message_id)
        run_id = (create.get("run") or {}).get("run_id")
        snapshot = agent2_orchestrator.get_run_snapshot(run_id) if run_id else None

        generated = False
        auto_approved = False
        handoff_emitted = False

        current_state = ((snapshot or {}).get("run") or {}).get("state")

        if run_id and current_state in {"intake_ready", "review_retry_requested"}:
            snapshot = await agent2_orchestrator.generate(run_id=run_id, model=request.model)
            generated = True
            current_state = ((snapshot or {}).get("run") or {}).get("state")

        if run_id and request.auto_approve and current_state == "review_pending":
            snapshot = agent2_orchestrator.review(
                run_id=run_id,
                decision="approve",
                reviewer_id=request.reviewer_id,
                reason_code=None,
                edited_payload=None,
            )
            auto_approved = True
            current_state = ((snapshot or {}).get("run") or {}).get("state")

        if run_id and request.emit_agent3_handoff and current_state == "handoff_pending":
            handoff_result = agent2_orchestrator.handoff(run_id)
            snapshot = handoff_result.get("snapshot")
            handoff_emitted = bool(handoff_result.get("created"))

        return {
            "scraper_job_id": job_id,
            "message_id": message_id,
            "agent2_run_id": run_id,
            "consume": consume,
            "create": create,
            "generated": generated,
            "auto_approved": auto_approved,
            "handoff_emitted": handoff_emitted,
            "snapshot": snapshot,
        }
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.get("/jobs/{job_id}", response_model=ScraperJobResponse)
async def get_scraper_job(
    job_id: str,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_scraper_orchestrator()
    try:
        return {"job": orchestrator.get_job_snapshot(job_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/jobs", response_model=ScraperJobListResponse)
async def list_scraper_jobs(
    backlog_item_id: str = Query(..., min_length=1),
    limit: int = Query(default=50, ge=1, le=200),
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_scraper_orchestrator()
    return orchestrator.list_jobs_for_backlog_item(backlog_item_id, limit=limit)


@router.post("/jobs/{job_id}/frontier/preview", response_model=ScraperFrontierPreviewResponse)
async def preview_scraper_frontier(
    job_id: str,
    request: ScraperFrontierPreviewRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_scraper_orchestrator()
    try:
        return orchestrator.preview_frontier(
            job_id=job_id,
            discovered_links=request.discovered_links,
            source_url=request.source_url,
            source_depth=request.source_depth,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/jobs/{job_id}/fetch/preview", response_model=ScraperFetchPreviewResponse)
async def preview_scraper_fetch(
    job_id: str,
    request: ScraperFetchPreviewRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_scraper_orchestrator()
    try:
        return await orchestrator.fetch_target_preview(
            job_id=job_id,
            mode=request.mode,
            timeout_seconds=request.timeout_seconds,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)


@router.post("/jobs/{job_id}/run", response_model=ScraperRunJobResponse)
async def run_scraper_job(
    job_id: str,
    request: ScraperRunJobRequest,
    container: AppContainer = Depends(get_container),
):
    orchestrator = container.get_scraper_orchestrator()
    try:
        return await orchestrator.run_job(
            job_id=job_id,
            mode=request.mode,
            timeout_seconds=request.timeout_seconds,
            force_restart=request.force_restart,
        )
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message)
