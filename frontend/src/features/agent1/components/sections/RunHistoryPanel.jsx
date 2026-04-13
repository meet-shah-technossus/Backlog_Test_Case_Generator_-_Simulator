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

export default function RunHistoryPanel({ runHistory, loading, resumeRun }) {
  const approvedRuns = runHistory.filter(
    (r) => r.state === 'review_approved' || r.state === 'handoff_pending' || r.state === 'handoff_emitted'
  )

  return (
    <div className="agent1-card">
      <div className="agent1-section-title">Approved / Handoff Runs</div>
      <div className="agent1-history">
        {approvedRuns.length === 0 && <div className="agent1-muted">No approved runs yet</div>}
        {approvedRuns.map((r) => (
          <div key={`approved-${r.run_id}`} className="agent1-history-row">
            <div className="min-w-0">
              <div className="agent1-small text-white/80 agent1-mono truncate">{r.run_id}</div>
              <div className="text-[10px] text-emerald-300/80">{r.state} • {formatDate(r.updated_at)}</div>
            </div>
            <button
              onClick={() => resumeRun(r.run_id)}
              disabled={loading}
              className="agent1-btn agent1-btn-teal"
            >
              Open
            </button>
          </div>
        ))}
      </div>

      <div className="agent1-section-title">Run History</div>
      <div className="agent1-history">
        {runHistory.length === 0 && <div className="agent1-muted">No runs saved yet</div>}
        {runHistory.map((r) => (
          <div key={r.run_id} className="agent1-history-row">
            <div className="min-w-0">
              <div className="agent1-small text-white/70 agent1-mono truncate">{r.run_id}</div>
              <div className="text-[10px] text-white/35">{r.state} • {formatDate(r.updated_at)}</div>
            </div>
            <button
              onClick={() => resumeRun(r.run_id)}
              disabled={loading}
              className="agent1-btn agent1-btn-neutral"
            >
              Resume
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
