import { useCallback, useRef, useState } from 'react'
import { useSSE } from '../../agent1/hooks/useSSE'
import {
  createAgent4Phase10Execution,
  emitAgent4Phase7Handoff,
  getAgent4Phase6Readiness,
  getAgent4Phase10ExecutionRunStreamUrl,
  getAgent4Phase6ReviewReasonCodes,
  getAgent4Phase5GenerateStreamUrl,
  getAgent4Phase9Integrity,
  getAgent4Phase9Observability,
  getAgent4RunSnapshot,
  listAgent4Phase10Executions,
  listAgent3RunsByBacklog,
  listAgent4RunsByBacklog,
  planAgent4Phase4Scripts,
  submitAgent4Phase6Review,
  submitAgent4Phase3Gate,
  startAgent4FromAgent3Run,
} from '../api/agent4Api'

function parseDateValue(value) {
  if (!value) return 0
  const normalized = typeof value === 'string' ? value.replace(' ', 'T') : value
  const ts = new Date(normalized).getTime()
  return Number.isFinite(ts) ? ts : 0
}

export function useAgent4Run() {
  const { start: startSSE, abort: abortSSE, streaming } = useSSE()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [agent3Runs, setAgent3Runs] = useState([])
  const [agent4History, setAgent4History] = useState([])

  const [runId, setRunId] = useState('')
  const [runSnapshot, setRunSnapshot] = useState(null)
  const [phase6Readiness, setPhase6Readiness] = useState(null)
  const [phase6ReasonCodes, setPhase6ReasonCodes] = useState({})
  const [observability, setObservability] = useState(null)
  const [integrity, setIntegrity] = useState(null)
  const [tokenBuffer, setTokenBuffer] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [phase10Config, setPhase10Config] = useState({
    targetUrl: '',
    maxAttempts: 1,
    maxScripts: 0,
    earlyStopAfterFailures: 0,
    parallelWorkers: 1,
    startedBy: 'operator',
  })
  const [phase10Execution, setPhase10Execution] = useState(null)
  const [phase10Events, setPhase10Events] = useState([])

  const tokenQueueRef = useRef([])
  const tokenDrainTimerRef = useRef(null)
  const tokenStreamDoneRef = useRef(false)

  const stopTokenDrain = useCallback(() => {
    if (tokenDrainTimerRef.current) {
      clearInterval(tokenDrainTimerRef.current)
      tokenDrainTimerRef.current = null
    }
  }, [])

  const startTokenDrain = useCallback(() => {
    if (tokenDrainTimerRef.current) return
    tokenDrainTimerRef.current = setInterval(() => {
      const nextPiece = tokenQueueRef.current.shift()
      if (nextPiece) {
        setTokenBuffer((prev) => {
          const merged = prev + nextPiece
          return merged.length > 12000 ? merged.slice(-12000) : merged
        })
        return
      }
      if (tokenStreamDoneRef.current) {
        stopTokenDrain()
      }
    }, 24)
  }, [stopTokenDrain])

  const enqueueToken = useCallback((token) => {
    const text = String(token || '')
    if (!text) return
    for (let i = 0; i < text.length; i += 14) {
      tokenQueueRef.current.push(text.slice(i, i + 14))
    }
    startTokenDrain()
  }, [startTokenDrain])

  const readLastRunByStory = useCallback(() => {
    try {
      const raw = window.localStorage.getItem('agent4LastRunByStory')
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  }, [])

  const writeLastRunByStory = useCallback((value) => {
    try {
      window.localStorage.setItem('agent4LastRunByStory', JSON.stringify(value))
    } catch {
      // Ignore localStorage failures.
    }
  }, [])

  const rememberLastRunForStory = useCallback((storyId, nextRunId) => {
    if (!storyId || !nextRunId) return
    const map = readLastRunByStory()
    map[storyId] = nextRunId
    writeLastRunByStory(map)
  }, [readLastRunByStory, writeLastRunByStory])

  const getLastRunForStory = useCallback((storyId) => {
    if (!storyId) return ''
    const map = readLastRunByStory()
    return String(map[storyId] || '')
  }, [readLastRunByStory])

  const loadAgent3Runs = useCallback(async (backlogItemId) => {
    if (!backlogItemId) {
      setAgent3Runs([])
      return []
    }

    setLoading(true)
    setError('')
    try {
      const data = await listAgent3RunsByBacklog(backlogItemId, 50)
      const runs = Array.isArray(data?.runs) ? data.runs : []
      const handoffReady = runs.filter((run) => {
        const state = String(run?.state || '')
        return state === 'handoff_emitted' || state === 'handoff_pending'
      })
      const sorted = [...handoffReady].sort((a, b) => parseDateValue(b.updated_at) - parseDateValue(a.updated_at))
      setAgent3Runs(sorted)
      return sorted
    } catch (e) {
      setError(e?.message || 'Failed to load Agent3 runs')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const loadAgent4History = useCallback(async (backlogItemId) => {
    if (!backlogItemId) {
      setAgent4History([])
      return []
    }

    setLoading(true)
    setError('')
    try {
      const data = await listAgent4RunsByBacklog(backlogItemId, 50)
      const runs = Array.isArray(data?.runs) ? data.runs : []
      const sorted = [...runs].sort((a, b) => parseDateValue(b.updated_at) - parseDateValue(a.updated_at))
      setAgent4History(sorted)
      return sorted
    } catch (e) {
      setError(e?.message || 'Failed to load Agent4 run history')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const refreshRun = useCallback(async (nextRunId, options = {}) => {
    if (!nextRunId) return null
    const { storyId = null } = options
    const [snapshot, phase9Obs, phase9Integrity, phase10ExecList] = await Promise.all([
      getAgent4RunSnapshot(nextRunId),
      getAgent4Phase9Observability(nextRunId),
      getAgent4Phase9Integrity(nextRunId),
      listAgent4Phase10Executions(nextRunId, 50).catch(() => ({ executions: [] })),
    ])

    let readiness = null
    try {
      readiness = await getAgent4Phase6Readiness(nextRunId)
    } catch {
      readiness = null
    }

    setRunId(nextRunId)
    setRunSnapshot(snapshot)
    setPhase6Readiness(readiness)
    setObservability(phase9Obs)
    setIntegrity(phase9Integrity)
    const executions = Array.isArray(phase10ExecList?.executions) ? phase10ExecList.executions : []
    setPhase10Execution(executions[0] || null)
    rememberLastRunForStory(storyId, nextRunId)
    return snapshot
  }, [rememberLastRunForStory])

  const startFromAgent3Run = useCallback(async (agent3RunId, options = {}) => {
    if (!agent3RunId) return null
    const { storyId = null } = options
    setLoading(true)
    setError('')
    setTokenBuffer('')
    try {
      const data = await startAgent4FromAgent3Run(agent3RunId)
      const nextRunId = data?.agent4_snapshot?.run?.run_id || data?.create?.run?.run_id
      if (nextRunId) {
        await refreshRun(nextRunId, { storyId })
      }
      return data
    } catch (e) {
      setError(e?.message || 'Failed to start Agent4 from Agent3 run')
      throw e
    } finally {
      setLoading(false)
    }
  }, [refreshRun])

  const loadPhase6ReasonCodes = useCallback(async () => {
    try {
      const data = await getAgent4Phase6ReviewReasonCodes()
      const nextCodes = data?.codes || {}
      setPhase6ReasonCodes(nextCodes)
      return nextCodes
    } catch (e) {
      setError(e?.message || 'Failed to load Agent4 review reason codes')
      throw e
    }
  }, [])

  const reviewPhase6 = useCallback(async (nextRunId, payload, options = {}) => {
    if (!nextRunId) return null
    const { storyId = null } = options
    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const data = await submitAgent4Phase6Review(nextRunId, payload)
      await refreshRun(nextRunId, { storyId })
      setActionMessage(`Review submitted: ${payload?.decision || 'unknown'}`)
      return data
    } catch (e) {
      setError(e?.message || 'Failed to submit Agent4 Phase 6 review')
      throw e
    } finally {
      setLoading(false)
    }
  }, [refreshRun])

  const handoffPhase7 = useCallback(async (nextRunId, options = {}) => {
    if (!nextRunId) return null
    const { storyId = null } = options
    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const data = await emitAgent4Phase7Handoff(nextRunId)
      await refreshRun(nextRunId, { storyId })
      setActionMessage(`Handoff emitted: ${data?.message_id || 'ok'}`)
      return data
    } catch (e) {
      setError(e?.message || 'Failed to emit Agent4 handoff')
      throw e
    } finally {
      setLoading(false)
    }
  }, [refreshRun])

  const generateScriptsStream = useCallback(async (nextRunId, options = {}) => {
    if (!nextRunId) return null
    const { storyId = null } = options
    setLoading(true)
    setError('')
    setTokenBuffer('')
    tokenQueueRef.current = []
    tokenStreamDoneRef.current = false
    stopTokenDrain()
    let latestSnapshot = null
    try {
      const preSnapshot = await getAgent4RunSnapshot(nextRunId)
      const preState = String(preSnapshot?.run?.state || '')
      if (preState === 'intake_ready') {
        await submitAgent4Phase3Gate(nextRunId, {
          decision: 'approve',
          gate_mode: 'quick',
          reviewer_id: 'ui-auto',
          reason_code: 'manual_override_confirmed',
          auto_retry: true,
        })
      }
      await planAgent4Phase4Scripts(nextRunId)

      await startSSE(
        getAgent4Phase5GenerateStreamUrl(nextRunId),
        { method: 'POST' },
        (event) => {
          if (event?.type === 'token') {
            enqueueToken(event.token || '')
            return
          }
          if (event?.type === 'done') {
            tokenStreamDoneRef.current = true
            latestSnapshot = event.snapshot || null
            if (latestSnapshot) {
              setRunSnapshot(latestSnapshot)
            }
            startTokenDrain()
            return
          }
          if (event?.type === 'error') {
            tokenStreamDoneRef.current = true
            startTokenDrain()
            setError(event.error || 'Agent4 script generation failed')
          }
        },
        async () => {
          const refreshed = await refreshRun(nextRunId, { storyId })
          latestSnapshot = refreshed || latestSnapshot
        },
        (msg) => {
          setError(msg || 'Agent4 script generation failed')
        }
      )
      return latestSnapshot
    } catch (e) {
      tokenStreamDoneRef.current = true
      startTokenDrain()
      setError(e?.message || 'Agent4 script generation failed')
      throw e
    } finally {
      setLoading(false)
    }
  }, [enqueueToken, refreshRun, startSSE, startTokenDrain, stopTokenDrain])

  const runPhase10ExecutionStream = useCallback(async (nextRunId, options = {}) => {
    if (!nextRunId) return null
    const { storyId = null } = options
    setLoading(true)
    setError('')
    setActionMessage('')
    setPhase10Events([])
    try {
      const payload = {
        requested_by: 'operator',
        reason: 'ui-phase10-execution',
        max_attempts: Number(phase10Config.maxAttempts || 1),
        target_url: String(phase10Config.targetUrl || '').trim() || null,
        max_scripts: Number(phase10Config.maxScripts || 0) || null,
        early_stop_after_failures: Number(phase10Config.earlyStopAfterFailures || 0) || null,
        parallel_workers: Number(phase10Config.parallelWorkers || 0) || null,
      }

      const create = await createAgent4Phase10Execution(nextRunId, payload)
      const execution = create?.execution || null
      const executionRunId = execution?.execution_run_id
      if (!executionRunId) {
        throw new Error('Phase10 execution creation failed: missing execution_run_id')
      }

      setPhase10Execution(execution)
      setActionMessage(`Phase10 execution created: ${executionRunId}`)

      await startSSE(
        getAgent4Phase10ExecutionRunStreamUrl(executionRunId, phase10Config.startedBy || 'operator'),
        { method: 'GET' },
        (event) => {
          setPhase10Events((prev) => {
            const next = [...prev, event]
            return next.length > 250 ? next.slice(next.length - 250) : next
          })

          if (event?.type === 'done' && event?.execution) {
            setPhase10Execution(event.execution)
          } else if (event?.type === 'run_finished' && event?.execution) {
            setPhase10Execution(event.execution)
          }
        },
        async () => {
          await refreshRun(nextRunId, { storyId })
        },
        (msg) => {
          setError(msg || 'Phase10 execution stream failed')
        }
      )

      return execution
    } catch (e) {
      setError(e?.message || 'Phase10 execution stream failed')
      throw e
    } finally {
      setLoading(false)
    }
  }, [phase10Config, refreshRun, startSSE])

  return {
    loading,
    error,
    streaming,
    runId,
    runSnapshot,
    phase6Readiness,
    phase6ReasonCodes,
    tokenBuffer,
    observability,
    integrity,
    actionMessage,
    phase10Config,
    phase10Execution,
    phase10Events,
    agent3Runs,
    agent4History,
    loadAgent3Runs,
    loadAgent4History,
    loadPhase6ReasonCodes,
    getLastRunForStory,
    refreshRun,
    startFromAgent3Run,
    generateScriptsStream,
    reviewPhase6,
    handoffPhase7,
    setPhase10Config,
    runPhase10ExecutionStream,
    abortSSE,
  }
}
