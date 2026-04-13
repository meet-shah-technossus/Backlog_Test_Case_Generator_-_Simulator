"""
AI Test Case Generator & Automation System — Backend
=====================================================
FastAPI application entry point.

Start the server:
    cd backend
    .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import BACKEND_CORS_ORIGINS, BACKEND_HOST, BACKEND_PORT, OPENAI_BASE_URL, OPENAI_MODEL
from app.core.config import EXECUTION_DISPATCHER_AUTO_START
from app.core.container import get_container
from app.api.routes import health
from app.api.routes.agent1 import router as agent1_router
from app.api.routes.agent2 import router as agent2_router
from app.api.routes.agent3 import router as agent3_router
from app.api.routes.agent4 import router as agent4_router
from app.api.routes.agent5 import router as agent5_router
from app.api.routes.business_ids import router as business_ids_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.retry_governance import router as retry_governance_router
from app.api.routes.scraper import router as scraper_router
from app.api.routes.demo import router as demo_router


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown logic.
    Prints a summary of the LLM configuration on boot.
    """
    print("\n" + "=" * 60)
    print("  AI Test Automation Backend — Starting Up")
    print("=" * 60)
    print(f"  OpenAI Base  : {OPENAI_BASE_URL}")
    print(f"  Model        : {OPENAI_MODEL}")
    print(f"  Docs         : http://localhost:{BACKEND_PORT}/docs")
    print("=" * 60 + "\n")

    container = get_container()
    dispatcher = container.get_execution_dispatcher_service()
    if EXECUTION_DISPATCHER_AUTO_START:
        await dispatcher.start()

    yield

    await dispatcher.stop()
    print("\nBackend shutting down.\n")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI Test Case Generator & Automation System",
    description=(
        "Automatically generates structured test cases from backlog acceptance criteria "
        "using OpenAI LLMs, then executes them visually via Playwright."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)


# ── CORS ──────────────────────────────────────────────────────────────────────
# Allow the Vite dev server (localhost:5173) and any local origin during development

app.add_middleware(
    CORSMiddleware,
    allow_origins=BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Error Handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc),
            "path": str(request.url),
        },
    )


# ── Routes ────────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(agent1_router)
app.include_router(agent2_router)
app.include_router(agent3_router)
app.include_router(agent4_router)
app.include_router(agent5_router)
app.include_router(business_ids_router)
app.include_router(evaluation_router)
app.include_router(retry_governance_router)
app.include_router(scraper_router)
app.include_router(demo_router)


# ── Root ──────────────────────────────────────────────────────────────────────

@app.get("/", tags=["Root"])
async def root() -> dict:
    return {
        "name": "AI Test Automation Backend",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# ── Dev entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        reload=True,
    )
