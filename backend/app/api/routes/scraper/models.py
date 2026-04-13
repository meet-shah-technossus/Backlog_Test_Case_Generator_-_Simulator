from pydantic import BaseModel, Field


class ScraperBlueprintResponse(BaseModel):
    module: str
    phase_window: list[int]
    status: str
    states: list[str]
    next_phase: str


class ScraperCreateJobRequest(BaseModel):
    backlog_item_id: str
    max_depth: int = Field(default=2, ge=0, le=5)
    max_pages: int = Field(default=100, ge=1, le=2000)
    same_origin_only: bool = True


class ScraperJobResponse(BaseModel):
    job: dict


class ScraperJobListResponse(BaseModel):
    backlog_item_id: str
    jobs: list[dict] = Field(default_factory=list)


class ScraperFrontierPreviewRequest(BaseModel):
    discovered_links: list[str] = Field(default_factory=list)
    source_url: str | None = None
    source_depth: int = Field(default=0, ge=0, le=20)


class ScraperFrontierPreviewResponse(BaseModel):
    job_id: str
    target_url: str
    source_url: str
    source_depth: int
    accepted: list[dict] = Field(default_factory=list)
    rejected: list[dict] = Field(default_factory=list)
    summary: dict = Field(default_factory=dict)


class ScraperFetchPreviewRequest(BaseModel):
    mode: str = Field(default="auto", pattern="^(auto|http|playwright)$")
    timeout_seconds: int = Field(default=20, ge=3, le=120)


class ScraperFetchPreviewResponse(BaseModel):
    job_id: str
    requested_url: str
    fetch_mode: str
    fetch_result: dict = Field(default_factory=dict)


class ScraperRunJobRequest(BaseModel):
    mode: str = Field(default="auto", pattern="^(auto|http|playwright)$")
    timeout_seconds: int = Field(default=20, ge=3, le=120)
    force_restart: bool = False


class ScraperRunJobResponse(BaseModel):
    job: dict = Field(default_factory=dict)
    summary: dict = Field(default_factory=dict)
    pages: list[dict] = Field(default_factory=list)


class ScraperContextPackRequest(BaseModel):
    max_pages: int = Field(default=50, ge=1, le=500)


class ScraperContextPackResponse(BaseModel):
    job_id: str
    phase: str
    story: dict = Field(default_factory=dict)
    crawl: dict = Field(default_factory=dict)
    llm_input: dict = Field(default_factory=dict)


class ScraperPhase6StartAgent2Request(BaseModel):
    max_pages: int = Field(default=50, ge=1, le=500)


class ScraperPhase6StartAgent2Response(BaseModel):
    scraper_job_id: str
    message_id: str
    consume: dict = Field(default_factory=dict)
    create: dict = Field(default_factory=dict)
    snapshot: dict | None = None


class ScraperPhase8CompleteRequest(BaseModel):
    max_pages: int = Field(default=50, ge=1, le=500)
    model: str | None = None
    auto_approve: bool = True
    emit_agent3_handoff: bool = True
    reviewer_id: str = Field(default="scraper_phase8_auto")


class ScraperPhase8CompleteResponse(BaseModel):
    scraper_job_id: str
    message_id: str
    agent2_run_id: str | None = None
    consume: dict = Field(default_factory=dict)
    create: dict = Field(default_factory=dict)
    generated: bool = False
    auto_approved: bool = False
    handoff_emitted: bool = False
    snapshot: dict | None = None
