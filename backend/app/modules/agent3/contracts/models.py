from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Agent3HandoffEnvelope(BaseModel):
    message_id: str
    run_id: str
    trace_id: str
    from_agent: Literal["agent_2"]
    to_agent: Literal["agent_3"]
    stage_id: str = "reasoning"
    task_type: Literal["reason_over_steps"]
    contract_version: str = "v1"
    retry_count: int = 0
    dedupe_key: str
    payload: dict = Field(default_factory=dict)
