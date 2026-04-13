# Phase 11 - Legacy Pruning and Non-Agent1 Decomposition

Status: Completed
Date: 2026-03-26

## Objective
Prune unnecessary legacy layers outside Agent 1 and continue decomposition of large non-Agent1 files while preserving currently working flows.

## Legacy Pruning

### Removed backend legacy abstractions and dead code
- Removed CQRS package (`backend/app/cqrs`) after replacing execution route usage with direct queue-manager calls.
- Removed unused evaluation surface:
  - `backend/app/api/routes/evaluation.py`
  - `backend/app/services/evaluation_service.py`
- Removed generated/non-source artifacts from backend app tree:
  - all `__pycache__` directories under `backend/app`
  - redundant `backend/app/infrastructure/testforge.db` (canonical runtime DB remains `backend/testforge.db`).

## Non-Agent1 Decomposition

### Backend route split
- Created `backend/app/api/routes/operator_security.py` and moved operator/security endpoints out of `execute.py`.
- Kept path compatibility (`/run/operator/...`) unchanged.
- Updated app route registration to include the new router.

### Frontend decomposition
- Extracted ScriptPanel utility/constants to `frontend/src/components/scriptPanelUtils.js`.
- Slimmed `frontend/src/components/ScriptPanel.jsx` by moving URL resolution, error formatting, and pipeline display helper logic to the new utility module.

## Size Impact Snapshot
- `backend/app/api/routes/execute.py`: 549 -> 325 lines.
- `frontend/src/components/ScriptPanel.jsx`: 669 -> 557 lines.
- Added focused modules:
  - `backend/app/api/routes/operator_security.py`
  - `frontend/src/components/scriptPanelUtils.js`

## Validation
- Backend compile check: passed (`python -m compileall app`).
- Frontend build check: passed (`npm run build`).

## Notes on Architecture Buckets
- `domain`: canonical shared entities/types across services and persistence.
- `infrastructure`: concrete adapters (DB store, OpenAI client, queue, runner, ws).
- CQRS layer was removed as unnecessary indirection for this codebase stage.

## Remaining Optional Hardening (Separate Track)
- Further decomposition of `backend/app/infrastructure/store.py` (still large).
- Additional decomposition of other large frontend panels if desired.
