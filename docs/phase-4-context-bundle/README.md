# Phase 4: Context Bundle (Compression + Relevance)

Phase 4 converts generated test cases + crawl snapshot into a token-budgeted context payload for LLM script generation.

## What was added

1. New service:
   - `backend/context_bundle_service.py`
   - Relevance scoring based on test-case terms vs page/element text.
   - Budget-aware trimming by page and element count.

2. New API route:
   - `POST /generate/context-bundle`
   - Input: `story_id`, `target_url`, `crawl_snapshot`, and budget controls.
   - Output: structured `context_build` payload.

## Why this matters

- Prevents oversized LLM inputs.
- Keeps only high-signal UI context for each run.
- Makes script generation more stable and cheaper.

## Request controls

- `max_input_tokens` (default `12000`)
- `max_pages` (default `8`)
- `max_elements_per_page` (default `40`)

## Dependency

`story_id` must already have test cases stored (after `POST /generate/testcases`).

## Examples

- `examples/context-bundle-request.json`
- `examples/context-bundle-response-sample.json`
