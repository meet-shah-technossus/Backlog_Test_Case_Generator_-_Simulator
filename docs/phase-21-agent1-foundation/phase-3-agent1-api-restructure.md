# Phase 3 Start (Agent 1 API + Folder Restructure)

Status: In progress (backend foundations implemented)
Date: 2026-03-26

## Completed in this step
1. Created explicit Agent 1 package folders for traceability:
- `backend/app/modules/agent1/mcp`
- `backend/app/modules/agent1/db`
- `backend/app/modules/agent1/workflow`

2. Split responsibilities into separate files:
- MCP contracts and intake service
- Backlog repository
- Run repository
- State machine
- Workflow orchestrator
- Dedicated Agent 1 route module

3. Added new Phase 3 Agent 1 API surface:
- `POST /agent1/intake/load`
- `POST /agent1/runs`
- `POST /agent1/runs/{run_id}/generate`
- `GET /agent1/runs/{run_id}`
- `POST /agent1/runs/{run_id}/review`
- `POST /agent1/runs/{run_id}/retry`
- `POST /agent1/runs/{run_id}/handoff`
- `GET /agent1/runs/{run_id}/timeline`

4. Registered new route in app startup and route exports.
5. Removed earlier flat Agent 1 scaffolding files to avoid mixed patterns.

## Validation results
1. Python compile checks passed for all changed files.
2. Runtime smoke test passed for:
- MCP intake from sample_db
- Agent 1 run creation
- Agent 1 retry transition

## Next work (remaining in Phase 3)
1. Frontend integration for new Agent 1 APIs and timeline visibility.
2. Human review UI actions mapped to `/review` and `/retry`.
3. Optional enhancement: normalize generation events for richer progress panel.
