from __future__ import annotations

import re
from urllib.parse import urlparse

from app.modules.agent1.mcp.contracts import BacklogItemCanonical

_URL_PATTERN = re.compile(r"https?://[^\s\]\)\">']+", re.IGNORECASE)
_DOMAIN_PATTERN = re.compile(r"\b([a-z0-9][a-z0-9-]*\.)+[a-z]{2,}\b", re.IGNORECASE)


def _is_valid_http_url(value: str | None) -> bool:
    if not value:
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _extract_first_url(text: str | None) -> str | None:
    if not text:
        return None
    match = _URL_PATTERN.search(text)
    return match.group(0) if match else None


def _extract_first_domain_as_url(text: str | None) -> str | None:
    if not text:
        return None
    match = _DOMAIN_PATTERN.search(text)
    if not match:
        return None
    domain = match.group(0).strip().rstrip('.,;:')
    return f"https://{domain}"


def resolve_target_url(
    *,
    backlog_item: BacklogItemCanonical,
    runtime_context: dict | None,
) -> str:
    candidates = [
        backlog_item.target_url,
        (runtime_context or {}).get("target_url"),
        backlog_item.source_ref,
        _extract_first_domain_as_url(backlog_item.source_ref),
        _extract_first_domain_as_url(backlog_item.title),
        _extract_first_url(backlog_item.description),
        _extract_first_domain_as_url(backlog_item.description),
    ]
    criteria = backlog_item.acceptance_criteria or []
    candidates.extend(_extract_first_url(item) for item in criteria)
    candidates.extend(_extract_first_domain_as_url(item) for item in criteria)

    for candidate in candidates:
        if _is_valid_http_url(candidate):
            return candidate.strip()

    raise ValueError(
        f"Unable to resolve target URL automatically for backlog item '{backlog_item.backlog_item_id}'"
    )
