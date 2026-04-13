from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.store import store
from app.main import app


def seed_agent1_artifact(agent1_run_id: str) -> None:
    store.add_agent1_artifact(
        run_id=agent1_run_id,
        backlog_item_id='story_mcp_bridge_001',
        artifact_version=1,
        artifact={
            'backlog_item_id': 'story_mcp_bridge_001',
            'test_cases': [
                {
                    'id': 'TC001',
                    'title': 'Valid flow',
                    'expected_result': 'Success',
                    'test_type': 'positive',
                }
            ],
        },
    )


def main() -> None:
    client = TestClient(app)

    run_id = 'agent1-mcp-bridge-run-001'
    trace_id = 'trace-mcp-bridge-001'

    store.upsert_agent1_run(
        run_id=run_id,
        backlog_item_id='story_mcp_bridge_001',
        trace_id=trace_id,
        state='handoff_pending',
        source_type='sample_db',
        source_ref='sanity_agent2_mcp_handoff_bridge',
    )

    seed_agent1_artifact(run_id)

    handoff = client.post(f'/agent1/runs/{run_id}/handoff')

    consume_from_mcp = client.post(f'/agent2/agent1-runs/{run_id}/consume')
    create_agent2_run = None
    if consume_from_mcp.status_code == 200:
        message_id = consume_from_mcp.json().get('inbox', {}).get('message_id')
        if message_id:
            create_agent2_run = client.post(f'/agent2/inbox/{message_id}/runs')

    print(
        {
            'agent1_seeded_run_id': run_id,
            'agent1_handoff_status': handoff.status_code,
            'agent2_consume_from_mcp_status': consume_from_mcp.status_code,
            'agent2_consume_created': consume_from_mcp.json().get('created') if consume_from_mcp.status_code == 200 else None,
            'agent2_create_run_status': create_agent2_run.status_code if create_agent2_run is not None else None,
            'agent2_run_state': create_agent2_run.json().get('run', {}).get('state') if create_agent2_run is not None and create_agent2_run.status_code == 200 else None,
        }
    )


if __name__ == '__main__':
    main()
