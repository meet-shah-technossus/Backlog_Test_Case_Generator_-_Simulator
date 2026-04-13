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
        backlog_item_id='story_phase3_001',
        artifact_version=1,
        artifact={
            'backlog_item_id': 'story_phase3_001',
            'test_cases': [
                {
                    'id': 'TC001',
                    'title': 'User can submit valid profile form',
                    'expected_result': 'Profile is saved successfully',
                    'test_type': 'positive',
                },
                {
                    'id': 'TC002',
                    'title': 'Email validation rejects invalid format',
                    'expected_result': 'Validation error is shown',
                    'test_type': 'negative',
                },
            ],
        },
    )


def main() -> None:
    client = TestClient(app)

    message_id = 'phase3-msg-001'
    agent1_run_id = 'agent1-phase3-run-001'

    seed_agent1_artifact(agent1_run_id)

    consume_payload = {
        'message_id': message_id,
        'run_id': agent1_run_id,
        'trace_id': 'trace-phase3-001',
        'from_agent': 'agent_1',
        'to_agent': 'agent_2',
        'task_type': 'generate_steps',
        'contract_version': 'v1',
        'payload': {'backlog_item_id': 'story_phase3_001', 'artifact_version': 1},
    }

    c = client.post('/agent2/inbox/consume', json=consume_payload)
    r = client.post(f'/agent2/inbox/{message_id}/runs')
    run_id = r.json().get('run', {}).get('run_id')

    llm_response = {
        'test_cases': [
            {
                'id': 'TC001',
                'steps': [
                    {'number': 1, 'action': 'Open the profile form screen'},
                    {'number': 2, 'action': 'Enter all required fields with valid values'},
                    {'number': 3, 'action': 'Click the Save button'},
                    {'number': 4, 'action': 'Verify the success toast is displayed'},
                ],
            },
            {
                'id': 'TC002',
                'steps': [
                    {'number': 1, 'action': 'Open the profile form screen'},
                    {'number': 2, 'action': 'Enter an invalid email value'},
                    {'number': 3, 'action': 'Click the Save button'},
                    {'number': 4, 'action': 'Verify email format validation message is shown'},
                ],
            },
        ]
    }

    with patch.object(OpenAIClient, 'generate', new=AsyncMock(return_value=str(llm_response).replace("'", '"'))):
        g = client.post(f'/agent2/runs/{run_id}/generate', json={})

    snap = client.get(f'/agent2/runs/{run_id}')

    print(
        {
            'consume_status': c.status_code,
            'create_run_status': r.status_code,
            'generate_status': g.status_code,
            'snapshot_status': snap.status_code,
            'state': snap.json().get('run', {}).get('state') if snap.status_code == 200 else None,
            'has_latest_artifact': bool(snap.json().get('latest_artifact')) if snap.status_code == 200 else None,
            'artifact_count': len(snap.json().get('artifacts') or []) if snap.status_code == 200 else None,
            'timeline_events': len(snap.json().get('timeline') or []) if snap.status_code == 200 else None,
        }
    )


if __name__ == '__main__':
    main()
