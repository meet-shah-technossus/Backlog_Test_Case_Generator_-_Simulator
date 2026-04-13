# Agent5 Phase 0 Kickoff

## Objective
Lock architectural decisions required before broad implementation starts.

## Decisions Finalized
1. Internal UUID keys remain primary keys for all tables.
2. New business IDs become canonical user-facing identifiers.
3. UI and external API payloads prioritize business IDs.
4. Raw UUIDs remain internal and hidden in normal operator views.
5. Backfill and compatibility mapping are mandatory for historical records.

## Business ID Naming Baseline
1. AG1-RUN-0001 style for runs.
2. AG2-TC-0001 style for test cases.
3. AG4-STEP-0001 style for steps.
4. AG5-ART-0001 style for artifacts.

## Required Outputs for Phase 0 Completion
1. Data model decision record approved.
2. ID namespace registry approved.
3. Rollback and migration safety checklist approved.
4. Compatibility contract for old clients documented.

## Risks and Mitigations
1. Risk: migration mismatch between old and new IDs.
2. Mitigation: deterministic backfill order and integrity checks.
3. Risk: mixed UUID and business ID usage in UI.
4. Mitigation: frontend adapter enforces business ID as default.

## Exit Criteria
1. Team sign-off on dual-ID architecture.
2. No unresolved critical objections on migration safety.
3. Phase 1 can start without blocking decisions.
