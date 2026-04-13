# Phase 9: Observability and Governance

This phase introduces traceable telemetry across generation, crawl, context-build, script generation, and execution.

## Implemented

1. Persistent telemetry storage
- New SQLite table: `observability_events`
- Captures:
  - `trace_id`, `run_id`, `story_id`
  - `stage`, `status`
  - model and prompt template metadata
  - prompt/response size metrics
  - duration
  - error code/message
  - free-form metadata JSON

2. Store APIs
- `store.log_event(...)`
- `store.get_events_by_trace(trace_id)`
- `store.get_events_by_run(run_id)`
- `store.get_recent_events(limit)`

3. Telemetry helper
- `backend/telemetry_service.py`
- `new_trace_id(...)`
- `log_stage_event(...)`

4. Instrumented stages
- `test_case_generation` (start/completed/failed)
- `crawl` (completed/failed)
- `context_build` (completed)
- `script_generation` (completed/failed with parse/provider/no-code reasons)
- `execution` (completed/failed)

5. Query endpoints
- `GET /observability/trace/{trace_id}`
- `GET /observability/run/{run_id}`
- `GET /observability/recent?limit=200`

## Notes

- Existing API behavior remains backward-compatible.
- Trace IDs are generated server-side for instrumented phases.
- Events are append-only for auditability.

## Examples

- `examples/get-observability-by-run.sh`
- `examples/get-recent-observability.sh`
