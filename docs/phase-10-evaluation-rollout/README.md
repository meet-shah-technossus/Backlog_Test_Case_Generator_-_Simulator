# Phase 10: Evaluation and Rollout

This phase adds benchmark and rollout-readiness analytics from execution history and observability events.

## Implemented metrics

- Pass rate
- Failed/total test counts
- Average run duration
- Flake rate (tests that pass in some runs and fail in others)
- Selector mismatch rate (share of failures tagged `selector_not_found`)
- Generation latency (avg completed stage durations)
- Token/cost snapshot from telemetry (`prompt_chars`/`response_chars`)

## New APIs

- `GET /evaluation/story/{story_id}?run_limit=100`
- `GET /evaluation/global?run_limit=300`
- `GET /evaluation/rollout/{story_id}?run_limit=100`

## Rollout readiness

`/evaluation/rollout/{story_id}` checks:

1. pass_rate >= 85%
2. flake_rate <= 15%
3. selector_mismatch_rate <= 20% of failures

Returns:
- `status`: `ready` or `needs_improvement`
- `score`: proportion of checks passed
- detailed check outcomes

## Cost settings

Configure via `.env`:

```env
EVAL_INPUT_COST_PER_1K_USD=0.0
EVAL_OUTPUT_COST_PER_1K_USD=0.0
```

Set these to your LLM provider pricing for real cost estimates.
