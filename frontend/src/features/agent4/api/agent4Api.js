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

export async function listAgent3RunsByBacklog(backlogItemId, limit = 50) {
  const q = new URLSearchParams({
    backlog_item_id: backlogItemId,
    limit: String(limit),
  })
  return jsonFetch(`/agent3/runs?${q.toString()}`)
}

export async function startAgent4FromAgent3Run(agent3RunId) {
  const safeRunId = encodePathPart(agent3RunId, 'agent3RunId')
  try {
    return await jsonFetch(`/agent4/agent3-runs/${safeRunId}/start`, { method: 'POST' })
  } catch (error) {
    const text = String(error?.message || '')
    const isNotFound =
      text.includes('404') ||
      text.includes('Not Found') ||
      text.includes('"detail":"Not Found"')
    if (!isNotFound) {
      throw error
    }
    return jsonFetch(`/agent3/runs/${safeRunId}/agent4/start`, { method: 'POST' })
  }
}

export async function getAgent4RunSnapshot(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}`)
}

export async function listAgent4RunsByBacklog(backlogItemId, limit = 20) {
  const q = new URLSearchParams({ backlog_item_id: backlogItemId, limit: String(limit) })
  return jsonFetch(`/agent4/runs?${q.toString()}`)
}

export function getAgent4Phase5GenerateStreamUrl(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return `/agent4/runs/${safeRunId}/phase5/generate-scripts/stream`
}

export async function submitAgent4Phase3Gate(runId, payload) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase3/gate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function planAgent4Phase4Scripts(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase4/plan-scripts`, {
    method: 'POST',
  })
}

export async function getAgent4Phase9Observability(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase9/observability`)
}

export async function getAgent4Phase9Integrity(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase9/integrity`)
}

export async function getAgent4Phase6Readiness(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase6/readiness`)
}

export async function getAgent4Phase6ReviewReasonCodes() {
  return jsonFetch('/agent4/phase6/review/reason-codes')
}

export async function submitAgent4Phase6Review(runId, payload) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase6/review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function emitAgent4Phase7Handoff(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase7/handoff`, {
    method: 'POST',
  })
}

export async function createAgent4Phase10Execution(runId, payload) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent4/runs/${safeRunId}/phase10/executions`, {
    method: 'POST',
    body: JSON.stringify(payload || {}),
  })
}

export function getAgent4Phase10ExecutionRunStreamUrl(executionRunId, startedBy = 'operator') {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ started_by: String(startedBy || 'operator') })
  return `/agent4/phase10/executions/${safeExecutionRunId}/run/stream?${q.toString()}`
}


export async function listAgent4Phase10Executions(runId, limit = 20) {
  const safeRunId = encodePathPart(runId, 'runId')
  const q = new URLSearchParams({ limit: String(Math.max(1, Math.min(200, Number(limit) || 20))) })
  return jsonFetch(`/agent4/runs/${safeRunId}/phase10/executions?${q.toString()}`)
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

export async function cancelAgent4Phase11QueueItem(executionRunId, canceledBy = 'agent4-ui') {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ canceled_by: String(canceledBy || 'agent4-ui') })
  return jsonFetch(`/agent4/phase11/queue/${safeExecutionRunId}?${q.toString()}`, {
    method: 'DELETE',
  })
}

export async function cancelAgent4Phase11QueueItemWithKey(
  executionRunId,
  { canceledBy = 'agent4-ui', operatorKey = '' } = {}
) {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ canceled_by: String(canceledBy || 'agent4-ui') })
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

export async function getAgent4Phase14QueueAudit({
  limit = 200,
  stage = '',
  status = '',
  storyId = '',
  operatorKey = '',
} = {}) {
  const q = new URLSearchParams({
    limit: String(Math.max(1, Math.min(1000, Number(limit) || 200))),
  })
  if (String(stage || '').trim()) q.set('stage', String(stage).trim())
  if (String(status || '').trim()) q.set('status', String(status).trim())
  if (String(storyId || '').trim()) q.set('story_id', String(storyId).trim())

  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase14/queue/audit?${q.toString()}`, {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function getAgent4Phase15OperatorWhoAmI(operatorKey = '') {
  const key = String(operatorKey || '').trim()
  return jsonFetch('/agent4/phase15/operator/whoami', {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function verifyAgent4Phase15QueueAudit({ limit = 500, storyId = '', operatorKey = '' } = {}) {
  const q = new URLSearchParams({ limit: String(Math.max(1, Math.min(1000, Number(limit) || 500))) })
  if (String(storyId || '').trim()) q.set('story_id', String(storyId).trim())
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase15/queue/audit/verify?${q.toString()}`, {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function getAgent4Phase16OperatorSecurityStatus(operatorKey = '') {
  const key = String(operatorKey || '').trim()
  return jsonFetch('/agent4/phase16/operator/security/status', {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function getAgent4Phase16OperatorSecurityEvents({ limit = 100, operatorKey = '' } = {}) {
  const q = new URLSearchParams({ limit: String(Math.max(1, Math.min(500, Number(limit) || 100))) })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase16/operator/security/events?${q.toString()}`, {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function getAgent4Phase17OperatorSecurityHistory({ limit = 100, operatorKey = '' } = {}) {
  const q = new URLSearchParams({ limit: String(Math.max(1, Math.min(500, Number(limit) || 100))) })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase17/operator/security/history?${q.toString()}`, {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function getAgent4Phase17OperatorSecuritySummary({ windowLimit = 1000, operatorKey = '' } = {}) {
  const q = new URLSearchParams({ window_limit: String(Math.max(1, Math.min(5000, Number(windowLimit) || 1000))) })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase17/operator/security/summary?${q.toString()}`, {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function testAgent4Phase17OperatorAlert({ source = 'operator-test', operatorKey = '' } = {}) {
  const q = new URLSearchParams({ source: String(source || 'operator-test') })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase17/operator/security/alerts/test?${q.toString()}`, {
    method: 'POST',
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function getAgent4Phase19OpenSecurityIncidents({ limit = 200, operatorKey = '' } = {}) {
  const q = new URLSearchParams({ limit: String(Math.max(1, Math.min(500, Number(limit) || 200))) })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase19/operator/security/incidents/open?${q.toString()}`, {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function ackAgent4Phase19SecurityIncident(
  incidentId,
  { ackedBy = 'operator', operatorKey = '' } = {}
) {
  const safeIncidentId = encodePathPart(incidentId, 'incidentId')
  const q = new URLSearchParams({ acked_by: String(ackedBy || 'operator') })
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase19/operator/security/incidents/${safeIncidentId}/ack?${q.toString()}`, {
    method: 'POST',
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function resolveAgent4Phase19SecurityIncident(
  incidentId,
  { resolvedBy = 'operator', resolutionNote = '', operatorKey = '' } = {}
) {
  const safeIncidentId = encodePathPart(incidentId, 'incidentId')
  const q = new URLSearchParams({ resolved_by: String(resolvedBy || 'operator') })
  if (String(resolutionNote || '').trim()) {
    q.set('resolution_note', String(resolutionNote).trim())
  }
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase19/operator/security/incidents/${safeIncidentId}/resolve?${q.toString()}`, {
    method: 'POST',
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function getAgent4Phase20SecurityReadiness(operatorKey = '') {
  const key = String(operatorKey || '').trim()
  return jsonFetch('/agent4/phase20/operator/security/readiness', {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}

export async function exportAgent4Phase20SecurityData({ limit = 500, state = '', operatorKey = '' } = {}) {
  const q = new URLSearchParams({ limit: String(Math.max(1, Math.min(5000, Number(limit) || 500))) })
  if (String(state || '').trim()) q.set('state', String(state).trim())
  const key = String(operatorKey || '').trim()
  return jsonFetch(`/agent4/phase20/operator/security/export?${q.toString()}`, {
    headers: key ? { 'X-Operator-Key': key } : undefined,
  })
}
