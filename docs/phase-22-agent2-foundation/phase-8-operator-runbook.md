# Agent2 Operator Runbook (Phase 8)

Status: Active
Date: 2026-03-27

## Purpose
Quick-response guide for common Agent2 production issues.

## Preconditions
1. Backend is running.
2. Agent1 handoff records are available.
3. MCP boundary sanity passes.

## Common Scenarios
### 1. Agent2 intake consume fails
Symptoms:
- `POST /agent2/agent1-runs/{run_id}/consume` returns 404/400.

Checks:
1. Verify Agent1 run exists.
2. Verify Agent1 handoff exists for run.
3. Verify handoff payload contains expected contract fields.

Actions:
1. Re-emit Agent1 handoff (`POST /agent1/runs/{run_id}/handoff`).
2. Retry Agent2 consume.

### 2. Agent2 generation blocked by state guardrail
Symptoms:
- `POST /agent2/runs/{run_id}/generate` returns 400 with state eligibility error.

Checks:
1. Inspect current run state from `GET /agent2/runs/{run_id}`.
2. Verify state is `intake_ready` or `review_retry_requested`.

Actions:
1. If in review state, perform review action first.
2. If failed, inspect error and restart from intake if needed.

### 3. Retry limit exceeded
Symptoms:
- Review retry returns 400.
- Run state is `failed` with `AGENT2_RETRY_LIMIT_EXCEEDED`.

Checks:
1. `GET /agent2/runs/{run_id}` for `last_error_code`.
2. `GET /agent2/runs/{run_id}/timeline?order=asc` for `retry_limit_exceeded` event.

Actions:
1. Apply `edit_approve` or `approve` after corrected generation path in new run.
2. Re-run from intake for fresh run if needed.

### 4. Handoff emission idempotency confusion
Symptoms:
- Repeated handoff call returns created=false.

Checks:
1. Verify existing handoff in snapshot `handoffs`.
2. Verify `state` is `handoff_emitted`.

Actions:
1. Treat as success; message already emitted.
2. Continue with downstream Agent3 intake.

## Operational Endpoints
1. `GET /agent2/runs?backlog_item_id=<id>&limit=<n>`
2. `GET /agent2/runs/{run_id}`
3. `GET /agent2/runs/{run_id}/timeline?order=asc|desc`
4. `GET /agent2/observability/counters?backlog_item_id=<id>`

## Quick Health Checklist
1. MCP boundary sanity passes.
2. Latest run state transitions are visible in timeline.
3. Counters reflect expected success/retry/reject/failure trends.
4. Smoke test (`backend/tests/smoke_agent2_api.py`) passes.
