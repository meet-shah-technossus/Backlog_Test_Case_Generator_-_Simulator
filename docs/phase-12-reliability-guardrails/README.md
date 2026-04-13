# Phase 12: Reliability Guardrails

This phase adds queue-level reliability protections and operator-facing health visibility.

## Implemented

1. Execution timeout guardrail
- New env config: `EXECUTION_RUN_TIMEOUT_SECONDS` (default `900`).
- Queue worker monitors active run duration.
- If timeout is exceeded, the Playwright subprocess is stopped and the queue item is marked failed with timeout reason.

2. Pending-item TTL expiration
- New env config: `EXECUTION_PENDING_TTL_SECONDS` (default `3600`).
- Pending items that wait longer than TTL are auto-cancelled.
- Expired items are marked with `Expired in queue (pending TTL exceeded)`.

3. Queue health and operational metrics
- `GET /run/queue/health` endpoint added.
- Snapshot and health now include:
  - saturation
  - in-flight counts
  - oldest pending age
  - queue totals (`enqueued`, `completed`, `failed`, `cancelled`, `timed_out`)

4. Queue telemetry events
- Queue lifecycle now emits observability events:
  - `queue.enqueue`
  - `queue.run_start`
  - `queue.run_end`
  - `queue.cancel`
  - `queue.expire`

## API updates

- Existing:
  - `POST /run/tests`
  - `GET /run/queue`
  - `GET /run/queue/{queue_id}`
  - `DELETE /run/queue/{queue_id}`
- New:
  - `GET /run/queue/health`

## Notes

- Guardrails are fail-safe and backward-compatible with existing queue workflow.
- Timeout/TTL values can be tuned by environment without code changes.

## Examples

- `examples/reliability-curl-examples.sh`
- `examples/reliability-env-example.env`
