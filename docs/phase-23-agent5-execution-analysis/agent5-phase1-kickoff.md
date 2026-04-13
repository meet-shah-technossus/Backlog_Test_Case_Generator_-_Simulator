# Agent5 Phase 1 Kickoff

## Objective
Define and freeze unified retry governance that applies to all agents with retry support.

## Unified Retry Lifecycle
1. retry_requested
2. retry_review_pending
3. retry_approved
4. retry_rejected
5. retry_running
6. retry_completed
7. retry_failed

## Mandatory Retry Metadata
1. requested_by
2. requested_at
3. reason_code
4. reason_text
5. reviewer_id
6. reviewer_decision
7. reviewer_comment
8. approved_at
9. retry_attempt_number
10. cooldown_until

## Rules
1. Retry request does not execute LLM work.
2. Execution can start only after reviewer approval.
3. Requester cannot self-approve unless policy allows.
4. Every transition emits timeline and audit events.
5. Retry limits and cooldown are policy-driven per agent.

## Simplification Objectives in Phase 1
1. One shared retry API contract for all agents.
2. One shared frontend retry request component.
3. One shared review decision component.
4. One pending approvals queue across agents.

## Required Outputs for Phase 1 Completion
1. Retry state machine specification approved.
2. API contract draft for retry endpoints approved.
3. Policy matrix drafted by agent type.
4. Test matrix draft for retry transitions completed.

## Exit Criteria
1. All agents with retry can map existing behavior to the unified model.
2. No direct execution path remains from retry button without review gate.
3. Phase 2 can implement reviewer roles without contract ambiguity.
