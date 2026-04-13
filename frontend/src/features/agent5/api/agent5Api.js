async function jsonFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }

  return res.json()
}

function encodePathPart(value, name) {
  const normalized = typeof value === 'string' ? value.trim() : String(value || '').trim()
  if (!normalized) {
    throw new Error(`Missing required path value: ${name}`)
  }
  return encodeURIComponent(normalized)
}

export async function listAgent4RunsByBacklog(backlogItemId, limit = 50) {
  const q = new URLSearchParams({ backlog_item_id: backlogItemId, limit: String(limit) })
  return jsonFetch(`/agent4/runs?${q.toString()}`)
}

export async function getAgent4RunSnapshot(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}`)
}

export async function listAgent4Phase10Executions(runId, limit = 30) {
  const safeRunId = encodePathPart(runId, 'runId')
  const q = new URLSearchParams({ limit: String(limit) })
  return jsonFetch(`/agent4/runs/${safeRunId}/phase10/executions?${q.toString()}`)
}

export async function createAgent4Phase10Execution(runId, payload) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase10/executions`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function cancelAgent4Phase10Execution(executionRunId, canceledBy = 'agent5-ui') {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ canceled_by: String(canceledBy || 'agent5-ui') })
  return jsonFetch(`/agent4/phase10/executions/${safeExecutionRunId}/cancel?${q.toString()}`, {
    method: 'POST',
  })
}

export async function cancelAgent4Phase10ExecutionWithKey(
  executionRunId,
  { canceledBy = 'agent5-ui', operatorKey = '' } = {}
) {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ canceled_by: String(canceledBy || 'agent5-ui') })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase10/executions/${safeExecutionRunId}/cancel?${q.toString()}`, {
    method: 'POST',
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function pauseAgent4Phase10Execution(executionRunId, pausedBy = 'agent5-ui') {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ paused_by: String(pausedBy || 'agent5-ui') })
  return jsonFetch(`/agent4/phase10/executions/${safeExecutionRunId}/pause?${q.toString()}`, {
    method: 'POST',
  })
}

export async function resumeAgent4Phase10Execution(executionRunId, resumedBy = 'agent5-ui') {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ resumed_by: String(resumedBy || 'agent5-ui') })
  return jsonFetch(`/agent4/phase10/executions/${safeExecutionRunId}/resume?${q.toString()}`, {
    method: 'POST',
  })
}

export async function getAgent4Phase10ExecutionNormalized(executionRunId) {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  return jsonFetch(`/agent4/phase10/executions/${safeExecutionRunId}/normalized`)
}

export async function getAgent4Phase10RuntimeCheck(launchProbe = true) {
  const q = new URLSearchParams({ launch_probe: String(Boolean(launchProbe)) })
  return jsonFetch(`/agent4/phase10/runtime/check?${q.toString()}`)
}

export async function getEvaluationStory(storyId, runLimit = 100) {
  const safeStoryId = encodePathPart(storyId, 'storyId')
  const q = new URLSearchParams({ run_limit: String(Math.max(1, Number(runLimit) || 100)) })
  return jsonFetch(`/evaluation/story/${safeStoryId}?${q.toString()}`)
}

export async function getEvaluationGlobal(runLimit = 300) {
  const q = new URLSearchParams({ run_limit: String(Math.max(1, Number(runLimit) || 300)) })
  return jsonFetch(`/evaluation/global?${q.toString()}`)
}

export async function getEvaluationRollout(storyId, runLimit = 100) {
  const safeStoryId = encodePathPart(storyId, 'storyId')
  const q = new URLSearchParams({ run_limit: String(Math.max(1, Number(runLimit) || 100)) })
  return jsonFetch(`/evaluation/rollout/${safeStoryId}?${q.toString()}`)
}

export async function getAgent5ContractSpec() {
  return jsonFetch('/agent5/contract')
}

export async function getAgent5StateMachineSpec() {
  return jsonFetch('/agent5/state-machine')
}

export async function createAgent5Run(payload) {
  return jsonFetch('/agent5/runs', {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function getAgent5RunSnapshot(agent5RunId) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}`)
}

export async function getAgent5RunOrchestration(agent5RunId) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/orchestration`)
}

export async function generateAgent5Stage7Analysis(agent5RunId, payload) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/stage7-analysis/generate`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function submitAgent5Gate7Decision(agent5RunId, payload) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/gate7/decision`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function generateAgent5Stage8Writeback(agent5RunId, payload) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/stage8-writeback/generate`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function submitAgent5Gate8Decision(agent5RunId, payload) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/gate8/decision`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function getAgent5RunObservability(agent5RunId) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/observability`)
}

export async function recoverAgent5StaleRuns(payload) {
  return jsonFetch('/agent5/reliability/recover-stale', {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function retryAgent5FailedRun(agent5RunId, payload) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/reliability/retry`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function listAgent5RunsForAgent4Run(sourceAgent4RunId, limit = 20) {
  const q = new URLSearchParams({
    source_agent4_run_id: String(sourceAgent4RunId || ''),
    limit: String(Math.max(1, Number(limit) || 20)),
  })
  return jsonFetch(`/agent5/runs?${q.toString()}`)
}

export async function applyAgent5RunCommand(agent5RunId, payload) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/commands`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export async function advanceAgent5RunToGate7Pending(agent5RunId, payload) {
  const safeRunId = encodePathPart(agent5RunId, 'agent5RunId')
  return jsonFetch(`/agent5/runs/${safeRunId}/advance-to-gate7-pending`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export function getAgent4Phase10ExecutionRunStreamUrl(executionRunId, startedBy = 'agent5-ui') {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ started_by: String(startedBy || 'agent5-ui') })
  return `/agent4/phase10/executions/${safeExecutionRunId}/run/stream?${q.toString()}`
}

export function getAgent4Phase10ExecutionStatusStreamUrl(executionRunId, pollMs = 500) {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ poll_ms: String(Math.max(100, Number(pollMs) || 500)) })
  return `/agent4/phase10/executions/${safeExecutionRunId}/stream?${q.toString()}`
}

export async function getAgent4Phase11QueueProfile() {
  return jsonFetch('/agent4/phase11/queue/profile')
}

export async function getAgent4Phase11QueueSnapshot(windowLimit = 1000) {
  const q = new URLSearchParams({ window_limit: String(Math.max(10, Number(windowLimit) || 1000)) })
  return jsonFetch(`/agent4/phase11/queue/snapshot?${q.toString()}`)
}

export async function getAgent4Phase11QueueItems(limit = 200) {
  const q = new URLSearchParams({ limit: String(Math.max(1, Number(limit) || 200)) })
  return jsonFetch(`/agent4/phase11/queue/items?${q.toString()}`)
}

export async function cancelAgent4Phase11QueueItem(executionRunId, canceledBy = 'agent5-ui') {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ canceled_by: String(canceledBy || 'agent5-ui') })
  return jsonFetch(`/agent4/phase11/queue/${safeExecutionRunId}?${q.toString()}`, {
    method: 'DELETE',
  })
}

export async function cancelAgent4Phase11QueueItemWithKey(
  executionRunId,
  { canceledBy = 'agent5-ui', operatorKey = '' } = {}
) {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ canceled_by: String(canceledBy || 'agent5-ui') })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase11/queue/${safeExecutionRunId}?${q.toString()}`, {
    method: 'DELETE',
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function startAgent4Phase10Dispatcher() {
  return jsonFetch('/agent4/phase10/dispatcher/start', { method: 'POST' })
}

export async function stopAgent4Phase10Dispatcher() {
  return jsonFetch('/agent4/phase10/dispatcher/stop', { method: 'POST' })
}

export async function stopAgent4Phase10DispatcherWithKey(operatorKey = '') {
  const key = String(operatorKey || '').trim()
  return jsonFetch('/agent4/phase10/dispatcher/stop', {
    method: 'POST',
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function recoverAgent4Phase10DispatcherStale(ttlSeconds = 3600) {
  const q = new URLSearchParams({ ttl_seconds: String(Math.max(1, Number(ttlSeconds) || 3600)) })
  return jsonFetch(`/agent4/phase10/dispatcher/recover-stale?${q.toString()}`, {
    method: 'POST',
  })
}

export async function getAgent4Phase12QueueHealth(windowLimit = 2000) {
  const q = new URLSearchParams({ window_limit: String(Math.max(10, Number(windowLimit) || 2000)) })
  return jsonFetch(`/agent4/phase12/queue/health?${q.toString()}`)
}

export async function expireAgent4Phase12Pending(ttlSeconds = 3600) {
  const q = new URLSearchParams({ ttl_seconds: String(Math.max(1, Number(ttlSeconds) || 3600)) })
  return jsonFetch(`/agent4/phase12/queue/expire-pending?${q.toString()}`, {
    method: 'POST',
  })
}

export async function expireAgent4Phase12PendingWithKey(ttlSeconds = 3600, operatorKey = '') {
  const q = new URLSearchParams({ ttl_seconds: String(Math.max(1, Number(ttlSeconds) || 3600)) })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase12/queue/expire-pending?${q.toString()}`, {
    method: 'POST',
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}
