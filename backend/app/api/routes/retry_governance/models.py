from pydantic import BaseModel, Field


class RetryGovernanceCreateRequest(BaseModel):
    requested_by: str = Field(default="operator")
    reason_code: str | None = None
    reason_text: str | None = None


class RetryGovernanceReviewRequest(BaseModel):
    reviewer_id: str = Field(default="reviewer")
    decision: str
    comment: str | None = None


class RetryGovernanceAssignRequest(BaseModel):
    reviewer_id: str
    assigned_by: str = Field(default="operator")
    reason: str | None = None


class RetryGovernanceAutoAssignRequest(BaseModel):
    assigned_by: str = Field(default="system")


class RetryGovernanceApproveAndRunRequest(BaseModel):
    reviewer_id: str = Field(default="reviewer")
    comment: str | None = None


class RetryRevisionPromoteRequest(BaseModel):
    artifact_version: int
    actor: str = Field(default="operator")
    reason: str | None = None


class RetryGovernanceListResponse(BaseModel):
    run_scope: str
    run_id: str
    requests: list[dict] = Field(default_factory=list)


class RetryGovernanceRecordResponse(BaseModel):
    request: dict = Field(default_factory=dict)


class RetryGovernanceAuditResponse(BaseModel):
    request_id: str
    events: list[dict] = Field(default_factory=list)


class RetryGovernanceApproveAndRunResponse(BaseModel):
    request: dict = Field(default_factory=dict)
    run_scope: str
    run_id: str
    result: dict = Field(default_factory=dict)


class RetryRevisionResponse(BaseModel):
    run_scope: str
    run_id: str
    active_revision: dict = Field(default_factory=dict)
    history: list[dict] = Field(default_factory=list)


class RetryGovernanceSpecResponse(BaseModel):
    spec: dict = Field(default_factory=dict)


class Phase23ChecklistItem(BaseModel):
    phase: str
    title: str
    status: str
    details: dict = Field(default_factory=dict)


class Phase23PreflightResponse(BaseModel):
    phase: str
    completion_status: str
    checklist: list[Phase23ChecklistItem] = Field(default_factory=list)
