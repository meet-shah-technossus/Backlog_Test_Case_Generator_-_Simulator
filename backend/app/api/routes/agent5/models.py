from pydantic import BaseModel, Field


class Agent5ContractResponse(BaseModel):
    contract: dict = Field(default_factory=dict)


class Agent5StateMachineResponse(BaseModel):
    state_machine: dict = Field(default_factory=dict)


class Agent5TransitionValidationRequest(BaseModel):
    from_state: str
    command: str
    actor: str = Field(default="operator")
    context: dict = Field(default_factory=dict)


class Agent5TransitionValidationResponse(BaseModel):
    validation: dict = Field(default_factory=dict)


class Agent5CreateRunRequest(BaseModel):
    source_agent4_run_id: str
    source_execution_run_id: str | None = None
    created_by: str = Field(default="operator")
    reason: str | None = None


class Agent5PersistPayloadRequest(BaseModel):
    actor: str = Field(default="operator")
    payload: dict = Field(default_factory=dict)


class Agent5Stage7AnalyzeRequest(BaseModel):
    actor: str = Field(default="operator")
    force_regenerate: bool = Field(default=False)


class Agent5Gate7DecisionRequest(BaseModel):
    reviewer_id: str = Field(default="operator")
    decision: str
    reason_code: str = Field(default="unspecified")
    comment: str | None = None


class Agent5Stage8WritebackRequest(BaseModel):
    actor: str = Field(default="operator")
    idempotency_key: str | None = None
    force_regenerate: bool = Field(default=False)


class Agent5Gate8DecisionRequest(BaseModel):
    reviewer_id: str = Field(default="operator")
    decision: str
    reason_code: str = Field(default="unspecified")
    comment: str | None = None


class Agent5ObservabilityResponse(BaseModel):
    observability: dict = Field(default_factory=dict)


class Agent5RecoverStaleRequest(BaseModel):
    actor: str = Field(default="operator")
    older_than_seconds: int = Field(default=1800, ge=60, le=86400)
    limit: int = Field(default=100, ge=1, le=1000)


class Agent5RecoverStaleResponse(BaseModel):
    recovery: dict = Field(default_factory=dict)


class Agent5RetryFailedRequest(BaseModel):
    actor: str = Field(default="operator")


class Agent5CommandRequest(BaseModel):
    actor: str = Field(default="operator")
    command: str
    context: dict = Field(default_factory=dict)


class Agent5AdvanceToGate7PendingRequest(BaseModel):
    actor: str = Field(default="operator")
    context: dict = Field(default_factory=dict)


class Agent5BlockedCommand(BaseModel):
    command: str
    reason: str


class Agent5OrchestrationResponse(BaseModel):
    agent5_run_id: str
    state: str
    stage: str
    available_commands: list[str] = Field(default_factory=list)
    blocked_commands: list[Agent5BlockedCommand] = Field(default_factory=list)
    can_advance_to_gate7_pending: bool = False
    phase: str = Field(default="A5.5")


class Agent5RunSnapshotResponse(BaseModel):
    run: dict = Field(default_factory=dict)
    artifacts: list[dict] = Field(default_factory=list)
    timeline: list[dict] = Field(default_factory=list)


class Agent5RunListResponse(BaseModel):
    source_agent4_run_id: str
    runs: list[dict] = Field(default_factory=list)
