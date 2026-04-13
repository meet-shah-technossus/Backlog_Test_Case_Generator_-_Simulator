from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateItem(BaseModel):
    selector: str
    action: str
    supporting_text_match: float = 0.0
    context_match: float = 0.0
    stability_indicators: dict = Field(default_factory=dict)


class ConfidenceScore(BaseModel):
    score: float
    band: str
    breakdown: dict = Field(default_factory=dict)


class ReasoningStepInput(BaseModel):
    step_id: str
    step_text: str
    expected_outcome: str
    page_intent: str
    available_ui_elements: list[dict] = Field(default_factory=list)
    current_page_context: dict = Field(default_factory=dict)


class ReasoningStepOutput(BaseModel):
    step_id: str
    top3_candidates: list[CandidateItem] = Field(default_factory=list)
    confidence: ConfidenceScore
    rationale: str
    failure_reason_code: str | None = None


class Agent3AssembledContextArtifact(BaseModel):
    run_id: str
    source_agent2_run_id: str
    context_version: int
    retry_count: int = 0
    policy: dict = Field(default_factory=dict)
    gate_requirements: dict = Field(default_factory=dict)
    input_steps: list[ReasoningStepInput] = Field(default_factory=list)
    output_steps: list[ReasoningStepOutput] = Field(default_factory=list)
    unresolved_count: int = 0
