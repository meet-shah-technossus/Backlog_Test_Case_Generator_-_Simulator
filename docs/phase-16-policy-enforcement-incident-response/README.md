# Phase 16: Policy Enforcement and Incident Response

This phase adds active policy enforcement for operator auth abuse and incident visibility APIs/UI.

## Implemented

1. Unauthorized-attempt policy controls
- New config in `backend/config.py`:
  - `OPERATOR_AUTH_FAILURE_WINDOW_SECONDS`
  - `OPERATOR_AUTH_MAX_FAILURES`
  - `OPERATOR_AUTH_LOCKOUT_SECONDS`
- Added to `.env.example` with defaults.

2. Source-level lockout service
- New service: `backend/operator_security_service.py`
- Tracks unauthorized attempts by request source (client host).
- Enforces temporary lockout after threshold failures in window.
- Emits telemetry events:
  - `operator.auth_denied`
  - `operator.auth_lockout`

3. Enforcement wired into operator authorization flow
- `backend/routes/execute.py` `_require_operator_access(...)` now:
  - blocks locked sources with `423 OPERATOR_LOCKED_OUT`
  - records unauthorized attempts
  - resets failure streak on successful authorized request

4. Incident response endpoints
- New endpoints in `backend/routes/execute.py`:
  - `GET /run/operator/security/status`
  - `GET /run/operator/security/events?limit=...`
- Protected for `viewer|executor|admin` roles.

5. Frontend incident visibility
- `frontend/src/hooks/useQueueOps.js` now fetches security status/events.
- `frontend/src/components/QueueOpsPanel.jsx` now shows:
  - lockout count
  - recent failure count
  - active lockouts with remaining time
  - security alert stream

## Notes

- Policy only applies when `OPERATOR_REQUIRE_API_KEY=true`.
- Lockouts are in-memory and reset on backend restart (intentional for lightweight control in current phase).

## Files changed

- `backend/config.py`
- `.env.example`
- `backend/operator_security_service.py`
- `backend/routes/execute.py`
- `frontend/src/hooks/useQueueOps.js`
- `frontend/src/components/QueueOpsPanel.jsx`
