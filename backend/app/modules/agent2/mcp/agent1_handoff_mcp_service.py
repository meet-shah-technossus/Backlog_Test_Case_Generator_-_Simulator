from __future__ import annotations

from app.modules.agent1.mcp.run_store_mcp_service import Agent1RunStoreMCPService
from app.modules.agent2.contracts.models import Agent2HandoffEnvelope


class Agent1HandoffMCPService:
    """MCP bridge that translates persisted Agent1 handoffs into Agent2 envelope contracts."""

    def __init__(self, agent1_run_mcp_store: Agent1RunStoreMCPService | None = None):
        self._agent1_run_mcp_store = agent1_run_mcp_store or Agent1RunStoreMCPService()

    def list_approved_runs_for_backlog_item(
        self,
        backlog_item_id: str,
        limit: int = 50,
        *,
        handoff_only: bool = True,
    ) -> list[dict]:
        rows = self._agent1_run_mcp_store.list_runs_for_backlog_item(backlog_item_id, limit=limit)
        approved_states = {'handoff_emitted'} if handoff_only else {'review_approved', 'handoff_pending', 'handoff_emitted'}
        approved = []
        for row in rows:
            if row.get('state') not in approved_states:
                continue
            run_id = row['run_id']
            handoffs = self._agent1_run_mcp_store.list_handoffs(run_id)
            reviews = self._agent1_run_mcp_store.list_reviews(run_id)
            approved.append(
                {
                    'run_id': run_id,
                    'trace_id': row.get('trace_id'),
                    'state': row.get('state'),
                    'updated_at': row.get('updated_at'),
                    'has_handoff': bool(handoffs),
                    'handoff_message_id': handoffs[0].get('message_id') if handoffs else None,
                    'latest_review_decision': reviews[0].get('decision') if reviews else None,
                }
            )
        return approved

    def read_latest_agent1_artifact(self, agent1_run_id: str) -> dict | None:
        return self._agent1_run_mcp_store.get_latest_artifact(agent1_run_id)

    def read_latest_agent1_envelope(self, agent1_run_id: str) -> Agent2HandoffEnvelope:
        handoffs = self._agent1_run_mcp_store.list_handoffs(agent1_run_id)
        handoff = handoffs[0] if handoffs else None
        if handoff is not None:
            payload = handoff.get('payload') or {}
            return Agent2HandoffEnvelope(
                message_id=handoff['message_id'],
                run_id=payload.get('run_id') or agent1_run_id,
                trace_id=payload.get('trace_id') or '',
                from_agent='agent_1',
                to_agent='agent_2',
                task_type='generate_steps',
                contract_version=handoff.get('contract_version') or 'v1',
                payload=payload,
            )

        run = self._agent1_run_mcp_store.get_run(agent1_run_id)
        if run is None:
            raise ValueError(f"Agent1 run '{agent1_run_id}' not found")
        if run.get('state') not in {'review_approved', 'handoff_pending', 'handoff_emitted'}:
            raise ValueError(
                f"Agent1 run '{agent1_run_id}' is not approved for Agent2 intake"
            )

        latest_artifact = self._agent1_run_mcp_store.get_latest_artifact(agent1_run_id)
        backlog_item_id = (
            (latest_artifact or {}).get('artifact', {}).get('backlog_item_id')
            or run.get('backlog_item_id')
        )
        payload = {
            'run_id': agent1_run_id,
            'backlog_item_id': backlog_item_id,
            'trace_id': run.get('trace_id') or '',
            'task': 'generate_steps',
            'source': 'auto_from_approved_run',
        }

        return Agent2HandoffEnvelope(
            message_id=f"agent1-{agent1_run_id}-auto-v1",
            run_id=agent1_run_id,
            trace_id=run.get('trace_id') or '',
            from_agent='agent_1',
            to_agent='agent_2',
            task_type='generate_steps',
            contract_version='v1',
            payload=payload,
        )
