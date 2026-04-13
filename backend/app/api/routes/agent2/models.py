from pydantic import BaseModel, Field


class Agent2BlueprintResponse(BaseModel):
    agent: str
    phase_window: list[int]
    status: str
    states: list[str]
    modules: list[str]
    next_phase: str


class Agent2ConsumeHandoffRequest(BaseModel):
    message_id: str
    run_id: str
    trace_id: str
    from_agent: str = Field(default="agent_1")
    to_agent: str = Field(default="agent_2")
    task_type: str = Field(default="generate_steps")
    contract_version: str = Field(default="v1")
    payload: dict = Field(default_factory=dict)


class Agent2InboxConsumeResponse(BaseModel):
    created: bool
    inbox: dict


class Agent2CreateRunFromInboxResponse(BaseModel):
    created: bool
    run: dict


class Agent2ApprovedAgent1RunsResponse(BaseModel):
    backlog_item_id: str
    runs: list[dict] = Field(default_factory=list)


class Agent2StartFromAgent1RunResponse(BaseModel):
    agent1_run_id: str
    message_id: str
    consume: dict
    create: dict
    snapshot: dict | None = None


class Agent2RunSnapshotResponse(BaseModel):
    run: dict
    latest_artifact: dict | None = None
    artifacts: list[dict] = Field(default_factory=list)
    reviews: list[dict] = Field(default_factory=list)
    handoffs: list[dict] = Field(default_factory=list)
    review_diff: dict | None = None
    timeline: list[dict]


class Agent2RunHistoryResponse(BaseModel):
    backlog_item_id: str
    runs: list[dict] = Field(default_factory=list)


class Agent2TimelineResponse(BaseModel):
    run_id: str
    order: str
    events: list[dict] = Field(default_factory=list)


class Agent2ObservabilityCountersResponse(BaseModel):
    scope: dict = Field(default_factory=dict)
    counters: dict = Field(default_factory=dict)


class Agent2GenerateRunRequest(BaseModel):
    model: str | None = None


class Agent2ReviewRunRequest(BaseModel):
    decision: str = Field(description="approve|edit_approve|reject|retry")
    reviewer_id: str
    reason_code: str | None = None
    edited_payload: dict | None = None


class Agent2ReviewDiffResponse(BaseModel):
    has_diff: bool
    latest_version: int | None = None
    previous_version: int | None = None
    summary: dict = Field(default_factory=dict)


class Agent2ReviewReasonCodesResponse(BaseModel):
    codes: dict[str, list[str]] = Field(default_factory=dict)


class Agent2EmitHandoffResponse(BaseModel):
    created: bool
    snapshot: Agent2RunSnapshotResponse


class Agent2StartAgent3Response(BaseModel):
    agent2_run_id: str
    handoff_emitted: bool = False
    message_id: str
    consume: dict = Field(default_factory=dict)
    create: dict = Field(default_factory=dict)
    agent3_snapshot: dict | None = None


class Agent2CurrentRevisionStatus(BaseModel):
    internal_id: int | None = None
    business_id: str | None = None
    artifact_version: int | None = None
    created_at: str | None = None


class Agent2RetryStatus(BaseModel):
    latest_request_id: str | None = None
    latest_status: str | None = None
    total_requests: int = 0


class Agent2ReviewStatus(BaseModel):
    latest_decision: str | None = None
    latest_reviewer_id: str | None = None
    latest_reviewed_at: str | None = None
    total_reviews: int = 0


class Agent2RunContractV1Response(BaseModel):
    contract_version: str
    run_scope: str
    internal_id: str
    business_id: str | None = None
    current_revision: Agent2CurrentRevisionStatus = Field(default_factory=Agent2CurrentRevisionStatus)
    retry_status: Agent2RetryStatus = Field(default_factory=Agent2RetryStatus)
    review_status: Agent2ReviewStatus = Field(default_factory=Agent2ReviewStatus)
    run: dict = Field(default_factory=dict)
