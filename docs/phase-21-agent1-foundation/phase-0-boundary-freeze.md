# Phase 0 Boundary Freeze (Agent 1 Vertical Slice)

Status: Approved baseline for implementation planning
Scope date: 2026-03-26

## 1. Objective of Phase 0
Freeze exact boundaries for the first delivery slice:
- MCP intake for backlog
- Agent 1 test case generation
- Human review/edit/approve loop
- A2A handoff event to Agent 2
- Full persistence and auditability

No implementation changes are performed in Phase 0.

## 2. In-Scope Capabilities (Must Exist in Slice 1)
1. Backlog intake through MCP abstraction only.
2. Dual source support:
- External backlog API (via MCP tool)
- Sample backlog records from database (via MCP tool)
3. Agent 1 generation pipeline (requirement -> structured test cases).
4. Human-in-the-loop controls per generation result:
- approve
- edit-and-approve
- reject with reason
- retry (scoped)
5. A2A handoff message emitted after approval for Agent 2 consumption.
6. Frontend visibility of all above states without backend-only inspection.
7. Database persistence for runs, artifacts, review actions, retries, and handoff logs.

## 3. Out-of-Scope for This Slice
1. Agent 2 logic execution (only handoff contract is included).
2. Crawler/Mapping/Script/Execution changes (Agents 3 to 5).
3. Profile/settings/theme feature expansion.
4. Broad microservice deployment split (logical modularization only in this phase).

## 4. Stage Boundaries for Agent 1 Slice
1. Intake stage
- Input artifact: raw backlog payload from selected source
- Output artifact: canonical backlog item list

2. Generation stage (Agent 1)
- Input artifact: approved backlog item and acceptance criteria
- Output artifact: test case artifact vN

3. Human review gate
- Input artifact: test case artifact vN
- Output artifact: approved/rejected/retry decision + optional edited artifact

4. Handoff stage (A2A envelope only)
- Input artifact: approved artifact
- Output artifact: handoff message persisted and marked ready for Agent 2

## 5. Source-of-Truth Policies
1. Database is source of truth for persisted run state and human actions.
2. Frontend state is derived from backend APIs, not local-only transient state.
3. In-memory cache may exist for acceleration but cannot be sole source of truth.
4. Every state mutation must produce an audit event.

## 6. Required Data Contracts (Freeze)
1. BacklogItemCanonical
- backlog_item_id
- title
- description
- acceptance_criteria[]
- source_type (api|sample_db)
- source_ref

2. Agent1TestCaseArtifact
- run_id
- story_id/backlog_item_id
- artifact_version
- generated_at
- model_metadata
- test_cases[]
- confidence_notes

3. HumanReviewDecision
- run_id
- stage
- decision (approve|edit_approve|reject|retry)
- reason_code
- reviewer_id
- edited_payload (optional)
- decided_at

4. A2AHandoffMessage
- message_id
- run_id
- trace_id
- from_agent (agent_1)
- to_agent (agent_2)
- task_type (generate_steps)
- contract_version
- payload
- delivery_status

## 7. State Machine Freeze (Agent 1 Slice)
Allowed states:
- intake_pending
- intake_ready
- agent1_generating
- agent1_generated
- review_pending
- review_approved
- review_rejected
- review_retry_requested
- handoff_pending
- handoff_emitted
- failed

Transition rule:
Only orchestrator/workflow service can move state forward.

## 8. Human Gate Requirements (Non-Negotiable)
1. Review is mandatory at each stage included in this slice.
2. No automatic progression from generation to handoff.
3. Rejection and retry must capture reason code.
4. Edited outputs must retain both original and modified versions.

## 9. Operational Constraints
1. Sequential execution only.
2. Deterministic IDs and traceability for each run.
3. Idempotent retries where possible (no duplicate handoff emission).
4. All external/system interactions routed through MCP-facing adapters.

## 10. Acceptance Criteria for Phase 0 Completion
1. Scope and boundaries are documented and stable.
2. In/out of scope is explicit.
3. State machine and contracts are defined.
4. Human review rules are formalized.
5. Ready to start Phase 1 structural blueprint and then implementation.
