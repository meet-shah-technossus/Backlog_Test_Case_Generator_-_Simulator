import { useEffect, useMemo, useState } from 'react'
import { Activity, Gauge, ShieldCheck, TrendingUp, AlertTriangle, RefreshCw } from 'lucide-react'
import {
  cancelPhase11QueueItem,
  getEvaluationGlobal,
  getEvaluationQueueLifecycle,
  getEvaluationRollout,
  getEvaluationStory,
  getPhase11QueueItems,
  getPhase11QueueProfile,
  getPhase11QueueSnapshot,
} from '../api/evaluationApi'
import './evaluation.css'

const STORY_WINDOWS = [20, 50, 100, 200]
const GLOBAL_WINDOWS = [50, 100, 200, 300]

function pct(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '0.0%'
  return `${n.toFixed(1)}%`
}

function num(value) {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

function badgeClass(value, mode) {
  const v = num(value)
  if (mode === 'pass') {
    if (v >= 85) return 'evaluation-badge good'
    if (v >= 70) return 'evaluation-badge warn'
    return 'evaluation-badge bad'
  }
  if (mode === 'inverse') {
    if (v <= 15) return 'evaluation-badge good'
    if (v <= 25) return 'evaluation-badge warn'
    return 'evaluation-badge bad'
  }
  if (v <= 20) return 'evaluation-badge good'
  if (v <= 30) return 'evaluation-badge warn'
  return 'evaluation-badge bad'
}

function TrendSpark({ title, points, color = 'var(--accent-blue)' }) {
  const width = 260
  const height = 70
  const safe = Array.isArray(points) ? points.filter((p) => Number.isFinite(p.y)) : []
  const values = safe.map((p) => p.y)
  const min = values.length ? Math.min(...values) : 0
  const max = values.length ? Math.max(...values) : 100
  const spread = Math.max(max - min, 1)

  const polyline = safe
    .map((p, i) => {
      const x = (i / Math.max(safe.length - 1, 1)) * width
      const y = height - ((p.y - min) / spread) * height
      return `${x},${y}`
    })
    .join(' ')

  return (
    <div className="evaluation-chart-card">
      <div className="evaluation-chart-title">{title}</div>
      <svg viewBox={`0 0 ${width} ${height}`} className="evaluation-chart" preserveAspectRatio="none">
        <polyline points={polyline} fill="none" stroke={color} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <div className="evaluation-chart-labels">
        {safe.map((point) => (
          <span key={point.x}>{point.x}</span>
        ))}
      </div>
    </div>
  )
}

export default function EvaluationBoard({ story }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [storyEval, setStoryEval] = useState(null)
  const [globalEval, setGlobalEval] = useState(null)
  const [rolloutEval, setRolloutEval] = useState(null)
  const [storyTrends, setStoryTrends] = useState([])
  const [globalTrends, setGlobalTrends] = useState([])
  const [queueProfile, setQueueProfile] = useState(null)
  const [queueSnapshot, setQueueSnapshot] = useState(null)
  const [queueItems, setQueueItems] = useState([])
  const [queueLifecycle, setQueueLifecycle] = useState(null)

  const load = async () => {
    setLoading(true)
    setError('')
    try {
      const [globalBase, globalTrendRows, storyBase, storyRollout, storyTrendRows, queueLifecycleRes] = await Promise.all([
        getEvaluationGlobal(300),
        Promise.all(GLOBAL_WINDOWS.map((w) => getEvaluationGlobal(w))),
        story?.id ? getEvaluationStory(story.id, 100) : Promise.resolve(null),
        story?.id ? getEvaluationRollout(story.id, 100) : Promise.resolve(null),
        story?.id ? Promise.all(STORY_WINDOWS.map((w) => getEvaluationStory(story.id, w))) : Promise.resolve([]),
        getEvaluationQueueLifecycle({ storyId: null, hours: 24, bucketMinutes: 30, limit: 8000 }),
      ])

      const [profile, snapshot, items] = await Promise.all([
        getPhase11QueueProfile(),
        getPhase11QueueSnapshot(1000),
        getPhase11QueueItems(25),
      ])

      setGlobalEval(globalBase)
      setStoryEval(storyBase)
      setRolloutEval(storyRollout)

      setGlobalTrends(
        globalTrendRows.map((row, idx) => ({
          x: `N${GLOBAL_WINDOWS[idx]}`,
          y: num(row?.metrics?.pass_rate),
        }))
      )

      setStoryTrends(
        (storyTrendRows || []).map((row, idx) => ({
          x: `N${STORY_WINDOWS[idx]}`,
          y: num(row?.metrics?.pass_rate),
        }))
      )

      setQueueProfile(profile)
      setQueueSnapshot(snapshot?.snapshot || null)
      setQueueItems(Array.isArray(items?.items) ? items.items : [])
      setQueueLifecycle(queueLifecycleRes || null)
    } catch (e) {
      setError(e?.message || 'Failed to load evaluation dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load().catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [story?.id])

  const storyMetrics = storyEval?.metrics || {}
  const globalMetrics = globalEval?.metrics || {}

  const rolloutStatusClass = useMemo(() => {
    const status = String(rolloutEval?.status || '').toLowerCase()
    if (status === 'ready') return 'evaluation-rollout-status ready'
    if (status === 'needs_improvement') return 'evaluation-rollout-status warning'
    return 'evaluation-rollout-status'
  }, [rolloutEval?.status])

  const queuePressureClass = useMemo(() => {
    const pressure = String(queueSnapshot?.pressure || '').toLowerCase()
    if (pressure === 'high') return 'evaluation-badge bad'
    if (pressure === 'elevated') return 'evaluation-badge warn'
    return 'evaluation-badge good'
  }, [queueSnapshot?.pressure])

  const queueLifecyclePoints = useMemo(() => {
    const buckets = Array.isArray(queueLifecycle?.buckets) ? queueLifecycle.buckets : []
    const tail = buckets.slice(-12)
    const label = (bucketStart) => {
      const iso = String(bucketStart || '')
      const idx = iso.indexOf('T')
      if (idx < 0) return iso.slice(11, 16)
      return iso.slice(idx + 1, idx + 6)
    }

    const makeSeries = (stage) =>
      tail.map((bucket) => ({
        x: label(bucket?.bucket_start),
        y: num(bucket?.counts?.[stage]),
      }))

    return {
      enqueue: makeSeries('queue.enqueue'),
      runStart: makeSeries('queue.run_start'),
      runEnd: makeSeries('queue.run_end'),
      cancel: makeSeries('queue.cancel'),
      expire: makeSeries('queue.expire'),
    }
  }, [queueLifecycle])

  const cancelQueued = async (executionRunId) => {
    try {
      await cancelPhase11QueueItem(executionRunId, 'evaluation-dashboard')
      await load()
    } catch (e) {
      setError(e?.message || 'Failed to cancel queued execution')
    }
  }

  return (
    <div className="evaluation-board">
      <section className="evaluation-header">
        <div>
          <h3>Evaluation Dashboard</h3>
          <p>Trend analytics, rollout readiness, and threshold badges for current execution quality.</p>
        </div>
        <button className="evaluation-refresh" onClick={() => load()} disabled={loading}>
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </section>

      {error ? <div className="evaluation-error">{error}</div> : null}

      <section className="evaluation-grid">
        <div className="evaluation-card">
          <div className="evaluation-card-head"><Activity size={14} /> Story Pass Rate</div>
          <div className="evaluation-metric-row">
            <span className={badgeClass(storyMetrics.pass_rate, 'pass')}>{pct(storyMetrics.pass_rate)}</span>
            <span>{num(storyMetrics.run_count)} runs</span>
          </div>
        </div>

        <div className="evaluation-card">
          <div className="evaluation-card-head"><AlertTriangle size={14} /> Flake Rate</div>
          <div className="evaluation-metric-row">
            <span className={badgeClass(storyMetrics.flake_rate, 'inverse')}>{pct(storyMetrics.flake_rate)}</span>
            <span>{num(storyMetrics.failed_tests)} failed / {num(storyMetrics.total_tests)} tests</span>
          </div>
        </div>

        <div className="evaluation-card">
          <div className="evaluation-card-head"><Gauge size={14} /> Selector Mismatch</div>
          <div className="evaluation-metric-row">
            <span className={badgeClass(storyMetrics.selector_mismatch_rate, 'selector')}>{pct(storyMetrics.selector_mismatch_rate)}</span>
            <span>Threshold: ≤ 20%</span>
          </div>
        </div>

        <div className="evaluation-card">
          <div className="evaluation-card-head"><ShieldCheck size={14} /> Rollout Readiness</div>
          <div className="evaluation-metric-row">
            <span className={rolloutStatusClass}>{String(rolloutEval?.status || 'n/a')}</span>
            <span>Score {Number(rolloutEval?.score || 0).toFixed(2)}</span>
          </div>
        </div>
      </section>

      <section className="evaluation-charts">
        <TrendSpark title="Story Pass Rate Trend" points={storyTrends} color="var(--accent-blue)" />
        <TrendSpark title="Global Pass Rate Trend" points={globalTrends} color="var(--accent-teal)" />
      </section>

      <section className="evaluation-charts">
        <TrendSpark title="queue.enqueue (24h)" points={queueLifecyclePoints.enqueue} color="#2f80ed" />
        <TrendSpark title="queue.run_start (24h)" points={queueLifecyclePoints.runStart} color="#159e91" />
        <TrendSpark title="queue.run_end (24h)" points={queueLifecyclePoints.runEnd} color="#5f7cff" />
        <TrendSpark title="queue.cancel (24h)" points={queueLifecyclePoints.cancel} color="#c27d17" />
        <TrendSpark title="queue.expire (24h)" points={queueLifecyclePoints.expire} color="#c34141" />
      </section>

      <section className="evaluation-grid">
        <div className="evaluation-card wide">
          <div className="evaluation-card-head"><TrendingUp size={14} /> Story Metrics</div>
          <pre className="evaluation-json">{storyEval ? JSON.stringify(storyEval, null, 2) : 'Select a story to view story-level evaluation metrics.'}</pre>
        </div>
        <div className="evaluation-card wide">
          <div className="evaluation-card-head"><TrendingUp size={14} /> Global Metrics</div>
          <pre className="evaluation-json">{globalEval ? JSON.stringify(globalEval, null, 2) : 'No global metrics loaded yet.'}</pre>
        </div>
      </section>

      <section className="evaluation-card">
        <div className="evaluation-card-head"><ShieldCheck size={14} /> Phase 11 Queue Hardening</div>
        <div className="evaluation-metric-row">
          <span className={queuePressureClass}>pressure: {String(queueSnapshot?.pressure || 'n/a')}</span>
          <span>
            queue {num(queueSnapshot?.queue_size)} / {num(queueSnapshot?.max_queue_size)}
          </span>
        </div>
        <div className="evaluation-metric-row">
          <span>utilization</span>
          <span>{num(queueSnapshot?.queue_utilization_pct).toFixed(1)}%</span>
        </div>
        <div className="evaluation-metric-row">
          <span>dispatcher running</span>
          <span>{String(Boolean(queueSnapshot?.dispatcher?.running))}</span>
        </div>
        <pre className="evaluation-json">{queueProfile ? JSON.stringify(queueProfile, null, 2) : 'No queue profile loaded yet.'}</pre>
        <pre className="evaluation-json">{queueLifecycle ? JSON.stringify(queueLifecycle?.totals || {}, null, 2) : 'No queue lifecycle telemetry loaded yet.'}</pre>
        <div className="evaluation-queue-list">
          {queueItems.map((item) => (
            <div key={item.execution_run_id} className="evaluation-queue-item">
              <div>
                <strong>{item.execution_run_id}</strong>
                <div className="evaluation-queue-meta">{item.state} · {item.stage} · position {item.queue_position ?? '-'}</div>
              </div>
              <button
                className="evaluation-refresh"
                disabled={String(item.state || '').toLowerCase() !== 'queued'}
                onClick={() => cancelQueued(item.execution_run_id)}
              >
                cancel queued
              </button>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}
