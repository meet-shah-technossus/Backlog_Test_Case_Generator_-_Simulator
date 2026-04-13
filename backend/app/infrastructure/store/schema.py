SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS test_suites (
    story_id        TEXT PRIMARY KEY,
    story_title     TEXT,
    feature_title   TEXT,
    epic_title      TEXT,
    model_used      TEXT,
    test_cases_json TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS backlog_items (
    backlog_item_id     TEXT PRIMARY KEY,
    story_title         TEXT,
    story_description   TEXT,
    acceptance_json     TEXT,
    target_url          TEXT,
    epic_id             TEXT,
    epic_title          TEXT,
    feature_id          TEXT,
    feature_title       TEXT,
    source_type         TEXT,
    source_ref          TEXT,
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent1_runs (
    run_id               TEXT PRIMARY KEY,
    business_id          TEXT,
    backlog_item_id      TEXT NOT NULL,
    trace_id             TEXT NOT NULL,
    state                TEXT NOT NULL,
    source_type          TEXT,
    source_ref           TEXT,
    last_error_code      TEXT,
    last_error_message   TEXT,
    created_at           TEXT DEFAULT (datetime('now')),
    updated_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent1_artifacts (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id          TEXT,
    run_id               TEXT NOT NULL,
    backlog_item_id      TEXT NOT NULL,
    artifact_version     INTEGER NOT NULL,
    artifact_json        TEXT NOT NULL,
    is_active            INTEGER NOT NULL DEFAULT 0,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent1_reviews (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               TEXT NOT NULL,
    stage                TEXT NOT NULL,
    decision             TEXT NOT NULL,
    reason_code          TEXT,
    reviewer_id          TEXT NOT NULL,
    edited_payload_json  TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent1_handoffs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               TEXT NOT NULL,
    message_id           TEXT NOT NULL,
    from_agent           TEXT NOT NULL,
    to_agent             TEXT NOT NULL,
    task_type            TEXT NOT NULL,
    contract_version     TEXT NOT NULL,
    payload_json         TEXT NOT NULL,
    delivery_status      TEXT NOT NULL,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent1_audit_events (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id               TEXT NOT NULL,
    stage                TEXT NOT NULL,
    action               TEXT NOT NULL,
    actor                TEXT NOT NULL,
    metadata_json        TEXT,
    created_at           TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent2_inbox (
    message_id              TEXT PRIMARY KEY,
    source_agent1_run_id    TEXT NOT NULL,
    trace_id                TEXT NOT NULL,
    contract_version        TEXT NOT NULL,
    task_type               TEXT NOT NULL,
    payload_json            TEXT NOT NULL,
    intake_status           TEXT NOT NULL,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent2_runs (
    run_id                  TEXT PRIMARY KEY,
    business_id             TEXT,
    inbox_message_id        TEXT NOT NULL UNIQUE,
    source_agent1_run_id    TEXT NOT NULL,
    trace_id                TEXT NOT NULL,
    state                   TEXT NOT NULL,
    stage                   TEXT NOT NULL,
    last_error_code         TEXT,
    last_error_message      TEXT,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent2_artifacts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id             TEXT,
    run_id                  TEXT NOT NULL,
    source_agent1_run_id    TEXT NOT NULL,
    artifact_version        INTEGER NOT NULL,
    artifact_json           TEXT NOT NULL,
    is_active               INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent2_reviews (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                  TEXT NOT NULL,
    stage                   TEXT NOT NULL,
    decision                TEXT NOT NULL,
    reason_code             TEXT,
    reviewer_id             TEXT NOT NULL,
    edited_payload_json     TEXT,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent2_handoffs (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                  TEXT NOT NULL UNIQUE,
    message_id              TEXT NOT NULL UNIQUE,
    from_agent              TEXT NOT NULL,
    to_agent                TEXT NOT NULL,
    task_type               TEXT NOT NULL,
    contract_version        TEXT NOT NULL,
    payload_json            TEXT NOT NULL,
    delivery_status         TEXT NOT NULL,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent2_audit_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                  TEXT NOT NULL,
    stage                   TEXT NOT NULL,
    action                  TEXT NOT NULL,
    actor                   TEXT NOT NULL,
    metadata_json           TEXT,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent3_inbox (
    message_id              TEXT PRIMARY KEY,
    source_agent2_run_id    TEXT NOT NULL,
    trace_id                TEXT NOT NULL,
    contract_version        TEXT NOT NULL,
    task_type               TEXT NOT NULL,
    payload_json            TEXT NOT NULL,
    intake_status           TEXT NOT NULL,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent3_runs (
    run_id                  TEXT PRIMARY KEY,
    business_id             TEXT,
    inbox_message_id        TEXT NOT NULL UNIQUE,
    source_agent2_run_id    TEXT NOT NULL,
    trace_id                TEXT NOT NULL,
    state                   TEXT NOT NULL,
    stage                   TEXT NOT NULL,
    last_error_code         TEXT,
    last_error_message      TEXT,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent3_audit_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                  TEXT NOT NULL,
    stage                   TEXT NOT NULL,
    action                  TEXT NOT NULL,
    actor                   TEXT NOT NULL,
    metadata_json           TEXT,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent3_artifacts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id             TEXT,
    run_id                  TEXT NOT NULL,
    artifact_version        INTEGER NOT NULL,
    artifact_json           TEXT NOT NULL,
    is_active               INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent4_inbox (
    message_id              TEXT PRIMARY KEY,
    source_agent3_run_id    TEXT NOT NULL,
    trace_id                TEXT NOT NULL,
    contract_version        TEXT NOT NULL,
    task_type               TEXT NOT NULL,
    payload_json            TEXT NOT NULL,
    intake_status           TEXT NOT NULL,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent4_runs (
    run_id                  TEXT PRIMARY KEY,
    business_id             TEXT,
    inbox_message_id        TEXT NOT NULL UNIQUE,
    source_agent3_run_id    TEXT NOT NULL,
    trace_id                TEXT NOT NULL,
    state                   TEXT NOT NULL,
    stage                   TEXT NOT NULL,
    last_error_code         TEXT,
    last_error_message      TEXT,
    created_at              TEXT DEFAULT (datetime('now')),
    updated_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent4_audit_events (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id                  TEXT NOT NULL,
    stage                   TEXT NOT NULL,
    action                  TEXT NOT NULL,
    actor                   TEXT NOT NULL,
    metadata_json           TEXT,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent4_artifacts (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id             TEXT,
    run_id                  TEXT NOT NULL,
    artifact_version        INTEGER NOT NULL,
    artifact_json           TEXT NOT NULL,
    is_active               INTEGER NOT NULL DEFAULT 0,
    created_at              TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS observability_events (
    event_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    trace_id         TEXT,
    run_id           TEXT,
    story_id         TEXT,
    stage            TEXT,
    status           TEXT,
    model_provider   TEXT,
    model_name       TEXT,
    prompt_template  TEXT,
    prompt_chars     INTEGER,
    response_chars   INTEGER,
    duration_ms      INTEGER,
    error_code       TEXT,
    error_message    TEXT,
    metadata_json    TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS story_runtime_context (
    story_id                  TEXT PRIMARY KEY,
    target_url                TEXT,
    last_context_bundle_json  TEXT,
    updated_at                TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scraper_jobs (
    job_id                TEXT PRIMARY KEY,
    backlog_item_id       TEXT NOT NULL,
    target_url            TEXT NOT NULL,
    state                 TEXT NOT NULL,
    stage                 TEXT NOT NULL,
    config_json           TEXT,
    last_error_code       TEXT,
    last_error_message    TEXT,
    created_at            TEXT DEFAULT (datetime('now')),
    updated_at            TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS scraper_pages (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id                TEXT NOT NULL,
    url                   TEXT NOT NULL,
    depth                 INTEGER NOT NULL,
    parent_url            TEXT,
    page_title            TEXT,
    text_excerpt          TEXT,
    source                TEXT,
    status_code           INTEGER,
    content_type          TEXT,
    links_json            TEXT,
    error_json            TEXT,
    fetched_at            TEXT DEFAULT (datetime('now')),
    UNIQUE(job_id, url)
);

CREATE TABLE IF NOT EXISTS execution_runs (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_run_id      TEXT NOT NULL UNIQUE,
    business_id           TEXT,
    source_agent4_run_id  TEXT NOT NULL,
    backlog_item_id       TEXT,
    trace_id              TEXT NOT NULL,
    state                 TEXT NOT NULL,
    stage                 TEXT NOT NULL,
    request_json          TEXT,
    runtime_policy_json   TEXT,
    attempt_count         INTEGER NOT NULL DEFAULT 0,
    max_attempts          INTEGER NOT NULL DEFAULT 1,
    result_json           TEXT,
    last_error_code       TEXT,
    last_error_message    TEXT,
    created_at            TEXT DEFAULT (datetime('now')),
    updated_at            TEXT DEFAULT (datetime('now')),
    started_at            TEXT,
    completed_at          TEXT,
    canceled_at           TEXT
);

CREATE TABLE IF NOT EXISTS execution_evidence (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id           TEXT,
    execution_run_id      TEXT NOT NULL,
    script_path           TEXT,
    step_index            INTEGER,
    status                TEXT,
    duration_ms           INTEGER,
    started_at            TEXT,
    finished_at           TEXT,
    error_code            TEXT,
    error_message         TEXT,
    stack_trace           TEXT,
    screenshot_path       TEXT,
    trace_path            TEXT,
    video_path            TEXT,
    metadata_json         TEXT,
    created_at            TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent5_runs (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    agent5_run_id              TEXT NOT NULL UNIQUE,
    business_id                TEXT,
    source_agent4_run_id       TEXT NOT NULL,
    source_execution_run_id     TEXT,
    backlog_item_id            TEXT,
    trace_id                   TEXT NOT NULL,
    state                      TEXT NOT NULL,
    stage                      TEXT NOT NULL,
    request_json               TEXT,
    execution_summary_json     TEXT,
    step_evidence_refs_json    TEXT,
    stage7_analysis_json       TEXT,
    gate7_decision_json        TEXT,
    stage8_writeback_json      TEXT,
    gate8_decision_json        TEXT,
    last_error_code            TEXT,
    last_error_message         TEXT,
    created_at                 TEXT DEFAULT (datetime('now')),
    updated_at                 TEXT DEFAULT (datetime('now')),
    completed_at               TEXT
);

CREATE TABLE IF NOT EXISTS agent5_artifacts (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    business_id                TEXT,
    agent5_run_id              TEXT NOT NULL,
    artifact_version           INTEGER NOT NULL,
    artifact_type              TEXT NOT NULL,
    artifact_json              TEXT NOT NULL,
    is_active                  INTEGER NOT NULL DEFAULT 0,
    created_at                 TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS agent5_timeline (
    id                         INTEGER PRIMARY KEY AUTOINCREMENT,
    agent5_run_id              TEXT NOT NULL,
    stage                      TEXT NOT NULL,
    action                     TEXT NOT NULL,
    actor                      TEXT NOT NULL,
    metadata_json              TEXT,
    created_at                 TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS business_id_sequences (
    namespace             TEXT PRIMARY KEY,
    next_value            INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS retry_governance_requests (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id            TEXT NOT NULL UNIQUE,
    run_scope             TEXT NOT NULL,
    run_id                TEXT NOT NULL,
    requested_by          TEXT NOT NULL,
    reason_code           TEXT,
    reason_text           TEXT,
    status                TEXT NOT NULL,
    assigned_reviewer_id  TEXT,
    assignment_mode       TEXT,
    assigned_by           TEXT,
    assignment_reason     TEXT,
    assigned_at           TEXT,
    escalation_status     TEXT,
    reviewer_id           TEXT,
    reviewer_decision     TEXT,
    reviewer_comment      TEXT,
    reviewed_at           TEXT,
    created_at            TEXT DEFAULT (datetime('now')),
    updated_at            TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS retry_governance_audit_events (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id            TEXT NOT NULL,
    action                TEXT NOT NULL,
    actor                 TEXT NOT NULL,
    metadata_json         TEXT,
    created_at            TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_backlog_source ON backlog_items(source_type, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent1_runs_item ON agent1_runs(backlog_item_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent1_artifacts_run ON agent1_artifacts(run_id, artifact_version DESC);
CREATE INDEX IF NOT EXISTS idx_agent1_reviews_run ON agent1_reviews(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent1_handoffs_run ON agent1_handoffs(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent1_audit_run ON agent1_audit_events(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent2_inbox_status ON agent2_inbox(intake_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent2_runs_stage ON agent2_runs(stage, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent2_artifacts_run ON agent2_artifacts(run_id, artifact_version DESC);
CREATE INDEX IF NOT EXISTS idx_agent2_reviews_run ON agent2_reviews(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent2_handoffs_run ON agent2_handoffs(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent2_audit_run ON agent2_audit_events(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent3_inbox_status ON agent3_inbox(intake_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent3_runs_stage ON agent3_runs(stage, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent3_audit_run ON agent3_audit_events(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent3_artifacts_run ON agent3_artifacts(run_id, artifact_version DESC);
CREATE INDEX IF NOT EXISTS idx_agent4_inbox_status ON agent4_inbox(intake_status, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent4_runs_stage ON agent4_runs(stage, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent4_audit_run ON agent4_audit_events(run_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent4_artifacts_run ON agent4_artifacts(run_id, artifact_version DESC);
CREATE INDEX IF NOT EXISTS idx_obs_trace_created ON observability_events(trace_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_runtime_context_updated ON story_runtime_context(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_scraper_jobs_story ON scraper_jobs(backlog_item_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_scraper_pages_job_depth ON scraper_pages(job_id, depth, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_runs_agent4 ON execution_runs(source_agent4_run_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_execution_runs_state ON execution_runs(state, created_at ASC, id ASC);
CREATE INDEX IF NOT EXISTS idx_execution_evidence_run ON execution_evidence(execution_run_id, step_index ASC, id ASC);
CREATE INDEX IF NOT EXISTS idx_agent5_runs_agent4 ON agent5_runs(source_agent4_run_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent5_runs_execution ON agent5_runs(source_execution_run_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent5_runs_state ON agent5_runs(state, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent5_artifacts_run ON agent5_artifacts(agent5_run_id, artifact_version DESC);
CREATE INDEX IF NOT EXISTS idx_agent5_timeline_run ON agent5_timeline(agent5_run_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_retry_governance_scope_run ON retry_governance_requests(run_scope, run_id, created_at DESC, id DESC);
CREATE INDEX IF NOT EXISTS idx_retry_governance_audit_request ON retry_governance_audit_events(request_id, created_at DESC, id DESC);
"""
