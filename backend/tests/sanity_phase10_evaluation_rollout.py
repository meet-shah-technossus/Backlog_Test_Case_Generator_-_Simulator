from __future__ import annotations

import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.infrastructure.store import store


def _seed_execution_run(*, story_id: str, source_run_id: str, suffix: str, verdict: str, error_code: str | None) -> None:
    execution_run_id = f"eval-exec-{suffix}-{uuid.uuid4().hex[:8]}"
    trace_id = f"trace-{suffix}-{uuid.uuid4().hex[:8]}"

    store.create_execution_run(
        execution_run_id=execution_run_id,
        source_agent4_run_id=source_run_id,
        backlog_item_id=story_id,
        trace_id=trace_id,
        state="queued",
        stage="phase10_execution_queued",
        request_payload={"started_by": "sanity"},
        runtime_policy={"worker_count": 1},
        max_attempts=1,
    )

    failed = 0 if verdict == "passed" else 1
    step_status = "passed" if verdict == "passed" else "failed"

    store.update_execution_run_state(
        execution_run_id=execution_run_id,
        state="completed" if verdict == "passed" else "failed",
        stage="phase10_execution_completed" if verdict == "passed" else "phase10_execution_failed",
        result_payload={
            "summary": {
                "total": 1,
                "passed": 1 - failed,
                "failed": failed,
                "skipped": 0,
                "final_verdict": verdict,
            },
            "per_script_status": [
                {
                    "script_path": "tests/generated/login.spec.ts",
                    "step_index": 1,
                    "status": step_status,
                    "duration_ms": 1200,
                    "error_code": error_code,
                }
            ],
            "step_results": [
                {
                    "script_path": "tests/generated/login.spec.ts",
                    "step_index": 1,
                    "status": step_status,
                    "duration_ms": 1200,
                    "error_code": error_code,
                    "evidence": {},
                    "metadata": {},
                }
            ],
        },
        last_error_code=error_code,
        last_error_message="selector failure" if error_code else None,
    )


def main() -> None:
    client = TestClient(app)

    story_id = f"eval-story-{uuid.uuid4().hex[:8]}"
    source_run_id = f"eval-agent4-run-{uuid.uuid4().hex[:8]}"

    _seed_execution_run(
        story_id=story_id,
        source_run_id=source_run_id,
        suffix="pass",
        verdict="passed",
        error_code=None,
    )
    _seed_execution_run(
        story_id=story_id,
        source_run_id=source_run_id,
        suffix="fail",
        verdict="failed",
        error_code="selector_not_found",
    )

    store.log_event(
        trace_id=f"trace-telemetry-{uuid.uuid4().hex[:8]}",
        run_id=source_run_id,
        story_id=story_id,
        stage="phase4_context_bundle",
        status="completed",
        prompt_chars=1000,
        response_chars=500,
        duration_ms=900,
    )

    story_response = client.get(f"/evaluation/story/{story_id}?run_limit=50")
    assert story_response.status_code == 200, story_response.text
    story_payload = story_response.json()

    metrics = story_payload.get("metrics") or {}
    token_cost = story_payload.get("token_cost_snapshot") or {}

    assert story_payload.get("scope") == "story", story_payload
    assert story_payload.get("story_id") == story_id, story_payload
    assert isinstance(metrics.get("run_count"), int) and metrics["run_count"] >= 2, metrics
    assert isinstance(metrics.get("pass_rate"), (int, float)), metrics
    assert isinstance(metrics.get("failed_tests"), int) and metrics["failed_tests"] >= 1, metrics
    assert isinstance(metrics.get("total_tests"), int) and metrics["total_tests"] >= 2, metrics
    assert isinstance(metrics.get("flake_rate"), (int, float)) and metrics["flake_rate"] > 0, metrics
    assert isinstance(metrics.get("selector_mismatch_rate"), (int, float)) and metrics["selector_mismatch_rate"] > 0, metrics
    assert isinstance(metrics.get("generation_latency_ms"), (int, float)) and metrics["generation_latency_ms"] > 0, metrics

    assert int(token_cost.get("prompt_chars") or 0) >= 1000, token_cost
    assert int(token_cost.get("response_chars") or 0) >= 500, token_cost

    global_response = client.get("/evaluation/global?run_limit=30")
    assert global_response.status_code == 200, global_response.text
    global_payload = global_response.json()
    assert global_payload.get("scope") == "global", global_payload
    assert global_payload.get("story_id") is None, global_payload

    rollout_response = client.get(f"/evaluation/rollout/{story_id}?run_limit=50")
    assert rollout_response.status_code == 200, rollout_response.text
    rollout_payload = rollout_response.json()

    assert rollout_payload.get("story_id") == story_id, rollout_payload
    assert rollout_payload.get("status") in {"ready", "needs_improvement"}, rollout_payload
    assert isinstance(rollout_payload.get("score"), (int, float)), rollout_payload

    checks = rollout_payload.get("checks") or []
    check_keys = {item.get("key") for item in checks if isinstance(item, dict)}
    assert check_keys == {"pass_rate", "flake_rate", "selector_mismatch_rate"}, checks

    print(
        {
            "story_metrics": metrics,
            "token_cost_snapshot": token_cost,
            "rollout_status": rollout_payload.get("status"),
            "rollout_score": rollout_payload.get("score"),
        }
    )


if __name__ == "__main__":
    main()
