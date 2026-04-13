import { useEffect, useMemo, useState } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import {
  buildScraperContextPack,
  completeScraperPhase8,
  createScraperJob,
  emitAgent2Handoff,
  getAgent2Run,
  getScraperJob,
  listAgent2RunsByBacklog,
  listAgent3RunsByBacklog,
  listScraperJobs,
  runScraperJob,
} from '../../agent2/api/agent2Api'
import {
  assembleAgent3Context,
  consumeAgent2HandoffForAgent3,
  createAgent3RunFromInbox,
  emitAgent3Handoff,
  generateAgent3Selectors,
  getAgent3Phase7Observability,
  getAgent3Phase8Integrity,
  getAgent3RunSnapshot,
  reviewAgent3Selectors,
  submitAgent3Gate,
} from '../api/agent3Api'
import './agent3.css'

function formatDate(value) {
  if (!value) return 'n/a'
  const normalized = typeof value === 'string' ? value.replace(' ', 'T') : value
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

function parseDateValue(value) {
  if (!value) return 0
  const normalized = typeof value === 'string' ? value.replace(' ', 'T') : value
  const ts = new Date(normalized).getTime()
  return Number.isFinite(ts) ? ts : 0
}

function dedupeKeyForAgent2Handoff(runId, handoffPayload) {
  const artifactVersion = handoffPayload?.artifact_version ?? 'na'
  return `agent2-agent3-${runId}-${artifactVersion}`
}

function isAgent3SuccessfulState(state) {
  if (!state) return false
  return state.includes('handoff') || state.includes('accepted') || state.includes('done')
}

function isPhase4SelectorArtifact(artifact) {
  return artifact?.artifact_type === 'phase4_selector_plan' || Array.isArray(artifact?.selector_steps)
}

function isPhase3ContextArtifact(artifact) {
  if (!artifact || typeof artifact !== 'object') return false
  if (artifact?.artifact_type === 'phase3_context') return true
  return Array.isArray(artifact?.input_steps) && Array.isArray(artifact?.output_steps) && !Array.isArray(artifact?.selector_steps)
}

export default function Agent3Board({ story }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [pipelineError, setPipelineError] = useState('')

  const [scraperJobs, setScraperJobs] = useState([])
  const [selectedScraperJobId, setSelectedScraperJobId] = useState('')
  const [scraperJobMeta, setScraperJobMeta] = useState(null)
  const [scraperJobId, setScraperJobId] = useState('')
  const [pipelineResult, setPipelineResult] = useState(null)
  const [scraperRunSummary, setScraperRunSummary] = useState(null)
  const [scraperPages, setScraperPages] = useState([])
  const [showAllPages, setShowAllPages] = useState(false)

  const [agent2Runs, setAgent2Runs] = useState([])
  const [selectedAgent2RunId, setSelectedAgent2RunId] = useState('')

  const [agent3Bootstrap, setAgent3Bootstrap] = useState(null)
  const [agent3RunId, setAgent3RunId] = useState('')
  const [agent3Snapshot, setAgent3Snapshot] = useState(null)
  const [agent3Observability, setAgent3Observability] = useState(null)
  const [agent3Integrity, setAgent3Integrity] = useState(null)
  const [agent3History, setAgent3History] = useState([])
  const [agent3ActionMessage, setAgent3ActionMessage] = useState('')

  const compactPipeline = useMemo(() => {
    if (!pipelineResult) return []
    return [
      { key: 'consume', label: 'Consume', ok: Boolean(pipelineResult.consume?.created) },
      { key: 'create', label: 'Create', ok: Boolean(pipelineResult.create?.created) },
      { key: 'generated', label: 'Generate', ok: Boolean(pipelineResult.generated) },
      { key: 'auto_approved', label: 'Approve', ok: Boolean(pipelineResult.auto_approved) },
      { key: 'handoff_emitted', label: 'Handoff', ok: Boolean(pipelineResult.handoff_emitted) },
    ]
  }, [pipelineResult])

  const visibleScraperPages = useMemo(() => {
    return showAllPages ? scraperPages : scraperPages.slice(0, 20)
  }, [scraperPages, showAllPages])

  const agent3Timeline = agent3Snapshot?.timeline || []
  const agent3Artifacts = agent3Snapshot?.artifacts || []
  const agent3LatestArtifact = agent3Snapshot?.latest_artifact?.artifact || null
  const agent3ContextArtifact = useMemo(() => {
    return agent3Artifacts.find((entry) => isPhase3ContextArtifact(entry?.artifact))?.artifact || null
  }, [agent3Artifacts])
  const agent3SelectorArtifact = useMemo(() => {
    return agent3Artifacts.find((entry) => isPhase4SelectorArtifact(entry?.artifact))?.artifact || null
  }, [agent3Artifacts])

  const isPhase4ReviewPending =
    agent3Snapshot?.run?.state === 'review_pending' &&
    String(agent3Snapshot?.run?.stage || '').startsWith('phase-4')

  const refreshScraperJobs = async () => {
    if (!story?.id) {
      setScraperJobs([])
      setSelectedScraperJobId('')
      return
    }
    const data = await listScraperJobs(story.id, 50)
    const jobs = Array.isArray(data?.jobs) ? data.jobs : []
    const sorted = [...jobs].sort((a, b) => parseDateValue(b.updated_at) - parseDateValue(a.updated_at))
    setScraperJobs(sorted)
    if (!selectedScraperJobId && sorted.length) {
      setSelectedScraperJobId(sorted[0].job_id)
    }
  }

  const refreshAgent2Runs = async () => {
    if (!story?.id) {
      setAgent2Runs([])
      setSelectedAgent2RunId('')
      return
    }
    const data = await listAgent2RunsByBacklog(story.id, 50)
    const runs = Array.isArray(data?.runs) ? data.runs : []
    const handoffOnly = runs.filter((run) => run?.state === 'handoff_emitted')
    const sorted = [...handoffOnly].sort((a, b) => parseDateValue(b.updated_at) - parseDateValue(a.updated_at))
    setAgent2Runs(sorted)
    if (!selectedAgent2RunId && sorted.length) {
      setSelectedAgent2RunId(sorted[0].run_id)
    }
  }

  const refreshAgent3History = async () => {
    if (!story?.id) {
      setAgent3History([])
      return
    }
    const data = await listAgent3RunsByBacklog(story.id, 50)
    const runs = Array.isArray(data?.runs) ? data.runs : []
    const sorted = [...runs].sort((a, b) => parseDateValue(b.updated_at) - parseDateValue(a.updated_at))
    setAgent3History(sorted)

    if (!agent3RunId && sorted.length) {
      const preferred = sorted.find((run) => isAgent3SuccessfulState(run.state)) || sorted[0]
      setAgent3RunId(preferred.run_id)
      await refreshAgent3Panels(preferred.run_id)
    }
  }

  useEffect(() => {
    Promise.all([
      refreshScraperJobs(),
      refreshAgent2Runs(),
      refreshAgent3History(),
    ]).catch(() => {})
  }, [story?.id])

  useEffect(() => {
    setError('')
    setPipelineError('')
    setScraperJobMeta(null)
    setScraperJobId('')
    setPipelineResult(null)
    setScraperRunSummary(null)
    setScraperPages([])
    setShowAllPages(false)
    setAgent3Bootstrap(null)
    setAgent3RunId('')
    setAgent3Snapshot(null)
    setAgent3Observability(null)
    setAgent3Integrity(null)
    setAgent3History([])
    setAgent3ActionMessage('')
  }, [story?.id])

  const resolveSelectedOrLatestScraperJob = async () => {
    if (selectedScraperJobId) {
      const match = scraperJobs.find((job) => job.job_id === selectedScraperJobId)
      if (match) return match
      const fetched = await getScraperJob(selectedScraperJobId)
      return fetched?.job || null
    }

    const listed = await listScraperJobs(story.id, 50)
    const jobs = Array.isArray(listed?.jobs) ? listed.jobs : []
    if (!jobs.length) {
      const created = await createScraperJob({ backlog_item_id: story.id })
      return created?.job || null
    }
    const sorted = [...jobs].sort((a, b) => parseDateValue(b?.updated_at) - parseDateValue(a?.updated_at))
    return sorted[0]
  }

  const loadScraperSnapshotFromHistory = async (jobId) => {
    if (!jobId) return
    const [jobResp, contextPack] = await Promise.all([
      getScraperJob(jobId),
      buildScraperContextPack(jobId, { max_pages: 50 }),
    ])

    const job = jobResp?.job || null
    setScraperJobMeta(job)
    setScraperJobId(jobId)

    const pages = contextPack?.crawl?.pages || []
    const normalizedPages = pages.map((p) => ({
      url: p.url,
      depth: p.depth,
      status_code: p.status_code,
      page_title: p.title,
      text_excerpt: p.text_excerpt,
      errors: p.error_count ? [`${p.error_count} issues`] : [],
    }))
    setScraperPages(normalizedPages)
    setShowAllPages(false)

    setScraperRunSummary({
      visited_count: pages.length,
      newly_fetched_count: null,
      error_count: pages.reduce((acc, p) => acc + Number(p.error_count || 0), 0),
      rejected_count: 0,
    })
  }

  const runScraperAndCompletePipeline = async () => {
    if (!story?.id) return
    setLoading(true)
    setPipelineError('')

    try {
      const job = await resolveSelectedOrLatestScraperJob()
      const jobId = job?.job_id
      if (!jobId) {
        throw new Error('Unable to resolve scraper job id for selected story')
      }

      setScraperJobId(jobId)
      setSelectedScraperJobId(jobId)

      const runResult = await runScraperJob(jobId, {
        mode: 'auto',
        timeout_seconds: 20,
        force_restart: false,
      })

      setScraperRunSummary(runResult?.summary || null)
      setScraperPages(Array.isArray(runResult?.pages) ? runResult.pages : [])
      setShowAllPages(false)

      const phase8 = await completeScraperPhase8(jobId, {
        max_pages: 50,
        auto_approve: true,
        emit_agent3_handoff: true,
      })

      setPipelineResult(phase8)
      if (phase8?.agent2_run_id) {
        setSelectedAgent2RunId(phase8.agent2_run_id)
      }

      await Promise.all([refreshScraperJobs(), refreshAgent2Runs()])
    } catch (e) {
      setPipelineError(e?.message || 'Failed to complete scraper pipeline')
    } finally {
      setLoading(false)
    }
  }

  const completePipelineWithoutRescrape = async () => {
    if (!selectedScraperJobId) {
      setPipelineError('Select a scraper job from history first.')
      return
    }

    setLoading(true)
    setPipelineError('')

    try {
      await loadScraperSnapshotFromHistory(selectedScraperJobId)
      const phase8 = await completeScraperPhase8(selectedScraperJobId, {
        max_pages: 50,
        auto_approve: true,
        emit_agent3_handoff: true,
      })
      setPipelineResult(phase8)
      if (phase8?.agent2_run_id) {
        setSelectedAgent2RunId(phase8.agent2_run_id)
      }
      await refreshAgent2Runs()
    } catch (e) {
      setPipelineError(e?.message || 'Failed to complete pipeline from existing scraper snapshot')
    } finally {
      setLoading(false)
    }
  }

  const refreshAgent3Panels = async (runId) => {
    const [snapshot, observability, integrity] = await Promise.all([
      getAgent3RunSnapshot(runId),
      getAgent3Phase7Observability(runId),
      getAgent3Phase8Integrity(runId),
    ])
    setAgent3Snapshot(snapshot)
    setAgent3Observability(observability)
    setAgent3Integrity(integrity)
  }

  const runAgent3FromSelectedAgent2 = async () => {
    if (!selectedAgent2RunId) return
    setLoading(true)
    setError('')
    setAgent3ActionMessage('')

    try {
      let agent2Snapshot = await getAgent2Run(selectedAgent2RunId)
      let handoffs = Array.isArray(agent2Snapshot?.handoffs) ? agent2Snapshot.handoffs : []

      if (!handoffs.length && agent2Snapshot?.run?.state === 'handoff_pending') {
        await emitAgent2Handoff(selectedAgent2RunId)
        agent2Snapshot = await getAgent2Run(selectedAgent2RunId)
        handoffs = Array.isArray(agent2Snapshot?.handoffs) ? agent2Snapshot.handoffs : []
      }

      if (!handoffs.length) {
        throw new Error('Selected Agent2 run has no handoff to Agent3 yet.')
      }

      const handoff = handoffs[0]
      const payload = handoff.payload || {}
      const consumePayload = {
        message_id: handoff.message_id,
        run_id: selectedAgent2RunId,
        trace_id: payload.trace_id || agent2Snapshot?.run?.trace_id || `agent2-${selectedAgent2RunId}`,
        from_agent: 'agent_2',
        to_agent: 'agent_3',
        stage_id: 'reasoning',
        task_type: 'reason_over_steps',
        contract_version: handoff.contract_version || 'v1',
        retry_count: 0,
        dedupe_key: dedupeKeyForAgent2Handoff(selectedAgent2RunId, payload),
        payload,
      }

      const consume = await consumeAgent2HandoffForAgent3(consumePayload)
      const create = await createAgent3RunFromInbox(handoff.message_id)
      const nextRunId = create?.run?.run_id

      setAgent3Bootstrap({
        message_id: handoff.message_id,
        consume,
        create,
      })

      if (!nextRunId) {
        throw new Error('Agent3 run id was not returned after inbox create')
      }

      setAgent3RunId(nextRunId)

      const runState = create?.run?.state
      if (!create?.created && runState && runState !== 'intake_ready' && runState !== 'review_retry_requested') {
        setAgent3ActionMessage(
          `Reused existing Agent3 run ${nextRunId} in state '${runState}'. No additional reasoning run executed.`
        )
        await refreshAgent3Panels(nextRunId)
        await refreshAgent3History()
        return
      }

      await assembleAgent3Context(nextRunId)
      await submitAgent3Gate(nextRunId, {
        decision: 'approve',
        gate_mode: 'deep',
        reviewer_id: 'frontend_agent3_page',
        reason_code: null,
        auto_retry: true,
      })
      await generateAgent3Selectors(nextRunId)
      await refreshAgent3Panels(nextRunId)
      await refreshAgent3History()
    } catch (e) {
      setError(e?.message || 'Failed to run Agent3 from selected Agent2 run')
    } finally {
      setLoading(false)
    }
  }

  const onRefreshAgent3 = async () => {
    if (!agent3RunId) return
    setLoading(true)
    setError('')
    try {
      await refreshAgent3Panels(agent3RunId)
      await refreshAgent3History()
    } catch (e) {
      setError(e?.message || 'Failed to refresh Agent3 results')
    } finally {
      setLoading(false)
    }
  }

  const onApprovePhase4Review = async () => {
    if (!agent3RunId) return
    setLoading(true)
    setError('')
    setAgent3ActionMessage('')
    try {
      await reviewAgent3Selectors(agent3RunId, {
        decision: 'approve',
        reviewer_id: 'frontend_agent3_page',
        reason_code: 'manual_override_confirmed',
      })
      await refreshAgent3Panels(agent3RunId)
      await refreshAgent3History()
      setAgent3ActionMessage('Selector review approved. Run moved to handoff_pending.')
    } catch (e) {
      setError(e?.message || 'Failed to approve Agent3 review')
    } finally {
      setLoading(false)
    }
  }

  const onEmitAgent3Handoff = async () => {
    if (!agent3RunId) return
    setLoading(true)
    setError('')
    setAgent3ActionMessage('')
    try {
      await emitAgent3Handoff(agent3RunId)
      await refreshAgent3Panels(agent3RunId)
      await refreshAgent3History()
      setAgent3ActionMessage('Agent3 handoff emitted successfully.')
    } catch (e) {
      setError(e?.message || 'Failed to emit Agent3 handoff')
    } finally {
      setLoading(false)
    }
  }

  const onSelectAgent3HistoryRun = async (runId) => {
    setAgent3RunId(runId)
    setLoading(true)
    setError('')
    try {
      await refreshAgent3Panels(runId)
    } catch (e) {
      setError(e?.message || 'Failed to load selected Agent3 run')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="agent2-board">
      <div className="agent2-card">
        <div className="agent2-header">
          <div>
            <div className="agent2-title">Agent 3 - Scraper and Reasoning</div>
            <div className="agent2-subtitle">Story: {story?.title || 'Select a story'}</div>
          </div>
        </div>

        <div className="agent2-form-grid agent2-form-grid-single">
          <label className="agent2-field">
            <span>Scraper job history (for this story)</span>
            <select value={selectedScraperJobId} onChange={(e) => setSelectedScraperJobId(e.target.value)}>
              <option value="">Select scraper job</option>
              {scraperJobs.map((job) => (
                <option key={job.job_id} value={job.job_id}>
                  {job.job_id} | {job.state} | {formatDate(job.updated_at)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="agent2-actions">
          <button
            onClick={runScraperAndCompletePipeline}
            disabled={!story?.id || loading}
            className="agent2-btn agent2-btn-cyan"
          >
            {loading ? <Loader2 size={12} className="inline animate-spin mr-1" /> : null}
            Run Scraper and Complete Pipeline
          </button>
          <button
            onClick={completePipelineWithoutRescrape}
            disabled={!selectedScraperJobId || loading}
            className="agent2-btn agent2-btn-teal"
          >
            Complete Pipeline from Existing Crawl
          </button>
          <button
            onClick={() => loadScraperSnapshotFromHistory(selectedScraperJobId)}
            disabled={!selectedScraperJobId || loading}
            className="agent2-btn agent2-btn-neutral"
          >
            Load Scraper Snapshot
          </button>
          <button
            onClick={refreshScraperJobs}
            disabled={!story?.id || loading}
            className="agent2-btn agent2-btn-neutral"
          >
            <RefreshCw size={11} className="inline mr-1" />
            Refresh Scraper Jobs
          </button>
        </div>

        <div className="agent3-note">
          You do not need to scrape every time. Use existing scraper history and only run crawl when the website changed.
        </div>

        {pipelineError ? <div className="agent2-error">{pipelineError}</div> : null}

        {scraperJobId ? (
          <div className="agent2-muted">
            Scraper Job: <span className="agent2-mono">{scraperJobId}</span>
            {scraperJobMeta ? <> | Stage: <span className="agent2-mono">{scraperJobMeta.stage}</span></> : null}
          </div>
        ) : null}

        {compactPipeline.length ? (
          <div className="agent2-compact-timeline">
            {compactPipeline.map((step) => (
              <div
                key={step.key}
                className={`agent2-compact-pill ${step.ok ? 'agent2-compact-pill-ok' : 'agent2-compact-pill-pending'}`}
              >
                <span>{step.label}</span>
              </div>
            ))}
          </div>
        ) : null}

        {scraperRunSummary ? (
          <div className="agent2-scraper-summary">
            <div><span className="agent2-label">Visited:</span> {scraperRunSummary.visited_count ?? 'n/a'}</div>
            <div><span className="agent2-label">New:</span> {scraperRunSummary.newly_fetched_count ?? 'n/a'}</div>
            <div><span className="agent2-label">Errors:</span> {scraperRunSummary.error_count ?? 0}</div>
            <div><span className="agent2-label">Rejected:</span> {scraperRunSummary.rejected_count ?? 0}</div>
          </div>
        ) : null}

        <div className="agent2-section-title agent2-section-title-tight">Crawled Pages</div>
        {!scraperPages.length ? (
          <div className="agent2-muted">No crawler pages loaded yet.</div>
        ) : (
          <>
            <div className="agent2-scraper-pages-toolbar">
              <div className="agent2-muted agent2-muted-no-margin">
                Showing {visibleScraperPages.length} of {scraperPages.length} pages
              </div>
              {scraperPages.length > 20 ? (
                <button
                  onClick={() => setShowAllPages((prev) => !prev)}
                  className="agent2-btn agent2-btn-neutral"
                >
                  {showAllPages ? 'Show first 20' : 'Show all pages'}
                </button>
              ) : null}
            </div>

            <div className="agent2-scraper-pages">
              {visibleScraperPages.map((page) => (
                <div key={`${page.url}-${page.depth ?? 0}`} className="agent2-scraper-page-row">
                  <div className="agent2-scraper-page-head">
                    <span className="agent2-mono">d{page.depth ?? 0}</span>
                    <span className="agent2-scraper-page-status">{page.status_code || 'n/a'}</span>
                  </div>
                  <div className="agent2-scraper-page-url">{page.url}</div>
                  {page.page_title ? <div className="agent2-scraper-page-title">{page.page_title}</div> : null}
                  {page.text_excerpt ? <div className="agent2-scraper-page-excerpt">{page.text_excerpt}</div> : null}
                  {Array.isArray(page.errors) && page.errors.length ? (
                    <div className="agent2-scraper-page-error">{page.errors[0]}</div>
                  ) : null}
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      <div className="agent2-card">
        <div className="agent2-section-title">Run Agent3 from Agent2 Handoff</div>

        <div className="agent2-form-grid agent2-form-grid-single">
          <label className="agent2-field">
            <span>Handoff-emitted Agent2 runs only</span>
            <select value={selectedAgent2RunId} onChange={(e) => setSelectedAgent2RunId(e.target.value)}>
              <option value="">Select handoff-emitted Agent2 run</option>
              {agent2Runs.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_id} | {run.state} | {formatDate(run.updated_at)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="agent2-actions">
          <button
            onClick={runAgent3FromSelectedAgent2}
            disabled={!selectedAgent2RunId || loading}
            className="agent2-btn agent2-btn-cyan"
          >
            {loading ? <Loader2 size={12} className="inline animate-spin mr-1" /> : null}
            Run Agent3 from Pipeline Output
          </button>
          <button
            onClick={onRefreshAgent3}
            disabled={!agent3RunId || loading}
            className="agent2-btn agent2-btn-neutral"
          >
            Refresh Agent3 Data
          </button>
          <button
            onClick={refreshAgent2Runs}
            disabled={!story?.id || loading}
            className="agent2-btn agent2-btn-neutral"
          >
            Refresh Agent2 Handoffs
          </button>
        </div>

        {error ? <div className="agent2-error">{error}</div> : null}
        {agent3ActionMessage ? <div className="agent2-note">{agent3ActionMessage}</div> : null}

        {agent3Bootstrap ? (
          <div className="agent2-muted">
            Agent3 bootstrap message: <span className="agent2-mono">{agent3Bootstrap.message_id}</span>
          </div>
        ) : null}

        {agent3RunId ? (
          <div className="agent2-muted">
            Active Agent3 run: <span className="agent2-mono">{agent3RunId}</span>
          </div>
        ) : null}

        {agent3Snapshot?.run ? (
          <div className="agent2-agent3-state-grid">
            <div><span className="agent2-label">State:</span> <span className="agent2-mono">{agent3Snapshot.run.state}</span></div>
            <div><span className="agent2-label">Stage:</span> <span className="agent2-mono">{agent3Snapshot.run.stage}</span></div>
            <div><span className="agent2-label">Source Agent2 Run:</span> <span className="agent2-mono">{agent3Snapshot.run.source_agent2_run_id}</span></div>
          </div>
        ) : null}

        <div className="agent2-actions">
          <button
            onClick={onApprovePhase4Review}
            disabled={!isPhase4ReviewPending || loading}
            className="agent2-btn agent2-btn-teal"
          >
            Approve Review (Phase 5)
          </button>
          <button
            onClick={onEmitAgent3Handoff}
            disabled={agent3Snapshot?.run?.state !== 'handoff_pending' || loading}
            className="agent2-btn agent2-btn-cyan"
          >
            Emit Agent3 Handoff
          </button>
        </div>

        {agent3ContextArtifact ? (
          <div className="agent2-scraper-summary">
            <div><span className="agent2-label">Phase 3 Context Version:</span> {agent3ContextArtifact.context_version ?? 'n/a'}</div>
            <div><span className="agent2-label">Input Steps:</span> {Array.isArray(agent3ContextArtifact.input_steps) ? agent3ContextArtifact.input_steps.length : 0}</div>
            <div><span className="agent2-label">Output Steps:</span> {Array.isArray(agent3ContextArtifact.output_steps) ? agent3ContextArtifact.output_steps.length : 0}</div>
            <div><span className="agent2-label">Unresolved:</span> {agent3ContextArtifact.unresolved_count ?? 0}</div>
          </div>
        ) : null}

        <div className="agent2-grid-2">
          <div className="agent2-field agent2-field-block">
            <span>Phase 3 Reasoning Context</span>
            <pre className="agent2-json-preview">
              {JSON.stringify(agent3ContextArtifact || { message: 'No phase3 context artifact yet.' }, null, 2)}
            </pre>
          </div>
          <div className="agent2-field agent2-field-block">
            <span>Phase 4 Selector Result</span>
            <pre className="agent2-json-preview">
              {JSON.stringify(agent3SelectorArtifact || agent3LatestArtifact || { message: 'No selector artifact yet.' }, null, 2)}
            </pre>
          </div>
        </div>

        <div className="agent2-grid-2">
          <div>
            <div className="agent2-section-title agent2-section-title-tight">Agent3 Observability</div>
            <pre className="agent2-json-preview">
              {JSON.stringify(agent3Observability?.counters || { message: 'No observability data yet.' }, null, 2)}
            </pre>
          </div>
          <div>
            <div className="agent2-section-title agent2-section-title-tight">Agent3 Integrity</div>
            <pre className="agent2-json-preview">
              {JSON.stringify(agent3Integrity?.integrity || { message: 'No integrity data yet.' }, null, 2)}
            </pre>
          </div>
        </div>

        <div className="agent2-section-title agent2-section-title-tight">Agent3 Timeline</div>
        {!agent3Timeline.length ? (
          <div className="agent2-muted">No Agent3 timeline events yet.</div>
        ) : (
          <div className="agent2-timeline">
            {agent3Timeline.map((event) => (
              <div key={event.id} className="agent2-timeline-row">
                <span className="agent2-mono">{event.stage}</span>
                <span>{event.action}</span>
                <span className="agent2-time">{event.created_at}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="agent2-card">
        <div className="agent2-section-title">Agent3 Run History (Current Story)</div>
        {!story?.id ? (
          <div className="agent2-muted">Select a story to view Agent3 run history.</div>
        ) : !agent3History.length ? (
          <div className="agent2-muted">No Agent3 runs recorded for this story yet.</div>
        ) : (
          <div className="agent2-history">
            {agent3History.map((entry) => (
              <button key={entry.run_id} className="agent2-history-row" onClick={() => onSelectAgent3HistoryRun(entry.run_id)}>
                <span className="agent2-mono">{entry.run_id}</span>
                <span>{entry.state} • {formatDate(entry.updated_at)}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
