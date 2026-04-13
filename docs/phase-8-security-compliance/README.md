# Phase 8: Security and Compliance Controls

This phase adds security hardening for URL policy and LLM context redaction.

## Implemented controls

1. URL/domain governance
- Optional strict allowlist policy (`SECURITY_REQUIRE_DOMAIN_ALLOWLIST`)
- If enabled, empty allowlist is rejected.
- Host must match configured `domain_allowlist`.

2. Crawler data sanitization
- Strips URL query/fragment from crawled URLs.
- Redacts sensitive text patterns in extracted element text.
- Drops sensitive attributes (`password`, `token`, `authorization`, `cookie`, etc.).

3. LLM context redaction
- Controlled via `SECURITY_REDACT_SENSITIVE_DATA` (default true).
- Redacts sensitive values in test-case text and crawled element text before context bundle output.

## Files

- `backend/config.py`
- `backend/execution_context.py`
- `backend/security_redaction_service.py`
- `backend/crawler_service.py`
- `backend/context_bundle_service.py`

## Environment flags

```env
SECURITY_REQUIRE_DOMAIN_ALLOWLIST=false
SECURITY_REDACT_SENSITIVE_DATA=true
```

## Examples

- `examples/security-env-example.env`
