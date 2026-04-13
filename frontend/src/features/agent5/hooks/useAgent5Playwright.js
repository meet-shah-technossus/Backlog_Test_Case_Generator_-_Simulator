import { useCallback, useMemo, useState } from 'react'
import { useSSE } from '../../agent1/hooks/useSSE'
import {
  advanceAgent5RunToGate7Pending,
  applyAgent5RunCommand,
  cancelAgent4Phase10ExecutionWithKey,
  createAgent4Phase10Execution,
  getAgent4Phase10ExecutionNormalized,
  getAgent4Phase10ExecutionRunStreamUrl,
  getAgent4Phase10ExecutionStatusStreamUrl,
  getAgent4Phase10RuntimeCheck,
  createAgent5Run,
  generateAgent5Stage7Analysis,
  generateAgent5Stage8Writeback,
  getAgent5ContractSpec,
  getAgent5RunObservability,
  getAgent5RunSnapshot,
  getAgent5RunOrchestration,
  getAgent5StateMachineSpec,
  getAgent4RunSnapshot,
  listAgent5RunsForAgent4Run,
  listAgent4Phase10Executions,
  listAgent4RunsByBacklog,
  pauseAgent4Phase10Execution,
  recoverAgent5StaleRuns,
  resumeAgent4Phase10Execution,
  retryAgent5FailedRun,
  submitAgent5Gate7Decision,
  submitAgent5Gate8Decision,
} from '../api/agent5Api'

function parseDateValue(value) {
  if (!value) return 0
  const normalized = typeof value === 'string' ? value.replace(' ', 'T') : value
  const ts = new Date(normalized).getTime()
  return Number.isFinite(ts) ? ts : 0
}

function latestScriptBundle(snapshot) {
  const artifacts = Array.isArray(snapshot?.artifacts) ? snapshot.artifacts : []
  const match = artifacts.find((row) => row?.artifact?.artifact_type === 'phase5_generated_script_bundle')
  return match?.artifact || null
}

function normalizeScriptPath(pathValue) {
  return String(pathValue || '').trim()
}

export function useAgent5Playwright() {
  const { start: startSSE, abort: abortSSE, streaming } = useSSE()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [actionMessage, setActionMessage] = useState('')

  const [runtimeCheck, setRuntimeCheck] = useState(null)
  const [agent5Contract, setAgent5Contract] = useState(null)
  const [agent5StateMachine, setAgent5StateMachine] = useState(null)
  const [handoffRuns, setHandoffRuns] = useState([])
  const [selectedRunId, setSelectedRunId] = useState('')
  const [runSnapshot, setRunSnapshot] = useState(null)
  const [executionHistory, setExecutionHistory] = useState([])
  const [agent5Runs, setAgent5Runs] = useState([])
  const [selectedAgent5RunId, setSelectedAgent5RunId] = useState('')
  const [agent5RunSnapshot, setAgent5RunSnapshot] = useState(null)
  const [agent5Orchestration, setAgent5Orchestration] = useState(null)
  const [agent5Command, setAgent5Command] = useState('submit_gate7')

  const [selectedScriptPaths, setSelectedScriptPaths] = useState({})
  const [forceRegenerateStage7, setForceRegenerateStage7] = useState(false)
  const [gate7Form, setGate7Form] = useState({
    reviewerId: 'agent5-ui',
    decision: 'approve',
    reasonCode: 'validated_by_operator',
    comment: '',
  })
  const [stage8WritebackForm, setStage8WritebackForm] = useState({
    actor: 'agent5-ui',
    idempotencyKey: '',
    forceRegenerate: false,
  })
  const [gate8Form, setGate8Form] = useState({
    reviewerId: 'agent5-ui',
    decision: 'confirm',
    reasonCode: 'writeback_confirmed',
    comment: '',
  })
  const [observabilitySnapshot, setObservabilitySnapshot] = useState(null)
  const [reliabilityRecoverForm, setReliabilityRecoverForm] = useState({
    actor: 'agent5-ui',
    olderThanSeconds: 1800,
    limit: 100,
  })
  const [lastReliabilityRecovery, setLastReliabilityRecovery] = useState(null)

  const [executionConfig, setExecutionConfig] = useState({
    startedBy: 'agent5-ui',
    targetUrl: '',
    maxAttempts: 1,
    maxScripts: 0,
    earlyStopAfterFailures: 1,
    parallelWorkers: 1,
    useSmokeProbeScript: false,
  })

  const [activeExecution, setActiveExecution] = useState(null)
  const [executionEvents, setExecutionEvents] = useState([])
  const [streamPaused, setStreamPaused] = useState(false)

  const scripts = useMemo(() => {
    const bundle = latestScriptBundle(runSnapshot)
    const list = Array.isArray(bundle?.scripts) ? bundle.scripts : []
    return list.map((item) => ({
      caseId: String(item?.case_id || ''),
      path: normalizeScriptPath(item?.path),
      content: String(item?.content || ''),
    })).filter((item) => item.path)
  }, [runSnapshot])

  const selectedScripts = useMemo(() => {
    return scripts.filter((script) => selectedScriptPaths[script.path])
  }, [scripts, selectedScriptPaths])

  const persistedRun = useMemo(() => {
    return agent5RunSnapshot?.run && typeof agent5RunSnapshot.run === 'object' ? agent5RunSnapshot.run : null
  }, [agent5RunSnapshot])

  const persistedArtifacts = useMemo(() => {
    return Array.isArray(agent5RunSnapshot?.artifacts) ? agent5RunSnapshot.artifacts : []
  }, [agent5RunSnapshot])

  const persistedTimeline = useMemo(() => {
    return Array.isArray(agent5RunSnapshot?.timeline) ? agent5RunSnapshot.timeline : []
  }, [agent5RunSnapshot])

  const transitionAuditArtifacts = useMemo(() => {
    return persistedArtifacts.filter((item) => String(item?.artifact_type || '') === 'state_transition_audit')
  }, [persistedArtifacts])

  const loadRuntimeCheck = useCallback(async () => {
    try {
      const data = await getAgent4Phase10RuntimeCheck(true)
      setRuntimeCheck(data)
      return data
    } catch (e) {
      setError(e?.message || 'Failed to run Playwright runtime check')
      throw e
    }
  }, [])

  const loadAgent5ContractAndStateMachine = useCallback(async () => {
    try {
      const [contractData, stateMachineData] = await Promise.all([
        getAgent5ContractSpec(),
        getAgent5StateMachineSpec(),
      ])
      setAgent5Contract(contractData?.contract || null)
      setAgent5StateMachine(stateMachineData?.state_machine || null)
      return { contractData, stateMachineData }
    } catch (e) {
      setError(e?.message || 'Failed to load Agent5 contract/state machine')
      throw e
    }
  }, [])

  const loadRunsForStory = useCallback(async (storyId) => {
    if (!storyId) {
      setHandoffRuns([])
      setSelectedRunId('')
      setRunSnapshot(null)
      setExecutionHistory([])
      return []
    }

    setLoading(true)
    setError('')
    try {
      const data = await listAgent4RunsByBacklog(storyId, 100)
      const runs = Array.isArray(data?.runs) ? data.runs : []
      const filtered = runs.filter((run) => String(run?.state || '') === 'handoff_emitted')
      const sorted = [...(filtered.length ? filtered : runs)].sort((a, b) => parseDateValue(b.updated_at) - parseDateValue(a.updated_at))
      setHandoffRuns(sorted)
      const firstRunId = String(sorted[0]?.run_id || '')
      if (firstRunId) {
        setSelectedRunId(firstRunId)
      }
      return sorted
    } catch (e) {
      setError(e?.message || 'Failed to load Agent4 runs')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const loadRunDetails = useCallback(async (runId) => {
    if (!runId) return null
    setLoading(true)
    setError('')
    try {
      const [snapshotData, historyData] = await Promise.all([
        getAgent4RunSnapshot(runId),
        listAgent4Phase10Executions(runId, 40),
      ])
      setRunSnapshot(snapshotData)
      const executions = Array.isArray(historyData?.executions) ? historyData.executions : []
      setExecutionHistory(executions)
      const agent5Data = await listAgent5RunsForAgent4Run(runId, 30)
      const storedRuns = Array.isArray(agent5Data?.runs) ? agent5Data.runs : []
      setAgent5Runs(storedRuns)
      if (storedRuns.length && !selectedAgent5RunId) {
        setSelectedAgent5RunId(String(storedRuns[0]?.agent5_run_id || ''))
      }

      const nextSelected = {}
      const bundle = latestScriptBundle(snapshotData)
      const list = Array.isArray(bundle?.scripts) ? bundle.scripts : []
      for (const script of list) {
        const path = normalizeScriptPath(script?.path)
        if (path) nextSelected[path] = true
      }
      setSelectedScriptPaths(nextSelected)
      return snapshotData
    } catch (e) {
      setError(e?.message || 'Failed to load run details')
      throw e
    } finally {
      setLoading(false)
    }
  }, [selectedAgent5RunId])

  const loadAgent5RunSnapshot = useCallback(async (agent5RunId) => {
    const runId = String(agent5RunId || '')
    if (!runId) {
      setAgent5RunSnapshot(null)
      setAgent5Orchestration(null)
      setObservabilitySnapshot(null)
      return null
    }
    setLoading(true)
    setError('')
    try {
      const snapshot = await getAgent5RunSnapshot(runId)
      setAgent5RunSnapshot(snapshot)
      try {
        const [orchestration, observability] = await Promise.all([
          getAgent5RunOrchestration(runId),
          getAgent5RunObservability(runId),
        ])
        setAgent5Orchestration(orchestration)
        setObservabilitySnapshot(observability?.observability || null)
        const available = Array.isArray(orchestration?.available_commands) ? orchestration.available_commands : []
        if (available.length) {
          setAgent5Command((prev) => (available.includes(prev) ? prev : available[0]))
        }
      } catch {
        setAgent5Orchestration(null)
        setObservabilitySnapshot(null)
      }
      return snapshot
    } catch (e) {
      setError(e?.message || 'Failed to load Agent5 run snapshot')
      throw e
    } finally {
      setLoading(false)
    }
  }, [])

  const createOrLinkAgent5Run = useCallback(async () => {
    if (!selectedRunId) return null
    setLoading(true)
    setError('')
    try {
      const executionRunId = String(activeExecution?.execution_run_id || '') || null
      const created = await createAgent5Run({
        source_agent4_run_id: selectedRunId,
        source_execution_run_id: executionRunId,
        created_by: 'agent5-ui',
        reason: 'a5.2 persisted run link',
      })
      const run = created?.run || null
      const runId = String(run?.agent5_run_id || '')
      if (runId) {
        setSelectedAgent5RunId(runId)
      }
      const refreshed = await listAgent5RunsForAgent4Run(selectedRunId, 30)
      setAgent5Runs(Array.isArray(refreshed?.runs) ? refreshed.runs : [])
      if (runId) {
        await loadAgent5RunSnapshot(runId)
      }
      return created
    } catch (e) {
      setError(e?.message || 'Failed to create Agent5 persisted run')
      throw e
    } finally {
      setLoading(false)
    }
  }, [activeExecution?.execution_run_id, loadAgent5RunSnapshot, selectedRunId])

  const refreshAgent5Runs = useCallback(async () => {
    if (!selectedRunId) return []
    const refreshed = await listAgent5RunsForAgent4Run(selectedRunId, 30)
    const runs = Array.isArray(refreshed?.runs) ? refreshed.runs : []
    setAgent5Runs(runs)
    return runs
  }, [selectedRunId])

  const applyAgent5Command = useCallback(async (command, context = {}) => {
    const runId = String(selectedAgent5RunId || '')
    const normalizedCommand = String(command || '').trim()
    if (!runId || !normalizedCommand) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const snapshot = await applyAgent5RunCommand(runId, {
        actor: 'agent5-ui',
        command: normalizedCommand,
        context,
      })
      setAgent5RunSnapshot(snapshot)
      const orchestration = await getAgent5RunOrchestration(runId)
      setAgent5Orchestration(orchestration)
      const available = Array.isArray(orchestration?.available_commands) ? orchestration.available_commands : []
      if (available.length) {
        setAgent5Command((prev) => (available.includes(prev) ? prev : available[0]))
      }
      await refreshAgent5Runs()
      setActionMessage(`Agent5 command applied: ${normalizedCommand}`)
      return snapshot
    } catch (e) {
      setError(e?.message || 'Failed to apply Agent5 command')
      throw e
    } finally {
      setLoading(false)
    }
  }, [refreshAgent5Runs, selectedAgent5RunId])

  const advanceToGate7Pending = useCallback(async () => {
    const runId = String(selectedAgent5RunId || '')
    if (!runId) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const snapshot = await advanceAgent5RunToGate7Pending(runId, {
        actor: 'agent5-ui',
        context: { source: 'agent5-board' },
      })
      setAgent5RunSnapshot(snapshot)
      const orchestration = await getAgent5RunOrchestration(runId)
      setAgent5Orchestration(orchestration)
      const available = Array.isArray(orchestration?.available_commands) ? orchestration.available_commands : []
      if (available.length) {
        setAgent5Command((prev) => (available.includes(prev) ? prev : available[0]))
      }
      await refreshAgent5Runs()
      setActionMessage('Agent5 run advanced to gate7_pending')
      return snapshot
    } catch (e) {
      setError(e?.message || 'Failed to advance Agent5 run to gate7_pending')
      throw e
    } finally {
      setLoading(false)
    }
  }, [refreshAgent5Runs, selectedAgent5RunId])

  const generateStage7Analysis = useCallback(async () => {
    const runId = String(selectedAgent5RunId || '')
    if (!runId) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const snapshot = await generateAgent5Stage7Analysis(runId, {
        actor: 'agent5-ui',
        force_regenerate: Boolean(forceRegenerateStage7),
      })
      setAgent5RunSnapshot(snapshot)
      const orchestration = await getAgent5RunOrchestration(runId)
      setAgent5Orchestration(orchestration)
      const available = Array.isArray(orchestration?.available_commands) ? orchestration.available_commands : []
      if (available.length) {
        setAgent5Command((prev) => (available.includes(prev) ? prev : available[0]))
      }
      await refreshAgent5Runs()
      setActionMessage('Stage 7 analysis generated')
      return snapshot
    } catch (e) {
      setError(e?.message || 'Failed to generate Stage 7 analysis')
      throw e
    } finally {
      setLoading(false)
    }
  }, [forceRegenerateStage7, refreshAgent5Runs, selectedAgent5RunId])

  const submitGate7Decision = useCallback(async () => {
    const runId = String(selectedAgent5RunId || '')
    if (!runId) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const snapshot = await submitAgent5Gate7Decision(runId, {
        reviewer_id: String(gate7Form.reviewerId || '').trim() || 'agent5-ui',
        decision: String(gate7Form.decision || '').trim() || 'approve',
        reason_code: String(gate7Form.reasonCode || '').trim() || 'unspecified',
        comment: String(gate7Form.comment || ''),
      })
      setAgent5RunSnapshot(snapshot)
      const orchestration = await getAgent5RunOrchestration(runId)
      setAgent5Orchestration(orchestration)
      const available = Array.isArray(orchestration?.available_commands) ? orchestration.available_commands : []
      if (available.length) {
        setAgent5Command((prev) => (available.includes(prev) ? prev : available[0]))
      }
      await refreshAgent5Runs()
      setActionMessage('Gate 7 decision submitted')
      return snapshot
    } catch (e) {
      setError(e?.message || 'Failed to submit Gate 7 decision')
      throw e
    } finally {
      setLoading(false)
    }
  }, [gate7Form.comment, gate7Form.decision, gate7Form.reasonCode, gate7Form.reviewerId, refreshAgent5Runs, selectedAgent5RunId])

  const generateStage8Writeback = useCallback(async () => {
    const runId = String(selectedAgent5RunId || '')
    if (!runId) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const snapshot = await generateAgent5Stage8Writeback(runId, {
        actor: String(stage8WritebackForm.actor || '').trim() || 'agent5-ui',
        idempotency_key: String(stage8WritebackForm.idempotencyKey || '').trim() || null,
        force_regenerate: Boolean(stage8WritebackForm.forceRegenerate),
      })
      setAgent5RunSnapshot(snapshot)
      const orchestration = await getAgent5RunOrchestration(runId)
      setAgent5Orchestration(orchestration)
      const available = Array.isArray(orchestration?.available_commands) ? orchestration.available_commands : []
      if (available.length) {
        setAgent5Command((prev) => (available.includes(prev) ? prev : available[0]))
      }
      await refreshAgent5Runs()
      setActionMessage('Stage 8 writeback generated')
      return snapshot
    } catch (e) {
      setError(e?.message || 'Failed to generate Stage 8 writeback')
      throw e
    } finally {
      setLoading(false)
    }
  }, [refreshAgent5Runs, selectedAgent5RunId, stage8WritebackForm.actor, stage8WritebackForm.forceRegenerate, stage8WritebackForm.idempotencyKey])

  const submitGate8Decision = useCallback(async () => {
    const runId = String(selectedAgent5RunId || '')
    if (!runId) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const snapshot = await submitAgent5Gate8Decision(runId, {
        reviewer_id: String(gate8Form.reviewerId || '').trim() || 'agent5-ui',
        decision: String(gate8Form.decision || '').trim() || 'confirm',
        reason_code: String(gate8Form.reasonCode || '').trim() || 'unspecified',
        comment: String(gate8Form.comment || ''),
      })
      setAgent5RunSnapshot(snapshot)
      const [orchestration, observability] = await Promise.all([
        getAgent5RunOrchestration(runId),
        getAgent5RunObservability(runId),
      ])
      setAgent5Orchestration(orchestration)
      setObservabilitySnapshot(observability?.observability || null)
      const available = Array.isArray(orchestration?.available_commands) ? orchestration.available_commands : []
      if (available.length) {
        setAgent5Command((prev) => (available.includes(prev) ? prev : available[0]))
      }
      await refreshAgent5Runs()
      setActionMessage('Gate 8 decision submitted')
      return snapshot
    } catch (e) {
      setError(e?.message || 'Failed to submit Gate 8 decision')
      throw e
    } finally {
      setLoading(false)
    }
  }, [gate8Form.comment, gate8Form.decision, gate8Form.reasonCode, gate8Form.reviewerId, refreshAgent5Runs, selectedAgent5RunId])

  const recoverStaleAgent5Runs = useCallback(async () => {
    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const recovery = await recoverAgent5StaleRuns({
        actor: String(reliabilityRecoverForm.actor || '').trim() || 'agent5-ui',
        older_than_seconds: Number(reliabilityRecoverForm.olderThanSeconds || 1800),
        limit: Number(reliabilityRecoverForm.limit || 100),
      })
      setLastReliabilityRecovery(recovery?.recovery || null)
      if (selectedRunId) {
        await refreshAgent5Runs()
      }
      if (selectedAgent5RunId) {
        await loadAgent5RunSnapshot(selectedAgent5RunId)
      }
      setActionMessage('Stale run recovery completed')
      return recovery
    } catch (e) {
      setError(e?.message || 'Failed to recover stale Agent5 runs')
      throw e
    } finally {
      setLoading(false)
    }
  }, [loadAgent5RunSnapshot, refreshAgent5Runs, reliabilityRecoverForm.actor, reliabilityRecoverForm.limit, reliabilityRecoverForm.olderThanSeconds, selectedAgent5RunId, selectedRunId])

  const retryFailedAgent5Run = useCallback(async () => {
    const runId = String(selectedAgent5RunId || '')
    if (!runId) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const snapshot = await retryAgent5FailedRun(runId, { actor: 'agent5-ui' })
      setAgent5RunSnapshot(snapshot)
      const [orchestration, observability] = await Promise.all([
        getAgent5RunOrchestration(runId),
        getAgent5RunObservability(runId),
      ])
      setAgent5Orchestration(orchestration)
      setObservabilitySnapshot(observability?.observability || null)
      const available = Array.isArray(orchestration?.available_commands) ? orchestration.available_commands : []
      if (available.length) {
        setAgent5Command((prev) => (available.includes(prev) ? prev : available[0]))
      }
      await refreshAgent5Runs()
      setActionMessage('Failed run moved to retry state')
      return snapshot
    } catch (e) {
      setError(e?.message || 'Failed to retry failed Agent5 run')
      throw e
    } finally {
      setLoading(false)
    }
  }, [refreshAgent5Runs, selectedAgent5RunId])

  const toggleScript = useCallback((scriptPath, checked) => {
    const key = normalizeScriptPath(scriptPath)
    if (!key) return
    setSelectedScriptPaths((prev) => ({ ...prev, [key]: Boolean(checked) }))
  }, [])

  const selectAllScripts = useCallback((checked) => {
    setSelectedScriptPaths((prev) => {
      const next = { ...prev }
      for (const key of Object.keys(next)) {
        next[key] = Boolean(checked)
      }
      return next
    })
  }, [])

  const runExecution = useCallback(async () => {
    if (!selectedRunId) return null
    setLoading(true)
    setError('')
    setActionMessage('')
    setExecutionEvents([])
    setStreamPaused(false)

    try {
      const selectedPaths = selectedScripts.map((item) => item.path)
      const payload = {
        requested_by: 'agent5-ui',
        reason: 'agent5-playwright-execution',
        max_attempts: Number(executionConfig.maxAttempts || 1),
        target_url: String(executionConfig.targetUrl || '').trim() || null,
        max_scripts: Number(executionConfig.maxScripts || 0) || null,
        early_stop_after_failures: Number(executionConfig.earlyStopAfterFailures || 0) || null,
        parallel_workers: Number(executionConfig.parallelWorkers || 0) || null,
        selected_script_paths: executionConfig.useSmokeProbeScript ? null : selectedPaths,
        use_smoke_probe_script: Boolean(executionConfig.useSmokeProbeScript),
      }

      const create = await createAgent4Phase10Execution(selectedRunId, payload)
      const execution = create?.execution || null
      const executionRunId = String(execution?.execution_run_id || '')
      if (!executionRunId) {
        throw new Error('Failed to create execution run')
      }

      setActiveExecution(execution)
      setActionMessage(`Execution created: ${executionRunId}`)

      await startSSE(
        getAgent4Phase10ExecutionRunStreamUrl(executionRunId, executionConfig.startedBy || 'agent5-ui'),
        { method: 'GET' },
        (event) => {
          setExecutionEvents((prev) => {
            const next = [...prev, event]
            return next.length > 300 ? next.slice(next.length - 300) : next
          })

          if (event?.type === 'run_finished' && event?.execution) {
            setActiveExecution(event.execution)
          }
          if (event?.type === 'done' && event?.execution) {
            setActiveExecution(event.execution)
          }
        },
        async () => {
          const normalized = await getAgent4Phase10ExecutionNormalized(executionRunId)
          if (normalized?.execution) {
            setActiveExecution(normalized.execution)
          }
          const historyData = await listAgent4Phase10Executions(selectedRunId, 40)
          const executions = Array.isArray(historyData?.executions) ? historyData.executions : []
          setExecutionHistory(executions)
        },
        (msg) => {
          setError(msg || 'Execution stream failed')
        }
      )

      return execution
    } catch (e) {
      setError(e?.message || 'Execution failed to start')
      throw e
    } finally {
      setLoading(false)
    }
  }, [executionConfig, selectedRunId, selectedScripts, startSSE])

  const pauseExecution = useCallback(async () => {
    const executionRunId = String(activeExecution?.execution_run_id || '')
    if (!executionRunId) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const paused = await pauseAgent4Phase10Execution(executionRunId, 'agent5-ui-pause')
      if (paused?.execution) {
        setActiveExecution(paused.execution)
      }
      abortSSE()
      setStreamPaused(true)
      setActionMessage(`Execution paused: ${executionRunId}`)
      return paused
    } catch (e) {
      setError(e?.message || 'Failed to pause execution')
      throw e
    } finally {
      setLoading(false)
    }
  }, [abortSSE, activeExecution?.execution_run_id])

  const resumeExecution = useCallback(async () => {
    const executionRunId = String(activeExecution?.execution_run_id || '')
    if (!executionRunId) return

    setLoading(true)
    setError('')
    setActionMessage('')
    setStreamPaused(false)

    try {
      const resumed = await resumeAgent4Phase10Execution(executionRunId, 'agent5-ui-resume')
      if (resumed?.execution) {
        setActiveExecution(resumed.execution)
      }

      await startSSE(
        getAgent4Phase10ExecutionStatusStreamUrl(executionRunId, 500),
        { method: 'GET' },
        (event) => {
          setExecutionEvents((prev) => {
            const next = [...prev, event]
            return next.length > 300 ? next.slice(next.length - 300) : next
          })

          if (event?.execution) {
            setActiveExecution(event.execution)
          }
        },
        async () => {
          const historyData = await listAgent4Phase10Executions(selectedRunId, 40)
          const executions = Array.isArray(historyData?.executions) ? historyData.executions : []
          setExecutionHistory(executions)
          setActionMessage('Execution monitor stream completed')
        },
        (msg) => {
          setError(msg || 'Status stream failed')
        }
      )
    } catch (e) {
      setError(e?.message || 'Failed to resume execution')
      throw e
    } finally {
      setLoading(false)
    }
  }, [activeExecution?.execution_run_id, selectedRunId, startSSE])

  const stopExecution = useCallback(async (operatorKey = '') => {
    const executionRunId = String(activeExecution?.execution_run_id || '')
    if (!executionRunId) return null

    setLoading(true)
    setError('')
    setActionMessage('')
    try {
      const canceled = await cancelAgent4Phase10ExecutionWithKey(executionRunId, {
        canceledBy: 'agent5-ui-stop',
        operatorKey,
      })
      setActiveExecution(canceled?.execution || activeExecution)
      setActionMessage(`Execution canceled: ${executionRunId}`)
      const historyData = await listAgent4Phase10Executions(selectedRunId, 40)
      const executions = Array.isArray(historyData?.executions) ? historyData.executions : []
      setExecutionHistory(executions)
      abortSSE()
      return canceled
    } catch (e) {
      setError(e?.message || 'Failed to stop execution')
      throw e
    } finally {
      setLoading(false)
    }
  }, [abortSSE, activeExecution, selectedRunId])

  return {
    loading,
    error,
    streaming,
    actionMessage,
    runtimeCheck,
    agent5Contract,
    agent5StateMachine,
    handoffRuns,
    selectedRunId,
    runSnapshot,
    scripts,
    selectedScriptPaths,
    selectedScripts,
    persistedRun,
    persistedArtifacts,
    persistedTimeline,
    transitionAuditArtifacts,
    executionConfig,
    activeExecution,
    executionHistory,
    agent5Runs,
    selectedAgent5RunId,
    agent5RunSnapshot,
    agent5Orchestration,
    agent5Command,
    executionEvents,
    streamPaused,
    forceRegenerateStage7,
    gate7Form,
    stage8WritebackForm,
    gate8Form,
    observabilitySnapshot,
    reliabilityRecoverForm,
    lastReliabilityRecovery,
    setExecutionConfig,
    setSelectedRunId,
    setSelectedAgent5RunId,
    setAgent5Command,
    setForceRegenerateStage7,
    setGate7Form,
    setStage8WritebackForm,
    setGate8Form,
    setReliabilityRecoverForm,
    loadRuntimeCheck,
    loadAgent5ContractAndStateMachine,
    loadRunsForStory,
    loadRunDetails,
    loadAgent5RunSnapshot,
    createOrLinkAgent5Run,
    applyAgent5Command,
    advanceToGate7Pending,
    generateStage7Analysis,
    submitGate7Decision,
    generateStage8Writeback,
    submitGate8Decision,
    recoverStaleAgent5Runs,
    retryFailedAgent5Run,
    toggleScript,
    selectAllScripts,
    runExecution,
    pauseExecution,
    resumeExecution,
    stopExecution,
  }
}
