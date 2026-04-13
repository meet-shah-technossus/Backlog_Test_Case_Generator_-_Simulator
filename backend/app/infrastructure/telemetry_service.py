"""
Telemetry Service
=================
Helpers for observability trace IDs and stage event logging.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.infrastructure.store import store


def new_trace_id(prefix: str = "trace") -> str:
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}_{ts}_{uuid4().hex[:8]}"


def log_stage_event(
    *,
    trace_id: str,
    stage: str,
    status: str,
    run_id: str | None = None,
    story_id: str | None = None,
    model_provider: str | None = None,
    model_name: str | None = None,
    prompt_template: str | None = None,
    prompt_chars: int | None = None,
    response_chars: int | None = None,
    duration_ms: int | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    metadata: dict | None = None,
) -> None:
    store.log_event(
        trace_id=trace_id,
        stage=stage,
        status=status,
        run_id=run_id,
        story_id=story_id,
        model_provider=model_provider,
        model_name=model_name,
        prompt_template=prompt_template,
        prompt_chars=prompt_chars,
        response_chars=response_chars,
        duration_ms=duration_ms,
        error_code=error_code,
        error_message=error_message,
        metadata=metadata,
    )
