import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'

export default function TimelinePanel({ timeline }) {
  return (
    <div className="agent1-card">
      <div className="agent1-section-title">Timeline</div>
      <div className="agent1-timeline">
        {timeline.length === 0 && <div className="agent1-muted">No timeline events yet</div>}
        {timeline.map((evt) => (
          <div key={evt.id} className="agent1-timeline-row">
            {evt.action?.includes('failed')
              ? <XCircle size={12} className="text-red-400 mt-0.5" />
              : evt.action?.includes('completed') || evt.action?.includes('approved') || evt.action?.includes('emitted')
                ? <CheckCircle2 size={12} className="text-teal-400 mt-0.5" />
                : evt.action?.includes('started')
                  ? <Loader2 size={12} className="text-blue-400 mt-0.5 animate-spin" />
                  : <Circle size={12} className="text-white/30 mt-0.5" />}
            <div>
              <div className="text-white/70">{evt.stage} - {evt.action}</div>
              <div className="agent1-small text-white/35">{evt.created_at}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
