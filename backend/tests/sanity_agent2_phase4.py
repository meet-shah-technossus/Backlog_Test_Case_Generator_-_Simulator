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
        backlog_item_id='story_phase4_001',
        artifact_version=1,
        artifact={
            'backlog_item_id': 'story_phase4_001',
            'test_cases': [
                {
                    'id': 'TC001',
                    'title': 'User can save profile with valid inputs',
                    'expected_result': 'Profile is saved',
                    'test_type': 'positive',
                }
            ],
        },
    )


def main() -> None:
    client = TestClient(app)

    message_id = 'phase4-msg-001'
    agent1_run_id = 'agent1-phase4-run-001'

    seed_agent1_artifact(agent1_run_id)

    consume_payload = {
        'message_id': message_id,
        'run_id': agent1_run_id,
        'trace_id': 'trace-phase4-001',
        'from_agent': 'agent_1',
        'to_agent': 'agent_2',
        'task_type': 'generate_steps',
        'contract_version': 'v1',
        'payload': {'backlog_item_id': 'story_phase4_001', 'artifact_version': 1},
    }

    client.post('/agent2/inbox/consume', json=consume_payload)
    created = client.post(f'/agent2/inbox/{message_id}/runs')
    run_id = created.json().get('run', {}).get('run_id')

    llm_response = {
        'test_cases': [
            {
                'id': 'TC001',
                'steps': [
                    {'number': 1, 'action': 'Open the profile page'},
                    {'number': 2, 'action': 'Enter valid values in all fields'},
                    {'number': 3, 'action': 'Click Save'},
                    {'number': 4, 'action': 'Verify success confirmation is visible'},
                ],
            }
        ]
    }

    with patch.object(OpenAIClient, 'generate', new=AsyncMock(return_value=str(llm_response).replace("'", '"'))):
        generated = client.post(f'/agent2/runs/{run_id}/generate', json={})

    reject_missing_reason = client.post(
        f'/agent2/runs/{run_id}/review',
        json={
            'decision': 'reject',
            'reviewer_id': 'human_reviewer',
            'reason_code': None,
            'edited_payload': None,
        },
    )

    edited_payload = {
        'generated_steps': {
            'test_cases': [
                {
                    'id': 'TC001',
                    'steps': [
                        {'number': 1, 'action': 'Open the profile page'},
                        {'number': 2, 'action': 'Fill in valid profile values'},
                        {'number': 3, 'action': 'Click Save'},
                        {'number': 4, 'action': 'Confirm success toast appears'},
                        {'number': 5, 'action': 'Verify data persists after refresh'},
                    ],
                }
            ]
        }
    }

    edit_approve = client.post(
        f'/agent2/runs/{run_id}/review',
        json={
            'decision': 'edit_approve',
            'reviewer_id': 'human_reviewer',
            'reason_code': None,
            'edited_payload': edited_payload,
        },
    )

    review_diff = client.get(f'/agent2/runs/{run_id}/review-diff')
    reason_codes = client.get('/agent2/review/reason-codes')
    snapshot = client.get(f'/agent2/runs/{run_id}')

    payload = snapshot.json() if snapshot.status_code == 200 else {}

    print(
        {
            'generate_status': generated.status_code,
            'reject_missing_reason_status': reject_missing_reason.status_code,
            'edit_approve_status': edit_approve.status_code,
            'review_diff_status': review_diff.status_code,
            'reason_codes_status': reason_codes.status_code,
            'snapshot_status': snapshot.status_code,
            'state': payload.get('run', {}).get('state'),
            'reviews_count': len(payload.get('reviews') or []),
            'artifact_count': len(payload.get('artifacts') or []),
            'has_review_diff': bool(payload.get('review_diff', {}).get('has_diff')),
        }
    )


if __name__ == '__main__':
    main()
