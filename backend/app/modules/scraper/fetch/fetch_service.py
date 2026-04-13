from __future__ import annotations

from app.modules.scraper.infrastructure.browser.playwright_fetcher import PlaywrightFetcher
from app.modules.scraper.infrastructure.http.http_fetcher import HttpFetcher
from app.modules.scraper.infrastructure.parser.link_extractor import extract_links_from_html
from app.modules.scraper.infrastructure.parser.page_snapshot_extractor import extract_page_snapshot


class ScraperFetchService:
    def __init__(
        self,
        *,
        http_fetcher: HttpFetcher | None = None,
        playwright_fetcher: PlaywrightFetcher | None = None,
    ):
        self._http_fetcher = http_fetcher or HttpFetcher()
        self._playwright_fetcher = playwright_fetcher or PlaywrightFetcher()

    async def fetch_page(
        self,
        *,
        url: str,
        mode: str = "auto",  # auto | http | playwright
        timeout_seconds: int = 20,
    ) -> dict:
        normalized_mode = (mode or "auto").strip().lower()
        if normalized_mode not in {"auto", "http", "playwright"}:
            raise ValueError("Invalid fetch mode. Allowed: auto, http, playwright")

        errors: list[str] = []

        async def _fetch_http() -> dict:
            return await self._http_fetcher.fetch(url=url, timeout_seconds=timeout_seconds)

        async def _fetch_playwright() -> dict:
            return await self._playwright_fetcher.fetch(url=url, timeout_seconds=max(timeout_seconds, 30))

        if normalized_mode == "http":
            result = await _fetch_http()
        elif normalized_mode == "playwright":
            result = await _fetch_playwright()
        else:
            try:
                result = await _fetch_http()
                status = int(result.get("status_code") or 0)
                if status >= 400:
                    errors.append(f"http_status_{status}")
                    result = await _fetch_playwright()
            except Exception as exc:
                errors.append(f"http_error:{exc}")
                result = await _fetch_playwright()

        links = extract_links_from_html(
            base_url=result.get("final_url") or url,
            html=result.get("html") or "",
        )
        snapshot = extract_page_snapshot(html=result.get("html") or "")

        return {
            **result,
            "links": links,
            "title": snapshot.get("title") or "",
            "text_excerpt": snapshot.get("text_excerpt") or "",
            "errors": errors,
        }
