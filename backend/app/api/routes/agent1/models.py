from pydantic import BaseModel, Field


class CreateRunRequest(BaseModel):
    backlog_item_id: str


class GenerateRunRequest(BaseModel):
    model: str | None = None


class ReviewRunRequest(BaseModel):
    decision: str = Field(description="approve|edit_approve|reject|retry")
    reviewer_id: str
    reason_code: str | None = None
    edited_payload: dict | None = None


class RetryRunRequest(BaseModel):
    reason_code: str | None = None
    actor: str = "human"


class Agent1RunContractV1Response(BaseModel):
    contract_version: str
    run_scope: str
    internal_id: str
    business_id: str | None = None
    current_revision: dict = Field(default_factory=dict)
    retry_status: dict = Field(default_factory=dict)
    review_status: dict = Field(default_factory=dict)
    run: dict = Field(default_factory=dict)


class Agent1RunSnapshotResponse(BaseModel):
    run: dict = Field(default_factory=dict)
    backlog_item: dict | None = None
    latest_artifact: dict | None = None
    review_diff: dict = Field(default_factory=dict)
    reviews: list[dict] = Field(default_factory=list)
    handoffs: list[dict] = Field(default_factory=list)
    timeline: list[dict] = Field(default_factory=list)


class Agent1TimelineResponse(BaseModel):
    run_id: str
    timeline: list[dict] = Field(default_factory=list)


class Agent1StoryRunsResponse(BaseModel):
    backlog_item_id: str
    runs: list[dict] = Field(default_factory=list)
