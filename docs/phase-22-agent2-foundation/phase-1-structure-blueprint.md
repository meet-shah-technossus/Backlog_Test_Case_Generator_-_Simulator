# Phase 1 Structure Blueprint (Agent2)

Status: Planned
Date: 2026-03-26

## Objective
Define clean modules for Agent2 before implementation.

## Backend Target Modules
1. contracts
- agent2_contracts.py
- review_contracts.py
- handoff_contracts.py

2. intake
- handoff_inbox_service.py
- handoff_repository.py

3. generation
- agent2_generation_service.py
- agent2_parser.py

4. review
- review_decision_service.py
- review_diff_service.py

5. handoff
- a2_to_a3_envelope_service.py
- a2_to_a3_dispatch_service.py

6. workflow
- agent2_orchestrator.py
- agent2_state_machine.py

7. persistence
- agent2_run_repository.py
- agent2_artifact_repository.py
- agent2_audit_repository.py

8. api
- agent2/router.py
- agent2/models.py

## Frontend Target Modules
1. src/features/agent2/api
2. src/features/agent2/hooks
3. src/features/agent2/components
4. src/features/agent2/state

## Exit Criteria
1. Folder and naming plan approved.
2. Keep/refactor/retire decisions documented.
3. Ready for contract and DB phases.
