# Phase 3: Crawler + DOM Normalization

Phase 3 introduces a structured crawler stage that converts live pages into LLM-friendly metadata.

## What was added

1. New crawler service:
   - `backend/crawler_service.py`
   - Uses Playwright to crawl and normalize interactive elements.

2. New API route:
   - `POST /generate/crawl-snapshot`
   - Validates URL through the Execution Context layer.
   - Crawls the target site and returns normalized page snapshots.

## Why this matters

- Avoids sending raw HTML blobs to the LLM.
- Captures only meaningful UI context:
  - buttons
  - inputs
  - links
  - forms
- Creates deterministic structured JSON for downstream prompt building.

## Request support

`POST /generate/crawl-snapshot` accepts:

- `target_url` (optional if `execution_context.base_url` is present)
- `execution_context` (recommended)
- `overrides` (`max_pages`, `max_depth`, `crawl_timeout_ms`)
- `run_id` (optional)

## Response shape (high level)

- `run_id`
- `base_url`
- `page_count`
- `interactive_element_count`
- `pages[]` with:
  - `url`
  - `title`
  - `elements[]` (`type`, `text`, `selector`, `attributes`, `visible`, `interactive`)
  - `links[]`
- `timestamps`

## Examples

- `examples/crawl-localhost-request.json`
- `examples/crawl-localhost-response-sample.json`
