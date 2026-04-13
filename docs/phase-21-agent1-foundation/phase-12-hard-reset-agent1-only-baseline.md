# Phase 12 - Hard Reset to Agent1-Only Baseline

Status: Completed
Date: 2026-03-26

## Objective
Remove legacy pre-existing Playwright/crawler/prompt/parser stack and keep only the currently valid Agent1 foundation plus minimum shared infrastructure.

## Structural Cleanup

### Backend routes
- Converted Agent1 routes to subfolder package:
  - `backend/app/api/routes/agent1/router.py`
  - `backend/app/api/routes/agent1/models.py`
- Root routes now keep only:
  - `health`
  - `agent1`

### Backend services
- Created Agent1 services subfolder:
  - `backend/app/services/agent1/backlog_service.py`
  - `backend/app/services/agent1/backlog_parser.py`
- Updated imports from legacy flat service paths.

### Legacy stack removed
- Removed old non-Agent1 routes and supporting modules:
  - generate/execute/artifacts/operator-security route files
  - old execution/playwright/crawler/prompt/parser services
  - queue/websocket/operator/playwright infrastructure modules
  - root `prompts/` folder
  - `seed_demo_script.py`
  - `backend/testforge.db`

### Frontend cleanup
- App simplified to Agent1 generate workflow only.
- Removed legacy script/run/results/ops panels and related hooks.
- Vite dev proxy reduced to active APIs only (`/health`, `/agent1`).

## Agent1 generation decoupling
- Replaced dependency on old `test_case_generator` with Agent1-local generation service:
  - `backend/app/modules/agent1/workflow/services/case_generation_service.py`
- Agent1 now generates baseline suites from canonical backlog item data without legacy prompt/parser pipeline.

## Store decomposition
- Split store concerns into separate files:
  - `backend/app/infrastructure/store.py` (core store class)
  - `backend/app/infrastructure/store_schema.py` (SQL schema)
  - `backend/app/infrastructure/store_rows.py` (row/JSON helpers)
- `store.py` reduced to Agent1/backlog/telemetry required operations only.

## Validation
- Backend compile check passed (`python -m compileall app`).
- Frontend build check passed (`npm run build`).

## Baseline after reset
- Active backend scope: Health + Agent1 intake/run/review/handoff/history.
- Active frontend scope: Agent1 board workflow.
- OpenAI client retained for future stepwise rebuild.
