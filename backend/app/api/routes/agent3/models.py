from pydantic import BaseModel, Field


class Agent3BlueprintResponse(BaseModel):
    agent: str
    phase_window: list[int]
    status: str
    states: list[str]
    modules: list[str]
    next_phase: str


class Agent3ConsumeHandoffRequest(BaseModel):
    message_id: str
    run_id: str
    trace_id: str
    from_agent: str = Field(default="agent_2")
    to_agent: str = Field(default="agent_3")
    stage_id: str = Field(default="reasoning")
    task_type: str = Field(default="reason_over_steps")
    contract_version: str = Field(default="v1")
    retry_count: int = Field(default=0, ge=0)
    dedupe_key: str
    payload: dict = Field(default_factory=dict)


class Agent3InboxConsumeResponse(BaseModel):
    created: bool
    inbox: dict


class Agent3CreateRunFromInboxResponse(BaseModel):
    created: bool
    run: dict


class Agent3RunSnapshotResponse(BaseModel):
    run: dict
    latest_artifact: dict | None = None
    artifacts: list[dict] = Field(default_factory=list)
    timeline: list[dict] = Field(default_factory=list)


class Agent3RunHistoryResponse(BaseModel):
    backlog_item_id: str
    runs: list[dict] = Field(default_factory=list)


class Agent3AssembleContextResponse(BaseModel):
    run: dict
    context_artifact: dict | None = None


class Agent3Phase3GateRequest(BaseModel):
    decision: str = Field(description="approve|reject|retry")
    gate_mode: str = Field(description="quick|deep")
    reviewer_id: str
    reason_code: str | None = None
    auto_retry: bool = True


class Agent3Phase3GateResponse(BaseModel):
    run: dict
    context_artifact: dict | None = None


class Agent3GateReasonCodesResponse(BaseModel):
    codes: dict[str, list[str]] = Field(default_factory=dict)


class Agent3Phase4GenerateResponse(BaseModel):
    created: bool = True
    run: dict
    selector_artifact: dict | None = None


class Agent3Phase5ReviewRequest(BaseModel):
    decision: str = Field(description="approve|edit_approve|reject")
    reviewer_id: str
    reason_code: str | None = None
    edited_selector_steps: list[dict] | None = None


class Agent3Phase5ReviewResponse(BaseModel):
    run: dict
    selector_artifact: dict | None = None


class Agent3Phase5ReviewReasonCodesResponse(BaseModel):
    codes: dict[str, list[str]] = Field(default_factory=dict)


class Agent3Phase5EmitHandoffResponse(BaseModel):
    created: bool
    message_id: str
    run: dict
    handoff_artifact: dict | None = None


class Agent3Phase6FeedbackRequest(BaseModel):
    message_id: str
    source_agent4_run_id: str
    outcome: str = Field(description="passed|partial|failed")
    recommended_action: str = Field(default="none", description="none|retry_selectors|manual_review|abort")
    step_results: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class Agent3Phase6FeedbackResponse(BaseModel):
    created: bool = True
    run: dict
    feedback_artifact: dict | None = None


class Agent3Phase6FeedbackReasonCodesResponse(BaseModel):
    codes: dict[str, list[str]] = Field(default_factory=dict)


class Agent3Phase7ObservabilityResponse(BaseModel):
    run: dict
    counters: dict = Field(default_factory=dict)


class Agent3Phase8IntegrityResponse(BaseModel):
    run: dict
    integrity: dict = Field(default_factory=dict)


class Agent3StartFromAgent2RunResponse(BaseModel):
    agent2_run_id: str
    handoff_emitted: bool = False
    message_id: str
    consume: dict = Field(default_factory=dict)
    create: dict = Field(default_factory=dict)
    agent3_snapshot: dict | None = None


class Agent3RunContractV1Response(BaseModel):
    contract_version: str
    run_scope: str
    internal_id: str
    business_id: str | None = None
    current_revision: dict = Field(default_factory=dict)
    retry_status: dict = Field(default_factory=dict)
    review_status: dict = Field(default_factory=dict)
    run: dict = Field(default_factory=dict)
