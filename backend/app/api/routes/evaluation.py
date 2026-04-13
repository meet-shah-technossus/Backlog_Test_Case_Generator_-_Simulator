from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.api.dependencies import AppContainer, get_container
from app.core import config
from app.infrastructure.store import store

router = APIRouter(prefix="/evaluation", tags=["Evaluation"])


class EvaluationMetrics(BaseModel):
    run_count: int
    pass_rate: float
    failed_tests: int
    total_tests: int
    average_run_duration_ms: float
    flake_rate: float
    selector_mismatch_rate: float
    generation_latency_ms: float


class EvaluationTokenCostSnapshot(BaseModel):
    prompt_chars: int
    response_chars: int
    estimated_input_cost_usd: float
    estimated_output_cost_usd: float
    estimated_total_cost_usd: float


class EvaluationSummaryResponse(BaseModel):
    scope: str
    story_id: str | None = None
    run_limit: int
    metrics: EvaluationMetrics
    token_cost_snapshot: EvaluationTokenCostSnapshot


class RolloutCheck(BaseModel):
    key: str
    passed: bool
    expected: str
    actual: float


class RolloutResponse(BaseModel):
    story_id: str
    run_limit: int
    status: str
    score: float
    checks: list[RolloutCheck] = Field(default_factory=list)
    metrics: EvaluationMetrics


class QueueLifecycleBucket(BaseModel):
    bucket_start: str
    counts: dict[str, int] = Field(default_factory=dict)
    total: int


class QueueLifecycleTrendResponse(BaseModel):
    scope: str
    story_id: str | None = None
    hours: int
    bucket_minutes: int
    event_names: list[str] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
    buckets: list[QueueLifecycleBucket] = Field(default_factory=list)


QUEUE_LIFECYCLE_EVENTS = (
    "queue.enqueue",
    "queue.run_start",
    "queue.run_end",
    "queue.cancel",
    "queue.expire",
)


def _parse_dt(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace(" ", "T"))
    except ValueError:
        return None


def _to_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _floor_to_bucket(dt: datetime, bucket_minutes: int) -> datetime:
    size = max(1, int(bucket_minutes))
    floored_minute = (dt.minute // size) * size
    return dt.replace(minute=floored_minute, second=0, microsecond=0)


def _compute_summary(*, runs: list[dict], telemetry_events: list[dict], scope: str, story_id: str | None, run_limit: int) -> EvaluationSummaryResponse:
    executed_runs = 0
    passed_runs = 0
    total_tests = 0
    failed_tests = 0
    duration_values: list[float] = []

    script_status_history: dict[str, set[str]] = {}
    total_failed_script_results = 0
    selector_not_found_failures = 0

    for run in runs:
        raw_result = run.get("result")
        result = raw_result if isinstance(raw_result, dict) else {}
        raw_summary = result.get("summary")
        summary = raw_summary if isinstance(raw_summary, dict) else {}
        raw_per_script = result.get("per_script_status")
        per_script = raw_per_script if isinstance(raw_per_script, list) else []

        total = _to_int(summary.get("total"), default=len(per_script))
        failed = _to_int(summary.get("failed"))
        final_verdict = str(summary.get("final_verdict") or "").lower()

        if total > 0 or per_script:
            executed_runs += 1
            total_tests += max(total, len(per_script))
            failed_tests += max(failed, 0)
            if final_verdict == "passed" or (failed == 0 and total > 0):
                passed_runs += 1

        run_duration_ms = 0.0
        for item in per_script:
            if not isinstance(item, dict):
                continue
            status = str(item.get("status") or "").lower()
            script_path = str(item.get("script_path") or "").strip()
            if script_path:
                history = script_status_history.setdefault(script_path, set())
                if status in {"passed", "failed", "skipped"}:
                    history.add(status)
            if status == "failed":
                total_failed_script_results += 1
                if str(item.get("error_code") or "").lower() == "selector_not_found":
                    selector_not_found_failures += 1
            run_duration_ms += max(_to_float(item.get("duration_ms")), 0.0)

        if run_duration_ms <= 0.0:
            started_at = _parse_dt(run.get("started_at"))
            completed_at = _parse_dt(run.get("completed_at"))
            if started_at and completed_at and completed_at >= started_at:
                run_duration_ms = (completed_at - started_at).total_seconds() * 1000.0

        if run_duration_ms > 0.0:
            duration_values.append(run_duration_ms)

    flaky_scripts = 0
    for statuses in script_status_history.values():
        if "passed" in statuses and "failed" in statuses:
            flaky_scripts += 1

    denominator_scripts = len(script_status_history)
    flake_rate = (flaky_scripts / denominator_scripts * 100.0) if denominator_scripts else 0.0
    selector_mismatch_rate = (
        selector_not_found_failures / total_failed_script_results * 100.0
        if total_failed_script_results
        else 0.0
    )

    # Completed/success events with positive duration are treated as generation latency inputs.
    generation_durations = []
    prompt_chars = 0
    response_chars = 0
    for event in telemetry_events:
        status = str(event.get("status") or "").lower()
        duration_ms = _to_float(event.get("duration_ms"))
        if duration_ms > 0 and status in {"completed", "success", "succeeded", "ok", "done"}:
            generation_durations.append(duration_ms)
        prompt_chars += max(_to_int(event.get("prompt_chars")), 0)
        response_chars += max(_to_int(event.get("response_chars")), 0)

    run_count = executed_runs
    pass_rate = (passed_runs / run_count * 100.0) if run_count else 0.0
    avg_duration = sum(duration_values) / len(duration_values) if duration_values else 0.0
    generation_latency_ms = sum(generation_durations) / len(generation_durations) if generation_durations else 0.0

    input_cost = (prompt_chars / 1000.0) * float(config.EVAL_INPUT_COST_PER_1K_USD)
    output_cost = (response_chars / 1000.0) * float(config.EVAL_OUTPUT_COST_PER_1K_USD)

    metrics = EvaluationMetrics(
        run_count=run_count,
        pass_rate=round(pass_rate, 3),
        failed_tests=failed_tests,
        total_tests=total_tests,
        average_run_duration_ms=round(avg_duration, 3),
        flake_rate=round(flake_rate, 3),
        selector_mismatch_rate=round(selector_mismatch_rate, 3),
        generation_latency_ms=round(generation_latency_ms, 3),
    )
    token_cost_snapshot = EvaluationTokenCostSnapshot(
        prompt_chars=prompt_chars,
        response_chars=response_chars,
        estimated_input_cost_usd=round(input_cost, 6),
        estimated_output_cost_usd=round(output_cost, 6),
        estimated_total_cost_usd=round(input_cost + output_cost, 6),
    )
    return EvaluationSummaryResponse(
        scope=scope,
        story_id=story_id,
        run_limit=run_limit,
        metrics=metrics,
        token_cost_snapshot=token_cost_snapshot,
    )


@router.get("/story/{story_id}", response_model=EvaluationSummaryResponse)
async def get_story_evaluation(
    story_id: str,
    run_limit: int = Query(default=100, ge=1, le=1000),
    container: AppContainer = Depends(get_container),
):
    _ = container
    runs = store.list_execution_runs(backlog_item_id=story_id, limit=run_limit)
    telemetry_events = store.get_events_by_story(story_id, limit=max(500, run_limit * 20))
    return _compute_summary(
        runs=runs,
        telemetry_events=telemetry_events,
        scope="story",
        story_id=story_id,
        run_limit=run_limit,
    )


@router.get("/global", response_model=EvaluationSummaryResponse)
async def get_global_evaluation(
    run_limit: int = Query(default=300, ge=1, le=1000),
    container: AppContainer = Depends(get_container),
):
    _ = container
    runs = store.list_execution_runs(limit=run_limit)

    story_ids: set[str] = set()
    for run in runs:
        story_id = str(run.get("backlog_item_id") or "").strip()
        if story_id:
            story_ids.add(story_id)

    telemetry_events: list[dict] = []
    for story_id in story_ids:
        telemetry_events.extend(store.get_events_by_story(story_id, limit=max(200, run_limit * 4)))

    return _compute_summary(
        runs=runs,
        telemetry_events=telemetry_events,
        scope="global",
        story_id=None,
        run_limit=run_limit,
    )


@router.get("/rollout/{story_id}", response_model=RolloutResponse)
async def get_story_rollout_readiness(
    story_id: str,
    run_limit: int = Query(default=100, ge=1, le=1000),
    container: AppContainer = Depends(get_container),
):
    summary = await get_story_evaluation(story_id=story_id, run_limit=run_limit, container=container)
    metrics = summary.metrics

    checks = [
        RolloutCheck(
            key="pass_rate",
            passed=metrics.pass_rate >= 85.0,
            expected=">= 85.0",
            actual=metrics.pass_rate,
        ),
        RolloutCheck(
            key="flake_rate",
            passed=metrics.flake_rate <= 15.0,
            expected="<= 15.0",
            actual=metrics.flake_rate,
        ),
        RolloutCheck(
            key="selector_mismatch_rate",
            passed=metrics.selector_mismatch_rate <= 20.0,
            expected="<= 20.0",
            actual=metrics.selector_mismatch_rate,
        ),
    ]

    passed_checks = sum(1 for check in checks if check.passed)
    total_checks = len(checks)
    score = (passed_checks / total_checks) if total_checks else 0.0
    status = "ready" if passed_checks == total_checks else "needs_improvement"

    return RolloutResponse(
        story_id=story_id,
        run_limit=run_limit,
        status=status,
        score=round(score, 3),
        checks=checks,
        metrics=metrics,
    )


@router.get("/queue-lifecycle", response_model=QueueLifecycleTrendResponse)
async def get_queue_lifecycle_trends(
    story_id: str | None = Query(default=None),
    hours: int = Query(default=24, ge=1, le=168),
    bucket_minutes: int = Query(default=30, ge=1, le=240),
    limit: int = Query(default=8000, ge=1, le=20000),
    container: AppContainer = Depends(get_container),
):
    _ = container
    scope = "story" if story_id else "global"
    event_names = [str(name) for name in QUEUE_LIFECYCLE_EVENTS]

    if story_id:
        raw_events = store.get_events_by_story(story_id, limit=limit)
    else:
        raw_events = store.get_recent_events(limit=limit)

    cutoff = datetime.now() - timedelta(hours=hours)
    totals = {name: 0 for name in event_names}
    buckets_map: dict[str, dict[str, int]] = {}

    for event in raw_events:
        stage = str(event.get("stage") or "")
        if stage not in totals:
            continue

        created_at = _parse_dt(event.get("created_at"))
        if created_at is None:
            continue
        if created_at < cutoff:
            continue

        bucket_start = _floor_to_bucket(created_at, bucket_minutes).isoformat(timespec="seconds")
        if bucket_start not in buckets_map:
            buckets_map[bucket_start] = {name: 0 for name in event_names}

        buckets_map[bucket_start][stage] += 1
        totals[stage] += 1

    buckets: list[QueueLifecycleBucket] = []
    for key in sorted(buckets_map.keys()):
        counts = buckets_map[key]
        buckets.append(
            QueueLifecycleBucket(
                bucket_start=key,
                counts=counts,
                total=sum(counts.values()),
            )
        )

    return QueueLifecycleTrendResponse(
        scope=scope,
        story_id=story_id,
        hours=hours,
        bucket_minutes=bucket_minutes,
        event_names=event_names,
        totals=totals,
        buckets=buckets,
    )
