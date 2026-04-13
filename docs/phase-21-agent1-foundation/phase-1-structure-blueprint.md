# Phase 1 Structure Blueprint (Agent 1 + MCP Intake)

Status: Target structure approved for next implementation phase
Scope date: 2026-03-26

## 1. Objective of Phase 1
Define clean production-grade module boundaries for Agent 1 vertical slice without coding changes yet.

## 2. Current Structure Observations
Backend currently has key files that overlap responsibilities:
- API routes already split under app/api/routes
- Backlog service currently handles API fetch + file load + in-memory cache
- Generation logic and orchestration are mixed in route/service flows
- No dedicated MCP tool registry module for backlog intake
- Frontend has tab panels but no explicit agent pipeline state timeline for Agent 1 review lifecycle

## 3. Target Backend Logical Modules
Proposed under app/modules/agent1 (or equivalent domain package):

1. contracts
- backlog_contracts.py
- agent1_contracts.py
- review_contracts.py
- handoff_contracts.py

2. intake
- backlog_source_service.py
- backlog_normalization_service.py
- backlog_repository.py

3. mcp
- mcp_tool_registry.py
- mcp_backlog_tools.py
- mcp_security_policy.py

4. generation
- agent1_generation_service.py
- agent1_prompt_service.py
- agent1_response_parser.py

5. review
- review_decision_service.py
- review_diff_service.py
- review_policy_service.py

6. handoff
- a2a_envelope_service.py
- a2a_dispatch_service.py
- a2a_delivery_store.py

7. workflow
- agent1_workflow_orchestrator.py
- agent1_state_machine.py
- retry_strategy_service.py

8. persistence
- agent1_run_repository.py
- agent1_artifact_repository.py
- agent1_audit_repository.py

9. api
- agent1_routes.py
- backlog_intake_routes.py
- review_routes.py
- handoff_routes.py

## 4. Target Frontend Structure
Proposed under src/features/agent1:

1. api
- agent1Api.js
- backlogIntakeApi.js
- reviewApi.js

2. hooks
- useAgent1Run.js
- useBacklogIntake.js
- useAgent1Review.js
- useAgent1Timeline.js

3. components
- Agent1RunBoard.jsx
- BacklogSourceSelector.jsx
- Agent1GenerationPanel.jsx
- Agent1ReviewPanel.jsx
- Agent1RetryPanel.jsx
- Agent1HandoffStatus.jsx
- Agent1Timeline.jsx

4. state
- agent1Store.js (or context reducer)

5. pages integration
- integrate into existing tab with explicit Agent 1 stage visibility

## 5. Keep / Refactor / Retire Plan (Current Files)

Keep as foundation (reuse likely):
- app/services/backlog_parser.py
- app/domain/models.py (parts)
- app/infrastructure/openai_client.py
- app/infrastructure/telemetry_service.py
- app/core/container.py (with extension)
- frontend/src/contexts/ToastContext.jsx

Refactor (split responsibilities):
- app/services/backlog_service.py -> split into intake + repository + source adapters
- app/api/routes/backlog.py -> convert to MCP-backed intake routes
- frontend/src/hooks/useBacklog.js -> split by source intake, reviewable run state, and timeline hooks
- frontend/src/components/GeneratePanel.jsx -> isolate Agent 1 generation/review subcomponents

Retire after replacement and parity checks:
- direct file-based sample loading in routes (tests/sample_backlog.json coupling)
- implicit in-memory-only backlog cache behavior as primary state

## 6. API Surface Blueprint (Phase 1 Scope)
1. POST /agent1/intake/load
- body: { source_type: api|sample_db, source_ref? }
- returns canonical backlog list and intake audit id

2. POST /agent1/runs
- body: { backlog_item_id, run_context }
- starts Agent 1 generation

3. GET /agent1/runs/{run_id}
- returns run status + latest artifact + review status

4. POST /agent1/runs/{run_id}/review
- body: { decision, reason_code, edited_payload? }

5. POST /agent1/runs/{run_id}/retry
- body: { scope, reason_code }

6. POST /agent1/runs/{run_id}/handoff
- emits A2A envelope for Agent 2

7. GET /agent1/runs/{run_id}/timeline
- ordered stage + audit events for frontend traceability

## 7. Database Blueprint (Phase 1 Scope)
1. backlog_items
- canonical backlog records for both API and sample sources

2. agent1_runs
- run metadata and state

3. agent1_artifacts
- versioned generation artifacts

4. agent1_reviews
- human review decisions and edits

5. agent1_handoffs
- A2A envelope records and delivery status

6. agent1_audit_events
- append-only event log

## 8. Latency and Reliability Plan
1. Cache canonical backlog reads in DB-backed short-lived cache table or timestamp strategy.
2. Keep latest approved artifact denormalized for fast read endpoints.
3. Use index on (run_id, created_at) for timeline and artifact retrieval.
4. Do not rely on frontend local state for persistence.

## 9. Naming and Code Quality Rules
1. Names must reflect action and domain intent.
2. One service one responsibility.
3. No route should include prompt logic, parsing logic, and persistence logic in one place.
4. Shared utilities only for true cross-module concerns.

## 10. Phase 1 Exit Criteria
1. Target module structure is documented and approved.
2. Keep/refactor/retire decisions are explicit.
3. API and DB blueprints are fixed.
4. Ready to start implementation phase with minimal ambiguity.
