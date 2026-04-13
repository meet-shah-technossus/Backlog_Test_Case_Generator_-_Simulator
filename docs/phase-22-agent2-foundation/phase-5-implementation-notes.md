# Phase 5 Implementation Notes (Agent2 Agent3 Handoff)

## Scope Completed

- Implemented Agent2 -> Agent3 handoff contract envelope.
- Added idempotent handoff persistence for repeated emission requests.
- Added handoff API endpoint and run state transition to `handoff_emitted`.
- Added handoff visibility in Agent2 snapshot and frontend handoff panel.

## Backend Changes

- Contracts:
  - Added `Agent2ToAgent3HandoffEnvelope` in `backend/app/modules/agent2/contracts/models.py`.
- Handoff service:
  - Implemented deterministic message ID and payload builder in `backend/app/modules/agent2/handoff/handoff_service.py`.
- Storage:
  - Added `agent2_handoffs` table and index in `backend/app/infrastructure/store/schema.py`.
  - Added store methods for idempotent insert and list in `backend/app/infrastructure/store/core.py`.
- Repository:
  - Added `add_handoff` and `list_handoffs` in `backend/app/modules/agent2/db/run_repository.py`.
- Workflow:
  - Added `emit_handoff` use case in `backend/app/modules/agent2/workflow/use_cases/handoff_run.py`.
  - Included `handoffs` in snapshot payload in `backend/app/modules/agent2/workflow/use_cases/get_run_snapshot.py`.
  - Wired orchestrator `handoff` action in `backend/app/modules/agent2/workflow/orchestrator.py`.
- API:
  - Added `POST /agent2/runs/{run_id}/handoff` in `backend/app/api/routes/agent2/router.py`.
  - Added `POST /agent2/agent1-runs/{agent1_run_id}/consume` to ingest Agent1 handoff via MCP bridge and contract parse.
  - Added `Agent2EmitHandoffResponse` and updated snapshot model in `backend/app/api/routes/agent2/models.py`.

## MCP Boundary Alignment

- Added explicit MCP bridge for Agent1 -> Agent2 handoff parsing:
  - `backend/app/modules/agent2/mcp/agent1_handoff_mcp_service.py`
- Added MCP data-plane adapters for repository persistence calls:
  - `backend/app/modules/agent1/mcp/backlog_store_mcp_service.py`
  - `backend/app/modules/agent1/mcp/run_store_mcp_service.py`
  - `backend/app/modules/agent2/mcp/inbox_store_mcp_service.py`
  - `backend/app/modules/agent2/mcp/run_store_mcp_service.py`

## Frontend Changes

- API client:
  - Added `emitAgent2Handoff` in `frontend/src/features/agent2/api/agent2Api.js`.
- Hook:
  - Added `handoffRun` in `frontend/src/features/agent2/hooks/useAgent2Run.js`.
- UI:
  - Enabled handoff panel action and summary display in `frontend/src/features/agent2/components/Agent2Board.jsx`.
  - Added handoff styles in `frontend/src/features/agent2/components/agent2.css`.

## Behavior Notes

- Handoff is allowed only from `handoff_pending` or `handoff_emitted`.
- Repeated handoff emit calls are idempotent and do not create duplicate active messages.
- Timeline captures both fresh emits and idempotent reuse events.

## Validation

- Added `backend/tests/sanity_agent2_phase5.py` for:
  - approve -> handoff emit path,
  - idempotent second emission,
  - snapshot state and handoff list checks.
