# Phase 15: Role Separation and Audit Integrity

This phase hardens production operations with role-based access control and tamper-evident audit verification.

## Implemented

1. Role-based operator keys
- Added role keys in `backend/config.py`:
  - `OPERATOR_VIEWER_KEY`
  - `OPERATOR_EXECUTOR_KEY`
  - `OPERATOR_ADMIN_KEY`
- Existing `OPERATOR_API_KEY` remains as backward-compatible admin fallback.
- Authorization model in `backend/routes/execute.py`:
  - Viewer: queue audit + verify + role introspection
  - Executor: viewer permissions + stop run + cancel queue item
  - Admin: executor permissions

2. New operator introspection endpoint
- `GET /run/operator/whoami`
- Resolves caller role from `x-operator-key` and returns effective permissions.

3. Signed observability event chain
- Added audit-signing config:
  - `AUDIT_SIGNING_SECRET`
- Store now signs each observability event with HMAC-SHA256 over canonical payload + previous signature.
- Added event columns (auto-migrated):
  - `prev_signature`
  - `event_signature`

4. Audit chain verification endpoint
- `GET /run/queue/audit/verify?limit=500&story_id=...`
- Verifies queue audit event signature chain and returns validity + invalid event IDs.

5. Queue Ops frontend role/verify UX
- Queue Ops panel now supports:
  - role refresh (`/run/operator/whoami`)
  - audit chain verification (`/run/queue/audit/verify`)
  - role badge + verify status chips

## Files changed

- `backend/config.py`
- `backend/store.py`
- `backend/routes/execute.py`
- `.env.example`
- `frontend/src/hooks/useQueueOps.js`
- `frontend/src/components/QueueOpsPanel.jsx`

## Notes

- Role enforcement only applies when `OPERATOR_REQUIRE_API_KEY=true`.
- Audit verification requires `AUDIT_SIGNING_SECRET` to be configured.
- Existing installations are migrated safely via additive columns.
