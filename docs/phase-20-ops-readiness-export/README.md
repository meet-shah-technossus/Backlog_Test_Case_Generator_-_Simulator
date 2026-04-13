# Phase 20: Ops Readiness and Export

This phase provides operational closure tools for audits and release readiness.

## Implemented

1. Security export API
- `GET /run/operator/security/export?limit=...&state=...`
- Returns summary + incident dataset for offline audit handling.

2. Readiness API
- `GET /run/operator/security/readiness`
- Checks:
  - operator auth enabled
  - audit signing enabled
  - webhook configured
  - open incidents within threshold (`OPERATOR_SECURITY_OPEN_INCIDENT_THRESHOLD`)

3. Frontend operational controls
- Queue Ops now includes:
  - readiness chip
  - export JSON action
  - open incident visibility

## Files changed

- `backend/config.py`
- `.env.example`
- `backend/routes/execute.py`
- `frontend/src/hooks/useQueueOps.js`
- `frontend/src/components/QueueOpsPanel.jsx`
