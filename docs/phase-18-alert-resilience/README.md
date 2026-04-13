# Phase 18: Alert Resilience

This phase adds resilient multi-channel alert delivery for operator security incidents.

## Implemented

1. Alert channel templates
- New config: `OPERATOR_ALERT_CHANNEL` (`webhook`, `slack`, `teams`).
- Alert payload formatting in `backend/operator_alert_service.py`.

2. Retry with exponential backoff
- New config:
  - `OPERATOR_ALERT_MAX_RETRIES`
  - `OPERATOR_ALERT_RETRY_BASE_MS`
- Alert delivery retries transient failures and reports attempt history.

3. Alert delivery telemetry
- Existing telemetry path now records success/failure with richer metadata.

## Files changed

- `backend/config.py`
- `.env.example`
- `backend/operator_alert_service.py`
