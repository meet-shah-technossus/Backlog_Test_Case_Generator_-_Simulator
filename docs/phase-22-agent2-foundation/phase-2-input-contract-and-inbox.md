# Phase 2 Input Contract and Inbox Persistence

Status: Planned
Date: 2026-03-26

## Objective
Create deterministic Agent2 input handling from Agent1 handoff records.

## Work Items
1. Define Agent2InputEnvelope contract.
2. Add agent2_runs and agent2_inbox tables.
3. Implement idempotent consume operation by message_id.
4. Add API endpoint to start Agent2 run from inbox item.
5. Add timeline/audit event for intake acceptance.

## Acceptance Criteria
1. Duplicate handoff messages do not create duplicate Agent2 runs.
2. Each consumed input maps to one traceable run_id.
3. Intake errors provide stable error codes and messages.
