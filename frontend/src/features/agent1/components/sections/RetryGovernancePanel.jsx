import { useMemo, useState } from 'react'

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

export default function RetryGovernancePanel({
  runId,
  retryRequests,
  retryAuditEvents,
  revisionState,
  migrationStatus,
  loading,
  loadRetryGovernance,
  loadRetryAudit,
  loadRevisions,
  loadMigrationStatus,
  repairMigrationLinks,
  assignRetryReviewer,
  autoAssignRetryReviewer,
  reviewRetryRequest,
  approveAndRunRetry,
  promoteRevision,
}) {
  const [selectedRequestId, setSelectedRequestId] = useState('')
  const [reviewerId, setReviewerId] = useState('agent1-reviewer')
  const [assignedBy, setAssignedBy] = useState('operator')
  const [comment, setComment] = useState('')

  const selectedRequest = useMemo(() => {
    return (retryRequests || []).find((row) => row.request_id === selectedRequestId) || null
  }, [retryRequests, selectedRequestId])

  return (
    <div className="agent1-card">
      <div className="agent1-section-title">Retry Governance (Phase 2)</div>
      {!runId ? <div className="agent1-muted">Create or load a run to view retry governance requests.</div> : null}

      <div className="agent1-governance-toolbar">
        <button
          className="agent1-btn agent1-btn-neutral"
          onClick={() => loadRetryGovernance(runId)}
          disabled={loading || !runId}
        >
          Refresh Requests
        </button>
        <button
          className="agent1-btn agent1-btn-neutral"
          onClick={() => loadRevisions(runId, true)}
          disabled={loading || !runId}
        >
          Refresh Revisions
        </button>
        <button
          className="agent1-btn agent1-btn-neutral"
          onClick={() => loadMigrationStatus()}
          disabled={loading}
        >
          Refresh Migration Status
        </button>
        <button
          className="agent1-btn agent1-btn-yellow"
          onClick={() => repairMigrationLinks('operator')}
          disabled={loading}
        >
          Repair Orphan Links
        </button>
      </div>

      <div className="agent1-section-title">Business ID Migration Status (Phase 6)</div>
      {migrationStatus ? (
        <>
          <div className="agent1-result-metrics">
            <div className="agent1-result-metric">
              <div className="agent1-result-metric-label">Rows Checked</div>
              <div className="agent1-result-metric-value">
                {migrationStatus?.summary?.total_rows_checked ?? 0}
              </div>
            </div>
            <div className="agent1-result-metric">
              <div className="agent1-result-metric-label">Missing IDs</div>
              <div className="agent1-result-metric-value">
                {migrationStatus?.summary?.rows_missing_business_id ?? 0}
              </div>
            </div>
            <div className="agent1-result-metric">
              <div className="agent1-result-metric-label">Orphan Links</div>
              <div className="agent1-result-metric-value">
                {migrationStatus?.summary?.orphan_link_count ?? 0}
              </div>
            </div>
          </div>

          <div className="agent1-history">
            {(migrationStatus?.tables || []).map((row) => (
              <div key={`mig-${row.table}`} className="agent1-history-row">
                <div className="min-w-0">
                  <div className="agent1-small text-white/80 agent1-mono truncate">{row.table}</div>
                  <div className="text-[10px] text-white/35">
                    total: {row.total_rows} | with_id: {row.rows_with_business_id} | missing: {row.rows_missing_business_id} | duplicates: {row.duplicate_business_id_groups}
                  </div>
                </div>
              </div>
            ))}
            {(migrationStatus?.tables || []).length === 0 ? (
              <div className="agent1-muted">No migration table data available.</div>
            ) : null}
          </div>
        </>
      ) : (
        <div className="agent1-muted">Migration status not loaded yet.</div>
      )}

      <div className="agent1-section-title">Current vs Previous Revisions (Phase 4)</div>
      <div className="agent1-history">
        {revisionState?.active_revision ? (
          <div className="agent1-history-row">
            <div className="min-w-0">
              <div className="agent1-small text-emerald-300/90 agent1-mono truncate">
                Active v{revisionState.active_revision.artifact_version}
              </div>
              <div className="text-[10px] text-white/35">{formatDate(revisionState.active_revision.created_at)}</div>
            </div>
          </div>
        ) : (
          <div className="agent1-muted">No active revision found yet.</div>
        )}

        {(revisionState?.history || [])
          .filter((row) => !row.is_active)
          .slice(0, 5)
          .map((row) => (
            <div key={`rev-${row.id}`} className="agent1-history-row">
              <div className="min-w-0">
                <div className="agent1-small text-white/75 agent1-mono truncate">Previous v{row.artifact_version}</div>
                <div className="text-[10px] text-white/35">{formatDate(row.created_at)}</div>
              </div>
              <button
                className="agent1-btn agent1-btn-blue"
                disabled={loading}
                onClick={() => promoteRevision({
                  runId,
                  artifactVersion: row.artifact_version,
                  actor: assignedBy,
                  reason: `Promoted from UI: version ${row.artifact_version}`,
                })}
              >
                Promote
              </button>
            </div>
          ))}
      </div>

      <div className="agent1-history">
        {(retryRequests || []).length === 0 ? <div className="agent1-muted">No retry governance requests yet.</div> : null}
        {(retryRequests || []).map((row) => (
          <div key={row.request_id} className="agent1-history-row">
            <div className="min-w-0">
              <div className="agent1-small text-white/80 agent1-mono truncate">{row.request_id}</div>
              <div className="text-[10px] text-white/35">{row.status} • {row.requested_by} • {formatDate(row.created_at)}</div>
            </div>
            <button
              className="agent1-btn agent1-btn-cyan"
              onClick={async () => {
                setSelectedRequestId(row.request_id)
                await loadRetryAudit(row.request_id)
              }}
              disabled={loading}
            >
              Audit
            </button>
          </div>
        ))}
      </div>

      {selectedRequest ? (
        <>
          <div className="agent1-section-title">Selected Request Controls</div>
          <div className="agent1-grid-two">
            <div>
              <label className="agent1-small text-white/45">Reviewer ID</label>
              <input
                className="agent1-input"
                value={reviewerId}
                onChange={(e) => setReviewerId(e.target.value)}
              />
            </div>
            <div>
              <label className="agent1-small text-white/45">Assigned By</label>
              <input
                className="agent1-input"
                value={assignedBy}
                onChange={(e) => setAssignedBy(e.target.value)}
              />
            </div>
          </div>
          <div>
            <label className="agent1-small text-white/45">Comment / Reason</label>
            <textarea
              className="agent1-review-textarea"
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>

          <div className="agent1-actions">
            <button
              className="agent1-btn agent1-btn-blue"
              disabled={loading}
              onClick={() => assignRetryReviewer({
                requestId: selectedRequest.request_id,
                reviewerId,
                assignedBy,
                reason: comment,
              })}
            >
              Assign Reviewer
            </button>
            <button
              className="agent1-btn agent1-btn-violet"
              disabled={loading}
              onClick={() => autoAssignRetryReviewer({
                requestId: selectedRequest.request_id,
                assignedBy,
              })}
            >
              Auto Assign
            </button>
            <button
              className="agent1-btn agent1-btn-teal"
              disabled={loading}
              onClick={() => reviewRetryRequest({
                requestId: selectedRequest.request_id,
                reviewerId,
                decision: 'approve',
                comment,
              })}
            >
              Approve
            </button>
            <button
              className="agent1-btn agent1-btn-red"
              disabled={loading}
              onClick={() => reviewRetryRequest({
                requestId: selectedRequest.request_id,
                reviewerId,
                decision: 'reject',
                comment,
              })}
            >
              Reject
            </button>
            <button
              className="agent1-btn agent1-btn-yellow"
              disabled={loading}
              onClick={() => approveAndRunRetry({
                requestId: selectedRequest.request_id,
                reviewerId,
                comment,
              })}
            >
              Approve and Run
            </button>
          </div>

          <div className="agent1-section-title">Audit Trail</div>
          <pre className="agent1-live-textarea">{retryAuditEvents.length ? JSON.stringify(retryAuditEvents, null, 2) : 'No audit events loaded yet.'}</pre>
        </>
      ) : null}
    </div>
  )
}
