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

export async function getAgent2Blueprint() {
  return jsonFetch('/agent2/blueprint')
}

export async function consumeAgent1HandoffForAgent2(payload) {
  return jsonFetch('/agent2/inbox/consume', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listApprovedAgent1Runs(backlogItemId, limit = 50, handoffOnly = true) {
  const q = new URLSearchParams({
    backlog_item_id: backlogItemId,
    limit: String(limit),
    handoff_only: String(Boolean(handoffOnly)),
  })
  return jsonFetch(`/agent2/agent1/approved-runs?${q.toString()}`)
}

export async function startAgent2FromAgent1Run(agent1RunId) {
  return jsonFetch(`/agent2/agent1-runs/${agent1RunId}/start`, {
    method: 'POST',
  })
}

export async function createAgent2RunFromInbox(messageId) {
  return jsonFetch(`/agent2/inbox/${messageId}/runs`, {
    method: 'POST',
  })
}

export async function getAgent2Run(runId) {
  return jsonFetch(`/agent2/runs/${runId}`)
}

export async function listAgent2RunsByBacklog(backlogItemId, limit = 20) {
  const q = new URLSearchParams({ backlog_item_id: backlogItemId, limit: String(limit) })
  return jsonFetch(`/agent2/runs?${q.toString()}`)
}

export async function getAgent2Timeline(runId, order = 'asc') {
  const q = new URLSearchParams({ order })
  return jsonFetch(`/agent2/runs/${runId}/timeline?${q.toString()}`)
}

export async function getAgent2ObservabilityCounters(backlogItemId = null) {
  const q = new URLSearchParams()
  if (backlogItemId) {
    q.set('backlog_item_id', backlogItemId)
  }
  const suffix = q.toString() ? `?${q.toString()}` : ''
  return jsonFetch(`/agent2/observability/counters${suffix}`)
}

export async function generateAgent2Run(runId, payload = {}) {
  return jsonFetch(`/agent2/runs/${runId}/generate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function getAgent2GenerateStreamUrl(runId) {
  return `/agent2/runs/${runId}/generate/stream`
}

export async function reviewAgent2Run(runId, payload) {
  return jsonFetch(`/agent2/runs/${runId}/review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getAgent2ReviewDiff(runId) {
  return jsonFetch(`/agent2/runs/${runId}/review-diff`)
}

export async function getAgent2ReviewReasonCodes() {
  return jsonFetch('/agent2/review/reason-codes')
}

export async function emitAgent2Handoff(runId) {
  return jsonFetch(`/agent2/runs/${runId}/handoff`, {
    method: 'POST',
  })
}

export async function listScraperJobs(backlogItemId, limit = 20) {
  const normalizedBacklogItemId = typeof backlogItemId === 'string'
    ? backlogItemId.trim()
    : String(backlogItemId || '').trim()
  if (!normalizedBacklogItemId) {
    throw new Error('Missing backlog item id for scraper job lookup')
  }

  const q = new URLSearchParams({
    backlog_item_id: normalizedBacklogItemId,
    limit: String(limit),
  })
  return jsonFetch(`/scraper/jobs?${q.toString()}`)
}

export async function createScraperJob(payload) {
  return jsonFetch('/scraper/jobs', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function runScraperJob(jobId, payload = {}) {
  const safeJobId = encodePathPart(jobId, 'jobId')
  return jsonFetch(`/scraper/jobs/${safeJobId}/run`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function completeScraperPhase8(jobId, payload = {}) {
  const safeJobId = encodePathPart(jobId, 'jobId')
  return jsonFetch(`/scraper/jobs/${safeJobId}/phase8/complete`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function getScraperJob(jobId) {
  const safeJobId = encodePathPart(jobId, 'jobId')
  return jsonFetch(`/scraper/jobs/${safeJobId}`)
}

export async function buildScraperContextPack(jobId, payload = { max_pages: 50 }) {
  const safeJobId = encodePathPart(jobId, 'jobId')
  return jsonFetch(`/scraper/jobs/${safeJobId}/phase5/context-pack`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listAgent3RunsByBacklog(backlogItemId, limit = 20) {
  const q = new URLSearchParams({ backlog_item_id: backlogItemId, limit: String(limit) })
  return jsonFetch(`/agent3/runs?${q.toString()}`)
}
