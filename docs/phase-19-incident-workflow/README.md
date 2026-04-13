# Phase 19: Incident Workflow

This phase introduces full incident lifecycle operations for operator security events.

## Implemented

1. Incident state model in persistence
- `operator_security_events` now tracks:
  - `state` (`open`, `acknowledged`, `resolved`)
  - `acked_by`, `acked_at`
  - `resolved_by`, `resolved_at`, `resolution_note`
  - `last_updated_at`

2. Lifecycle APIs
- `GET /run/operator/security/incidents/open`
- `POST /run/operator/security/incidents/{incident_id}/ack`
- `POST /run/operator/security/incidents/{incident_id}/resolve`

3. UI actions
- Queue Ops now supports Ack and Resolve actions directly from persistent history.

## Files changed

- `backend/store.py`
- `backend/routes/execute.py`
- `frontend/src/hooks/useQueueOps.js`
- `frontend/src/components/QueueOpsPanel.jsx`
