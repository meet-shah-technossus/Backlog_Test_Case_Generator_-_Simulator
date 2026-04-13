# Phase 2: Execution Context Layer

Phase 2 introduces dynamic URL and environment handling so target websites are not hardcoded into acceptance criteria or test cases.

## What was added

1. Request-level `execution_context` support in `POST /generate/playwright`.
2. New preflight endpoint: `POST /generate/execution-context/validate`.
3. Environment-aware URL policy:
   - `local` accepts localhost/private hosts only.
   - `staging` and `production` reject localhost/private hosts.
4. Domain allowlist enforcement when configured.

## Updated `POST /generate/playwright` payload

`target_url` is now optional if `execution_context.base_url` is provided.

- Priority: `target_url` (if present) overrides `execution_context.base_url`.
- If both are missing, request fails with `INVALID_EXECUTION_CONTEXT`.

## New endpoint

`POST /generate/execution-context/validate`

Use this before generation to validate and normalize the final target URL.

## Examples

- `examples/validate-localhost-request.json`
- `examples/generate-playwright-with-context.json`

## Error format

Validation errors return HTTP 400 with:

```json
{
  "detail": {
    "code": "INVALID_EXECUTION_CONTEXT",
    "message": "..."
  }
}
```
