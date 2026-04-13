from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Agent2HandoffEnvelope(BaseModel):
    message_id: str
    run_id: str
    trace_id: str
    from_agent: Literal["agent_1", "scraper"]
    to_agent: Literal["agent_2"]
    task_type: Literal["generate_steps"]
    contract_version: str = "v1"
    payload: dict = Field(default_factory=dict)


class Agent2RunSnapshot(BaseModel):
    run_id: str
    state: str
    stage: str
    note: str | None = None


class Agent2PhaseDefinition(BaseModel):
    id: int
    name: str
    status: Literal["planned", "in_progress", "completed"] = "planned"
    objective: str


class Agent2ToAgent3HandoffEnvelope(BaseModel):
    message_id: str
    run_id: str
    trace_id: str
    from_agent: Literal["agent_2"] = "agent_2"
    to_agent: Literal["agent_3"] = "agent_3"
    stage_id: str = "reasoning"
    task_type: Literal["reason_over_steps"] = "reason_over_steps"
    contract_version: str = "v1"
    retry_count: int = 0
    dedupe_key: str
    payload: dict = Field(default_factory=dict)
