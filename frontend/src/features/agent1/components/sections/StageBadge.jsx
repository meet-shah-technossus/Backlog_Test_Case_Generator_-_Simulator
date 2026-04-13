export default function StageBadge({ state }) {
  const color =
    state === 'handoff_emitted' ? 'agent1-stage-handoff' :
    state === 'failed' ? 'agent1-stage-failed' :
    state?.includes('review') ? 'agent1-stage-review' :
    'agent1-stage-default'

  return <span className={`agent1-stage-badge ${color}`}>{state || 'not_started'}</span>
}
