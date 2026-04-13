from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BacklogItemCanonical(BaseModel):
    backlog_item_id: str
    title: str
    description: str = ""
    acceptance_criteria: list[str] = []
    target_url: str | None = None
    epic_id: str | None = None
    epic_title: str | None = None
    feature_id: str | None = None
    feature_title: str | None = None
    source_type: Literal["api", "sample_db"]
    source_ref: str | None = None


class MCPBacklogIntakeRequest(BaseModel):
    source_type: Literal["api", "sample_db"] = Field(
        description="Backlog source selection routed through MCP intake service"
    )
    source_ref: str | None = Field(
        default=None,
        description="Optional source descriptor used for traceability",
    )


class MCPBacklogIntakeResponse(BaseModel):
    source_type: Literal["api", "sample_db"]
    source_ref: str | None = None
    item_count: int
    items: list[BacklogItemCanonical]
