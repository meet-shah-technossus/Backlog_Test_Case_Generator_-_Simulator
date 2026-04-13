export default function ArtifactPanel({ latestArtifact, caseCount }) {
  const cases = latestArtifact?.test_cases || []
  const typeCounts = cases.reduce((acc, tc) => {
    const key = (tc?.test_type || 'unknown').toString().toLowerCase()
    acc[key] = (acc[key] || 0) + 1
    return acc
  }, {})

  return (
    <div className="agent1-card">
      <div className="agent1-section-title">Latest Artifact</div>
      <div className="agent1-result-metrics">
        <div className="agent1-result-metric">
          <span className="agent1-result-metric-label">Cases</span>
          <span className="agent1-result-metric-value">{caseCount || 0}</span>
        </div>
        <div className="agent1-result-metric">
          <span className="agent1-result-metric-label">Smoke</span>
          <span className="agent1-result-metric-value">{typeCounts.smoke || 0}</span>
        </div>
        <div className="agent1-result-metric">
          <span className="agent1-result-metric-label">Regression</span>
          <span className="agent1-result-metric-value">{typeCounts.regression || 0}</span>
        </div>
      </div>
      {!latestArtifact ? (
        <div className="agent1-muted">No artifact yet</div>
      ) : (
        <div className="agent1-case-list">
          {cases.map((tc) => (
            <div key={tc.id} className="agent1-case-item">
              <div className="agent1-case-header">
                <div className="agent1-case-title">{tc.id}</div>
                <div className="agent1-case-step-count">{tc.test_type || 'n/a'}</div>
              </div>
              <div className="agent1-case-text">{tc.title}</div>
              {tc.expected_result ? (
                <div className="agent1-case-expected">Expected: {tc.expected_result}</div>
              ) : null}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
