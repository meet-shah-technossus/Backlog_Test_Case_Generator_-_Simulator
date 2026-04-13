"""
Backlog Service
===============
Fetches backlog data from the external API, normalizes it, and caches it.
"""

import json
from pathlib import Path

import httpx

from app.core.config import BACKLOG_API_BASE_URL, BACKLOG_API_KEY
from app.domain.models import BacklogData
from app.modules.agent1.mcp.backlog_store_mcp_service import Agent1BacklogStoreMCPService
from app.modules.agent1.services.backlog_parser import normalize_backlog


class BacklogServiceError(Exception):
    pass


class BacklogService:
    _shared_cache: BacklogData | None = None

    def __init__(self, mcp_store: Agent1BacklogStoreMCPService | None = None):
        self._mcp_store = mcp_store or Agent1BacklogStoreMCPService()

    @property
    def _cache(self) -> BacklogData | None:
        return BacklogService._shared_cache

    @_cache.setter
    def _cache(self, value: BacklogData | None) -> None:
        BacklogService._shared_cache = value

    async def fetch(self) -> BacklogData:
        if not BACKLOG_API_BASE_URL or "REPLACE" in BACKLOG_API_BASE_URL:
            raise BacklogServiceError(
                "BACKLOG_API_BASE_URL is not configured. Please set it in your .env file."
            )

        raw = await self._call_api()
        normalized = normalize_backlog(raw)
        self._cache = normalized
        self._mcp_store.upsert_backlog_items(
            backlog=normalized,
            source_type="api",
            source_ref=BACKLOG_API_BASE_URL,
        )
        return normalized

    async def get_cached(self) -> BacklogData:
        if self._cache is None:
            return await self.fetch()
        return self._cache

    def invalidate_cache(self) -> None:
        self._cache = None

    def load_from_file(self, path: str | Path) -> BacklogData:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        normalized = normalize_backlog(data)
        self._cache = normalized
        self._mcp_store.upsert_backlog_items(
            backlog=normalized,
            source_type="sample_db",
            source_ref=str(path),
        )
        return normalized

    def load_from_dict(self, raw: dict | list) -> BacklogData:
        normalized = normalize_backlog(raw)
        self._cache = normalized
        return normalized

    def get_sample_from_db(self) -> BacklogData | None:
        backlog = self._mcp_store.get_backlog_data_by_source("sample_db")
        if backlog.total_stories <= 0:
            return None
        self._cache = backlog
        return backlog

    async def _call_api(self) -> dict | list:
        headers = {"Content-Type": "application/json"}
        if BACKLOG_API_KEY and "REPLACE" not in BACKLOG_API_KEY:
            headers["Authorization"] = f"Bearer {BACKLOG_API_KEY}"

        base = BACKLOG_API_BASE_URL.rstrip("/")
        url = base if base.endswith(("/backlog", "/api/backlog")) else f"{base}/api/backlog"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
        except httpx.ConnectError:
            raise BacklogServiceError(
                f"Cannot connect to backlog API at {url}. Check BACKLOG_API_BASE_URL in .env."
            )
        except httpx.TimeoutException:
            raise BacklogServiceError(f"Backlog API request timed out after 30s. URL: {url}")
        except httpx.HTTPStatusError as e:
            raise BacklogServiceError(
                f"Backlog API returned HTTP {e.response.status_code}: {e.response.text[:200]}"
            )
        except Exception as e:
            raise BacklogServiceError(f"Unexpected error fetching backlog: {e}")
