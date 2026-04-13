# Agent 5 Completion Plan (Architecture + UX + Governance)

## Scope Lock
1. Light and dark theme support across all pages and components.
2. Retry logic redesign for every agent that supports retry.
3. Human reviewer approval workflow before retry execution.
4. Real LLM re-run on retry, not only state flip.
5. Database policy where retry outputs become active latest outputs.
6. Business ID redesign from random IDs to readable incremental IDs.
7. Backfill and migration for historical records and references.
8. Architecture hardening checklist with no open blind spots.
9. Frontend simplification with reduced manual clicking and guided automation.

## Phase 0: Architecture Decision Freeze (Required)
1. Keep internal UUID primary keys for integrity and references.
2. Add user-facing immutable business IDs for all major entities.
3. Use business IDs in UI and user-facing API payloads.
4. Hide raw UUIDs in operator UX.
5. Approve migration rollback and compatibility policy.
6. Simplification requirement: define one common navigation identity pattern across all pages.
7. Acceptance:
8. Decision signed.
9. Naming conventions frozen.
10. Rollback strategy approved.

## Phase 1: Unified Retry Governance Model
1. Define one retry lifecycle used by all agents.
2. States: retry_requested, retry_review_pending, retry_approved, retry_rejected, retry_running, retry_completed, retry_failed.
3. Required metadata: requester, reason, reviewer, decision, approval timestamps, attempt count.
4. Enforce rule: retry execution only after reviewer approval.
5. Add cooldown and retry limit policies.
6. Simplification requirement: one shared retry component and one shared decision modal in frontend.
7. Acceptance:
8. Shared retry state machine is finalized.
9. All agent-specific retry paths map to this model.

## Phase 2: Reviewer Workflow and Authorization
1. Introduce explicit reviewer role and permission checks.
2. Block self-approval unless policy allows it.
3. Support manual reviewer assignment and rule-based assignment.
4. Add escalation fallback for missing reviewer.
5. Audit every request, assignment, approval, rejection.
6. Simplification requirement: one inbox queue for all pending retry approvals.
7. Acceptance:
8. Retry approval APIs enforce reviewer rules.
9. Reviewer actions are fully auditable.

## Phase 3: True Retry Execution Pipeline
1. Retry button creates request, not execution.
2. Approval triggers real regeneration and re-execution.
3. Rebuild prompt/context from latest active artifacts.
4. Invoke LLM and dependent downstream stages.
5. Store each retry attempt as a revisioned attempt.
6. Mark superseded versus active outputs.
7. Simplification requirement: one-click "approve and run" option for authorized reviewers.
8. Acceptance:
9. Every retry includes real execution traces and outputs.
10. No retry can complete without attempt artifacts.

## Phase 4: Active Revision Data Policy
1. Keep complete revision history for traceability.
2. Promote one revision as active_current.
3. On successful retry, new revision becomes active by default.
4. APIs return active revision by default with optional history view.
5. Ensure scripts, reasoning, steps, and summaries resolve to active revision.
6. Simplification requirement: "Current vs Previous" diff view with promote/revert actions.
7. Acceptance:
8. UI always shows latest active output.
9. Historical lineage remains queryable.

## Phase 5: Business ID Redesign
1. Define namespaces by entity: run, test case, step, script, reasoning, evidence.
2. Use monotonic sequence with fixed-width formatting.
3. Add unique constraints and indexes for business IDs.
4. Preserve UUID-to-business-id mapping.
5. Simplification requirement: universal quick-jump by business ID from global header.
6. Acceptance:
7. All user-visible entities have stable business IDs.
8. Lists, filters, and links work with business IDs.

## Phase 6: Historical Backfill and Migration
1. Backfill business IDs for existing data in deterministic order.
2. Update historical references to new business IDs in UI payloads.
3. Repair old links for scripts, reasoning, steps, and evidence.
4. Validate no orphan links and no duplicate business IDs.
5. Simplification requirement: add migration-status dashboard for operator verification.
6. Acceptance:
7. Existing records are navigable via business IDs.
8. Migration rollback path is verified.

## Phase 7: API Contract Completion
1. Standardize payload envelope across agents.
2. Include internal_id, business_id, current_revision, retry_status, review_status.
3. Add retry APIs: request, assign reviewer, approve/reject, execute, history.
4. Add idempotency keys for retry execution starts.
5. Maintain backward compatibility during deprecation window.
6. Simplification requirement: frontend consumes one normalized API adapter layer.
7. Acceptance:
8. Unified retry contract is available on all applicable agents.
9. Legacy clients remain functional during transition.

## Phase 8: Full Theming System (Light and Dark)
1. Introduce design tokens with semantic color roles.
2. Implement theme provider with persistence and system preference fallback.
3. Ensure all pages and components support both themes.
4. Validate chart, table, badge, code block, and panel contrast.
5. Simplification requirement: one global theme toggle and no page-specific theme divergence.
6. Acceptance:
7. Full dual-theme coverage.
8. Accessibility contrast checks pass.

## Phase 9: Frontend Navigation and Workflow Simplification
1. Replace dense layout with guided three-column workspace.
2. Add action queue for pending approvals, failed runs, and stale runs.
3. Introduce progressive disclosure for advanced diagnostics.
4. Add breadcrumbs: Story > Agent > Run > Revision.
5. Add global status legend and clear action affordances.
6. Add bulk actions for repetitive operator operations.
7. Simplification requirement: reduce operator flow to minimal clicks for common actions.
8. Acceptance:
9. New user can complete core flow with minimal navigation friction.
10. Advanced diagnostics stay available but unobtrusive.

## Phase 10: Architecture Hardening
1. Add transaction boundaries for state plus revision updates.
2. Prevent double-approval and duplicate retry starts.
3. Normalize cross-agent error taxonomy.
4. Add policy configuration by agent and environment.
5. Add immutable audit trails for reviewer actions.
6. Add retention and purge policy for historical revisions.
7. Simplification requirement: auto-recovery jobs for stale and partially completed flows.
8. Acceptance:
9. Architecture checklist has no unresolved critical items.

## Phase 11: Testing and Release Readiness
1. Add unit, API, integration, migration, and UI workflow tests.
2. Add retry governance and reviewer approval test matrices.
3. Add migration integrity tests for historical business ID backfill.
4. Add theme visual regression checks.
5. Add load testing for retry and approval pipelines.
6. Simplification requirement: release checklist automation and preflight validation command.
7. Acceptance:
8. All quality gates pass.
9. Release and rollback runbooks are complete.

## Global Simplification Principles (Applied to Every Phase)
1. Prefer automation-first and queue-based processing over manual repetitive actions.
2. Collapse multi-step user actions into single guided actions where safe.
3. Surface only next required action by default.
4. Keep advanced details behind expandable diagnostics.
5. Preserve full auditability even when UX is simplified.

## Definition of Done
1. Retry is reviewer-governed and truly re-executes LLM workflows.
2. Latest active revisions are always visible and persisted.
3. Business IDs are stable, readable, and fully backfilled.
4. All pages support light and dark themes consistently.
5. Frontend flow is simplified, guided, and low-click.
6. Architecture, migration, and release checklists are complete.
