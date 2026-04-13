async function jsonFetch(url, options = {}) {
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(text || `HTTP ${res.status}`)
  }

  return res.json()
}

function roleHeaders(role) {
  return {
    'X-Retry-Role': role,
  }
}

export async function listRetryGovernanceRequests(runScope, runId, limit = 20) {
  const q = new URLSearchParams({ limit: String(limit) })
  return jsonFetch(`/retry-governance/${encodeURIComponent(runScope)}/${encodeURIComponent(runId)}?${q.toString()}`, {
    headers: roleHeaders('reviewer'),
  })
}

export async function assignRetryGovernanceReviewer(requestId, payload) {
  return jsonFetch(`/retry-governance/requests/${encodeURIComponent(requestId)}/assign`, {
    method: 'POST',
    headers: roleHeaders('operator'),
    body: JSON.stringify(payload || {}),
  })
}

export async function autoAssignRetryGovernanceReviewer(requestId, payload) {
  return jsonFetch(`/retry-governance/requests/${encodeURIComponent(requestId)}/assign/auto`, {
    method: 'POST',
    headers: roleHeaders('operator'),
    body: JSON.stringify(payload || {}),
  })
}

export async function listRetryGovernanceAuditEvents(requestId) {
  return jsonFetch(`/retry-governance/requests/${encodeURIComponent(requestId)}/audit`, {
    headers: roleHeaders('reviewer'),
  })
}

export async function reviewRetryGovernanceRequest(requestId, payload) {
  return jsonFetch(`/retry-governance/requests/${encodeURIComponent(requestId)}/review`, {
    method: 'POST',
    headers: roleHeaders('reviewer'),
    body: JSON.stringify(payload || {}),
  })
}

export async function approveAndRunRetryGovernanceRequest(requestId, payload) {
  return jsonFetch(`/retry-governance/requests/${encodeURIComponent(requestId)}/approve-and-run`, {
    method: 'POST',
    headers: roleHeaders('reviewer'),
    body: JSON.stringify(payload || {}),
  })
}

export async function getRetryRevisions(runScope, runId, includeHistory = false) {
  const q = new URLSearchParams({ include_history: includeHistory ? 'true' : 'false' })
  return jsonFetch(`/retry-governance/revisions/${encodeURIComponent(runScope)}/${encodeURIComponent(runId)}?${q.toString()}`, {
    headers: roleHeaders('reviewer'),
  })
}

export async function promoteRetryRevision(runScope, runId, payload) {
  return jsonFetch(`/retry-governance/revisions/${encodeURIComponent(runScope)}/${encodeURIComponent(runId)}/promote`, {
    method: 'POST',
    headers: roleHeaders('operator'),
    body: JSON.stringify(payload || {}),
  })
}

export async function getBusinessIdMigrationStatus() {
  return jsonFetch('/business-ids/migration/status', {
    headers: roleHeaders('reviewer'),
  })
}

export async function repairBusinessIdMigrationLinks(payload) {
  return jsonFetch('/business-ids/migration/repair', {
    method: 'POST',
    headers: roleHeaders('operator'),
    body: JSON.stringify(payload || {}),
  })
}
