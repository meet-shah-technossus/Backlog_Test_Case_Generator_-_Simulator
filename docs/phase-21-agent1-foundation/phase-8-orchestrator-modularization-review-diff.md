# Phase 8 (Orchestrator Modularization + Review Diff)

Status: Completed
Date: 2026-03-26

## Why this phase
The Agent1 orchestrator file was growing too large and reducing traceability. This phase modularizes orchestration into use-case and support-service files and adds review diff visibility for auditability.

## Architecture improvements completed
1. Introduced workflow subfolders:
- `workflow/use_cases`
- `workflow/services`

2. Split long orchestrator logic into focused use-cases:
- create run
- generate run
- submit review
- retry run
- emit handoff
- get run snapshot

3. Extracted support services:
- human edited artifact persistence
- artifact-to-artifact review diff summary

4. Kept `orchestrator.py` as a thin coordinator/facade.

## Files added
- `backend/app/modules/agent1/workflow/use_cases/create_run.py`
- `backend/app/modules/agent1/workflow/use_cases/generate_run.py`
- `backend/app/modules/agent1/workflow/use_cases/review_run.py`
- `backend/app/modules/agent1/workflow/use_cases/retry_run.py`
- `backend/app/modules/agent1/workflow/use_cases/handoff_run.py`
- `backend/app/modules/agent1/workflow/use_cases/get_snapshot.py`
- `backend/app/modules/agent1/workflow/services/review_edit_service.py`
- `backend/app/modules/agent1/workflow/services/review_diff_service.py`

## Files updated
- `backend/app/modules/agent1/workflow/orchestrator.py`
- `backend/app/modules/agent1/db/run_repository.py`
- `frontend/src/features/agent1/components/Agent1RunBoard.jsx`

## Functional enhancement
Added snapshot-level review diff summary (`review_diff`) based on latest two artifact versions, and surfaced it in Agent1 frontend panel.

## Validation
1. Backend compile checks passed.
2. Frontend build passed.
3. Diagnostics checks for all changed files report no errors.
