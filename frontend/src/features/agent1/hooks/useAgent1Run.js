import { useCallback, useState } from 'react'
import { useSSE } from './useSSE.js'
import {
  createAgent1Run,
  emitAgent1Handoff,
  getAgent1Run,
  listAgent1RunsForStory,
  retryAgent1Run,
  submitAgent1Review,
} from '../api/agent1Api'
import {
  approveAndRunRetryGovernanceRequest,
  getBusinessIdMigrationStatus,
  repairBusinessIdMigrationLinks,
  getRetryRevisions,
  assignRetryGovernanceReviewer,
  autoAssignRetryGovernanceReviewer,
  listRetryGovernanceAuditEvents,
  listRetryGovernanceRequests,
  promoteRetryRevision,
  reviewRetryGovernanceRequest,
} from '../../retryGovernance/api/retryGovernanceApi'

export function useAgent1Run({ storyId, onSuiteReady }) {
  const { start: startSSE, abort: abortSSE, streaming } = useSSE()
  const [runId, setRunId] = useState(null)
  const [snapshot, setSnapshot] = useState(null)
  const [runHistory, setRunHistory] = useState([])
  const [tokenBuffer, setTokenBuffer] = useState('')
  const [retryRequests, setRetryRequests] = useState([])
  const [retryAuditEvents, setRetryAuditEvents] = useState([])
  const [revisionState, setRevisionState] = useState({ active_revision: null, history: [] })
  const [migrationStatus, setMigrationStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const loadRetryGovernance = useCallback(async (id = runId) => {
    if (!id) {
      setRetryRequests([])
      return []
    }
    try {
      const data = await listRetryGovernanceRequests('agent1', id, 20)
      const rows = Array.isArray(data?.requests) ? data.requests : []
      setRetryRequests(rows)
      return rows
    } catch (e) {
      setError(e.message || 'Failed to load retry governance requests')
      return []
    }
  }, [runId])

  const loadRetryAudit = useCallback(async (requestId) => {
    if (!requestId) {
      setRetryAuditEvents([])
      return []
    }
    try {
      const data = await listRetryGovernanceAuditEvents(requestId)
      const rows = Array.isArray(data?.events) ? data.events : []
      setRetryAuditEvents(rows)
      return rows
    } catch (e) {
      setError(e.message || 'Failed to load retry governance audit events')
      return []
    }
  }, [])

  const loadRevisions = useCallback(async (id = runId, includeHistory = true) => {
    if (!id) {
      setRevisionState({ active_revision: null, history: [] })
      return { active_revision: null, history: [] }
    }
    try {
      const data = await getRetryRevisions('agent1', id, includeHistory)
      const active = data?.active_revision || null
      const history = Array.isArray(data?.history) ? data.history : []
      const next = { active_revision: active, history }
      setRevisionState(next)
      return next
    } catch {
      const next = { active_revision: null, history: [] }
      setRevisionState(next)
      return next
    }
  }, [runId])

  const loadMigrationStatus = useCallback(async () => {
    try {
      const data = await getBusinessIdMigrationStatus()
      setMigrationStatus(data || null)
      return data || null
    } catch (e) {
      setError(e.message || 'Failed to load business ID migration status')
      return null
    }
  }, [])

  const repairMigrationLinks = useCallback(async (actor = 'operator') => {
    setLoading(true)
    setError(null)
    try {
      const data = await repairBusinessIdMigrationLinks({ actor })
      await loadMigrationStatus()
      return data
    } catch (e) {
      setError(e.message || 'Failed to repair migration links')
      throw e
    } finally {
      setLoading(false)
    }
  }, [loadMigrationStatus])

  const loadHistory = useCallback(async () => {
    if (!storyId) {
      setRunHistory([])
      return []
    }
    try {
      const data = await listAgent1RunsForStory(storyId)
      const runs = data?.runs || []
      setRunHistory(runs)
      return runs
    } catch (e) {
      setError(e.message || 'Failed to load run history')
      return []
    }
  }, [storyId])

  const createRun = useCallback(async () => {
    if (!storyId) return
    setLoading(true)
    setError(null)
    try {
      const data = await createAgent1Run(storyId)
      setRunId(data?.run?.run_id || null)
      setSnapshot(data)
      await loadHistory()
      await loadRetryGovernance(data?.run?.run_id || null)
      await loadRevisions(data?.run?.run_id || null, true)
      await loadMigrationStatus()
      return data
    } catch (e) {
      setError(e.message || 'Failed to create run')
      throw e
    } finally {
      setLoading(false)
    }
  }, [storyId, loadRetryGovernance, loadHistory, loadRevisions, loadMigrationStatus])

  const refresh = useCallback(async (id = runId) => {
    if (!id) return null
    setLoading(true)
    setError(null)
    try {
      const data = await getAgent1Run(id)
      setSnapshot(data)
      await loadHistory()
      await loadRetryGovernance(id)
      await loadRevisions(id, true)
      await loadMigrationStatus()
      return data
    } catch (e) {
      setError(e.message || 'Failed to refresh run')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, loadHistory, loadRetryGovernance, loadRevisions, loadMigrationStatus])

  const generate = useCallback(async () => {
    if (!runId) return
    setLoading(true)
    setError(null)
    setTokenBuffer('')
    try {
      await startSSE(
        `/agent1/runs/${runId}/generate/stream`,
        {
          method: 'POST',
          body: JSON.stringify({ model: null }),
        },
        (event) => {
          if (event?.type === 'token') {
            setTokenBuffer((prev) => {
              const merged = prev + (event.token || '')
              return merged.length > 4000 ? merged.slice(-4000) : merged
            })
            return
          }
          if (event?.type === 'done') {
            setSnapshot(event.snapshot || null)
            onSuiteReady?.()
          }
          if (event?.type === 'error') {
            setError(event.error || 'Generation failed')
          }
        },
        async () => {
          await loadHistory()
        },
        (msg) => {
          setError(msg || 'Generation failed')
        }
      )
      return snapshot
    } catch (e) {
      setError(e.message || 'Generation failed')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, onSuiteReady, loadHistory, startSSE, snapshot])

  const review = useCallback(async (decision, reasonCode = null, editedPayload = null) => {
    if (!runId) return
    setLoading(true)
    setError(null)
    try {
      const data = await submitAgent1Review(runId, {
        decision,
        reviewer_id: 'human_reviewer',
        reason_code: reasonCode,
        edited_payload: editedPayload,
      })
      setSnapshot(data)
      await loadHistory()
      return data
    } catch (e) {
      setError(e.message || 'Review submission failed')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, loadHistory])

  const retry = useCallback(async (reasonCode = 'manual_retry') => {
    if (!runId) return
    setLoading(true)
    setError(null)
    try {
      const data = await retryAgent1Run(runId, reasonCode, 'human_reviewer')
      setSnapshot(data)
      await loadHistory()
      await loadRetryGovernance(runId)
      await loadRevisions(runId, true)
      return data
    } catch (e) {
      setError(e.message || 'Retry failed')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, loadHistory, loadRetryGovernance, loadRevisions])

  const assignRetryReviewer = useCallback(async ({ requestId, reviewerId, assignedBy, reason }) => {
    if (!requestId) return null
    setLoading(true)
    setError(null)
    try {
      const data = await assignRetryGovernanceReviewer(requestId, {
        reviewer_id: reviewerId,
        assigned_by: assignedBy || 'operator',
        reason: reason || null,
      })
      await loadRetryGovernance(runId)
      await loadRetryAudit(requestId)
      return data
    } catch (e) {
      setError(e.message || 'Failed to assign reviewer')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, loadRetryGovernance, loadRetryAudit])

  const autoAssignRetryReviewer = useCallback(async ({ requestId, assignedBy }) => {
    if (!requestId) return null
    setLoading(true)
    setError(null)
    try {
      const data = await autoAssignRetryGovernanceReviewer(requestId, {
        assigned_by: assignedBy || 'operator',
      })
      await loadRetryGovernance(runId)
      await loadRetryAudit(requestId)
      return data
    } catch (e) {
      setError(e.message || 'Failed to auto-assign reviewer')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, loadRetryGovernance, loadRetryAudit])

  const reviewRetryRequest = useCallback(async ({ requestId, reviewerId, decision, comment }) => {
    if (!requestId) return null
    setLoading(true)
    setError(null)
    try {
      const data = await reviewRetryGovernanceRequest(requestId, {
        reviewer_id: reviewerId,
        decision,
        comment: comment || null,
      })
      await loadRetryGovernance(runId)
      await loadRetryAudit(requestId)
      return data
    } catch (e) {
      setError(e.message || 'Failed to review retry request')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, loadRetryGovernance, loadRetryAudit])

  const approveAndRunRetry = useCallback(async ({ requestId, reviewerId, comment }) => {
    if (!requestId) return null
    setLoading(true)
    setError(null)
    try {
      const data = await approveAndRunRetryGovernanceRequest(requestId, {
        reviewer_id: reviewerId,
        comment: comment || null,
      })
      await refresh(runId)
      await loadRetryAudit(requestId)
      await loadRevisions(runId, true)
      return data
    } catch (e) {
      setError(e.message || 'Failed to approve and run retry request')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, refresh, loadRetryAudit, loadRevisions])

  const promoteRevision = useCallback(async ({ runId: targetRunId, artifactVersion, actor, reason }) => {
    const effectiveRunId = targetRunId || runId
    if (!effectiveRunId || !artifactVersion) return null
    setLoading(true)
    setError(null)
    try {
      const data = await promoteRetryRevision('agent1', effectiveRunId, {
        artifact_version: Number(artifactVersion),
        actor: actor || 'operator',
        reason: reason || null,
      })
      await refresh(effectiveRunId)
      await loadRevisions(effectiveRunId, true)
      return data
    } catch (e) {
      setError(e.message || 'Failed to promote revision')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, refresh, loadRevisions])

  const handoff = useCallback(async () => {
    if (!runId) return
    setLoading(true)
    setError(null)
    try {
      const data = await emitAgent1Handoff(runId)
      setSnapshot(data)
      await loadHistory()
      return data
    } catch (e) {
      setError(e.message || 'Handoff failed')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId, loadHistory])

  const resumeRun = useCallback(async (id) => {
    if (!id) return null
    setRunId(id)
    return refresh(id)
  }, [refresh])

  return {
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
    abortSSE,
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
  }
}
