from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.openai_client import OpenAIClient
from app.infrastructure.store import store
from app.main import app


def seed_agent1_artifact(agent1_run_id: str) -> None:
    store.add_agent1_artifact(
        run_id=agent1_run_id,
        backlog_item_id='story_phase5_001',
        artifact_version=1,
        artifact={
            'backlog_item_id': 'story_phase5_001',
            'test_cases': [
                {
                    'id': 'TC001',
                    'title': 'Profile update succeeds',
                    'expected_result': 'Data persists after save',
                    'test_type': 'positive',
                }
            ],
        },
    )


def main() -> None:
    client = TestClient(app)

    message_id = 'phase5-msg-001'
    agent1_run_id = 'agent1-phase5-run-001'

    seed_agent1_artifact(agent1_run_id)

    consume_payload = {
        'message_id': message_id,
        'run_id': agent1_run_id,
        'trace_id': 'trace-phase5-001',
        'from_agent': 'agent_1',
        'to_agent': 'agent_2',
        'task_type': 'generate_steps',
        'contract_version': 'v1',
        'payload': {'backlog_item_id': 'story_phase5_001', 'artifact_version': 1},
    }

    client.post('/agent2/inbox/consume', json=consume_payload)
    created = client.post(f'/agent2/inbox/{message_id}/runs')
    run_id = created.json().get('run', {}).get('run_id')

    llm_response = {
        'test_cases': [
            {
                'id': 'TC001',
                'steps': [
                    {'number': 1, 'action': 'Open profile page'},
                    {'number': 2, 'action': 'Edit profile values'},
                    {'number': 3, 'action': 'Click save'},
                    {'number': 4, 'action': 'Verify success indicator'},
                ],
            }
        ]
    }

    with patch.object(OpenAIClient, 'generate', new=AsyncMock(return_value=str(llm_response).replace("'", '"'))):
        client.post(f'/agent2/runs/{run_id}/generate', json={})

    client.post(
        f'/agent2/runs/{run_id}/review',
        json={
            'decision': 'approve',
            'reviewer_id': 'human_reviewer',
            'reason_code': None,
            'edited_payload': None,
        },
    )

    first_emit = client.post(f'/agent2/runs/{run_id}/handoff')
    second_emit = client.post(f'/agent2/runs/{run_id}/handoff')
    snapshot = client.get(f'/agent2/runs/{run_id}')

    payload = snapshot.json() if snapshot.status_code == 200 else {}
    handoffs = payload.get('handoffs') or []

    print(
        {
            'first_emit_status': first_emit.status_code,
            'first_emit_created': first_emit.json().get('created') if first_emit.status_code == 200 else None,
            'second_emit_status': second_emit.status_code,
            'second_emit_created': second_emit.json().get('created') if second_emit.status_code == 200 else None,
            'snapshot_status': snapshot.status_code,
            'state': payload.get('run', {}).get('state'),
            'handoff_count': len(handoffs),
            'delivery_status': handoffs[0].get('delivery_status') if handoffs else None,
            'timeline_events': len(payload.get('timeline') or []),
        }
    )


if __name__ == '__main__':
    main()
