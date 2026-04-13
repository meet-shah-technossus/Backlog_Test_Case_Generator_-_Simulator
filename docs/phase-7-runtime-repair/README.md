# Phase 7: Runtime Failure Handling and Retry Loop

This phase adds post-run failure analysis and bounded retry operations.

## Added capabilities

1. Failure classification during execution
- Classified categories include:
  - `timeout`
  - `selector_not_found`
  - `navigation_error`
  - `assertion_mismatch`
  - `auth_or_state`
  - `unknown`
- Persisted on each failed test result as:
  - `failure_category`
  - `retry_recommended`

2. Repair plan endpoint
- `POST /run/tests/repair-plan`
- Builds a targeted failure summary and an LLM-ready repair prompt payload.

3. Bounded failed-test retry endpoint
- `POST /run/tests/retry-failed`
- Re-runs only failed test functions from a selected run.
- Enforces `max_attempts` guardrails.

## Files added/updated

- `backend/failure_analysis_service.py`
- `backend/playwright_runner.py`
- `backend/models.py`
- `backend/routes/execute.py`

## Endpoints

### 1) Repair Plan
`POST /run/tests/repair-plan`

Request body:

```json
{ "run_id": "<run-id>" }
```

Response contains:
- `failed_tests` with categories/artifact links
- `repair_prompt` for targeted LLM script repair

### 2) Retry Failed
`POST /run/tests/retry-failed`

Request body:

```json
{ "run_id": "<run-id>", "max_attempts": 2 }
```

Behavior:
- Finds failed test function IDs from source run
- Starts execution for only those tests
- Blocks when retry limit is reached

## Examples

- `examples/repair-plan-request.json`
- `examples/retry-failed-request.json`
