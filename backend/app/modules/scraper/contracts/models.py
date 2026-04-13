from __future__ import annotations

from pydantic import BaseModel, Field


class ScraperJobCreateRequest(BaseModel):
    backlog_item_id: str
    max_depth: int = Field(default=2, ge=0, le=5)
    max_pages: int = Field(default=100, ge=1, le=2000)
    same_origin_only: bool = True


class ScraperJobSnapshot(BaseModel):
    job_id: str
    backlog_item_id: str
    target_url: str
    state: str
    stage: str
    config: dict = Field(default_factory=dict)
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
