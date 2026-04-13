# Phase 14: Operator Access and Audit Controls

This phase adds secure operator controls and queue audit drill-down for production operations.

## Implemented

1. Operator API key enforcement for sensitive actions
- New config in `backend/config.py`:
  - `OPERATOR_REQUIRE_API_KEY` (default `false`)
  - `OPERATOR_API_KEY` (default empty)
- When enabled, these endpoints require `x-operator-key`:
  - `DELETE /run/tests/stop`
  - `DELETE /run/queue/{queue_id}`
  - `GET /run/queue/audit`

2. Queue audit API with filters
- New endpoint: `GET /run/queue/audit`
- Query filters:
  - `limit` (1..1000)
  - `stage` (example: `queue.run_end`)
  - `status` (`ok` or `error`)
  - `story_id`
- Backed by new store query method `get_queue_events(...)` in `backend/store.py`.

3. Operator UX in frontend Queue Ops
- Added operator key input in Queue Ops panel.
- Key stored in local storage under `operator_api_key`.
- Added audit timeline with filters:
  - story id
  - stage
  - status
- Cancel action now uses `x-operator-key` header.

4. Stop-run flow updated for protected endpoint
- Run stop call now includes optional `x-operator-key` from local storage.
- Properly surfaces authorization errors in the execution panel.

## Files changed

- `backend/config.py`
- `backend/routes/execute.py`
- `backend/store.py`
- `.env.example`
- `frontend/src/hooks/useQueueOps.js`
- `frontend/src/components/QueueOpsPanel.jsx`
- `frontend/src/components/ExecutionPanel.jsx`

## Notes

- Backward compatible by default because key enforcement is off unless enabled.
- This phase builds on Phase 12-13 queue reliability and operations visibility.
