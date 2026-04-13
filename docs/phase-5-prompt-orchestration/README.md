# Phase 5: Prompt Orchestration (Grounded Script Generation)

Phase 5 introduces selector-grounded LLM script generation from the Phase 4 context bundle.

## What was added

1. Prompt builder support:
   - `PromptBuilder.playwright_contextual_prompt(...)`
   - Uses new templates:
     - `prompts/playwright_contextual_system.j2`
     - `prompts/playwright_contextual_prompt.j2`

2. Grounded Playwright generator path:
   - `generate_playwright_script_from_context_bundle(...)`
   - Validates:
     - Python syntax
     - required imports/signature
     - selector grounding (direct selector calls must exist in ALLOWED SELECTORS)

3. New endpoint:
   - `POST /generate/playwright/contextual`
   - Input: `story_id`, `context_bundle`, optional `model`
   - Streams SSE events like existing generation flow.

## Why this matters

- Prevents hallucinated selectors.
- Forces generated scripts to stay within crawler-discovered UI context.
- Keeps your dynamic adaptation workflow stable and auditable.

## Notes

- Existing `POST /generate/playwright` remains unchanged for backward compatibility.
- Contextual endpoint is the recommended path for adaptive architecture.

## Example payload

See `examples/playwright-contextual-request.json`.
