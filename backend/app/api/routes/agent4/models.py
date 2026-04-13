from pydantic import BaseModel, Field


class Agent4BlueprintResponse(BaseModel):
    agent: str
    phase_window: list[int]
    status: str
    states: list[str]
    modules: list[str]
    next_phase: str


class Agent4ConsumeHandoffRequest(BaseModel):
    message_id: str
    run_id: str
    trace_id: str
    from_agent: str = Field(default="agent_3")
    to_agent: str = Field(default="agent_4")
    stage_id: str = Field(default="script_generation")
    task_type: str = Field(default="generate_test_scripts")
    contract_version: str = Field(default="v1")
    retry_count: int = Field(default=0, ge=0)
    dedupe_key: str
    payload: dict = Field(default_factory=dict)


class Agent4InboxConsumeResponse(BaseModel):
    created: bool
    inbox: dict


class Agent4CreateRunFromInboxResponse(BaseModel):
    created: bool
    run: dict


class Agent4RunSnapshotResponse(BaseModel):
    run: dict
    latest_artifact: dict | None = None
    artifacts: list[dict] = Field(default_factory=list)
    timeline: list[dict] = Field(default_factory=list)


class Agent4RunHistoryResponse(BaseModel):
    backlog_item_id: str
    runs: list[dict] = Field(default_factory=list)


class Agent4Phase3GateRequest(BaseModel):
    decision: str = Field(description="approve|reject|retry")
    gate_mode: str = Field(description="quick|deep")
    reviewer_id: str
    reason_code: str | None = None
    auto_retry: bool = True


class Agent4Phase3GateResponse(BaseModel):
    run: dict
    gate_artifact: dict | None = None


class Agent4GateReasonCodesResponse(BaseModel):
    codes: dict[str, list[str]] = Field(default_factory=dict)


class Agent4Phase3ReadinessResponse(BaseModel):
    run: dict
    readiness: dict = Field(default_factory=dict)
    recommended_decision: str
    missing_keys: list[str] = Field(default_factory=list)
    reason_code_options: dict[str, list[str]] = Field(default_factory=dict)


class Agent4Phase4PlanScriptsResponse(BaseModel):
    created: bool = True
    run: dict
    blueprint_artifact: dict | None = None


class Agent4Phase5GenerateScriptsResponse(BaseModel):
    created: bool = True
    run: dict
    script_bundle_artifact: dict | None = None


class Agent4Phase6ReadinessResponse(BaseModel):
    run: dict
    readiness: dict = Field(default_factory=dict)
    recommended_decision: str
    reason_code_options: dict[str, list[str]] = Field(default_factory=dict)


class Agent4Phase6ReviewRequest(BaseModel):
    decision: str = Field(description="approve|edit_approve|reject|retry")
    reviewer_id: str
    reason_code: str | None = None
    edited_scripts: list[dict] | None = None


class Agent4Phase6ReviewResponse(BaseModel):
    run: dict
    script_bundle_artifact: dict | None = None


class Agent4Phase6ReviewReasonCodesResponse(BaseModel):
    codes: dict[str, list[str]] = Field(default_factory=dict)


class Agent4Phase7EmitHandoffResponse(BaseModel):
    created: bool
    message_id: str
    run: dict
    handoff_artifact: dict | None = None


class Agent4Phase8FeedbackRequest(BaseModel):
    message_id: str
    source_agent5_run_id: str
    outcome: str = Field(description="passed|partial|failed")
    recommended_action: str = Field(default="none", description="none|retry_generation|manual_review|abort")
    step_results: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class Agent4Phase8FeedbackResponse(BaseModel):
    created: bool = True
    run: dict
    feedback_artifact: dict | None = None


class Agent4Phase8FeedbackReasonCodesResponse(BaseModel):
    codes: dict[str, list[str]] = Field(default_factory=dict)


class Agent4Phase9ObservabilityResponse(BaseModel):
    run: dict
    counters: dict = Field(default_factory=dict)


class Agent4Phase9IntegrityResponse(BaseModel):
    run: dict
    integrity: dict = Field(default_factory=dict)


class Agent4Phase10ProfileResponse(BaseModel):
    scope: dict = Field(default_factory=dict)
    policy: dict = Field(default_factory=dict)


class Agent4Phase10RuntimeCheckResponse(BaseModel):
    version: str
    ready: bool
    policy: dict = Field(default_factory=dict)
    capabilities: dict = Field(default_factory=dict)
    launch_probe_attempted: bool = False
    launch_probe_ok: bool = False
    diagnostics: list[str] = Field(default_factory=list)


class Agent4Phase10ExecutionStartRequest(BaseModel):
    requested_by: str = Field(default="operator")
    reason: str | None = None
    max_attempts: int = Field(default=1, ge=1, le=5)
    target_url: str | None = None
    max_scripts: int | None = Field(default=None, ge=1, le=100)
    early_stop_after_failures: int | None = Field(default=None, ge=1, le=100)
    parallel_workers: int | None = Field(default=None, ge=1, le=10)
    selected_script_paths: list[str] | None = None
    use_smoke_probe_script: bool = False


class Agent4Phase10ExecutionRunRequest(BaseModel):
    started_by: str = Field(default="operator")


class Agent4Phase10DispatchRequest(BaseModel):
    started_by: str = Field(default="dispatcher")


class Agent4Phase10ExecutionSnapshotResponse(BaseModel):
    execution: dict = Field(default_factory=dict)


class Agent4Phase10ExecutionListResponse(BaseModel):
    run_id: str
    executions: list[dict] = Field(default_factory=list)


class Agent4Phase10DispatchResponse(BaseModel):
    execution: dict | None = None


class Agent4Phase10DispatcherStatusResponse(BaseModel):
    dispatcher: dict = Field(default_factory=dict)


class Agent4Phase10RecoveryResponse(BaseModel):
    recovery: dict = Field(default_factory=dict)


class Agent4Phase11QueueProfileResponse(BaseModel):
    phase: str = Field(default="phase11")
    strategy: str = Field(default="queue_backpressure_hardening")
    limits: dict = Field(default_factory=dict)
    protections: list[str] = Field(default_factory=list)


class Agent4Phase11QueueSnapshotResponse(BaseModel):
    snapshot: dict = Field(default_factory=dict)


class Agent4Phase11QueueItemsResponse(BaseModel):
    limit: int
    items: list[dict] = Field(default_factory=list)


class Agent4Phase12QueueHealthResponse(BaseModel):
    health: dict = Field(default_factory=dict)


class Agent4Phase12QueueExpireResponse(BaseModel):
    expiration: dict = Field(default_factory=dict)


class Agent4Phase14QueueAuditResponse(BaseModel):
    limit: int
    stage: str | None = None
    status: str | None = None
    story_id: str | None = None
    events: list[dict] = Field(default_factory=list)


class Agent4Phase15OperatorWhoAmIResponse(BaseModel):
    identity: dict = Field(default_factory=dict)


class Agent4Phase15QueueAuditVerifyResponse(BaseModel):
    verification: dict = Field(default_factory=dict)


class Agent4Phase16OperatorSecurityStatusResponse(BaseModel):
    security: dict = Field(default_factory=dict)


class Agent4Phase16OperatorSecurityEventsResponse(BaseModel):
    limit: int
    events: list[dict] = Field(default_factory=list)


class Agent4Phase17OperatorSecurityHistoryResponse(BaseModel):
    limit: int
    events: list[dict] = Field(default_factory=list)


class Agent4Phase17OperatorSecuritySummaryResponse(BaseModel):
    summary: dict = Field(default_factory=dict)


class Agent4Phase17OperatorAlertTestResponse(BaseModel):
    alert_test: dict = Field(default_factory=dict)


class Agent4Phase19OpenIncidentsResponse(BaseModel):
    limit: int
    incidents: list[dict] = Field(default_factory=list)


class Agent4Phase19IncidentLifecycleResponse(BaseModel):
    incident: dict = Field(default_factory=dict)


class Agent4Phase20SecurityExportResponse(BaseModel):
    export: dict = Field(default_factory=dict)


class Agent4Phase20SecurityReadinessResponse(BaseModel):
    readiness: dict = Field(default_factory=dict)


class Agent4StartFromAgent3RunResponse(BaseModel):
    agent3_run_id: str
    handoff_emitted: bool = False
    message_id: str
    consume: dict = Field(default_factory=dict)
    create: dict = Field(default_factory=dict)
    agent4_snapshot: dict | None = None
