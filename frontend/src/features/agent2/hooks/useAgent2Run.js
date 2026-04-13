import { useCallback, useState } from 'react'
import {
  consumeAgent1HandoffForAgent2,
  createAgent2RunFromInbox,
  emitAgent2Handoff,
  generateAgent2Run,
  getAgent2GenerateStreamUrl,
  getAgent2Blueprint,
  getAgent2ObservabilityCounters,
  getAgent2ReviewReasonCodes,
  getAgent2Run,
  getAgent2Timeline,
  listApprovedAgent1Runs,
  listAgent2RunsByBacklog,
  startAgent2FromAgent1Run,
  reviewAgent2Run,
} from '../api/agent2Api'
import { useSSE } from '../../agent1/hooks/useSSE'

function parseDateValue(value) {
  if (!value) return 0
  const normalized = typeof value === 'string' ? value.replace(' ', 'T') : value
  const ts = new Date(normalized).getTime()
  return Number.isFinite(ts) ? ts : 0
}

export function useAgent2Run() {
  const { start: startSSE, abort: abortSSE, streaming } = useSSE()
  const [blueprint, setBlueprint] = useState(null)
  const [runId, setRunId] = useState(null)
  const [runSnapshot, setRunSnapshot] = useState(null)
  const [reasonCodes, setReasonCodes] = useState({})
  const [dashboard, setDashboard] = useState({
    counters: {
      total_runs: 0,
      success_count: 0,
      retry_count: 0,
      rejection_count: 0,
      failure_count: 0,
    },
    recentRuns: [],
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [approvedAgent1Runs, setApprovedAgent1Runs] = useState([])
  const [tokenBuffer, setTokenBuffer] = useState('')

  const readLocalHistory = useCallback(() => {
    try {
      const raw = window.localStorage.getItem('agent2RunsByStory')
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  }, [])

  const writeLocalHistory = useCallback((value) => {
    try {
      window.localStorage.setItem('agent2RunsByStory', JSON.stringify(value))
    } catch {
      // Ignore localStorage failures.
    }
  }, [])

  const appendRunHistory = useCallback((storyId, nextRunId) => {
    if (!storyId || !nextRunId) return
    const history = readLocalHistory()
    const current = Array.isArray(history[storyId]) ? history[storyId] : []
    if (!current.includes(nextRunId)) {
      history[storyId] = [nextRunId, ...current].slice(0, 20)
      writeLocalHistory(history)
    }
  }, [readLocalHistory, writeLocalHistory])

  const getStoryHistory = useCallback((storyId) => {
    if (!storyId) return []
    const history = readLocalHistory()
    return Array.isArray(history[storyId]) ? history[storyId] : []
  }, [readLocalHistory])

  const loadBlueprint = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getAgent2Blueprint()
      setBlueprint(data)
      return data
    } catch (e) {
      setError(e.message || 'Failed to load Agent2 blueprint')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const loadReasonCodes = useCallback(async () => {
    try {
      const data = await getAgent2ReviewReasonCodes()
      setReasonCodes(data?.codes || {})
      return data?.codes || {}
    } catch (e) {
      setError(e.message || 'Failed to load Agent2 reason codes')
      throw e
    }
  }, [])

  const consumeHandoff = useCallback(async (payload) => {
    setLoading(true)
    setError(null)
    try {
      return await consumeAgent1HandoffForAgent2(payload)
    } catch (e) {
      setError(e.message || 'Failed to consume handoff')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const createRunFromInbox = useCallback(async (messageId, storyId = null) => {
    setLoading(true)
    setError(null)
    try {
      const data = await createAgent2RunFromInbox(messageId)
      const nextRunId = data?.run?.run_id
      if (nextRunId) {
        setRunId(nextRunId)
        appendRunHistory(storyId, nextRunId)
        const snap = await getAgent2Run(nextRunId)
        setRunSnapshot(snap)
      }
      return data
    } catch (e) {
      setError(e.message || 'Failed to create Agent2 run from inbox')
      throw e
    } finally {
      setLoading(false)
    }
  }, [appendRunHistory])

  const refreshRun = useCallback(async (id = runId) => {
    if (!id) return null
    setLoading(true)
    setError(null)
    try {
      const data = await getAgent2Run(id)
      const timelineResp = await getAgent2Timeline(id, 'asc')
      data.timeline = timelineResp?.events || data.timeline || []
      setRunId(id)
      setRunSnapshot(data)
      return data
    } catch (e) {
      setError(e.message || 'Failed to load Agent2 run')
      throw e
    } finally {
      setLoading(false)
    }
  }, [runId])

  const loadRun = useCallback(async (id) => {
    return refreshRun(id)
  }, [refreshRun])

  const loadApprovedRuns = useCallback(async (backlogItemId, limit = 50) => {
    if (!backlogItemId) {
      setApprovedAgent1Runs([])
      return []
    }
    setLoading(true)
    setError(null)
    try {
      const data = await listApprovedAgent1Runs(backlogItemId, limit)
      const runs = Array.isArray(data?.runs) ? data.runs : []
      const sorted = [...runs].sort((a, b) => {
        const left = parseDateValue(a?.updated_at)
        const right = parseDateValue(b?.updated_at)
        return right - left
      })
      setApprovedAgent1Runs(sorted)
      return sorted
    } catch (e) {
      setError(e.message || 'Failed to load approved Agent1 runs')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const startFromAgent1Run = useCallback(async (agent1RunId) => {
    if (!agent1RunId) return null
    setLoading(true)
    setError(null)
    try {
      const data = await startAgent2FromAgent1Run(agent1RunId)
      const nextRunId = data?.snapshot?.run?.run_id || data?.create?.run?.run_id
      if (nextRunId) {
        setRunId(nextRunId)
        const snap = await getAgent2Run(nextRunId)
        const timelineResp = await getAgent2Timeline(nextRunId, 'asc')
        snap.timeline = timelineResp?.events || snap.timeline || []
        setRunSnapshot(snap)
      }
      return data
    } catch (e) {
      setError(e.message || 'Failed to start Agent2 from Agent1 run')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const loadDashboard = useCallback(async (backlogItemId) => {
    if (!backlogItemId) {
      setDashboard({
        counters: {
          total_runs: 0,
          success_count: 0,
          retry_count: 0,
          rejection_count: 0,
          failure_count: 0,
        },
        recentRuns: [],
      })
      return null
    }

    setLoading(true)
    setError(null)
    try {
      const [runsResp, countersResp] = await Promise.all([
        listAgent2RunsByBacklog(backlogItemId, 20),
        getAgent2ObservabilityCounters(backlogItemId),
      ])
      const nextDashboard = {
        counters: countersResp?.counters || {},
        recentRuns: runsResp?.runs || [],
      }
      setDashboard(nextDashboard)
      return nextDashboard
    } catch (e) {
      setError(e.message || 'Failed to load Agent2 dashboard')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const generateRun = useCallback(async (runId, payload = {}) => {
    setLoading(true)
    setError(null)
    try {
      const data = await generateAgent2Run(runId, payload)
      setRunId(runId)
      setRunSnapshot(data)
      return data
    } catch (e) {
      setError(e.message || 'Failed to generate Agent2 test steps')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const generateRunStream = useCallback(async (runId, payload = {}) => {
    if (!runId) return null
    setLoading(true)
    setError(null)
    setTokenBuffer('')
    let latestSnapshot = null
    try {
      await startSSE(
        getAgent2GenerateStreamUrl(runId),
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
        (event) => {
          if (event?.type === 'token') {
            setTokenBuffer((prev) => {
              const merged = prev + (event.token || '')
              return merged.length > 6000 ? merged.slice(-6000) : merged
            })
            return
          }
          if (event?.type === 'done') {
            const snap = event.snapshot || null
            latestSnapshot = snap
            setRunId(runId)
            setRunSnapshot(snap)
            return
          }
          if (event?.type === 'error') {
            setError(event.error || 'Agent2 generation failed')
          }
        },
        async () => {
          const refreshed = await refreshRun(runId)
          latestSnapshot = refreshed || latestSnapshot
        },
        (msg) => {
          setError(msg || 'Agent2 generation failed')
        }
      )
      return latestSnapshot
    } catch (e) {
      setError(e.message || 'Agent2 generation failed')
      throw e
    } finally {
      setLoading(false)
    }
  }, [refreshRun, startSSE])

  const reviewRun = useCallback(async (runId, payload) => {
    setLoading(true)
    setError(null)
    try {
      const data = await reviewAgent2Run(runId, payload)
      setRunId(runId)
      setRunSnapshot(data)
      return data
    } catch (e) {
      setError(e.message || 'Failed to submit Agent2 review')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const handoffRun = useCallback(async (runId) => {
    setLoading(true)
    setError(null)
    try {
      const data = await emitAgent2Handoff(runId)
      const snap = data?.snapshot
      setRunId(runId)
      if (snap) {
        setRunSnapshot(snap)
      }
      return data
    } catch (e) {
      setError(e.message || 'Failed to emit Agent2 handoff')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  return {
    blueprint,
    runId,
    runSnapshot,
    reasonCodes,
    loading,
    error,
    loadBlueprint,
    loadReasonCodes,
    consumeHandoff,
    createRunFromInbox,
    refreshRun,
    loadRun,
    loadDashboard,
    loadApprovedRuns,
    startFromAgent1Run,
    getStoryHistory,
    generateRun,
    reviewRun,
    handoffRun,
    dashboard,
    approvedAgent1Runs,
    tokenBuffer,
    streaming,
    abortSSE,
    generateRunStream,
  }
}
