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

export async function loadBacklogViaMCP(sourceType) {
  return jsonFetch('/agent1/intake/load', {
    method: 'POST',
    body: JSON.stringify({ source_type: sourceType }),
  })
}

export async function createAgent1Run(backlogItemId) {
  return jsonFetch('/agent1/runs', {
    method: 'POST',
    body: JSON.stringify({ backlog_item_id: backlogItemId }),
  })
}

export async function generateAgent1Run(runId, model = null) {
  return jsonFetch(`/agent1/runs/${runId}/generate`, {
    method: 'POST',
    body: JSON.stringify({ model }),
  })
}

export async function getAgent1Run(runId) {
  return jsonFetch(`/agent1/runs/${runId}`)
}

export async function submitAgent1Review(runId, payload) {
  return jsonFetch(`/agent1/runs/${runId}/review`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function retryAgent1Run(runId, reasonCode = null, actor = 'human') {
  return jsonFetch(`/agent1/runs/${runId}/retry`, {
    method: 'POST',
    body: JSON.stringify({ reason_code: reasonCode, actor }),
  })
}

export async function emitAgent1Handoff(runId) {
  return jsonFetch(`/agent1/runs/${runId}/handoff`, {
    method: 'POST',
  })
}

export async function getAgent1Timeline(runId) {
  return jsonFetch(`/agent1/runs/${runId}/timeline`)
}

export async function listAgent1RunsForStory(backlogItemId, limit = 50) {
  const q = new URLSearchParams({ limit: String(limit) })
  return jsonFetch(`/agent1/stories/${backlogItemId}/runs?${q.toString()}`)
}
