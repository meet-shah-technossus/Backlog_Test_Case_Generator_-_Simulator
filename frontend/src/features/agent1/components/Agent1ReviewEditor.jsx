import { useEffect, useState } from 'react'

export default function Agent1ReviewEditor({ latestArtifact, loading, locked = false, onEditApprove }) {
  const [draftJson, setDraftJson] = useState('')
  const [localError, setLocalError] = useState(null)

  useEffect(() => {
    const cases = latestArtifact?.test_cases || []
    setDraftJson(JSON.stringify({ test_cases: cases }, null, 2))
    setLocalError(null)
  }, [latestArtifact])

  const submitEditApprove = async () => {
    setLocalError(null)
    let parsed
    try {
      parsed = JSON.parse(draftJson)
    } catch (e) {
      setLocalError(`Invalid JSON: ${e.message}`)
      return
    }

    if (!Array.isArray(parsed.test_cases)) {
      setLocalError('edited payload must include test_cases as an array')
      return
    }

    try {
      await onEditApprove(parsed)
    } catch (e) {
      setLocalError(e.message || 'Failed to submit edited artifact')
    }
  }

  return (
    <div className="agent1-card">
      <div className="agent1-section-title">Human Edit + Approve</div>
      <textarea
        value={draftJson}
        onChange={(e) => setDraftJson(e.target.value)}
        className="agent1-review-textarea"
        readOnly={locked}
        placeholder={`{\n  "test_cases": []\n}`}
      />

      {locked && (
        <div className="agent1-muted">
          Manual edits are disabled after handoff emission for this run.
        </div>
      )}

      {localError && (
        <div className="agent1-error">
          {localError}
        </div>
      )}

      <div className="agent1-review-actions">
        <button
          onClick={submitEditApprove}
          disabled={loading || locked}
          className="agent1-btn agent1-btn-teal"
        >
          Submit Edit + Approve
        </button>
      </div>
    </div>
  )
}
