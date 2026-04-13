import { useMemo, useState } from 'react'
import { AlertTriangle, Clock3, RefreshCw, ShieldCheck } from 'lucide-react'
import { useQueueOps } from '../hooks/useQueueOps'
import './QueueOpsPanel.css'

const OPERATOR_KEY_STORAGE = 'operator_api_key'

function n(value) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

export default function QueueOpsPanel() {
  const [operatorKey, setOperatorKey] = useState(() => localStorage.getItem(OPERATOR_KEY_STORAGE) || '')
  const [auditStage, setAuditStage] = useState('')
  const [auditStatus, setAuditStatus] = useState('')
  const [auditStoryId, setAuditStoryId] = useState('')

  const {
    loading,
    error,
    queueHealth,
    queueItems,
    queueAudit,
    operatorIdentity,
    auditVerification,
    securityStatus,
    securityEvents,
    securityHistory,
    securitySummary,
    openIncidents,
    securityReadiness,
    lastUpdatedAt,
    refresh,
    cancelQueued,
    expirePending,
    triggerSecurityAlertTest,
    acknowledgeSecurityIncident,
    resolveSecurityIncident,
    exportSecurityData,
  } = useQueueOps({
    pollMs: 7000,
    limit: 50,
    operatorKey,
    auditFilters: {
      stage: auditStage,
      status: auditStatus,
      storyId: auditStoryId,
    },
  })

  const [busyId, setBusyId] = useState('')
  const [expireBusy, setExpireBusy] = useState(false)
  const [alertTestBusy, setAlertTestBusy] = useState(false)
  const [alertTestMessage, setAlertTestMessage] = useState('')
  const [incidentBusyId, setIncidentBusyId] = useState('')
  const [incidentMessage, setIncidentMessage] = useState('')
  const [exportBusy, setExportBusy] = useState(false)
  const [exportMessage, setExportMessage] = useState('')
  const activeLockouts = Array.isArray(securityStatus?.active_lockouts) ? securityStatus.active_lockouts : []

  const health = useMemo(() => {
    const pressure = String(queueHealth?.pressure || '').toLowerCase()
    if (pressure === 'high') return { label: 'degraded', className: 'queueops-badge bad' }
    if (pressure === 'elevated') return { label: 'watch', className: 'queueops-badge warn' }
    return { label: 'healthy', className: 'queueops-badge good' }
  }, [queueHealth?.pressure])

  const cancelItem = async (id) => {
    try {
      setBusyId(id)
      await cancelQueued(id)
    } finally {
      setBusyId('')
    }
  }

  const expireOld = async () => {
    try {
      setExpireBusy(true)
      await expirePending(3600)
    } finally {
      setExpireBusy(false)
    }
  }

  const runAlertTest = async () => {
    try {
      setAlertTestBusy(true)
      setAlertTestMessage('')
      const result = await triggerSecurityAlertTest('queue-ops-ui')
      const accepted = Boolean(result?.alert_test?.accepted)
      setAlertTestMessage(accepted ? 'Test alert sent.' : 'Test alert accepted.')
    } catch (e) {
      setAlertTestMessage(String(e?.message || 'Failed to send test alert'))
    } finally {
      setAlertTestBusy(false)
    }
  }

  const onAckIncident = async (incidentId) => {
    try {
      setIncidentBusyId(incidentId)
      setIncidentMessage('')
      await acknowledgeSecurityIncident(incidentId, 'queue-ops-ui')
      setIncidentMessage('Incident acknowledged.')
    } catch (e) {
      setIncidentMessage(String(e?.message || 'Failed to acknowledge incident'))
    } finally {
      setIncidentBusyId('')
    }
  }

  const onResolveIncident = async (incidentId) => {
    const note = window.prompt('Resolution note (optional):', '') || ''
    try {
      setIncidentBusyId(incidentId)
      setIncidentMessage('')
      await resolveSecurityIncident(incidentId, {
        resolvedBy: 'queue-ops-ui',
        resolutionNote: note,
      })
      setIncidentMessage('Incident resolved.')
    } catch (e) {
      setIncidentMessage(String(e?.message || 'Failed to resolve incident'))
    } finally {
      setIncidentBusyId('')
    }
  }

  const downloadJson = (filename, data) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  const onExportSecurity = async () => {
    try {
      setExportBusy(true)
      setExportMessage('')
      const payload = await exportSecurityData({ limit: 2000 })
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-')
      downloadJson(`operator-security-export-${timestamp}.json`, payload?.export || payload || {})
      setExportMessage('Export downloaded.')
    } catch (e) {
      setExportMessage(String(e?.message || 'Failed to export security dataset'))
    } finally {
      setExportBusy(false)
    }
  }

  const persistOperatorKey = (value) => {
    const next = String(value || '')
    setOperatorKey(next)
    localStorage.setItem(OPERATOR_KEY_STORAGE, next)
  }

  return (
    <div className="queueops-wrap">
      <section className="queueops-head">
        <div>
          <h3>Queue Ops</h3>
          <p>Live queue visibility and controls from Phase 13 operator experience.</p>
        </div>
        <div className="queueops-controls">
          <button className="queueops-btn" onClick={() => refresh()} disabled={loading}>
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
          <button className="queueops-btn" onClick={expireOld} disabled={expireBusy || loading}>
            <Clock3 size={13} className={expireBusy ? 'animate-spin' : ''} />
            Expire {'>'} 1h pending
          </button>
        </div>
      </section>

      {error ? <div className="queueops-error">{error}</div> : null}

      <section className="queueops-card">
        <div className="queueops-card-head">Operator Access</div>
        <label className="queueops-label">
          Operator API Key
          <input
            type="password"
            value={operatorKey}
            onChange={(e) => persistOperatorKey(e.target.value)}
            placeholder="x-operator-key"
            className="queueops-input"
          />
        </label>
        <div className="queueops-row" style={{ marginTop: 8 }}>
          <span>role</span>
          <span className="queueops-badge good">{String(operatorIdentity?.role || 'unknown')}</span>
        </div>
        <div className="queueops-row">
          <span>audit verify</span>
          <span className={Boolean(auditVerification?.valid) ? 'queueops-badge good' : 'queueops-badge bad'}>
            {Boolean(auditVerification?.valid) ? 'valid' : 'invalid'}
          </span>
        </div>
        <div className="queueops-row">
          <span>lockouts</span>
          <span className={activeLockouts.length ? 'queueops-badge bad' : 'queueops-badge good'}>
            {n(securityStatus?.lockout_count)}
          </span>
        </div>
        <div className="queueops-row">
          <span>recent failures</span>
          <span>{n(securityStatus?.recent_failure_count)}</span>
        </div>
        <div className="queueops-row">
          <span>ops readiness</span>
          <span className={Boolean(securityReadiness?.ready) ? 'queueops-badge good' : 'queueops-badge bad'}>
            {Boolean(securityReadiness?.ready) ? 'ready' : 'blocked'}
          </span>
        </div>
      </section>

      <section className="queueops-card">
        <div className="queueops-card-head">Security Incidents</div>
        <div className="queueops-row">
          <span>policy enabled</span>
          <span className={Boolean(securityStatus?.policy?.enabled) ? 'queueops-badge warn' : 'queueops-badge good'}>
            {Boolean(securityStatus?.policy?.enabled) ? 'yes' : 'no'}
          </span>
        </div>
        <div className="queueops-row">
          <span>window / max failures</span>
          <span>
            {n(securityStatus?.policy?.failure_window_seconds)}s / {n(securityStatus?.policy?.max_failures)}
          </span>
        </div>
        <div className="queueops-row">
          <span>lockout duration</span>
          <span>{n(securityStatus?.policy?.lockout_seconds)}s</span>
        </div>

        <div className="queueops-list queueops-security-list">
          {activeLockouts.map((lockout) => (
            <div key={String(lockout?.source || Math.random())} className="queueops-item">
              <div>
                <strong>{String(lockout?.source || 'unknown')}</strong>
                <div className="queueops-meta">
                  remaining: {n(lockout?.remaining_seconds)}s · failures: {n(lockout?.failures_recent)}
                </div>
              </div>
            </div>
          ))}
          {!activeLockouts.length ? <div className="queueops-empty">No active lockouts.</div> : null}
        </div>
        <div className="queueops-row" style={{ marginTop: 8 }}>
          <button className="queueops-btn" onClick={runAlertTest} disabled={alertTestBusy || loading}>
            {alertTestBusy ? 'sending...' : 'Send Test Alert'}
          </button>
          <span className="queueops-meta">admin only</span>
        </div>
        {alertTestMessage ? <div className="queueops-meta" style={{ marginTop: 6 }}>{alertTestMessage}</div> : null}
      </section>

      <section className="queueops-card">
        <div className="queueops-card-head">Incident History (Persistent)</div>
        <div className="queueops-row">
          <span>events</span>
          <span>{n(securitySummary?.events_count)}</span>
        </div>
        <div className="queueops-row">
          <span>denied</span>
          <span>{n(securitySummary?.denied_count)}</span>
        </div>
        <div className="queueops-row">
          <span>lockouts</span>
          <span>{n(securitySummary?.lockout_count)}</span>
        </div>
        <div className="queueops-row">
          <span>unique sources</span>
          <span>{n(securitySummary?.unique_sources)}</span>
        </div>
        <div className="queueops-row">
          <span>open incidents</span>
          <span>{openIncidents.length}</span>
        </div>
        <div className="queueops-row">
          <span>threshold</span>
          <span>{n(securityReadiness?.open_incident_threshold)}</span>
        </div>
        <div className="queueops-row" style={{ marginTop: 8 }}>
          <button className="queueops-btn" onClick={onExportSecurity} disabled={exportBusy || loading}>
            {exportBusy ? 'exporting...' : 'Export JSON'}
          </button>
          <span className="queueops-meta">offline audit bundle</span>
        </div>
        {exportMessage ? <div className="queueops-meta" style={{ marginTop: 6 }}>{exportMessage}</div> : null}

        <div className="queueops-list queueops-security-list">
          {securityHistory.map((event) => (
            <div key={String(event?.event_id || Math.random())} className="queueops-item">
              <div>
                <strong>{String(event?.stage || 'operator.auth')}</strong>
                <div className="queueops-meta">
                  status: {String(event?.status || 'n/a')} · source: {String(event?.source || '-')} · reason: {String(event?.reason || '-')}
                </div>
                <div className="queueops-meta">{String(event?.created_at || '')}</div>
              </div>
            </div>
          ))}
          {!securityHistory.length ? <div className="queueops-empty">No persisted incidents yet.</div> : null}
        </div>
      </section>

      <section className="queueops-card">
        <div className="queueops-card-head">Open Incident Workflow</div>
        <div className="queueops-list queueops-security-list">
          {openIncidents.map((incident) => {
            const incidentId = String(incident?.event_id || '')
            const state = String(incident?.state || 'open')
            const busy = incidentBusyId === incidentId
            return (
              <div key={incidentId || Math.random()} className="queueops-item">
                <div>
                  <strong>{String(incident?.stage || 'operator.auth')}</strong>
                  <div className="queueops-meta">
                    state: {state} · source: {String(incident?.source || '-')} · reason: {String(incident?.reason || '-')}
                  </div>
                  <div className="queueops-meta">{String(incident?.created_at || '')}</div>
                </div>
                <div className="queueops-actions-inline">
                  <button
                    className="queueops-btn"
                    disabled={busy || state === 'resolved'}
                    onClick={() => onAckIncident(incidentId)}
                  >
                    Ack
                  </button>
                  <button
                    className="queueops-btn"
                    disabled={busy || state === 'resolved'}
                    onClick={() => onResolveIncident(incidentId)}
                  >
                    Resolve
                  </button>
                </div>
              </div>
            )
          })}
          {!openIncidents.length ? <div className="queueops-empty">No open incidents.</div> : null}
        </div>
        {incidentMessage ? <div className="queueops-meta" style={{ marginTop: 6 }}>{incidentMessage}</div> : null}
      </section>

      <section className="queueops-grid">
        <div className="queueops-card">
          <div className="queueops-card-head"><ShieldCheck size={14} /> Health</div>
          <div className="queueops-row">
            <span className={health.className}>{health.label}</span>
            <span>pressure: {String(queueHealth?.pressure || 'n/a')}</span>
          </div>
          <div className="queueops-row">
            <span>saturation</span>
            <span>{n(queueHealth?.saturation).toFixed(3)}</span>
          </div>
          <div className="queueops-row">
            <span>oldest pending</span>
            <span>{n(queueHealth?.oldest_pending_age_seconds)}s</span>
          </div>
        </div>

        <div className="queueops-card">
          <div className="queueops-card-head"><AlertTriangle size={14} /> Totals</div>
          <div className="queueops-row"><span>enqueued</span><span>{n(queueHealth?.queue_totals?.enqueued)}</span></div>
          <div className="queueops-row"><span>completed</span><span>{n(queueHealth?.queue_totals?.completed)}</span></div>
          <div className="queueops-row"><span>failed</span><span>{n(queueHealth?.queue_totals?.failed)}</span></div>
          <div className="queueops-row"><span>timed out</span><span>{n(queueHealth?.queue_totals?.timed_out)}</span></div>
          <div className="queueops-row"><span>cancelled</span><span>{n(queueHealth?.queue_totals?.cancelled)}</span></div>
        </div>
      </section>

      <section className="queueops-card">
        <div className="queueops-card-head">Queued Items</div>
        <div className="queueops-list">
          {queueItems.map((item) => {
            const queued = String(item?.state || '').toLowerCase() === 'queued'
            const id = String(item?.execution_run_id || '')
            return (
              <div key={id} className="queueops-item">
                <div>
                  <strong>{id}</strong>
                  <div className="queueops-meta">{String(item?.state || 'unknown')} · {String(item?.stage || 'n/a')}</div>
                </div>
                <button
                  className="queueops-btn"
                  disabled={!queued || busyId === id}
                  onClick={() => cancelItem(id)}
                >
                  {busyId === id ? 'canceling...' : 'cancel queued'}
                </button>
              </div>
            )
          })}
          {!queueItems.length ? <div className="queueops-empty">No queue items to display.</div> : null}
        </div>
      </section>

      <section className="queueops-card">
        <div className="queueops-card-head">Queue Audit</div>
        <div className="queueops-filters">
          <input
            className="queueops-input"
            value={auditStoryId}
            onChange={(e) => setAuditStoryId(e.target.value)}
            placeholder="story_id filter"
          />
          <input
            className="queueops-input"
            value={auditStage}
            onChange={(e) => setAuditStage(e.target.value)}
            placeholder="stage filter (queue.run_end)"
          />
          <select
            className="queueops-input"
            value={auditStatus}
            onChange={(e) => setAuditStatus(e.target.value)}
          >
            <option value="">all status</option>
            <option value="ok">ok</option>
            <option value="error">error</option>
          </select>
        </div>
        <div className="queueops-list">
          {queueAudit.map((event) => (
            <div key={String(event?.event_id || Math.random())} className="queueops-item">
              <div>
                <strong>{String(event?.stage || 'queue.unknown')}</strong>
                <div className="queueops-meta">
                  status: {String(event?.status || 'n/a')} · story: {String(event?.story_id || '-')} · run: {String(event?.run_id || '-')}
                </div>
                <div className="queueops-meta">{String(event?.created_at || '')}</div>
              </div>
            </div>
          ))}
          {!queueAudit.length ? <div className="queueops-empty">No queue audit events for current filters.</div> : null}
        </div>
      </section>

      <section className="queueops-card">
        <div className="queueops-card-head">Security Alert Stream</div>
        <div className="queueops-list queueops-security-list">
          {securityEvents.map((event) => (
            <div key={String(event?.event_id || Math.random())} className="queueops-item">
              <div>
                <strong>{String(event?.stage || 'operator.auth')}</strong>
                <div className="queueops-meta">
                  status: {String(event?.status || 'n/a')} · source: {String(event?.source || '-')} · failures: {n(event?.failures_recent)}
                </div>
                <div className="queueops-meta">{String(event?.created_at || '')}</div>
              </div>
            </div>
          ))}
          {!securityEvents.length ? <div className="queueops-empty">No security alerts yet.</div> : null}
        </div>
      </section>

      <div className="queueops-footnote">Last updated: {lastUpdatedAt || 'n/a'}</div>
    </div>
  )
}
