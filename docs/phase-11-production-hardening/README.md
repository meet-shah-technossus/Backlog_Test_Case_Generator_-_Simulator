# Phase 11: Production Hardening

This phase adds queueing, backpressure, and safer execution operations for multi-user/production-like usage.

## Implemented

1. Execution queue manager
- New `backend/run_queue_service.py`
- Queues run requests and executes them sequentially.
- Maintains item states:
  - `pending`
  - `running`
  - `completed`
  - `failed`
  - `cancelled`

2. Backpressure controls
- Configurable via `.env`:
  - `EXECUTION_MAX_QUEUE_SIZE` (default `20`)
  - `EXECUTION_QUEUE_POLL_MS` (default `500`)
- Queue rejects new entries when at capacity.

3. Execute route upgrades
- `POST /run/tests` now queues requests and returns `queue_id`.
- `GET /run/tests/status` includes queue snapshot.
- New queue endpoints:
  - `GET /run/queue?limit=200`
  - `GET /run/queue/{queue_id}`
  - `DELETE /run/queue/{queue_id}` (cancel pending item)

## Notes

- Existing script/run behavior remains compatible.
- `DELETE /run/tests/stop` still stops currently running Playwright process.
- Running queue items cannot be cancelled via queue delete; use stop endpoint.

## Examples

- `examples/queue-curl-examples.sh`
- `examples/production-env-example.env`
