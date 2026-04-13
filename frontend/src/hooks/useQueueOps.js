import { useCallback, useEffect, useRef, useState } from 'react'
import {
  ackAgent4Phase19SecurityIncident,
  cancelAgent4Phase11QueueItemWithKey,
  expireAgent4Phase12PendingWithKey,
  getAgent4Phase19OpenSecurityIncidents,
  getAgent4Phase11QueueItems,
  getAgent4Phase14QueueAudit,
  getAgent4Phase15OperatorWhoAmI,
  getAgent4Phase16OperatorSecurityEvents,
  getAgent4Phase16OperatorSecurityStatus,
  getAgent4Phase17OperatorSecurityHistory,
  getAgent4Phase17OperatorSecuritySummary,
  getAgent4Phase20SecurityReadiness,
  getAgent4Phase12QueueHealth,
  exportAgent4Phase20SecurityData,
  resolveAgent4Phase19SecurityIncident,
  testAgent4Phase17OperatorAlert,
  verifyAgent4Phase15QueueAudit,
} from '../features/agent4/api/agent4Api'

export function useQueueOps({ pollMs = 7000, limit = 50, operatorKey = '', auditFilters = {} } = {}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [queueHealth, setQueueHealth] = useState(null)
  const [queueItems, setQueueItems] = useState([])
  const [queueAudit, setQueueAudit] = useState([])
  const [operatorIdentity, setOperatorIdentity] = useState(null)
  const [auditVerification, setAuditVerification] = useState(null)
  const [securityStatus, setSecurityStatus] = useState(null)
  const [securityEvents, setSecurityEvents] = useState([])
  const [securityHistory, setSecurityHistory] = useState([])
  const [securitySummary, setSecuritySummary] = useState(null)
  const [openIncidents, setOpenIncidents] = useState([])
  const [securityReadiness, setSecurityReadiness] = useState(null)
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null)

  const mounted = useRef(true)

  const refresh = useCallback(async () => {
    if (!mounted.current) return
    setLoading(true)
    setError('')
    try {
      const [healthRes, itemsRes] = await Promise.all([
        getAgent4Phase12QueueHealth(2000),
        getAgent4Phase11QueueItems(limit),
      ])
      const auditRes = await getAgent4Phase14QueueAudit({
        limit: 200,
        stage: auditFilters?.stage || '',
        status: auditFilters?.status || '',
        storyId: auditFilters?.storyId || '',
        operatorKey,
      })
      const [
        whoamiRes,
        verifyRes,
        securityStatusRes,
        securityEventsRes,
        securityHistoryRes,
        securitySummaryRes,
        openIncidentsRes,
        readinessRes,
      ] = await Promise.all([
        getAgent4Phase15OperatorWhoAmI(operatorKey),
        verifyAgent4Phase15QueueAudit({
          limit: 500,
          storyId: auditFilters?.storyId || '',
          operatorKey,
        }),
        getAgent4Phase16OperatorSecurityStatus(operatorKey),
        getAgent4Phase16OperatorSecurityEvents({
          limit: 100,
          operatorKey,
        }),
        getAgent4Phase17OperatorSecurityHistory({
          limit: 100,
          operatorKey,
        }),
        getAgent4Phase17OperatorSecuritySummary({
          windowLimit: 1000,
          operatorKey,
        }),
        getAgent4Phase19OpenSecurityIncidents({
          limit: 200,
          operatorKey,
        }),
        getAgent4Phase20SecurityReadiness(operatorKey),
      ])
      if (!mounted.current) return
      setQueueHealth(healthRes?.health || null)
      setQueueItems(Array.isArray(itemsRes?.items) ? itemsRes.items : [])
      setQueueAudit(Array.isArray(auditRes?.events) ? auditRes.events : [])
      setOperatorIdentity(whoamiRes?.identity || null)
      setAuditVerification(verifyRes?.verification || null)
      setSecurityStatus(securityStatusRes?.security || null)
      setSecurityEvents(Array.isArray(securityEventsRes?.events) ? securityEventsRes.events : [])
      setSecurityHistory(Array.isArray(securityHistoryRes?.events) ? securityHistoryRes.events : [])
      setSecuritySummary(securitySummaryRes?.summary || null)
      setOpenIncidents(Array.isArray(openIncidentsRes?.incidents) ? openIncidentsRes.incidents : [])
      setSecurityReadiness(readinessRes?.readiness || null)
      setLastUpdatedAt(new Date().toISOString())
    } catch (e) {
      if (!mounted.current) return
      setError(e?.message || 'Failed to load queue operations data')
    } finally {
      if (mounted.current) {
        setLoading(false)
      }
    }
  }, [auditFilters?.stage, auditFilters?.status, auditFilters?.storyId, limit, operatorKey])

  useEffect(() => {
    mounted.current = true
    refresh().catch(() => {})

    const id = setInterval(() => {
      refresh().catch(() => {})
    }, Math.max(1000, Number(pollMs) || 7000))

    return () => {
      mounted.current = false
      clearInterval(id)
    }
  }, [pollMs, refresh])

  const cancelQueued = useCallback(async (executionRunId, canceledBy = 'queue-ops-panel') => {
    await cancelAgent4Phase11QueueItemWithKey(executionRunId, { canceledBy, operatorKey })
    await refresh()
  }, [operatorKey, refresh])

  const expirePending = useCallback(async (ttlSeconds = 3600) => {
    const res = await expireAgent4Phase12PendingWithKey(ttlSeconds, operatorKey)
    await refresh()
    return res
  }, [operatorKey, refresh])

  const triggerSecurityAlertTest = useCallback(async (source = 'queue-ops-ui') => {
    const res = await testAgent4Phase17OperatorAlert({ source, operatorKey })
    await refresh()
    return res
  }, [operatorKey, refresh])

  const acknowledgeSecurityIncident = useCallback(async (incidentId, ackedBy = 'queue-ops-ui') => {
    const res = await ackAgent4Phase19SecurityIncident(incidentId, { ackedBy, operatorKey })
    await refresh()
    return res
  }, [operatorKey, refresh])

  const resolveSecurityIncident = useCallback(
    async (incidentId, { resolvedBy = 'queue-ops-ui', resolutionNote = '' } = {}) => {
      const res = await resolveAgent4Phase19SecurityIncident(incidentId, {
        resolvedBy,
        resolutionNote,
        operatorKey,
      })
      await refresh()
      return res
    },
    [operatorKey, refresh]
  )

  const exportSecurityData = useCallback(
    async ({ limit = 1000, state = '' } = {}) => {
      return exportAgent4Phase20SecurityData({ limit, state, operatorKey })
    },
    [operatorKey]
  )

  return {
    loading,
    error,
    queueHealth,
    queueItems,
    queueAudit,
    operatorIdentity,
    auditVerification,
    securityStatus,
    securityEvents,
    securityHistory,
    securitySummary,
    openIncidents,
    securityReadiness,
    lastUpdatedAt,
    refresh,
    cancelQueued,
    expirePending,
    triggerSecurityAlertTest,
    acknowledgeSecurityIncident,
    resolveSecurityIncident,
    exportSecurityData,
  }
}
