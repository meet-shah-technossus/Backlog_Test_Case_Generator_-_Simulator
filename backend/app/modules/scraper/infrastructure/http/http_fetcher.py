from __future__ import annotations

import httpx


class HttpFetcher:
    async def fetch(self, *, url: str, timeout_seconds: int = 20) -> dict:
        async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
            response = await client.get(url)

        return {
            "url": url,
            "final_url": str(response.url),
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "html": response.text,
            "source": "http",
        }
