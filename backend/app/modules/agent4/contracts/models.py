from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Agent4HandoffEnvelope(BaseModel):
    message_id: str
    run_id: str
    trace_id: str
    from_agent: Literal["agent_3"]
    to_agent: Literal["agent_4"]
    stage_id: str = "script_generation"
    task_type: Literal["generate_test_scripts"]
    contract_version: str = "v1"
    retry_count: int = 0
    dedupe_key: str
    payload: dict = Field(default_factory=dict)
