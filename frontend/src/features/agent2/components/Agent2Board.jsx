import { useEffect, useMemo, useState } from 'react'
import { Loader2, RefreshCw } from 'lucide-react'
import { useAgent2Run } from '../hooks/useAgent2Run'
import './agent2.css'

function jsonPositionToLineColumn(text, position) {
  const safePos = Math.max(0, Math.min(position, text.length))
  let line = 1
  let lastLineBreak = -1
  for (let i = 0; i < safePos; i += 1) {
    if (text[i] === '\n') {
      line += 1
      lastLineBreak = i
    }
  }
  return { line, column: safePos - lastLineBreak }
}

function getEditedPayloadValidation(text) {
  const value = (text || '').trim()
  if (!value) return { valid: false, error: null }
  try {
    JSON.parse(value)
    return { valid: true, error: null }
  } catch (e) {
    const message = e?.message || 'Invalid JSON'
    const match = /position\s+(\d+)/i.exec(message)
    if (match) {
      const position = Number.parseInt(match[1], 10)
      if (Number.isFinite(position)) {
        const { line, column } = jsonPositionToLineColumn(value, position)
        return {
          valid: false,
          error: `${message} (line ${line}, column ${column})`,
        }
      }
    }
    return { valid: false, error: message }
  }
}

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

function stageTone(state) {
  if (!state) return 'agent2-stage-default'
  if (state.includes('failed')) return 'agent2-stage-failed'
  if (state.includes('review')) return 'agent2-stage-review'
  if (state.includes('handoff')) return 'agent2-stage-handoff'
  return 'agent2-stage-default'
}

export default function Agent2Board({ story }) {
  const {
    blueprint,
    runId,
    runSnapshot,
    loading,
    error,
    loadBlueprint,
    refreshRun,
    loadRun,
    loadApprovedRuns,
    startFromAgent1Run,
    loadDashboard,
    generateRunStream,
    reasonCodes,
    loadReasonCodes,
    reviewRun,
    handoffRun,
    dashboard,
    approvedAgent1Runs,
    tokenBuffer,
    streaming,
    abortSSE,
  } = useAgent2Run()

  const [selectedAgent1RunId, setSelectedAgent1RunId] = useState('')
  const [reasonCode, setReasonCode] = useState('')
  const [editedPayload, setEditedPayload] = useState('')
  const [hydratedPayloadRunId, setHydratedPayloadRunId] = useState('')

  const state = runSnapshot?.run?.state || 'intake_pending'
  const latestArtifact = runSnapshot?.latest_artifact?.artifact || null
  const generatedCases = latestArtifact?.generated_steps?.test_cases || []
  const timeline = runSnapshot?.timeline || []
  const reviewDiff = runSnapshot?.review_diff || null
  const handoffs = runSnapshot?.handoffs || []
  const latestHandoff = handoffs[0] || null
  const storyHistory = useMemo(() => dashboard?.recentRuns || [], [dashboard])
  const counters = dashboard?.counters || {}
  const currentSourceAgent1RunId = runSnapshot?.run?.source_agent1_run_id || null
  const failureCode = runSnapshot?.run?.last_error_code || ''
  const failureMessage = runSnapshot?.run?.last_error_message || ''
  const isLockedAfterHandoff = state === 'handoff_emitted'
  const generatedPayload = useMemo(() => {
    if (!latestArtifact) return ''
    try {
      return JSON.stringify(latestArtifact, null, 2)
    } catch {
      return ''
    }
  }, [latestArtifact])
  const generatedCaseCount = generatedCases.length
  const generatedStepCount = generatedCases.reduce((acc, testCase) => {
    const steps = Array.isArray(testCase?.steps) ? testCase.steps.length : 0
    return acc + steps
  }, 0)
  const editedPayloadValidation = useMemo(
    () => getEditedPayloadValidation(editedPayload),
    [editedPayload]
  )

  useEffect(() => {
    loadBlueprint().catch(() => {})
    loadReasonCodes().catch(() => {})
  }, [loadBlueprint, loadReasonCodes])

  useEffect(() => {
    let stopped = false

    const syncApprovedAndInitialize = async () => {
      const [approved] = await Promise.all([
        loadApprovedRuns(story?.id || null),
        loadDashboard(story?.id || null),
      ])

      if (stopped) return
      if (!Array.isArray(approved) || !approved.length) {
        setSelectedAgent1RunId('')
        return
      }

      const latest = approved[0]
      setSelectedAgent1RunId((prev) => {
        if (!prev) return latest.run_id
        const stillExists = approved.some((item) => item.run_id === prev)
        return stillExists ? prev : latest.run_id
      })

      if (!runId && !currentSourceAgent1RunId) {
        await startFromAgent1Run(latest.run_id)
      }
    }

    syncApprovedAndInitialize().catch(() => {})

    return () => {
      stopped = true
    }
  }, [
    loadApprovedRuns,
    loadDashboard,
    startFromAgent1Run,
    story?.id,
    runId,
    currentSourceAgent1RunId,
  ])

  useEffect(() => {
    if (!runId) {
      setEditedPayload('')
      setHydratedPayloadRunId('')
      return
    }
    if (!generatedPayload) return
    if (hydratedPayloadRunId !== runId) {
      setEditedPayload(generatedPayload)
      setHydratedPayloadRunId(runId)
    }
  }, [generatedPayload, hydratedPayloadRunId, runId])

  const onStartFromSelected = async () => {
    if (!selectedAgent1RunId) return
    await startFromAgent1Run(selectedAgent1RunId)
    await loadApprovedRuns(story?.id || null)
    await loadDashboard(story?.id || null)
  }

  const onGenerate = async () => {
    if (!runId) return
    await generateRunStream(runId, {})
  }

  const onReview = async (decision) => {
    if (!runId) return

    let parsedEdited = null
    if (decision === 'edit_approve') {
      try {
        parsedEdited = JSON.parse(editedPayload)
      } catch {
        parsedEdited = null
      }
    }

    await reviewRun(runId, {
      decision,
      reviewer_id: 'human_reviewer',
      reason_code: reasonCode || null,
      edited_payload: parsedEdited,
    })
  }

  const rejectCodes = reasonCodes?.reject || []
  const retryCodes = reasonCodes?.retry || []

  return (
    <div className="agent2-board">
      <div className="agent2-card">
        <div className="agent2-header">
          <div>
            <div className="agent2-title">Agent 2 - Step Assembly</div>
            <div className="agent2-subtitle">Story: {story?.title || 'Select a story'}</div>
          </div>
          <span className={`agent2-stage ${stageTone(state)}`}>{state}</span>
        </div>

        <div className="agent2-form-grid agent2-form-grid-single">
          <label className="agent2-field">
            <span>Approved Agent1 Runs (latest selected by default)</span>
            <select value={selectedAgent1RunId} onChange={(e) => setSelectedAgent1RunId(e.target.value)}>
              <option value="">Select approved Agent1 run</option>
              {approvedAgent1Runs.map((run) => (
                <option key={run.run_id} value={run.run_id}>
                  {run.run_id} | {run.state} | {formatDate(run.updated_at)}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="agent2-actions">
          <button onClick={onStartFromSelected} disabled={loading || !selectedAgent1RunId} className="agent2-btn agent2-btn-blue">
            {loading ? <Loader2 size={12} className="inline animate-spin mr-1" /> : null}
            Start From Selected Agent1 Run
          </button>
          <button onClick={() => loadApprovedRuns(story?.id || null)} disabled={loading || !story?.id} className="agent2-btn agent2-btn-violet">Refresh Approved Runs</button>
          <button onClick={onGenerate} disabled={(loading && !streaming) || !runId || streaming} className="agent2-btn agent2-btn-teal">
            {streaming ? 'Generating...' : 'Generate Steps'}
          </button>
          {streaming && (
            <button onClick={abortSSE} className="agent2-btn agent2-btn-red">Stop Stream</button>
          )}
          <button onClick={() => refreshRun()} disabled={loading || !runId} className="agent2-btn agent2-btn-neutral">
            <RefreshCw size={11} className="inline mr-1" />
            Refresh
          </button>
        </div>

        {error && <div className="agent2-error">{error}</div>}

        {!loading && blueprint && (
          <div className="agent2-muted">
            {blueprint.agent} phase window: {blueprint.phase_window.join(' to ')}
          </div>
        )}

        {approvedAgent1Runs.length > 0 && (
          <div className="agent2-muted">
            Latest approved Agent1 run: <span className="agent2-mono">{approvedAgent1Runs[0].run_id}</span> ({formatDate(approvedAgent1Runs[0].updated_at)})
          </div>
        )}

        {selectedAgent1RunId && (
          <div className="agent2-muted">
            Selected Agent1 run: <span className="agent2-mono">{selectedAgent1RunId}</span>
          </div>
        )}

        {runId && (
          <div className="agent2-muted">
            Active Agent2 run: <span className="agent2-mono">{runId}</span>
            {currentSourceAgent1RunId ? (
              <> | Source Agent1 run: <span className="agent2-mono">{currentSourceAgent1RunId}</span></>
            ) : null}
          </div>
        )}

        {streaming && (
          <div className="agent2-stream-box">
            <div className="agent2-stream-title">Live Model Output</div>
            <pre className="agent2-stream-content">{tokenBuffer || 'Waiting for tokens...'}</pre>
          </div>
        )}

        {state === 'failed' && (failureCode || failureMessage) && (
          <div className="agent2-error-detail">
            <div className="agent2-error-detail-title">Generation Failure Detail</div>
            {failureCode ? <div><span className="agent2-label">Code:</span> <span className="agent2-mono">{failureCode}</span></div> : null}
            {failureMessage ? <div><span className="agent2-label">Message:</span> {failureMessage}</div> : null}
          </div>
        )}
      </div>

      <div className="agent2-card">
        <div className="agent2-section-title">Operational Widgets</div>
        <div className="agent2-stats-grid">
          <div className="agent2-stat-card">
            <div className="agent2-stat-label">Total Runs</div>
            <div className="agent2-stat-value">{counters.total_runs ?? 0}</div>
          </div>
          <div className="agent2-stat-card">
            <div className="agent2-stat-label">Success</div>
            <div className="agent2-stat-value">{counters.success_count ?? 0}</div>
          </div>
          <div className="agent2-stat-card">
            <div className="agent2-stat-label">Retry</div>
            <div className="agent2-stat-value">{counters.retry_count ?? 0}</div>
          </div>
          <div className="agent2-stat-card">
            <div className="agent2-stat-label">Rejected</div>
            <div className="agent2-stat-value">{counters.rejection_count ?? 0}</div>
          </div>
          <div className="agent2-stat-card">
            <div className="agent2-stat-label">Failed</div>
            <div className="agent2-stat-value">{counters.failure_count ?? 0}</div>
          </div>
        </div>
      </div>

      <div className="agent2-card">
        <div className="agent2-section-title">Generation Result</div>
        <div className="agent2-result-metrics">
          <div className="agent2-result-metric">
            <span className="agent2-result-metric-label">Cases</span>
            <span className="agent2-result-metric-value">{generatedCaseCount}</span>
          </div>
          <div className="agent2-result-metric">
            <span className="agent2-result-metric-label">Steps</span>
            <span className="agent2-result-metric-value">{generatedStepCount}</span>
          </div>
          <div className="agent2-result-metric">
            <span className="agent2-result-metric-label">Run</span>
            <span className="agent2-result-metric-value agent2-mono">{runId || 'n/a'}</span>
          </div>
        </div>
        {!generatedCases.length ? (
          <div className="agent2-muted">No generated steps yet.</div>
        ) : (
          <div className="agent2-case-list">
            {generatedCases.map((testCase) => (
              <div key={testCase.id} className="agent2-case-item">
                <div className="agent2-case-header">
                  <div className="agent2-case-title">{testCase.id}</div>
                  <div className="agent2-case-step-count">{(testCase.steps || []).length} steps</div>
                </div>
                <ol className="agent2-steps-list">
                  {(testCase.steps || []).map((step) => (
                    <li key={`${testCase.id}-${step.number}`} className="agent2-step-row">
                      <span className="agent2-step-badge">{step.number}</span>
                      <span>{step.action}</span>
                    </li>
                  ))}
                </ol>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="agent2-grid-2">
        <div className="agent2-card">
          <div className="agent2-section-title">Review Panel</div>
          <div className="agent2-actions">
            <button
              onClick={() => setEditedPayload(generatedPayload)}
              disabled={!generatedPayload || loading || isLockedAfterHandoff}
              className="agent2-btn agent2-btn-neutral"
            >
              Load Latest Generated JSON
            </button>
          </div>

          <div className="agent2-field agent2-field-block">
            <span>Generated Output JSON (read-only)</span>
            <pre className="agent2-json-preview">
              {generatedPayload || 'No generated payload yet.'}
            </pre>
          </div>

          <div className="agent2-actions">
            <button onClick={() => onReview('approve')} disabled={loading || !runId || isLockedAfterHandoff} className="agent2-btn agent2-btn-teal">Approve</button>
            <button
              onClick={() => onReview('edit_approve')}
              disabled={loading || !runId || !editedPayload || !editedPayloadValidation.valid || isLockedAfterHandoff}
              className="agent2-btn agent2-btn-violet"
            >
              Edit + Approve
            </button>
            <button onClick={() => onReview('reject')} disabled={loading || !runId || !reasonCode || isLockedAfterHandoff} className="agent2-btn agent2-btn-red">Reject</button>
            <button onClick={() => onReview('retry')} disabled={loading || !runId || !reasonCode || isLockedAfterHandoff} className="agent2-btn agent2-btn-yellow">Retry</button>
          </div>
          <label className="agent2-field agent2-field-block">
            <span>Reason Code (required for reject/retry)</span>
            <select value={reasonCode} onChange={(e) => setReasonCode(e.target.value)}>
              <option value="">Select reason code</option>
              {[...rejectCodes, ...retryCodes].map((code) => (
                <option key={code} value={code}>{code}</option>
              ))}
            </select>
          </label>
          <label className="agent2-field agent2-field-block">
            <span>Edited Payload JSON (for edit_approve)</span>
            <textarea
              value={editedPayload}
              onChange={(e) => setEditedPayload(e.target.value)}
              readOnly={isLockedAfterHandoff}
              placeholder='{"generated_steps":{"test_cases":[...]}}'
            />
            {isLockedAfterHandoff ? (
              <div className="agent2-muted">Manual edits are disabled after handoff emission for this run.</div>
            ) : null}
            {editedPayload.trim() && editedPayloadValidation.error ? (
              <div className="agent2-json-error">{editedPayloadValidation.error}</div>
            ) : null}
            {editedPayload.trim() && editedPayloadValidation.valid ? (
              <div className="agent2-json-ok">Valid JSON</div>
            ) : null}
          </label>
          {reviewDiff?.has_diff && (
            <div className="agent2-muted">
              Diff: latest v{reviewDiff.latest_version} vs v{reviewDiff.previous_version} | cases delta {reviewDiff.summary?.cases_delta ?? 0} | steps delta {reviewDiff.summary?.steps_delta ?? 0}
            </div>
          )}
        </div>
        <div className="agent2-card">
          <div className="agent2-section-title">Handoff Panel</div>
          <div className="agent2-actions">
            <button onClick={() => handoffRun(runId)} disabled={loading || !runId || isLockedAfterHandoff} className="agent2-btn agent2-btn-cyan">
              Emit Agent2 {'->'} Agent3 Handoff
            </button>
          </div>
          {isLockedAfterHandoff ? (
            <div className="agent2-muted">This run is locked after handoff emission. Create a new run to make further changes.</div>
          ) : null}
          {!latestHandoff ? (
            <div className="agent2-muted">No handoff emitted yet.</div>
          ) : (
            <div className="agent2-handoff-summary">
              <div><span className="agent2-label">Message:</span> <span className="agent2-mono">{latestHandoff.message_id}</span></div>
              <div><span className="agent2-label">Status:</span> {latestHandoff.delivery_status}</div>
              <div><span className="agent2-label">Contract:</span> {latestHandoff.contract_version}</div>
              <div><span className="agent2-label">Task:</span> {latestHandoff.task_type}</div>
            </div>
          )}
        </div>
      </div>

      <div className="agent2-card">
        <div className="agent2-section-title">Timeline</div>
        {!timeline.length ? (
          <div className="agent2-muted">No events recorded yet.</div>
        ) : (
          <div className="agent2-timeline">
            {timeline.map((event) => (
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
        <div className="agent2-section-title">Run History (Current Story)</div>
        {!story?.id ? (
          <div className="agent2-muted">Select a story to view run history.</div>
        ) : !storyHistory.length ? (
          <div className="agent2-muted">No Agent2 runs recorded for this backlog item yet.</div>
        ) : (
          <div className="agent2-history">
            {storyHistory
              .slice()
              .sort((a, b) => parseDateValue(b.updated_at) - parseDateValue(a.updated_at))
              .map((entry) => (
                <button key={entry.run_id} className="agent2-history-row" onClick={() => loadRun(entry.run_id)}>
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