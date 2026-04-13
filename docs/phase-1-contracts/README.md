# Phase 1: Contracts and Run Context

This package defines the versioned interfaces for the adaptive test automation pipeline.

## Objective

Standardize all stage boundaries so each module can evolve independently while maintaining compatibility.

## Scope

- Run request contract
- Execution context contract
- Stage I/O contracts
- Error taxonomy
- Run state machine
- Golden end-to-end payload set

## Contract Version

- `contract_version`: `v1`

## Run State Machine

Allowed state transitions:

1. `created` -> `test_cases_generated`
2. `test_cases_generated` -> `crawl_completed`
3. `crawl_completed` -> `context_built`
4. `context_built` -> `script_generated`
5. `script_generated` -> `script_validated`
6. `script_validated` -> `executed`
7. `executed` -> `completed`
8. Any state -> `failed`

## Artifacts

### Schemas

- `schemas/run_request.schema.json`
- `schemas/execution_context.schema.json`
- `schemas/test_case_generation_result.schema.json`
- `schemas/crawl_snapshot.schema.json`
- `schemas/context_bundle.schema.json`
- `schemas/script_generation_result.schema.json`
- `schemas/script_validation_result.schema.json`
- `schemas/execution_summary.schema.json`
- `schemas/stage_event.schema.json`

### Error Catalog

- `errors.json`

### Golden Payload Chain

- `examples/golden-run/01_run_request.json`
- `examples/golden-run/02_test_case_generation_result.json`
- `examples/golden-run/03_crawl_snapshot.json`
- `examples/golden-run/04_context_bundle.json`
- `examples/golden-run/05_script_generation_result.json`
- `examples/golden-run/06_script_validation_result.json`
- `examples/golden-run/07_execution_summary.json`
- `examples/golden-run/08_stage_events.json`

## Validation Rules (Phase 1 baseline)

1. `target_url` must be absolute and include protocol.
2. If `environment_type` is `local`, only loopback/private hosts are allowed.
3. If `environment_type` is `staging` or `production`, localhost URLs are rejected.
4. `domain_allowlist` must include the `target_url` host.
5. Every stage output must include:
   - `run_id`
   - `contract_version`
   - `stage`
   - `stage_version`
   - `timestamps.started_at`
   - `timestamps.completed_at`

## Notes

This phase intentionally focuses on interface design, not implementation code. Phase 2 will wire these contracts into API routes and persistence.
