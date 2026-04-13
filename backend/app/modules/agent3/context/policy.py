from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TokenSafeCrawlContextPolicy:
    """Token-safe normalization policy for crawl evidence in Agent3 prompts."""

    per_page_char_budget: int = 1200
    per_run_char_budget: int = 12000
    max_ui_elements_per_step: int = 12


def _clip(value: str, max_chars: int) -> str:
    text = (value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3] + "..."


def normalize_page(page: dict, policy: TokenSafeCrawlContextPolicy) -> dict:
    title = _clip(str(page.get("title") or page.get("page_title") or ""), 180)
    visible_text = _clip(str(page.get("text_excerpt") or ""), max(200, policy.per_page_char_budget - 260))
    links = page.get("sample_links") or page.get("links") or []
    links = [str(x) for x in links[:8] if str(x).strip()]

    return {
        "url": str(page.get("url") or ""),
        "depth": int(page.get("depth") or 0),
        "status_code": int(page.get("status_code") or 0),
        "title": title,
        "visible_text": visible_text,
        "interactive_controls": [],
        "labels": [],
        "form_associations": [],
        "link_graph_summary": {
            "links_count": int(page.get("links_count") or len(links)),
            "sample_links": links,
        },
        "raw_artifact_ref": {
            "kind": "scraper_page",
            "url": str(page.get("url") or ""),
        },
    }


def enforce_run_budget(normalized_pages: list[dict], policy: TokenSafeCrawlContextPolicy) -> list[dict]:
    used = 0
    kept: list[dict] = []
    for page in normalized_pages:
        page_cost = len(page.get("title") or "") + len(page.get("visible_text") or "")
        if used + page_cost > policy.per_run_char_budget and kept:
            break
        kept.append(page)
        used += page_cost
    return kept
