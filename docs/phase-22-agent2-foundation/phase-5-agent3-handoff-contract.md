# Phase 5 Agent3 Handoff Contract

Status: Planned
Date: 2026-03-26

## Objective
Emit stable A2A handoff from Agent2 to Agent3.

## Work Items
1. Define Agent2ToAgent3Handoff contract (versioned).
2. Persist handoff envelope and delivery_status.
3. Add idempotency protection for repeated emission requests.
4. Add handoff endpoint and state transition to handoff_emitted.

## Acceptance Criteria
1. Handoff payload is reproducible from persisted artifacts.
2. Duplicate emission does not create extra active messages.
3. Timeline includes handoff emitted event.
