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

export async function startAgent3FromAgent2Run(agent2RunId) {
  const safeRunId = encodePathPart(agent2RunId, 'agent2RunId')
  try {
    return await jsonFetch(`/agent2/runs/${safeRunId}/agent3/start`, { method: 'POST' })
  } catch (error) {
    const text = String(error?.message || '')
    if (!text.includes('404')) {
      throw error
    }
    return jsonFetch(`/agent3/agent2-runs/${safeRunId}/start`, { method: 'POST' })
  }
}

export async function consumeAgent2HandoffForAgent3(payload) {
  return jsonFetch('/agent3/inbox/consume', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function createAgent3RunFromInbox(messageId) {
  const safeMessageId = encodePathPart(messageId, 'messageId')
  return jsonFetch(`/agent3/inbox/${safeMessageId}/runs`, {
    method: 'POST',
  })
}

export async function getAgent3RunSnapshot(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent3/runs/${safeRunId}`)
}

export async function assembleAgent3Context(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent3/runs/${safeRunId}/phase3/assemble-context`, {
    method: 'POST',
  })
}

export async function submitAgent3Gate(runId, payload) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent3/runs/${safeRunId}/phase3/gate`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function generateAgent3Selectors(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent3/runs/${safeRunId}/phase4/generate-selectors`, {
    method: 'POST',
  })
}

export async function reviewAgent3Selectors(runId, payload) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent3/runs/${safeRunId}/phase5/review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function emitAgent3Handoff(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent3/runs/${safeRunId}/phase5/handoff`, {
    method: 'POST',
  })
}

export async function getAgent3Phase7Observability(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent3/runs/${safeRunId}/phase7/observability`)
}

export async function getAgent3Phase8Integrity(runId) {
  const safeRunId = encodePathPart(runId, 'runId')
  return jsonFetch(`/agent3/runs/${safeRunId}/phase8/integrity`)
}
