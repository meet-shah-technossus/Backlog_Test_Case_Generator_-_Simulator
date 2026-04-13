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
        trace_id='trace-smoke-agent2-001',
        state='handoff_pending',
        source_type='sample_db',
        source_ref='smoke_agent2_api',
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
                    'title': 'Basic flow',
                    'expected_result': 'Pass',
                    'test_type': 'positive',
                }
            ],
        },
    )


def main() -> None:
    client = TestClient(app)

    seed = uuid4().hex[:8]
    story_id = f'story_smoke_agent2_{seed}'
    agent1_run_id = f'agent1-smoke-agent2-run-{seed}'
    seed_agent1(agent1_run_id, story_id)

    handoff = client.post(f'/agent1/runs/{agent1_run_id}/handoff')
    consume = client.post(f'/agent2/agent1-runs/{agent1_run_id}/consume')
    message_id = consume.json().get('inbox', {}).get('message_id') if consume.status_code == 200 else None
    create_run = client.post(f'/agent2/inbox/{message_id}/runs') if message_id else None
    run_id = create_run.json().get('run', {}).get('run_id') if create_run is not None and create_run.status_code == 200 else None

    llm_response = {
        'test_cases': [
            {
                'id': 'TC001',
                'steps': [
                    {'number': 1, 'action': 'Open page'},
                    {'number': 2, 'action': 'Do action'},
                    {'number': 3, 'action': 'Submit changes'},
                    {'number': 4, 'action': 'Verify expected result'},
                ],
            }
        ]
    }

    generate = None
    review = None
    emit = None
    snapshot = None
    if run_id:
        with patch.object(OpenAIClient, 'generate', new=AsyncMock(return_value=str(llm_response).replace("'", '"'))):
            generate = client.post(f'/agent2/runs/{run_id}/generate', json={})

        review = client.post(
            f'/agent2/runs/{run_id}/review',
            json={
                'decision': 'approve',
                'reviewer_id': 'smoke_test',
                'reason_code': None,
                'edited_payload': None,
            },
        )

        emit = client.post(f'/agent2/runs/{run_id}/handoff')
        snapshot = client.get(f'/agent2/runs/{run_id}')

    payload = snapshot.json() if snapshot is not None and snapshot.status_code == 200 else {}

    print(
        {
            'agent1_handoff_status': handoff.status_code,
            'agent2_consume_status': consume.status_code,
            'agent2_create_run_status': create_run.status_code if create_run is not None else None,
            'agent2_generate_status': generate.status_code if generate is not None else None,
            'agent2_review_status': review.status_code if review is not None else None,
            'agent2_handoff_status': emit.status_code if emit is not None else None,
            'final_snapshot_status': snapshot.status_code if snapshot is not None else None,
            'final_state': payload.get('run', {}).get('state'),
            'handoff_count': len(payload.get('handoffs') or []),
        }
    )


if __name__ == '__main__':
    main()
