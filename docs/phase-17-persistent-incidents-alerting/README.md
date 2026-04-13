# Phase 17: Persistent Incidents and Alerting

This phase persists operator security incidents across restarts and adds webhook-based alert delivery.

## Implemented

1. Persistent operator incident store
- Added `operator_security_events` table in `backend/store.py`.
- New store APIs:
  - `log_operator_security_event(...)`
  - `get_recent_operator_security_events(...)`
  - `get_operator_security_summary(...)`

2. Security incident webhook alerts
- New config in `backend/config.py`:
  - `OPERATOR_ALERT_WEBHOOK_URL`
  - `OPERATOR_ALERT_TIMEOUT_SECONDS`
- New service `backend/operator_alert_service.py` posts incident payloads to webhook.

3. Incident persistence and alert wiring
- `backend/operator_security_service.py` now:
  - logs every unauthorized/lockout event to SQLite history
  - triggers webhook alert delivery (best effort)
  - emits telemetry for alert delivery success/failure

4. New incident response APIs
- Added in `backend/routes/execute.py`:
  - `GET /run/operator/security/history`
  - `GET /run/operator/security/summary`
  - `POST /run/operator/security/alerts/test` (admin)

5. Frontend visibility for persisted incidents
- `frontend/src/hooks/useQueueOps.js` now fetches:
  - security history
  - security summary
  - test-alert action
- `frontend/src/components/QueueOpsPanel.jsx` now shows:
  - persistent incident summary metrics
  - persistent incident history list
  - test-alert trigger button

## Notes

- Webhook delivery is best effort and does not block core auth handling.
- Persistent history complements in-memory lockout state from Phase 16.

## Files changed

- `backend/config.py`
- `.env.example`
- `backend/store.py`
- `backend/operator_alert_service.py`
- `backend/operator_security_service.py`
- `backend/routes/execute.py`
- `frontend/src/hooks/useQueueOps.js`
- `frontend/src/components/QueueOpsPanel.jsx`
