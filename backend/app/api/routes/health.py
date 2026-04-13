"""
Health Route — GET /health
===========================
System status check. Reports connectivity to:
    - OpenAI API
  - The backlog API
    - Available OpenAI models
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.config import OPENAI_BASE_URL, OPENAI_MODEL, BACKLOG_API_BASE_URL
from app.api.dependencies import AppContainer, get_container

router = APIRouter(prefix="/health", tags=["Health"])


class ServiceStatus(BaseModel):
    status: str           # "ok" | "error" | "unconfigured"
    detail: str = ""


class HealthResponse(BaseModel):
    overall: str          # "ok" | "degraded" | "error"
    llm: ServiceStatus
    backlog_api: ServiceStatus
    available_models: list[str] = []
    configured_model: str = OPENAI_MODEL


@router.get("", response_model=HealthResponse)
async def health_check(container: AppContainer = Depends(get_container)) -> HealthResponse:
    """
    Check connectivity to all external services.
    Called by the frontend on load to show connection status indicators.
    """
    client = container.get_openai_client()

    # ── OpenAI check ──────────────────────────────────────────
    available_models: list[str] = []
    try:
        reachable = await client.ping()
        if reachable:
            available_models = await client.list_models()
            llm_status = ServiceStatus(
                status="ok",
                detail=f"Connected — {len(available_models)} model(s) available",
            )
        else:
            llm_status = ServiceStatus(
                status="error",
                detail="OpenAI API unreachable or API key missing.",
            )
    except Exception as e:
        llm_status = ServiceStatus(status="error", detail=str(e))

    # ── Backlog API check ─────────────────────────────────────
    if not BACKLOG_API_BASE_URL or "REPLACE" in BACKLOG_API_BASE_URL:
        backlog_status = ServiceStatus(
            status="unconfigured",
            detail="BACKLOG_API_BASE_URL not set in .env",
        )
    else:
        import httpx
        try:
            async with httpx.AsyncClient(timeout=8) as http:
                r = await http.get(BACKLOG_API_BASE_URL.rstrip("/") + "/api/backlog")
                if r.status_code < 500:
                    backlog_status = ServiceStatus(
                        status="ok",
                        detail=f"Reachable (HTTP {r.status_code})",
                    )
                else:
                    backlog_status = ServiceStatus(
                        status="error",
                        detail=f"Server error HTTP {r.status_code}",
                    )
        except Exception as e:
            backlog_status = ServiceStatus(status="error", detail=str(e))

    # ── Overall status ────────────────────────────────────────
    statuses = [llm_status.status, backlog_status.status]
    if all(s == "ok" for s in statuses):
        overall = "ok"
    elif any(s == "error" for s in statuses):
        overall = "degraded"
    else:
        overall = "degraded"

    return HealthResponse(
        overall=overall,
        llm=llm_status,
        backlog_api=backlog_status,
        available_models=available_models,
        configured_model=OPENAI_MODEL,
    )
