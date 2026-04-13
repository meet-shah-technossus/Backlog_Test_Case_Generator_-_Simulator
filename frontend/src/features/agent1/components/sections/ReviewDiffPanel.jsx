export default function ReviewDiffPanel({ reviewDiff }) {
  return (
    <div className="agent1-card">
      <div className="agent1-section-title">Review Diff</div>
      {!reviewDiff?.available ? (
        <div className="agent1-muted">{reviewDiff?.message || 'Diff not available yet'}</div>
      ) : (
        <div className="space-y-2">
          <div className="agent1-small text-white/55">
            v{reviewDiff.base_version} {'->'} v{reviewDiff.target_version}
          </div>
          <div className="agent1-diff-grid">
            <div className="agent1-pill agent1-pill-added">Added: {reviewDiff.counts?.added || 0}</div>
            <div className="agent1-pill agent1-pill-changed">Changed: {reviewDiff.counts?.changed || 0}</div>
            <div className="agent1-pill agent1-pill-removed">Removed: {reviewDiff.counts?.removed || 0}</div>
          </div>
        </div>
      )}
    </div>
  )
}
