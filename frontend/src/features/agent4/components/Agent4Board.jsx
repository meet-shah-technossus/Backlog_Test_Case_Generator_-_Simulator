import { useEffect, useMemo, useState } from 'react'
import { Loader2, Play, RefreshCw } from 'lucide-react'
import { useAgent4Run } from '../hooks/useAgent4Run'
import {
  cancelAgent4Phase11QueueItemWithKey,
  getAgent4Phase11QueueItems,
  getAgent4Phase11QueueProfile,
  getAgent4Phase11QueueSnapshot,
  getAgent4Phase12QueueHealth,
  expireAgent4Phase12PendingWithKey,
  recoverAgent4Phase10DispatcherStale,
  startAgent4Phase10Dispatcher,
  stopAgent4Phase10DispatcherWithKey,
} from '../api/agent4Api'
import './agent4.css'

const OPERATOR_KEY_STORAGE = 'operator_api_key'

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

function latestScriptBundle(snapshot) {
  const artifacts = Array.isArray(snapshot?.artifacts) ? snapshot.artifacts : []
  const match = artifacts.find((row) => row?.artifact?.artifact_type === 'phase5_generated_script_bundle')
  return match?.artifact || null
}

function uniqueRunsById(runs) {
  const seen = new Set()
  const out = []
  for (const run of runs || []) {
    const id = String(run?.run_id || '')
    if (!id || seen.has(id)) continue
    seen.add(id)
    out.push(run)
  }
  return out
}

function queuePressureClass(pressure) {
  const value = String(pressure || '').toLowerCase()
  if (value === 'high') return 'agent4-badge danger'
  if (value === 'elevated') return 'agent4-badge warn'
  return 'agent4-badge ok'
}

function inferTargetUrlFromStory(story) {
  const explicit = String(story?.target_url || '').trim()
  if (explicit) return explicit

  const corpus = `${String(story?.title || '')} ${String(story?.description || '')}`.toLowerCase()
  const keywordMap = [
    ['amazon', 'https://www.amazon.in'],
    ['airbnb', 'https://www.airbnb.com'],
    ['booking.com', 'https://www.booking.com'],
    ['flipkart', 'https://www.flipkart.com'],
    ['myntra', 'https://www.myntra.com'],
    ['walmart', 'https://www.walmart.com'],
    ['ebay', 'https://www.ebay.com'],
  ]

  for (const [keyword, url] of keywordMap) {
    if (corpus.includes(keyword)) return url
  }
  return ''
}

export default function Agent4Board({ story }) {
  const {
    loading,
    error,
    streaming,
    runId,
    runSnapshot,
    phase6Readiness,
    phase6ReasonCodes,
    tokenBuffer,
    observability,
    integrity,
    actionMessage,
    phase10Config,
    phase10Execution,
    phase10Events,
    agent3Runs,
    agent4History,
    loadAgent3Runs,
    loadAgent4History,
    loadPhase6ReasonCodes,
    getLastRunForStory,
    refreshRun,
    startFromAgent3Run,
    generateScriptsStream,
    reviewPhase6,
    handoffPhase7,
    setPhase10Config,
    runPhase10ExecutionStream,
    abortSSE,
  } = useAgent4Run()

  const [selectedAgent3RunId, setSelectedAgent3RunId] = useState('')
  const [selectedAgent4RunId, setSelectedAgent4RunId] = useState('')
  const [scriptDrafts, setScriptDrafts] = useState({})
  const [reviewDecision, setReviewDecision] = useState('approve')
  const [reviewReasonCode, setReviewReasonCode] = useState('')
  const [reviewerId, setReviewerId] = useState('human-reviewer')
  const [reviewSubmittedForRunId, setReviewSubmittedForRunId] = useState('')
  const [queueLoading, setQueueLoading] = useState(false)
  const [queueProfile, setQueueProfile] = useState(null)
  const [queueSnapshot, setQueueSnapshot] = useState(null)
  const [queueItems, setQueueItems] = useState([])
  const [queueHealth, setQueueHealth] = useState(null)
  const [operatorKey, setOperatorKey] = useState(() => localStorage.getItem(OPERATOR_KEY_STORAGE) || '')
  const inferredTargetUrl = useMemo(() => inferTargetUrlFromStory(story), [story])

  const draftKey = useMemo(() => {
    if (!runId) return ''
    return `agent4ScriptDrafts:${runId}`
  }, [runId])

  useEffect(() => {
    setSelectedAgent3RunId('')
    setSelectedAgent4RunId('')
  }, [story?.id])

  useEffect(() => {
    if (!story?.id) return
    Promise.all([
      loadAgent3Runs(story.id),
      loadAgent4History(story.id),
      loadPhase6ReasonCodes(),
    ]).catch(() => {})
  }, [story?.id, loadAgent3Runs, loadAgent4History, loadPhase6ReasonCodes])

  useEffect(() => {
    if (!selectedAgent3RunId && agent3Runs.length) {
      setSelectedAgent3RunId(agent3Runs[0].run_id)
    }
  }, [selectedAgent3RunId, agent3Runs])

  useEffect(() => {
    if (!inferredTargetUrl) return
    const current = String(phase10Config.targetUrl || '').trim()
    if (!current) {
      setPhase10Config((prev) => ({ ...prev, targetUrl: inferredTargetUrl }))
    }
  }, [inferredTargetUrl, phase10Config.targetUrl, setPhase10Config])

  useEffect(() => {
    if (!agent4History.length) return
    const remembered = getLastRunForStory(story?.id)
    const preferred = agent4History.find((run) => run.run_id === remembered)?.run_id || agent4History[0].run_id
    if (!selectedAgent4RunId) {
      setSelectedAgent4RunId(preferred)
    }
  }, [selectedAgent4RunId, agent4History, getLastRunForStory, story?.id])

  useEffect(() => {
    if (!story?.id || !selectedAgent4RunId) return
    const currentRunId = String(runSnapshot?.run?.run_id || '')
    if (currentRunId === String(selectedAgent4RunId)) return
    refreshRun(selectedAgent4RunId, { storyId: story?.id }).catch(() => {})
  }, [story?.id, selectedAgent4RunId, runSnapshot?.run?.run_id, refreshRun])

  useEffect(() => {
    if (!draftKey) {
      setScriptDrafts({})
      return
    }
    try {
      const raw = window.localStorage.getItem(draftKey)
      setScriptDrafts(raw ? JSON.parse(raw) : {})
    } catch {
      setScriptDrafts({})
    }
  }, [draftKey])

  useEffect(() => {
    if (!draftKey) return
    try {
      window.localStorage.setItem(draftKey, JSON.stringify(scriptDrafts || {}))
    } catch {
      // Ignore localStorage failures.
    }
  }, [draftKey, scriptDrafts])

  useEffect(() => {
    let active = true
    let timer = null

    const tick = async () => {
      try {
        const [profile, snapshotRes, itemsRes, healthRes] = await Promise.all([
          getAgent4Phase11QueueProfile(),
          getAgent4Phase11QueueSnapshot(1000),
          getAgent4Phase11QueueItems(50),
          getAgent4Phase12QueueHealth(2000),
        ])
        if (!active) return
        setQueueProfile(profile)
        setQueueSnapshot(snapshotRes?.snapshot || null)
        setQueueItems(Array.isArray(itemsRes?.items) ? itemsRes.items : [])
        setQueueHealth(healthRes?.health || null)
      } catch {
        // Keep board interactive even if queue snapshot fails.
      }
    }

    tick().catch(() => {})
    timer = window.setInterval(() => {
      tick().catch(() => {})
    }, 5000)

    return () => {
      active = false
      if (timer) window.clearInterval(timer)
    }
  }, [])

  const bundle = useMemo(() => latestScriptBundle(runSnapshot), [runSnapshot])
  const scripts = Array.isArray(bundle?.scripts) ? bundle.scripts : []
  const combinedScript = useMemo(() => {
    if (!scripts.length) return ''
    return scripts
      .map((script) => {
        const path = String(script?.path || 'tests/generated/unknown.py')
        const content = String(scriptDrafts?.[path] ?? script?.content ?? '')
        return `# ===== ${path} =====\n${content}`
      })
      .join('\n\n')
  }, [scripts, scriptDrafts])
  const runState = String(runSnapshot?.run?.state || '')
  const isLockedAfterHandoff = runState === 'handoff_emitted'
  const activeRunId = runId || selectedAgent4RunId
  const historyOptions = useMemo(() => {
    const currentRun = runSnapshot?.run || (runId ? { run_id: runId, state: 'active', updated_at: null } : null)
    return uniqueRunsById([...(currentRun ? [currentRun] : []), ...agent4History])
  }, [agent4History, runSnapshot?.run, runId])

  const hasManualEdits = useMemo(() => {
    return scripts.some((script) => {
      const original = String(script?.content ?? '')
      const current = String(scriptDrafts?.[script.path] ?? original)
      return current !== original
    })
  }, [scripts, scriptDrafts])

  useEffect(() => {
    if (hasManualEdits && reviewDecision === 'approve') {
      setReviewDecision('edit_approve')
      return
    }
    if (!hasManualEdits && reviewDecision === 'edit_approve') {
      setReviewDecision('approve')
    }
  }, [hasManualEdits, reviewDecision])

  useEffect(() => {
    if (!activeRunId) return
    if (reviewSubmittedForRunId && reviewSubmittedForRunId !== activeRunId) {
      setReviewSubmittedForRunId('')
    }
  }, [activeRunId, reviewSubmittedForRunId])

  const handleStart = async () => {
    if (!selectedAgent3RunId) return
    const data = await startFromAgent3Run(selectedAgent3RunId, { storyId: story?.id })
    const nextRunId = data?.agent4_snapshot?.run?.run_id || data?.create?.run?.run_id
    if (nextRunId) {
      setSelectedAgent4RunId(nextRunId)
    }
    await loadAgent4History(story?.id)
  }

  const handleLoadRun = async () => {
    if (!selectedAgent4RunId) return
    await refreshRun(selectedAgent4RunId, { storyId: story?.id })
  }

  const handleGenerate = async () => {
    const targetRunId = activeRunId
    if (!targetRunId) return
    await generateScriptsStream(targetRunId, { storyId: story?.id })
    await loadAgent4History(story?.id)
  }

  const reasonOptions = phase6ReasonCodes?.[reviewDecision] || []

  const handleReview = async () => {
    const targetRunId = activeRunId
    if (!targetRunId) return

    const editedScripts = scripts.map((script) => ({
      case_id: script.case_id,
      path: script.path,
      content: String(scriptDrafts?.[script.path] ?? script.content ?? ''),
    }))

    await reviewPhase6(
      targetRunId,
      {
        decision: reviewDecision,
        reviewer_id: reviewerId || 'human-reviewer',
        reason_code: reviewReasonCode || null,
        edited_scripts: reviewDecision === 'edit_approve' ? editedScripts : null,
      },
      { storyId: story?.id }
    )
    setReviewSubmittedForRunId(targetRunId)
    await loadAgent4History(story?.id)
  }

  const handleHandoff = async () => {
    const targetRunId = activeRunId
    if (!targetRunId) return
    await handoffPhase7(targetRunId, { storyId: story?.id })
    await loadAgent4History(story?.id)
  }

  const handlePhase10Run = async () => {
    const targetRunId = activeRunId
    if (!targetRunId) return
    await runPhase10ExecutionStream(targetRunId, { storyId: story?.id })
    await loadAgent4History(story?.id)
  }

  const handoffEnabledByFlow = reviewSubmittedForRunId === activeRunId

  const queuedItems = useMemo(() => {
    return queueItems.filter((item) => String(item?.state || '').toLowerCase() === 'queued')
  }, [queueItems])

  const phase10ProgressRows = useMemo(() => {
    return (phase10Events || [])
      .filter((event) => ['step_started', 'step_finished', 'step_skipped'].includes(String(event?.type || '')))
      .slice(-20)
      .map((event) => {
        const stepIndex = Number(event?.step_index || event?.result?.step_index || 0)
        const scriptPath =
          String(event?.script_path || '') ||
          String(event?.result?.script_path || '') ||
          'unknown-script'
        const status =
          String(event?.result?.status || '') ||
          (event?.type === 'step_started' ? 'running' : event?.type)
        const errorMessage = String(event?.result?.error_message || '')
        return {
          id: `${String(event?.type || 'evt')}:${stepIndex}:${scriptPath}:${status}`,
          type: String(event?.type || ''),
          stepIndex,
          scriptPath,
          status,
          errorMessage,
        }
      })
  }, [phase10Events])

  const refreshQueueOps = async () => {
    setQueueLoading(true)
    try {
      const [profile, snapshotRes, itemsRes, healthRes] = await Promise.all([
        getAgent4Phase11QueueProfile(),
        getAgent4Phase11QueueSnapshot(1000),
        getAgent4Phase11QueueItems(50),
        getAgent4Phase12QueueHealth(2000),
      ])
      setQueueProfile(profile)
      setQueueSnapshot(snapshotRes?.snapshot || null)
      setQueueItems(Array.isArray(itemsRes?.items) ? itemsRes.items : [])
      setQueueHealth(healthRes?.health || null)
    } finally {
      setQueueLoading(false)
    }
  }

  const cancelQueuedBulk = async () => {
    const targets = queuedItems.slice(0, 20)
    if (!targets.length) return
    setQueueLoading(true)
    try {
      await Promise.all(
        targets.map((item) =>
          cancelAgent4Phase11QueueItemWithKey(item.execution_run_id, {
            canceledBy: 'agent4-ops-panel',
            operatorKey,
          })
        )
      )
      await refreshQueueOps()
    } catch {
      setQueueLoading(false)
    }
  }

  const recoverStaleBulk = async () => {
    setQueueLoading(true)
    try {
      await recoverAgent4Phase10DispatcherStale(3600)
      await refreshQueueOps()
    } catch {
      setQueueLoading(false)
    }
  }

  const startDispatcher = async () => {
    setQueueLoading(true)
    try {
      await startAgent4Phase10Dispatcher()
      await refreshQueueOps()
    } catch {
      setQueueLoading(false)
    }
  }

  const stopDispatcher = async () => {
    setQueueLoading(true)
    try {
      await stopAgent4Phase10DispatcherWithKey(operatorKey)
      await refreshQueueOps()
    } catch {
      setQueueLoading(false)
    }
  }

  const expirePendingBulk = async () => {
    setQueueLoading(true)
    try {
      await expireAgent4Phase12PendingWithKey(3600, operatorKey)
      await refreshQueueOps()
    } catch {
      setQueueLoading(false)
    }
  }

  const persistOperatorKey = (value) => {
    const next = String(value || '')
    setOperatorKey(next)
    localStorage.setItem(OPERATOR_KEY_STORAGE, next)
  }

  return (
    <div className="agent4-board">
      <section className="agent4-panel">
        <div className="agent4-panel-header">
          <h3>Phase 11 Operations</h3>
          <button className="agent4-btn ghost" onClick={refreshQueueOps} disabled={queueLoading}>
            <RefreshCw size={12} /> Refresh Queue
          </button>
        </div>

        <div className="agent4-actions-row">
          <label className="agent4-muted" style={{ minWidth: 120 }}>Operator Key</label>
          <input
            value={operatorKey}
            onChange={(e) => persistOperatorKey(e.target.value)}
            type="password"
            placeholder="x-operator-key"
          />
        </div>

        <div className="agent4-actions-row">
          <span className={queuePressureClass(queueSnapshot?.pressure)}>
            pressure: {String(queueSnapshot?.pressure || 'n/a')}
          </span>
          <span className="agent4-muted">
            queue {Number(queueSnapshot?.queue_size || 0)} / {Number(queueSnapshot?.max_queue_size || 0)}
          </span>
          <span className="agent4-muted">
            dispatcher: {String(Boolean(queueSnapshot?.dispatcher?.running))}
          </span>
        </div>

        <div className="agent4-actions-row">
          <button className="agent4-btn" onClick={startDispatcher} disabled={queueLoading}>Start Dispatcher</button>
          <button className="agent4-btn" onClick={stopDispatcher} disabled={queueLoading}>Stop Dispatcher</button>
          <button className="agent4-btn" onClick={recoverStaleBulk} disabled={queueLoading}>Recover Stale</button>
          <button className="agent4-btn" onClick={expirePendingBulk} disabled={queueLoading}>Expire Pending TTL</button>
          <button className="agent4-btn danger" onClick={cancelQueuedBulk} disabled={queueLoading || !queuedItems.length}>
            Cancel Queued (bulk)
          </button>
        </div>

        <div className="agent4-actions-row">
          <span className="agent4-muted">saturation: {Number(queueHealth?.saturation || 0).toFixed(3)}</span>
          <span className="agent4-muted">oldest pending: {Number(queueHealth?.oldest_pending_age_seconds || 0)}s</span>
          <span className="agent4-muted">timed out: {Number(queueHealth?.queue_totals?.timed_out || 0)}</span>
        </div>

        <pre className="agent4-stream agent4-stream-sm">
          {JSON.stringify(
            {
              queue_profile: queueProfile,
              queue_snapshot: queueSnapshot,
              queue_health: queueHealth,
              queued_items_preview: queuedItems.slice(0, 10),
            },
            null,
            2
          )}
        </pre>
      </section>

      <section className="agent4-panel">
        <div className="agent4-panel-header">
          <h3>Agent 4 Run Control</h3>
          <button className="agent4-btn ghost" onClick={() => {
            Promise.all([loadAgent3Runs(story?.id), loadAgent4History(story?.id)]).catch(() => {})
          }} disabled={loading || !story?.id}>
            <RefreshCw size={12} /> Refresh
          </button>
        </div>

        <div className="agent4-grid-two">
          <div>
            <label>Agent 3 Runs (handoff-ready)</label>
            <select
              value={selectedAgent3RunId}
              onChange={(e) => setSelectedAgent3RunId(e.target.value)}
            >
              <option value="">Select Agent 3 run</option>
              {agent3Runs.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_id} | {run.state} | {formatDate(run.updated_at)}
                </option>
              ))}
            </select>
            <button
              className="agent4-btn primary"
              onClick={handleStart}
              disabled={loading || !selectedAgent3RunId}
            >
              {loading ? <Loader2 className="spin" size={12} /> : <Play size={12} />} Start Agent 4 Run
            </button>
          </div>

          <div>
            <label>Agent 4 Run History</label>
            <select
              value={selectedAgent4RunId}
              onChange={(e) => setSelectedAgent4RunId(e.target.value)}
            >
              <option value="">Select Agent 4 run</option>
              {historyOptions.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_id} | {run.state} | {formatDate(run.updated_at)}
                </option>
              ))}
            </select>
            <button className="agent4-btn" onClick={handleLoadRun} disabled={loading || !selectedAgent4RunId}>
              Load Run Snapshot
            </button>
          </div>
        </div>

        <div className="agent4-actions-row">
          <button className="agent4-btn accent" onClick={handleGenerate} disabled={loading || !activeRunId || isLockedAfterHandoff}>
            {streaming ? <Loader2 className="spin" size={12} /> : <Play size={12} />} Run Script Generation (Stream)
          </button>
          {streaming && (
            <button className="agent4-btn ghost" onClick={abortSSE}>Stop Stream</button>
          )}
        </div>

        {phase6Readiness ? (
          <div className="agent4-phase6-banner">
            <strong>Phase 6 Suggested Action:</strong> {phase6Readiness?.recommended_decision || 'n/a'}
            <span>
              {' '}| readiness_score: {phase6Readiness?.readiness?.readiness_score ?? 'n/a'}
            </span>
          </div>
        ) : null}

        {error ? <p className="agent4-error">{error}</p> : null}
        {actionMessage ? <p className="agent4-note">{actionMessage}</p> : null}
      </section>

      <section className="agent4-panel">
        <h3>Live Token Stream</h3>
        <pre className="agent4-stream">{tokenBuffer || 'No streamed tokens yet.'}</pre>
      </section>

      <section className="agent4-panel">
        <h3>Phase 10 Execution Stream</h3>
        <div className="agent4-grid-two">
          <div>
            <label>Target URL</label>
            <input
              value={phase10Config.targetUrl}
              onChange={(e) => setPhase10Config((prev) => ({ ...prev, targetUrl: e.target.value }))}
              placeholder="https://example.com"
            />
          </div>
          <div>
            <label>Started By</label>
            <input
              value={phase10Config.startedBy}
              onChange={(e) => setPhase10Config((prev) => ({ ...prev, startedBy: e.target.value }))}
            />
          </div>
          <div>
            <label>Max Attempts</label>
            <input
              type="number"
              min={1}
              max={5}
              value={phase10Config.maxAttempts}
              onChange={(e) => setPhase10Config((prev) => ({ ...prev, maxAttempts: Number(e.target.value || 1) }))}
            />
          </div>
          <div>
            <label>Max Scripts</label>
            <input
              type="number"
              min={0}
              max={100}
              value={phase10Config.maxScripts}
              onChange={(e) => setPhase10Config((prev) => ({ ...prev, maxScripts: Number(e.target.value || 0) }))}
            />
          </div>
          <div>
            <label>Early Stop After Failures</label>
            <input
              type="number"
              min={0}
              max={100}
              value={phase10Config.earlyStopAfterFailures}
              onChange={(e) => setPhase10Config((prev) => ({ ...prev, earlyStopAfterFailures: Number(e.target.value || 0) }))}
            />
          </div>
          <div>
            <label>Parallel Workers</label>
            <input
              type="number"
              min={1}
              max={10}
              value={phase10Config.parallelWorkers}
              onChange={(e) => setPhase10Config((prev) => ({ ...prev, parallelWorkers: Number(e.target.value || 1) }))}
            />
          </div>
        </div>

        <div className="agent4-actions-row">
          <button className="agent4-btn accent" onClick={handlePhase10Run} disabled={loading || !activeRunId}>
            {streaming ? <Loader2 className="spin" size={12} /> : <Play size={12} />} Run Phase 10 Execution Stream
          </button>
        </div>

        {phase10Execution ? (
          <pre className="agent4-stream agent4-stream-sm">{JSON.stringify(phase10Execution, null, 2)}</pre>
        ) : (
          <p className="agent4-muted">No phase10 execution snapshot yet.</p>
        )}

        {phase10ProgressRows.length ? (
          <div className="agent4-stream agent4-stream-sm">
            <strong>Execution Progress</strong>
            {phase10ProgressRows.map((row) => (
              <div key={row.id} className="agent4-muted">
                step {row.stepIndex || '?'} | {row.status} | {row.scriptPath}
                {row.errorMessage ? ` | ${row.errorMessage}` : ''}
              </div>
            ))}
          </div>
        ) : null}

        <pre className="agent4-stream">{phase10Events.length ? JSON.stringify(phase10Events, null, 2) : 'No phase10 stream events yet.'}</pre>
      </section>

      <section className="agent4-panel">
        <h3>Generated Scripts</h3>
        {!scripts.length ? <p className="agent4-muted">No script bundle generated for this run yet.</p> : null}
        {scripts.map((script) => (
          <article className="agent4-script-card" key={script.path}>
            <header>
              <strong>{script.path}</strong>
              <span>{script.case_id}</span>
            </header>
            <textarea
              value={String(scriptDrafts?.[script.path] ?? script.content ?? '')}
              disabled={isLockedAfterHandoff}
              onChange={(e) => {
                const value = e.target.value
                setScriptDrafts((prev) => ({ ...(prev || {}), [script.path]: value }))
              }}
            />
          </article>
        ))}
      </section>

      <section className="agent4-panel">
        <h3>Combined Playwright Script (All Test Cases)</h3>
        <pre className="agent4-stream">{combinedScript || 'No generated scripts available yet.'}</pre>
      </section>

      <section className="agent4-panel">
        <h3>Phase 6 Review And Phase 7 Handoff</h3>
        <div className="agent4-grid-two">
          <div>
            <label>Decision</label>
            <select value={reviewDecision} onChange={(e) => setReviewDecision(e.target.value)} disabled={isLockedAfterHandoff}>
              <option value="approve">approve</option>
              <option value="edit_approve">edit_approve</option>
              <option value="retry">retry</option>
              <option value="reject">reject</option>
            </select>
          </div>
          <div>
            <label>Reviewer</label>
            <input value={reviewerId} onChange={(e) => setReviewerId(e.target.value)} disabled={isLockedAfterHandoff} />
          </div>
          <div>
            <label>Reason Code</label>
            <select value={reviewReasonCode} onChange={(e) => setReviewReasonCode(e.target.value)} disabled={isLockedAfterHandoff}>
              <option value="">None</option>
              {reasonOptions.map((code) => (
                <option key={code} value={code}>{code}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="agent4-actions-row">
          <button className="agent4-btn primary" onClick={handleReview} disabled={loading || !activeRunId || isLockedAfterHandoff}>
            Submit Review Decision
          </button>
          <button className="agent4-btn accent" onClick={handleHandoff} disabled={loading || !activeRunId || !handoffEnabledByFlow || isLockedAfterHandoff}>
            Emit Handoff (Persist/Publish)
          </button>
        </div>
        {!handoffEnabledByFlow && !isLockedAfterHandoff ? (
          <p className="agent4-muted">Submit Review Decision first to enable Emit Handoff.</p>
        ) : null}
        {isLockedAfterHandoff ? (
          <p className="agent4-muted">Run is locked after handoff emission. Editing and review actions are disabled.</p>
        ) : null}
      </section>

      <section className="agent4-grid-two">
        <article className="agent4-panel">
          <h3>Phase 9 Observability</h3>
          <pre>{JSON.stringify(observability?.counters || {}, null, 2)}</pre>
        </article>
        <article className="agent4-panel">
          <h3>Phase 9 Integrity</h3>
          <pre>{JSON.stringify(integrity?.integrity || {}, null, 2)}</pre>
        </article>
      </section>
    </div>
  )
}
