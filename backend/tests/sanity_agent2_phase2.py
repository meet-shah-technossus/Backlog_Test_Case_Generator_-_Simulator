from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


def main() -> None:
    client = TestClient(app)

    payload = {
        "message_id": "phase2-msg-001",
        "run_id": "agent1-run-001",
        "trace_id": "trace-phase2-001",
        "from_agent": "agent_1",
        "to_agent": "agent_2",
        "task_type": "generate_steps",
        "contract_version": "v1",
        "payload": {"backlog_item_id": "story_site_001", "artifact_version": 1},
    }

    c1 = client.post('/agent2/inbox/consume', json=payload)
    c2 = client.post('/agent2/inbox/consume', json=payload)

    r1 = client.post('/agent2/inbox/phase2-msg-001/runs')
    r2 = client.post('/agent2/inbox/phase2-msg-001/runs')

    run_id = r1.json().get('run', {}).get('run_id')
    snap = client.get(f'/agent2/runs/{run_id}') if run_id else None

    print({
        "consume_first_status": c1.status_code,
        "consume_first_created": c1.json().get('created') if c1.status_code == 200 else None,
        "consume_second_status": c2.status_code,
        "consume_second_created": c2.json().get('created') if c2.status_code == 200 else None,
        "create_run_first_status": r1.status_code,
        "create_run_first_created": r1.json().get('created') if r1.status_code == 200 else None,
        "create_run_second_status": r2.status_code,
        "create_run_second_created": r2.json().get('created') if r2.status_code == 200 else None,
        "run_id": run_id,
        "snapshot_status": snap.status_code if snap is not None else None,
        "snapshot_state": snap.json().get('run', {}).get('state') if snap is not None and snap.status_code == 200 else None,
    })


if __name__ == '__main__':
    main()
