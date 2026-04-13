from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.store import store
from app.main import app


def main() -> None:
    client = TestClient(app)

    seed = uuid4().hex[:8]
    story_id = f'story_agent2_approved_{seed}'
    agent1_run_id = f'agent1-approved-{seed}'

    store.upsert_agent1_run(
        run_id=agent1_run_id,
        backlog_item_id=story_id,
        trace_id=f'trace-{seed}',
        state='handoff_pending',
        source_type='sample_db',
        source_ref='sanity_agent2_approved_intake',
    )
    store.add_agent1_artifact(
        run_id=agent1_run_id,
        backlog_item_id=story_id,
        artifact_version=1,
        artifact={
            'backlog_item_id': story_id,
            'test_cases': [
                {
                    'id': 'TC001',
                    'title': 'Approved input test case',
                    'expected_result': 'Agent2 can consume automatically',
                    'test_type': 'positive',
                }
            ],
        },
    )

    review = client.post(
        f'/agent1/runs/{agent1_run_id}/review',
        json={
            'decision': 'approve',
            'reviewer_id': 'qa',
            'reason_code': None,
            'edited_payload': None,
        },
    )
    handoff = client.post(f'/agent1/runs/{agent1_run_id}/handoff')

    approved = client.get(f'/agent2/agent1/approved-runs?backlog_item_id={story_id}&limit=20')
    start = client.post(f'/agent2/agent1-runs/{agent1_run_id}/start')

    start_payload = start.json() if start.status_code == 200 else {}
    snapshot = start_payload.get('snapshot') or {}

    print(
        {
            'agent1_review_status': review.status_code,
            'agent1_handoff_status': handoff.status_code,
            'approved_list_status': approved.status_code,
            'approved_count': len((approved.json() if approved.status_code == 200 else {}).get('runs') or []),
            'start_status': start.status_code,
            'agent2_run_id': (snapshot.get('run') or {}).get('run_id'),
            'agent2_state': (snapshot.get('run') or {}).get('state'),
        }
    )


if __name__ == '__main__':
    main()
