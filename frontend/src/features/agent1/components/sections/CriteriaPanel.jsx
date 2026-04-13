function normalizeCriterionText(criterion) {
  if (typeof criterion === 'string') return criterion
  if (criterion && typeof criterion.text === 'string') return criterion.text
  return ''
}

function normalizeCaseType(value) {
  const raw = String(value || '').trim().toLowerCase()
  if (raw === 'functional') return 'positive'
  if (raw === 'positive' || raw === 'negative' || raw === 'edge') return raw
  return 'positive'
}

export default function CriteriaPanel({ story, latestArtifact }) {
  const criteria = story?.acceptance_criteria || []
  const generated = latestArtifact?.test_cases || []

  const byCriterion = generated.reduce((acc, tc) => {
    const key = tc?.criterion_id || 'unknown'
    if (!acc[key]) {
      acc[key] = { total: 0, positive: 0, negative: 0, edge: 0 }
    }
    const kind = normalizeCaseType(tc?.test_type)
    acc[key].total += 1
    if (kind === 'positive') acc[key].positive += 1
    if (kind === 'negative') acc[key].negative += 1
    if (kind === 'edge') acc[key].edge += 1
    return acc
  }, {})

  return (
    <div className="agent1-card">
      <div className="agent1-section-title">Acceptance Criteria Coverage</div>
      {criteria.length === 0 ? (
        <div className="agent1-muted">No acceptance criteria available for this story.</div>
      ) : (
        <div className="agent1-criteria-list">
          {criteria.map((criterion, idx) => {
            const criterionId = `${story.id}_ac_${idx + 1}`
            const coverage = byCriterion[criterionId] || { total: 0, positive: 0, negative: 0, edge: 0 }
            return (
              <div className="agent1-criteria-item" key={criterionId}>
                <div className="agent1-criteria-header">
                  <span className="agent1-criteria-index">AC {idx + 1}</span>
                  <span className="agent1-criteria-count">{coverage.total} cases</span>
                </div>
                <div className="agent1-criteria-text">{normalizeCriterionText(criterion)}</div>
                <div className="agent1-criteria-pills">
                  <span className="agent1-pill agent1-pill-positive">Positive: {coverage.positive}</span>
                  <span className="agent1-pill agent1-pill-removed">Negative: {coverage.negative}</span>
                  <span className="agent1-pill agent1-pill-changed">Edge: {coverage.edge}</span>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
