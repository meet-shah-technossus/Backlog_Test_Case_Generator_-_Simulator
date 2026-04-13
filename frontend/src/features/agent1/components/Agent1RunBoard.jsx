import { Loader2, RefreshCw, Send } from 'lucide-react'
import { useEffect, useMemo } from 'react'
import { useAgent1Run } from '../hooks/useAgent1Run'
import Agent1ReviewEditor from './Agent1ReviewEditor'
import './agent1.css'
import ArtifactPanel from './sections/ArtifactPanel'
import CriteriaPanel from './sections/CriteriaPanel'
import ReviewDiffPanel from './sections/ReviewDiffPanel'
import RetryGovernancePanel from './sections/RetryGovernancePanel'
import RunHistoryPanel from './sections/RunHistoryPanel'
import StageBadge from './sections/StageBadge'
import TimelinePanel from './sections/TimelinePanel'

export default function Agent1RunBoard({ story, onSuiteReady }) {
  const {
    runId,
    snapshot,
    runHistory,
    retryRequests,
    retryAuditEvents,
    revisionState,
    migrationStatus,
    tokenBuffer,
    streaming,
    loading,
    error,
    loadHistory,
    loadRetryGovernance,
    loadRetryAudit,
    loadRevisions,
    loadMigrationStatus,
    repairMigrationLinks,
    resumeRun,
    createRun,
    refresh,
    generate,
    review,
    retry,
    assignRetryReviewer,
    autoAssignRetryReviewer,
    reviewRetryRequest,
    approveAndRunRetry,
    promoteRevision,
    handoff,
  } = useAgent1Run({ storyId: story?.id, onSuiteReady })

  const latestArtifact = snapshot?.latest_artifact?.artifact
  const runState = snapshot?.run?.state
  const timeline = snapshot?.timeline || []
  const reviewDiff = snapshot?.review_diff
  const isLockedAfterHandoff = runState === 'handoff_emitted'

  const caseCount = useMemo(() => {
    return latestArtifact?.test_cases?.length || 0
  }, [latestArtifact])

  const approveAndEmit = async () => {
    await review('approve')
    await handoff()
  }

  const editApproveAndEmit = async (payload) => {
    await review('edit_approve', 'manual_edit_approve', payload)
    await handoff()
  }

  useEffect(() => {
    loadHistory()
    loadMigrationStatus()
  }, [loadHistory, loadMigrationStatus])

  useEffect(() => {
    const id = window.setInterval(() => {
      loadHistory().catch(() => {})
    }, 5000)
    return () => window.clearInterval(id)
  }, [loadHistory])

  return (
    <div className="agent1-board">
      <div className="agent1-card">
        <div className="agent1-header">
          <div>
            <div className="agent1-title">Agent 1 - Test Case Generation</div>
            <div className="agent1-subtitle">Story: {story?.title || 'Select a story'}</div>
          </div>
          <StageBadge state={runState} />
        </div>

        <div className="agent1-actions">
          <button
            onClick={createRun}
            disabled={!story || loading || streaming}
            className="agent1-btn agent1-btn-blue"
          >
            {loading ? <Loader2 size={12} className="inline animate-spin mr-1" /> : null}
            Create Run
          </button>
          <button
            onClick={generate}
            disabled={!runId || loading || streaming}
            className="agent1-btn agent1-btn-violet"
          >
            {streaming ? 'Generating...' : 'Generate'}
          </button>
          <button
            onClick={approveAndEmit}
            disabled={!runId || loading || streaming || isLockedAfterHandoff}
            className="agent1-btn agent1-btn-teal"
          >
            Approve + Emit
          </button>
          <button
            onClick={() => review('reject', 'manual_reject')}
            disabled={!runId || loading || streaming || isLockedAfterHandoff}
            className="agent1-btn agent1-btn-red"
          >
            Reject
          </button>
          <button
            onClick={() => retry('manual_retry')}
            disabled={!runId || loading || streaming || isLockedAfterHandoff}
            className="agent1-btn agent1-btn-yellow"
          >
            Retry
          </button>
          <button
            onClick={handoff}
            disabled={!runId || loading || streaming || isLockedAfterHandoff}
            className="agent1-btn agent1-btn-cyan"
          >
            <Send size={11} className="inline mr-1" />
            Handoff to Agent 2
          </button>
          <button
            onClick={() => refresh()}
            disabled={!runId || loading || streaming}
            className="agent1-btn agent1-btn-neutral"
          >
            <RefreshCw size={11} className="inline mr-1" />
            Refresh
          </button>
        </div>

        {error && (
          <div className="agent1-error">
            {error}
          </div>
        )}

        {(streaming || tokenBuffer) && (
          <div className="agent1-live-wrap">
            <div className="agent1-live-head">
              <span className="agent1-section-title agent1-section-title-tight">Live generation</span>
              <span className={`agent1-live-dot ${streaming ? 'agent1-live-dot-active' : ''}`} />
            </div>
            <div className="agent1-live-textarea">
              {tokenBuffer || 'Waiting for first token...'}
            </div>
          </div>
        )}

        {isLockedAfterHandoff && (
          <div className="agent1-muted">
            This run is locked after handoff emission. Create a new run to make further changes.
          </div>
        )}
      </div>

      <CriteriaPanel story={story} latestArtifact={latestArtifact} />

      <ArtifactPanel latestArtifact={latestArtifact} caseCount={caseCount} />

      <Agent1ReviewEditor
        latestArtifact={latestArtifact}
        locked={isLockedAfterHandoff}
        loading={loading}
        onEditApprove={editApproveAndEmit}
      />

      <ReviewDiffPanel reviewDiff={reviewDiff} />

      <RetryGovernancePanel
        runId={runId}
        retryRequests={retryRequests}
        retryAuditEvents={retryAuditEvents}
        revisionState={revisionState}
        migrationStatus={migrationStatus}
        loading={loading}
        loadRetryGovernance={loadRetryGovernance}
        loadRetryAudit={loadRetryAudit}
        loadRevisions={loadRevisions}
        loadMigrationStatus={loadMigrationStatus}
        repairMigrationLinks={repairMigrationLinks}
        assignRetryReviewer={assignRetryReviewer}
        autoAssignRetryReviewer={autoAssignRetryReviewer}
        reviewRetryRequest={reviewRetryRequest}
        approveAndRunRetry={approveAndRunRetry}
        promoteRevision={promoteRevision}
      />

      <TimelinePanel timeline={timeline} />

      <RunHistoryPanel runHistory={runHistory} loading={loading} resumeRun={resumeRun} />
    </div>
  )
}
