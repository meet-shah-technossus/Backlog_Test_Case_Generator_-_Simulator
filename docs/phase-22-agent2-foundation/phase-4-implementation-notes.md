# Phase 4 Implementation Notes (Agent2 Human Review Loop)

## Scope Completed

- Implemented Agent2 review decisions: `approve`, `edit_approve`, `reject`, `retry`.
- Enforced reason code requirement for `reject` and `retry`.
- Persisted Agent2 review records with reviewer identity and decision metadata.
- Preserved original and edited artifacts by versioning on `edit_approve`.
- Added review diff API and reason code catalog API.

## Backend Changes

- Storage:
  - Added `agent2_reviews` table and index in `backend/app/infrastructure/store/schema.py`.
  - Added review CRUD methods in `backend/app/infrastructure/store/core.py`.
- Repository:
  - Added `add_review` and `list_reviews` in `backend/app/modules/agent2/db/run_repository.py`.
- Review service:
  - Expanded `backend/app/modules/agent2/review/review_service.py` with:
    - decision validation,
    - reason code catalog,
    - review diff builder.
- Workflow:
  - Added `backend/app/modules/agent2/workflow/use_cases/review_run.py` with:
    - review submit use case,
    - review diff use case.
  - Extended snapshot use case to include `reviews` and `review_diff`.
  - Updated orchestrator for review actions and reason catalog retrieval.
- API:
  - Added `POST /agent2/runs/{run_id}/review`.
  - Added `GET /agent2/runs/{run_id}/review-diff`.
  - Added `GET /agent2/review/reason-codes`.
  - Extended snapshot response model with review data.

## Frontend Changes

- Agent2 API client:
  - Added review and reason-code methods in `frontend/src/features/agent2/api/agent2Api.js`.
- Agent2 hook:
  - Added `reviewRun` and `loadReasonCodes` actions in `frontend/src/features/agent2/hooks/useAgent2Run.js`.
- Agent2 board:
  - Enabled review actions and editor controls in `frontend/src/features/agent2/components/Agent2Board.jsx`.
  - Added styling for review controls in `frontend/src/features/agent2/components/agent2.css`.

## State Behavior

- `review_pending` -> `review_rejected` for `reject`.
- `review_pending` -> `review_retry_requested` for `retry`.
- `review_pending` -> `handoff_pending` for `approve` and `edit_approve`.

## Validation

- Added sanity script `backend/tests/sanity_agent2_phase4.py` to validate:
  - reason code enforcement,
  - edit-and-approve artifact versioning,
  - review diff and reason-code endpoints.
