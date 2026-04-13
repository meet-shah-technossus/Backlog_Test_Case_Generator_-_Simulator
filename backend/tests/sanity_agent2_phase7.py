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
        trace_id='trace-phase7-001',
        state='handoff_pending',
        source_type='sample_db',
        source_ref='sanity_agent2_phase7',
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
                    'title': 'Profile save works',
                    'expected_result': 'Saved',
                    'test_type': 'positive',
                }
            ],
        },
    )


def main() -> None:
    client = TestClient(app)

    seed = uuid4().hex[:8]
    story_id = f'story_phase7_{seed}'
    agent1_run_id = f'agent1-phase7-run-{seed}'
    seed_agent1(agent1_run_id, story_id)

    handoff = client.post(f'/agent1/runs/{agent1_run_id}/handoff')
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
                    {'number': 2, 'action': 'Update field'},
                    {'number': 3, 'action': 'Save'},
                    {'number': 4, 'action': 'Verify success'},
                ],
            }
        ]
    }

    generate = None
    reject = None
    retry = None
    timeline = None
    runs = None
    counters = None
    if run_id:
        with patch.object(OpenAIClient, 'generate', new=AsyncMock(return_value=str(llm_response).replace("'", '"'))):
            generate = client.post(f'/agent2/runs/{run_id}/generate', json={})

        reject = client.post(
            f'/agent2/runs/{run_id}/review',
            json={
                'decision': 'reject',
                'reviewer_id': 'qa',
                'reason_code': 'incorrect_steps',
                'edited_payload': None,
            },
        )

        retry = client.post(
            f'/agent2/runs/{run_id}/review',
            json={
                'decision': 'retry',
                'reviewer_id': 'qa',
                'reason_code': 'llm_quality_low',
                'edited_payload': None,
            },
        )

        timeline = client.get(f'/agent2/runs/{run_id}/timeline?order=asc')

    runs = client.get(f'/agent2/runs?backlog_item_id={story_id}&limit=20')
    counters = client.get(f'/agent2/observability/counters?backlog_item_id={story_id}')

    timeline_events = timeline.json().get('events', []) if timeline and timeline.status_code == 200 else []
    is_ordered = True
    if len(timeline_events) >= 2:
        ids = [e.get('id', 0) for e in timeline_events]
        is_ordered = ids == sorted(ids)

    print(
        {
            'agent1_handoff_status': handoff.status_code,
            'consume_status': consume.status_code,
            'create_run_status': created.status_code if created is not None else None,
            'generate_status': generate.status_code if generate is not None else None,
            'reject_status': reject.status_code if reject is not None else None,
            'retry_status': retry.status_code if retry is not None else None,
            'list_runs_status': runs.status_code if runs is not None else None,
            'timeline_status': timeline.status_code if timeline is not None else None,
            'timeline_ordered': is_ordered,
            'counters_status': counters.status_code if counters is not None else None,
            'counters': counters.json().get('counters') if counters is not None and counters.status_code == 200 else None,
        }
    )


if __name__ == '__main__':
    main()
