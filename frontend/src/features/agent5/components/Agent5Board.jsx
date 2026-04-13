import { useEffect, useMemo, useState } from 'react'
import { Loader2, Pause, Play, RefreshCw, Square, CheckCircle2 } from 'lucide-react'
import { useAgent5Playwright } from '../hooks/useAgent5Playwright'
import {
  cancelAgent4Phase11QueueItemWithKey,
  getAgent4Phase11QueueItems,
  getAgent4Phase11QueueProfile,
  getAgent4Phase11QueueSnapshot,
  getAgent4Phase12QueueHealth,
  expireAgent4Phase12PendingWithKey,
  getEvaluationGlobal,
  getEvaluationRollout,
  getEvaluationStory,
  recoverAgent4Phase10DispatcherStale,
  startAgent4Phase10Dispatcher,
  stopAgent4Phase10DispatcherWithKey,
} from '../api/agent5Api'
import './agent5.css'

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

function renderCapability(runtimeCheck) {
  const caps = runtimeCheck?.capabilities || {}
  const installs = caps.browser_installations || {}
  const entries = Object.entries(installs)
  if (!entries.length) return 'n/a'
  return entries.map(([name, ok]) => `${name}:${ok ? 'ok' : 'missing'}`).join(' | ')
}

function formatPercent(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '0.0%'
  return `${n.toFixed(1)}%`
}

function queuePressureClass(pressure) {
  const value = String(pressure || '').toLowerCase()
  if (value === 'high') return 'agent5-badge bad'
  if (value === 'elevated') return 'agent5-badge warn'
  return 'agent5-badge good'
}

export default function Agent5Board({ story }) {
  const [runFilter, setRunFilter] = useState('all')
  const [storyEvaluation, setStoryEvaluation] = useState(null)
  const [globalEvaluation, setGlobalEvaluation] = useState(null)
  const [rolloutEvaluation, setRolloutEvaluation] = useState(null)
  const [queueLoading, setQueueLoading] = useState(false)
  const [queueProfile, setQueueProfile] = useState(null)
  const [queueSnapshot, setQueueSnapshot] = useState(null)
  const [queueItems, setQueueItems] = useState([])
  const [queueHealth, setQueueHealth] = useState(null)
  const [operatorKey, setOperatorKey] = useState(() => localStorage.getItem(OPERATOR_KEY_STORAGE) || '')
  const {
    loading,
    error,
    streaming,
    actionMessage,
    runtimeCheck,
    agent5Contract,
    agent5StateMachine,
    handoffRuns,
    selectedRunId,
    runSnapshot,
    scripts,
    selectedScriptPaths,
    selectedScripts,
    persistedRun,
    persistedArtifacts,
    persistedTimeline,
    transitionAuditArtifacts,
    executionConfig,
    activeExecution,
    executionHistory,
    agent5Runs,
    selectedAgent5RunId,
    agent5RunSnapshot,
    agent5Orchestration,
    agent5Command,
    executionEvents,
    streamPaused,
    forceRegenerateStage7,
    gate7Form,
    stage8WritebackForm,
    gate8Form,
    observabilitySnapshot,
    reliabilityRecoverForm,
    lastReliabilityRecovery,
    setExecutionConfig,
    setSelectedRunId,
    setSelectedAgent5RunId,
    setAgent5Command,
    setForceRegenerateStage7,
    setGate7Form,
    setStage8WritebackForm,
    setGate8Form,
    setReliabilityRecoverForm,
    loadRuntimeCheck,
    loadAgent5ContractAndStateMachine,
    loadRunsForStory,
    loadRunDetails,
    loadAgent5RunSnapshot,
    createOrLinkAgent5Run,
    applyAgent5Command,
    advanceToGate7Pending,
    generateStage7Analysis,
    submitGate7Decision,
    generateStage8Writeback,
    submitGate8Decision,
    recoverStaleAgent5Runs,
    retryFailedAgent5Run,
    toggleScript,
    selectAllScripts,
    runExecution,
    pauseExecution,
    resumeExecution,
    stopExecution,
  } = useAgent5Playwright()

  useEffect(() => {
    loadRuntimeCheck().catch(() => {})
  }, [loadRuntimeCheck])

  useEffect(() => {
    loadAgent5ContractAndStateMachine().catch(() => {})
  }, [loadAgent5ContractAndStateMachine])

  useEffect(() => {
    if (!story?.id) return
    loadRunsForStory(story.id).catch(() => {})
  }, [story?.id, loadRunsForStory])

  useEffect(() => {
    if (!story?.id) {
      setStoryEvaluation(null)
      setRolloutEvaluation(null)
      return
    }
    getEvaluationStory(story.id, 100).then(setStoryEvaluation).catch(() => {})
    getEvaluationRollout(story.id, 100).then(setRolloutEvaluation).catch(() => {})
  }, [story?.id])

  useEffect(() => {
    getEvaluationGlobal(300).then(setGlobalEvaluation).catch(() => {})
  }, [story?.id])

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

  useEffect(() => {
    if (!selectedRunId) return
    loadRunDetails(selectedRunId).catch(() => {})
  }, [selectedRunId, loadRunDetails])

  useEffect(() => {
    if (!selectedAgent5RunId) return
    loadAgent5RunSnapshot(selectedAgent5RunId).catch(() => {})
  }, [selectedAgent5RunId, loadAgent5RunSnapshot])

  const activeState = String(activeExecution?.state || '')
  const availableCommands = Array.isArray(agent5Orchestration?.available_commands) ? agent5Orchestration.available_commands : []
  const blockedCommands = Array.isArray(agent5Orchestration?.blocked_commands) ? agent5Orchestration.blocked_commands : []
  const videos = useMemo(() => {
    const evidence = activeExecution?.evidence || activeExecution?.result?.evidence || {}
    return Array.isArray(evidence?.videos) ? evidence.videos : []
  }, [activeExecution])

  const runSummary = activeExecution?.summary || activeExecution?.result?.summary || {}
  const stage7Analysis = persistedRun?.stage7_analysis || {}
  const executionSummary = persistedRun?.execution_summary || {}
  const gate7Decision = persistedRun?.gate7_decision || {}
  const stage8Writeback = persistedRun?.stage8_writeback || {}
  const gate8Decision = persistedRun?.gate8_decision || {}
  const observabilityDurations = Array.isArray(observabilitySnapshot?.stage_durations) ? observabilitySnapshot.stage_durations : []
  const observabilityChecksums = observabilitySnapshot?.payload_checksums || {}
  const observabilityEvidence = observabilitySnapshot?.evidence_summary || {}
  const filteredAgent5Runs = useMemo(() => {
    const runs = Array.isArray(agent5Runs) ? agent5Runs : []
    if (runFilter === 'all') {
      return runs
    }

    const classify = (state) => {
      const value = String(state || '').toLowerCase()
      if (value === 'completed') return 'passed'
      if (value === 'failed' || value === 'canceled') return 'failed'
      return 'partial'
    }

    return runs.filter((run) => classify(run?.state) === runFilter)
  }, [agent5Runs, runFilter])

  const queuedItems = useMemo(() => {
    return queueItems.filter((item) => String(item?.state || '').toLowerCase() === 'queued')
  }, [queueItems])

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
            canceledBy: 'agent5-ops-panel',
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
    <div className="agent5-board">
      <section className="agent5-panel">
        <div className="agent5-panel-header">
          <h3>Agent 5 Playwright Runner</h3>
          <button
            className="agent5-btn ghost"
            onClick={() => {
              Promise.all([
                loadRuntimeCheck(),
                loadAgent5ContractAndStateMachine(),
                loadRunsForStory(story?.id),
                selectedRunId ? loadRunDetails(selectedRunId) : Promise.resolve(null),
                story?.id ? getEvaluationStory(story.id, 100).then(setStoryEvaluation) : Promise.resolve(null),
                story?.id ? getEvaluationRollout(story.id, 100).then(setRolloutEvaluation) : Promise.resolve(null),
                getEvaluationGlobal(300).then(setGlobalEvaluation),
              ]).catch(() => {})
            }}
            disabled={loading}
          >
            <RefreshCw size={12} /> Refresh
          </button>
        </div>

        <div className="agent5-meta-grid">
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Runtime Ready</span>
            <span className="agent5-meta-value">{String(Boolean(runtimeCheck?.ready))}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Browser Installations</span>
            <span className="agent5-meta-value">{renderCapability(runtimeCheck)}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Diagnostics</span>
            <span className="agent5-meta-value">{(runtimeCheck?.diagnostics || []).join(' | ') || 'none'}</span>
          </div>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Phase 10 Evaluation and Rollout</h3>
        <div className="agent5-meta-grid">
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Story Pass Rate</span>
            <span className="agent5-meta-value">{formatPercent(storyEvaluation?.metrics?.pass_rate)}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Story Flake Rate</span>
            <span className="agent5-meta-value">{formatPercent(storyEvaluation?.metrics?.flake_rate)}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Selector Mismatch Rate</span>
            <span className="agent5-meta-value">{formatPercent(storyEvaluation?.metrics?.selector_mismatch_rate)}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Global Pass Rate</span>
            <span className="agent5-meta-value">{formatPercent(globalEvaluation?.metrics?.pass_rate)}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Story Rollout Status</span>
            <span className="agent5-meta-value">{String(rolloutEvaluation?.status || 'n/a')}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Rollout Score</span>
            <span className="agent5-meta-value">{Number(rolloutEvaluation?.score || 0).toFixed(2)}</span>
          </div>
        </div>
        <div className="agent5-history">
          <strong>Story Evaluation Snapshot</strong>
          <pre>{storyEvaluation ? JSON.stringify(storyEvaluation, null, 2) : 'No story evaluation loaded yet.'}</pre>
        </div>
      </section>

      <section className="agent5-panel">
        <div className="agent5-panel-header">
          <h3>Phase 11 Operations</h3>
          <button className="agent5-btn ghost" onClick={() => refreshQueueOps()} disabled={queueLoading}>
            <RefreshCw size={12} /> Refresh Queue
          </button>
        </div>

        <div className="agent5-actions-row">
          <label className="agent5-muted" style={{ minWidth: 120 }}>Operator Key</label>
          <input
            value={operatorKey}
            onChange={(e) => persistOperatorKey(e.target.value)}
            type="password"
            placeholder="x-operator-key"
          />
        </div>

        <div className="agent5-actions-row">
          <span className={queuePressureClass(queueSnapshot?.pressure)}>
            pressure: {String(queueSnapshot?.pressure || 'n/a')}
          </span>
          <span className="agent5-muted">
            queue {Number(queueSnapshot?.queue_size || 0)} / {Number(queueSnapshot?.max_queue_size || 0)}
          </span>
          <span className="agent5-muted">
            dispatcher: {String(Boolean(queueSnapshot?.dispatcher?.running))}
          </span>
        </div>

        <div className="agent5-actions-row">
          <button className="agent5-btn" onClick={() => startDispatcher()} disabled={queueLoading}>Start Dispatcher</button>
          <button className="agent5-btn" onClick={() => stopDispatcher()} disabled={queueLoading}>Stop Dispatcher</button>
          <button className="agent5-btn" onClick={() => recoverStaleBulk()} disabled={queueLoading}>Recover Stale</button>
          <button className="agent5-btn" onClick={() => expirePendingBulk()} disabled={queueLoading}>Expire Pending TTL</button>
          <button className="agent5-btn danger" onClick={() => cancelQueuedBulk()} disabled={queueLoading || !queuedItems.length}>
            Cancel Queued (bulk)
          </button>
        </div>

        <div className="agent5-actions-row">
          <span className="agent5-muted">saturation: {Number(queueHealth?.saturation || 0).toFixed(3)}</span>
          <span className="agent5-muted">oldest pending: {Number(queueHealth?.oldest_pending_age_seconds || 0)}s</span>
          <span className="agent5-muted">timed out: {Number(queueHealth?.queue_totals?.timed_out || 0)}</span>
        </div>

        <pre className="agent5-stream">{JSON.stringify({
          queue_profile: queueProfile,
          queue_snapshot: queueSnapshot,
          queue_health: queueHealth,
          queued_items_preview: queuedItems.slice(0, 10),
        }, null, 2)}</pre>
      </section>

      <section className="agent5-panel">
        <h3>Agent 5 Contract and Lifecycle</h3>
        <div className="agent5-meta-grid">
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Contract Phase</span>
            <span className="agent5-meta-value">{agent5Contract?.phase || 'n/a'}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Contract Version</span>
            <span className="agent5-meta-value">{agent5Contract?.contract_version || 'n/a'}</span>
          </div>
          <div className="agent5-meta-item">
            <span className="agent5-meta-label">Lifecycle States</span>
            <span className="agent5-meta-value">{Array.isArray(agent5StateMachine?.states) ? agent5StateMachine.states.length : 0}</span>
          </div>
        </div>
        <pre className="agent5-stream">{agent5Contract ? JSON.stringify(agent5Contract, null, 2) : 'No Agent5 contract loaded.'}</pre>
        <pre className="agent5-stream">{agent5StateMachine ? JSON.stringify(agent5StateMachine, null, 2) : 'No Agent5 lifecycle state machine loaded.'}</pre>
      </section>

      <section className="agent5-panel">
        <h3>Select Agent 4 Handoff Run</h3>
        <label>Handoff-emitted runs for selected story</label>
        <select value={selectedRunId} onChange={(e) => setSelectedRunId(e.target.value)}>
          <option value="">Select run</option>
          {handoffRuns.map((run) => (
            <option key={run.run_id} value={run.run_id}>
              {run.run_id} | {run.state} | {formatDate(run.updated_at)}
            </option>
          ))}
        </select>

        <div className="agent5-history">
          <strong>Execution History</strong>
          <pre>{executionHistory.length ? JSON.stringify(executionHistory, null, 2) : 'No phase10 executions yet.'}</pre>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Persisted Agent 5 Runs (A5.2)</h3>
        <div className="agent5-actions-row">
          <button
            className="agent5-btn"
            onClick={() => createOrLinkAgent5Run()}
            disabled={loading || !selectedRunId}
          >
            Persist Current Agent 5 Run
          </button>
        </div>

        <label>Persisted runs for selected Agent4 run</label>
        <div className="agent5-actions-row">
          <label>Run Filter</label>
          <select value={runFilter} onChange={(e) => setRunFilter(e.target.value)}>
            <option value="all">all</option>
            <option value="passed">passed</option>
            <option value="partial">partial</option>
            <option value="failed">failed</option>
          </select>
          <span className="agent5-muted">Showing {filteredAgent5Runs.length} of {agent5Runs.length}</span>
        </div>
        <select
          value={selectedAgent5RunId}
          onChange={(e) => setSelectedAgent5RunId(e.target.value)}
          disabled={!filteredAgent5Runs.length}
        >
          <option value="">Select Agent5 run</option>
          {filteredAgent5Runs.map((run) => (
            <option key={run.agent5_run_id} value={run.agent5_run_id}>
              {run.agent5_run_id} | {run.state} | {formatDate(run.updated_at)}
            </option>
          ))}
        </select>

        <pre className="agent5-stream">{agent5RunSnapshot ? JSON.stringify(agent5RunSnapshot, null, 2) : 'No persisted Agent5 run selected.'}</pre>

        <div className="agent5-history">
          <strong>A5.5 Orchestration Readiness</strong>
          <pre>{agent5Orchestration ? JSON.stringify(agent5Orchestration, null, 2) : 'No orchestration snapshot loaded yet.'}</pre>
        </div>

        <div className="agent5-actions-row">
          <select
            value={agent5Command}
            onChange={(e) => setAgent5Command(e.target.value)}
            disabled={loading || !selectedAgent5RunId}
          >
            {!availableCommands.length ? <option value="">No available commands</option> : null}
            {availableCommands.map((command) => (
              <option key={command} value={command}>{command}</option>
            ))}
          </select>
          <button
            className="agent5-btn"
            onClick={() => applyAgent5Command(agent5Command, { source: 'agent5-board' })}
            disabled={loading || !selectedAgent5RunId || !agent5Command || !availableCommands.length}
          >
            Apply A5.3 Command
          </button>
          <button
            className="agent5-btn"
            onClick={() => advanceToGate7Pending()}
            disabled={loading || !selectedAgent5RunId || !agent5Orchestration?.can_advance_to_gate7_pending}
          >
            Advance To gate7_pending
          </button>
        </div>

        {!!blockedCommands.length ? (
          <div className="agent5-history">
            <strong>A5.4 Blocked Commands</strong>
            <pre>{JSON.stringify(blockedCommands, null, 2)}</pre>
          </div>
        ) : null}

        <div className="agent5-actions-row">
          <label className="agent5-toggle">
            <input
              type="checkbox"
              checked={Boolean(forceRegenerateStage7)}
              onChange={(e) => setForceRegenerateStage7(e.target.checked)}
            />
            Force regenerate Stage 7 analysis
          </label>
          <button
            className="agent5-btn accent"
            onClick={() => generateStage7Analysis()}
            disabled={loading || !selectedAgent5RunId}
          >
            Generate Stage 7 Analysis (A5.7)
          </button>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Script Selection</h3>
        <div className="agent5-actions-row">
          <button className="agent5-btn" onClick={() => selectAllScripts(true)} disabled={!scripts.length}>Select All</button>
          <button className="agent5-btn" onClick={() => selectAllScripts(false)} disabled={!scripts.length}>Clear All</button>
          <span className="agent5-muted">Selected {selectedScripts.length} / {scripts.length}</span>
        </div>

        <div className="agent5-script-list">
          {!scripts.length ? <p className="agent5-muted">No generated scripts found in this run snapshot.</p> : null}
          {scripts.map((script) => (
            <label key={script.path} className="agent5-script-item">
              <input
                type="checkbox"
                checked={Boolean(selectedScriptPaths[script.path])}
                onChange={(e) => toggleScript(script.path, e.target.checked)}
              />
              <span>{script.path}</span>
              {script.caseId ? <em>{script.caseId}</em> : null}
            </label>
          ))}
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Run Controls</h3>
        <div className="agent5-grid-two">
          <div>
            <label>Target URL</label>
            <input
              value={executionConfig.targetUrl}
              onChange={(e) => setExecutionConfig((prev) => ({ ...prev, targetUrl: e.target.value }))}
              placeholder="https://example.com"
            />
          </div>
          <div>
            <label>Started By</label>
            <input
              value={executionConfig.startedBy}
              onChange={(e) => setExecutionConfig((prev) => ({ ...prev, startedBy: e.target.value }))}
            />
          </div>
          <div>
            <label>Max Attempts</label>
            <input
              type="number"
              min={1}
              max={5}
              value={executionConfig.maxAttempts}
              onChange={(e) => setExecutionConfig((prev) => ({ ...prev, maxAttempts: Number(e.target.value || 1) }))}
            />
          </div>
          <div>
            <label>Max Scripts (optional cap)</label>
            <input
              type="number"
              min={0}
              max={100}
              value={executionConfig.maxScripts}
              onChange={(e) => setExecutionConfig((prev) => ({ ...prev, maxScripts: Number(e.target.value || 0) }))}
            />
          </div>
          <div>
            <label>Early Stop After Failures</label>
            <input
              type="number"
              min={1}
              max={100}
              value={executionConfig.earlyStopAfterFailures}
              onChange={(e) => setExecutionConfig((prev) => ({ ...prev, earlyStopAfterFailures: Number(e.target.value || 1) }))}
            />
          </div>
          <div>
            <label>Parallel Workers</label>
            <input
              type="number"
              min={1}
              max={10}
              value={executionConfig.parallelWorkers}
              onChange={(e) => setExecutionConfig((prev) => ({ ...prev, parallelWorkers: Number(e.target.value || 1) }))}
            />
          </div>
        </div>

        <label className="agent5-toggle">
          <input
            type="checkbox"
            checked={Boolean(executionConfig.useSmokeProbeScript)}
            onChange={(e) => setExecutionConfig((prev) => ({ ...prev, useSmokeProbeScript: e.target.checked }))}
          />
          Use deterministic smoke probe script (fast-pass validation)
        </label>

        <div className="agent5-actions-row">
          <button
            className="agent5-btn accent"
            onClick={() => runExecution()}
            disabled={loading || !selectedRunId || (!executionConfig.useSmokeProbeScript && selectedScripts.length === 0)}
          >
            {loading ? <Loader2 className="spin" size={12} /> : <Play size={12} />} Start Script Testing
          </button>

          <button
            className="agent5-btn"
            onClick={() => pauseExecution()}
            disabled={loading || !activeExecution?.execution_run_id || activeState !== 'running'}
          >
            <Pause size={12} /> Pause Execution
          </button>

          <button
            className="agent5-btn"
            onClick={() => resumeExecution()}
            disabled={loading || !activeExecution?.execution_run_id || activeState !== 'paused'}
          >
            <Play size={12} /> Resume Execution
          </button>

          <button className="agent5-btn danger" onClick={() => stopExecution(operatorKey)} disabled={loading || !activeExecution?.execution_run_id}>
            <Square size={12} /> Stop Run
          </button>
        </div>

        <div className="agent5-status-row">
          <span>Streaming: {String(streaming)}</span>
          <span>Paused: {String(streamPaused)}</span>
          <span>State: {activeState || 'n/a'}</span>
        </div>

        {error ? <p className="agent5-error">{error}</p> : null}
        {actionMessage ? <p className="agent5-note">{actionMessage}</p> : null}
      </section>

      <section className="agent5-panel">
        <h3>Execution Output</h3>
        <div className="agent5-summary-row">
          <span className="agent5-pill"><CheckCircle2 size={12} /> passed: {runSummary?.passed ?? 'n/a'}</span>
          <span className="agent5-pill">failed: {runSummary?.failed ?? 'n/a'}</span>
          <span className="agent5-pill">total: {runSummary?.total ?? 'n/a'}</span>
        </div>

        <div>
          <strong>Video Evidence</strong>
          <ul className="agent5-video-list">
            {videos.length ? videos.map((path) => <li key={path}>{path}</li>) : <li>None yet</li>}
          </ul>
        </div>

        <pre className="agent5-stream">{activeExecution ? JSON.stringify(activeExecution, null, 2) : 'No execution snapshot yet.'}</pre>
        <pre className="agent5-stream">{executionEvents.length ? JSON.stringify(executionEvents, null, 2) : 'No execution events yet.'}</pre>
      </section>

      <section className="agent5-panel">
        <h3>Persisted Result Viewer (A5.6)</h3>
        <div className="agent5-grid-two">
          <div className="agent5-history">
            <strong>Execution Summary</strong>
            <pre>{Object.keys(executionSummary).length ? JSON.stringify(executionSummary, null, 2) : 'No execution summary persisted.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Stage 7 Analysis</strong>
            <pre>{Object.keys(stage7Analysis).length ? JSON.stringify(stage7Analysis, null, 2) : 'No stage7 analysis persisted.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Gate 7 Decision</strong>
            <pre>{Object.keys(gate7Decision).length ? JSON.stringify(gate7Decision, null, 2) : 'No gate7 decision persisted.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Stage 8 Writeback</strong>
            <pre>{Object.keys(stage8Writeback).length ? JSON.stringify(stage8Writeback, null, 2) : 'No stage8 writeback persisted.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Gate 8 Decision</strong>
            <pre>{Object.keys(gate8Decision).length ? JSON.stringify(gate8Decision, null, 2) : 'No gate8 decision persisted.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Artifacts Count</strong>
            <pre>{JSON.stringify({ artifacts: persistedArtifacts.length, timeline: persistedTimeline.length }, null, 2)}</pre>
          </div>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Human Gate 7 (A5.8)</h3>
        <div className="agent5-grid-two">
          <div>
            <label>Reviewer ID</label>
            <input
              value={gate7Form.reviewerId}
              onChange={(e) => setGate7Form((prev) => ({ ...prev, reviewerId: e.target.value }))}
            />
          </div>
          <div>
            <label>Decision</label>
            <select
              value={gate7Form.decision}
              onChange={(e) => setGate7Form((prev) => ({ ...prev, decision: e.target.value }))}
            >
              <option value="approve">approve</option>
              <option value="request_revision">request_revision</option>
              <option value="reject">reject</option>
            </select>
          </div>
          <div>
            <label>Reason Code</label>
            <input
              value={gate7Form.reasonCode}
              onChange={(e) => setGate7Form((prev) => ({ ...prev, reasonCode: e.target.value }))}
            />
          </div>
          <div>
            <label>Comment</label>
            <input
              value={gate7Form.comment}
              onChange={(e) => setGate7Form((prev) => ({ ...prev, comment: e.target.value }))}
              placeholder="Optional reviewer comment"
            />
          </div>
        </div>
        <div className="agent5-actions-row">
          <button
            className="agent5-btn accent"
            onClick={() => submitGate7Decision()}
            disabled={loading || !selectedAgent5RunId}
          >
            Submit Gate 7 Decision
          </button>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Stage 8 Backlog Writeback (A5.9)</h3>
        <div className="agent5-grid-two">
          <div>
            <label>Actor</label>
            <input
              value={stage8WritebackForm.actor}
              onChange={(e) => setStage8WritebackForm((prev) => ({ ...prev, actor: e.target.value }))}
            />
          </div>
          <div>
            <label>Idempotency Key (optional)</label>
            <input
              value={stage8WritebackForm.idempotencyKey}
              onChange={(e) => setStage8WritebackForm((prev) => ({ ...prev, idempotencyKey: e.target.value }))}
              placeholder="Leave empty for deterministic key"
            />
          </div>
        </div>
        <label className="agent5-toggle">
          <input
            type="checkbox"
            checked={Boolean(stage8WritebackForm.forceRegenerate)}
            onChange={(e) => setStage8WritebackForm((prev) => ({ ...prev, forceRegenerate: e.target.checked }))}
          />
          Force regenerate writeback payload
        </label>
        <div className="agent5-actions-row">
          <button
            className="agent5-btn accent"
            onClick={() => generateStage8Writeback()}
            disabled={loading || !selectedAgent5RunId}
          >
            Generate Stage 8 Writeback
          </button>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Gate 8 Final Confirmation (A5.10)</h3>
        <div className="agent5-grid-two">
          <div>
            <label>Reviewer ID</label>
            <input
              value={gate8Form.reviewerId}
              onChange={(e) => setGate8Form((prev) => ({ ...prev, reviewerId: e.target.value }))}
            />
          </div>
          <div>
            <label>Decision</label>
            <select
              value={gate8Form.decision}
              onChange={(e) => setGate8Form((prev) => ({ ...prev, decision: e.target.value }))}
            >
              <option value="confirm">confirm</option>
              <option value="followup">followup</option>
              <option value="reject">reject</option>
            </select>
          </div>
          <div>
            <label>Reason Code</label>
            <input
              value={gate8Form.reasonCode}
              onChange={(e) => setGate8Form((prev) => ({ ...prev, reasonCode: e.target.value }))}
            />
          </div>
          <div>
            <label>Comment</label>
            <input
              value={gate8Form.comment}
              onChange={(e) => setGate8Form((prev) => ({ ...prev, comment: e.target.value }))}
              placeholder="Optional reviewer comment"
            />
          </div>
        </div>
        <div className="agent5-actions-row">
          <button
            className="agent5-btn accent"
            onClick={() => submitGate8Decision()}
            disabled={loading || !selectedAgent5RunId}
          >
            Submit Gate 8 Decision
          </button>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Observability Snapshot (A5.11)</h3>
        <div className="agent5-grid-two">
          <div className="agent5-history">
            <strong>Stage Durations</strong>
            <pre>{observabilityDurations.length ? JSON.stringify(observabilityDurations, null, 2) : 'No stage durations available.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Payload Checksums</strong>
            <pre>{Object.keys(observabilityChecksums).length ? JSON.stringify(observabilityChecksums, null, 2) : 'No checksums available.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Evidence Summary</strong>
            <pre>{Object.keys(observabilityEvidence).length ? JSON.stringify(observabilityEvidence, null, 2) : 'No evidence summary available.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Raw Observability</strong>
            <pre>{observabilitySnapshot ? JSON.stringify(observabilitySnapshot, null, 2) : 'No observability snapshot loaded.'}</pre>
          </div>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Reliability Controls (A5.12)</h3>
        <div className="agent5-grid-two">
          <div>
            <label>Recovery Actor</label>
            <input
              value={reliabilityRecoverForm.actor}
              onChange={(e) => setReliabilityRecoverForm((prev) => ({ ...prev, actor: e.target.value }))}
            />
          </div>
          <div>
            <label>Older Than Seconds</label>
            <input
              type="number"
              min={60}
              max={86400}
              value={reliabilityRecoverForm.olderThanSeconds}
              onChange={(e) => setReliabilityRecoverForm((prev) => ({ ...prev, olderThanSeconds: Number(e.target.value || 1800) }))}
            />
          </div>
          <div>
            <label>Recovery Limit</label>
            <input
              type="number"
              min={1}
              max={1000}
              value={reliabilityRecoverForm.limit}
              onChange={(e) => setReliabilityRecoverForm((prev) => ({ ...prev, limit: Number(e.target.value || 100) }))}
            />
          </div>
        </div>
        <div className="agent5-actions-row">
          <button
            className="agent5-btn"
            onClick={() => recoverStaleAgent5Runs()}
            disabled={loading}
          >
            Recover Stale Runs
          </button>
          <button
            className="agent5-btn"
            onClick={() => retryFailedAgent5Run()}
            disabled={loading || !selectedAgent5RunId}
          >
            Retry Selected Failed Run
          </button>
        </div>
        <div className="agent5-history">
          <strong>Last Recovery Result</strong>
          <pre>{lastReliabilityRecovery ? JSON.stringify(lastReliabilityRecovery, null, 2) : 'No recovery run yet.'}</pre>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Timeline and Audit Panel (A5.6)</h3>
        <div className="agent5-grid-two">
          <div className="agent5-history">
            <strong>Timeline Events</strong>
            <pre>{persistedTimeline.length ? JSON.stringify(persistedTimeline, null, 2) : 'No timeline events yet.'}</pre>
          </div>
          <div className="agent5-history">
            <strong>Transition Audit Artifacts</strong>
            <pre>{transitionAuditArtifacts.length ? JSON.stringify(transitionAuditArtifacts, null, 2) : 'No transition audit artifacts yet.'}</pre>
          </div>
        </div>
      </section>

      <section className="agent5-panel">
        <h3>Selected Run Snapshot</h3>
        <pre className="agent5-stream">{runSnapshot ? JSON.stringify(runSnapshot, null, 2) : 'No run snapshot loaded.'}</pre>
      </section>
    </div>
  )
}
