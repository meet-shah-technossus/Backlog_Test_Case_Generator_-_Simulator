from __future__ import annotations

import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.core import config
from app.infrastructure.store import store


def _seed_execution(*, state: str) -> str:
    execution_run_id = f"phase11-exec-{state}-{uuid.uuid4().hex[:8]}"
    store.create_execution_run(
        execution_run_id=execution_run_id,
        source_agent4_run_id=f"phase11-agent4-{uuid.uuid4().hex[:8]}",
        backlog_item_id=f"phase11-story-{uuid.uuid4().hex[:8]}",
        trace_id=f"phase11-trace-{uuid.uuid4().hex[:8]}",
        state='queued',
        stage='phase10_execution_queued',
        request_payload={'started_by': 'sanity-phase11'},
        runtime_policy={'worker_count': 1},
        max_attempts=1,
    )
    if state == 'running':
        store.mark_execution_run_running(execution_run_id=execution_run_id, stage='phase10_execution_running')
    return execution_run_id


def main() -> None:
    client = TestClient(app)
    auth_headers = {'X-Operator-Key': config.OPERATOR_API_KEY} if config.OPERATOR_REQUIRE_API_KEY else {}

    queued_id = _seed_execution(state='queued')
    running_id = _seed_execution(state='running')

    profile = client.get('/agent4/phase11/queue/profile')
    assert profile.status_code == 200, profile.text
    profile_payload = profile.json()
    assert profile_payload.get('phase') == 'phase11', profile_payload
    assert isinstance(profile_payload.get('limits'), dict), profile_payload

    snapshot = client.get('/agent4/phase11/queue/snapshot?window_limit=200')
    assert snapshot.status_code == 200, snapshot.text
    snapshot_payload = snapshot.json().get('snapshot') or {}
    counts = snapshot_payload.get('counts') or {}
    assert isinstance(counts.get('queued'), int), snapshot_payload
    assert isinstance(counts.get('running'), int), snapshot_payload

    items = client.get('/agent4/phase11/queue/items?limit=50')
    assert items.status_code == 200, items.text
    item_payload = items.json()
    rows = item_payload.get('items') or []
    row_ids = {row.get('execution_run_id') for row in rows if isinstance(row, dict)}
    assert queued_id in row_ids, row_ids
    assert running_id in row_ids, row_ids

    cancel_queued = client.delete(
        f'/agent4/phase11/queue/{queued_id}?canceled_by=sanity-phase11',
        headers=auth_headers,
    )
    assert cancel_queued.status_code == 200, cancel_queued.text
    cancelled_execution = (cancel_queued.json() or {}).get('execution') or {}
    assert cancelled_execution.get('state') == 'canceled', cancelled_execution

    cancel_running = client.delete(
        f'/agent4/phase11/queue/{running_id}?canceled_by=sanity-phase11',
        headers=auth_headers,
    )
    assert cancel_running.status_code == 409, cancel_running.text

    print(
        {
            'profile_phase': profile_payload.get('phase'),
            'queued_count': counts.get('queued'),
            'running_count': counts.get('running'),
            'cancelled_queued': queued_id,
            'running_cancel_status': cancel_running.status_code,
        }
    )


if __name__ == '__main__':
    main()
