from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.openai_client import OpenAIClient
from app.infrastructure.store import store
from app.main import app


def seed_agent1(run_id: str, story_id: str) -> None:
    store.upsert_agent1_run(
        run_id=run_id,
        backlog_item_id=story_id,
        trace_id='trace-phase8-001',
        state='handoff_pending',
        source_type='sample_db',
        source_ref='sanity_agent2_phase8',
    )
    store.add_agent1_artifact(
        run_id=run_id,
        backlog_item_id=story_id,
        artifact_version=1,
        artifact={
            'backlog_item_id': story_id,
            'test_cases': [
                {
                    'id': 'TC001',
                    'title': 'Update succeeds',
                    'expected_result': 'Success',
                    'test_type': 'positive',
                }
            ],
        },
    )


def main() -> None:
    client = TestClient(app)

    seed = uuid4().hex[:8]
    story_id = f'story_phase8_{seed}'
    agent1_run_id = f'agent1-phase8-run-{seed}'
    seed_agent1(agent1_run_id, story_id)

    client.post(f'/agent1/runs/{agent1_run_id}/handoff')
    consume = client.post(f'/agent2/agent1-runs/{agent1_run_id}/consume')
    message_id = consume.json().get('inbox', {}).get('message_id') if consume.status_code == 200 else None
    created = client.post(f'/agent2/inbox/{message_id}/runs') if message_id else None
    run_id = created.json().get('run', {}).get('run_id') if created is not None and created.status_code == 200 else None

    llm_response = {
        'test_cases': [
            {
                'id': 'TC001',
                'steps': [
                    {'number': 1, 'action': 'Open page'},
                    {'number': 2, 'action': 'Edit'},
                    {'number': 3, 'action': 'Save'},
                    {'number': 4, 'action': 'Verify saved state'},
                ],
            }
        ]
    }

    generate = None
    generate_invalid_state = None
    retry1 = None
    retry2 = None
    retry3 = None
    snapshot = None
    if run_id:
        with patch.object(OpenAIClient, 'generate', new=AsyncMock(return_value=str(llm_response).replace("'", '"'))):
            generate = client.post(f'/agent2/runs/{run_id}/generate', json={})

        generate_invalid_state = client.post(f'/agent2/runs/{run_id}/generate', json={})

        retry1 = client.post(
            f'/agent2/runs/{run_id}/review',
            json={
                'decision': 'retry',
                'reviewer_id': 'qa',
                'reason_code': 'llm_quality_low',
                'edited_payload': None,
            },
        )
        retry2 = client.post(
            f'/agent2/runs/{run_id}/review',
            json={
                'decision': 'retry',
                'reviewer_id': 'qa',
                'reason_code': 'llm_quality_low',
                'edited_payload': None,
            },
        )
        retry3 = client.post(
            f'/agent2/runs/{run_id}/review',
            json={
                'decision': 'retry',
                'reviewer_id': 'qa',
                'reason_code': 'llm_quality_low',
                'edited_payload': None,
            },
        )
        snapshot = client.get(f'/agent2/runs/{run_id}')

    payload = snapshot.json() if snapshot is not None and snapshot.status_code == 200 else {}

    print(
        {
            'consume_status': consume.status_code,
            'create_run_status': created.status_code if created is not None else None,
            'generate_status': generate.status_code if generate is not None else None,
            'generate_invalid_state_status': generate_invalid_state.status_code if generate_invalid_state is not None else None,
            'retry1_status': retry1.status_code if retry1 is not None else None,
            'retry2_status': retry2.status_code if retry2 is not None else None,
            'retry3_status': retry3.status_code if retry3 is not None else None,
            'snapshot_status': snapshot.status_code if snapshot is not None else None,
            'final_state': payload.get('run', {}).get('state'),
            'last_error_code': payload.get('run', {}).get('last_error_code'),
        }
    )


if __name__ == '__main__':
    main()
