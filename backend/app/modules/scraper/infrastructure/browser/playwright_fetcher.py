from __future__ import annotations

from typing import Literal

from playwright.async_api import async_playwright


class PlaywrightFetcher:
    async def fetch(
        self,
        *,
        url: str,
        timeout_seconds: int = 30,
        wait_until: Literal["commit", "domcontentloaded", "load", "networkidle"] = "domcontentloaded",
    ) -> dict:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            try:
                response = await page.goto(url, wait_until=wait_until, timeout=timeout_seconds * 1000)
                html = await page.content()
                final_url = page.url
                status_code = response.status if response is not None else 0
                content_type = ""
                if response is not None:
                    headers = response.headers or {}
                    content_type = headers.get("content-type", "")
            finally:
                await browser.close()

        return {
            "url": url,
            "final_url": final_url,
            "status_code": status_code,
            "content_type": content_type,
            "html": html,
            "source": "playwright",
        }
