# Phase 13: Operator Experience

This phase brings reliability controls into the frontend so queue operations are visible and actionable without curl/manual API calls.

## Implemented

1. Queue Operations tab in frontend
- New tab: `Queue Ops`.
- New panel: `frontend/src/components/QueueOpsPanel.jsx`.
- Shows:
  - queue health (`healthy`/`degraded`)
  - saturation and in-flight counts
  - pending age and queue depth
  - cumulative totals (`enqueued`, `completed`, `failed`, `timed_out`, `cancelled`)
  - queue item list with status pills

2. Queue API hook
- New hook: `frontend/src/hooks/useQueueOps.js`.
- Polls:
  - `GET /run/queue?limit=50`
  - `GET /run/queue/health`
- Supports pending cancellation via `DELETE /run/queue/{queue_id}`.

3. Queue-aware Run Tests UX
- `ExecutionPanel` now reflects queued execution behavior.
- On `POST /run/tests`, stores `queue_id` and displays status banner.
- Polls `GET /run/queue/{queue_id}` to track transition:
  - `pending` -> `running` -> terminal (`completed`, `failed`, `cancelled`)

## Why this phase

Phase 12 added backend reliability guardrails; this phase ensures operators can monitor and react in real time from the app UI.

## Files changed

- `frontend/src/App.jsx`
- `frontend/src/components/ExecutionPanel.jsx`
- `frontend/src/components/QueueOpsPanel.jsx`
- `frontend/src/hooks/useQueueOps.js`
