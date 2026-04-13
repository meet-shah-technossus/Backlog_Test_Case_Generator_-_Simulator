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
  if (!normalized) throw new Error(`Missing required path value: ${name}`)
  return encodeURIComponent(normalized)
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

export async function getEvaluationQueueLifecycle({ storyId = null, hours = 24, bucketMinutes = 30, limit = 8000 } = {}) {
  const q = new URLSearchParams({
    hours: String(Math.max(1, Number(hours) || 24)),
    bucket_minutes: String(Math.max(1, Number(bucketMinutes) || 30)),
    limit: String(Math.max(1, Number(limit) || 8000)),
  })
  if (storyId) {
    q.set('story_id', String(storyId).trim())
  }
  return jsonFetch(`/evaluation/queue-lifecycle?${q.toString()}`)
}

export async function getPhase11QueueProfile() {
  return jsonFetch('/agent4/phase11/queue/profile')
}

export async function getPhase11QueueSnapshot(windowLimit = 1000) {
  const q = new URLSearchParams({ window_limit: String(Math.max(10, Number(windowLimit) || 1000)) })
  return jsonFetch(`/agent4/phase11/queue/snapshot?${q.toString()}`)
}

export async function getPhase11QueueItems(limit = 200) {
  const q = new URLSearchParams({ limit: String(Math.max(1, Number(limit) || 200)) })
  return jsonFetch(`/agent4/phase11/queue/items?${q.toString()}`)
}

export async function cancelPhase11QueueItem(executionRunId, canceledBy = 'evaluation-dashboard') {
  const safeExecutionRunId = encodePathPart(executionRunId, 'executionRunId')
  const q = new URLSearchParams({ canceled_by: String(canceledBy || 'evaluation-dashboard') })
  return jsonFetch(`/agent4/phase11/queue/${safeExecutionRunId}?${q.toString()}`, {
    method: 'DELETE',
  })
}
