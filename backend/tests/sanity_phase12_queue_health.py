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


def _seed_queued_execution(*, make_old: bool) -> str:
    execution_run_id = f"phase12-exec-{uuid.uuid4().hex[:8]}"
    store.create_execution_run(
        execution_run_id=execution_run_id,
        source_agent4_run_id=f"phase12-agent4-{uuid.uuid4().hex[:8]}",
        backlog_item_id=f"phase12-story-{uuid.uuid4().hex[:8]}",
        trace_id=f"phase12-trace-{uuid.uuid4().hex[:8]}",
        state='queued',
        stage='phase10_execution_queued',
        request_payload={'started_by': 'sanity-phase12'},
        runtime_policy={'worker_count': 1},
        max_attempts=1,
    )

    if make_old:
        with store._lock, store._conn() as conn:  # pylint: disable=protected-access
            conn.execute(
                """
                UPDATE execution_runs
                SET created_at = datetime('now', '-2 hours'),
                    updated_at = datetime('now', '-2 hours')
                WHERE execution_run_id = ?
                """,
                (execution_run_id,),
            )
            conn.commit()

    return execution_run_id


def main() -> None:
    client = TestClient(app)
    auth_headers = {'X-Operator-Key': config.OPERATOR_API_KEY} if config.OPERATOR_REQUIRE_API_KEY else {}

    old_queued = _seed_queued_execution(make_old=True)
    fresh_queued = _seed_queued_execution(make_old=False)

    health_resp = client.get('/agent4/phase12/queue/health?window_limit=500')
    assert health_resp.status_code == 200, health_resp.text
    health = (health_resp.json() or {}).get('health') or {}

    assert isinstance(health.get('saturation'), (int, float)), health
    assert isinstance((health.get('in_flight') or {}).get('queued'), int), health
    assert isinstance(health.get('oldest_pending_age_seconds'), int), health
    totals = health.get('queue_totals') or {}
    assert isinstance(totals.get('enqueued'), int), totals
    assert isinstance(totals.get('timed_out'), int), totals

    expire_resp = client.post('/agent4/phase12/queue/expire-pending?ttl_seconds=120', headers=auth_headers)
    assert expire_resp.status_code == 200, expire_resp.text
    expiration = (expire_resp.json() or {}).get('expiration') or {}
    expired_ids = set(expiration.get('expired_execution_run_ids') or [])

    assert old_queued in expired_ids, expiration
    assert fresh_queued not in expired_ids, expiration

    old_snapshot = store.get_execution_run(old_queued) or {}
    fresh_snapshot = store.get_execution_run(fresh_queued) or {}

    assert old_snapshot.get('state') == 'canceled', old_snapshot
    assert old_snapshot.get('last_error_code') == 'pending_ttl_expired', old_snapshot
    assert fresh_snapshot.get('state') == 'queued', fresh_snapshot

    print(
        {
            'saturation': health.get('saturation'),
            'oldest_pending_age_seconds': health.get('oldest_pending_age_seconds'),
            'expired_count': expiration.get('expired_count'),
            'expired_old_queued': old_queued,
            'fresh_queued_state': fresh_snapshot.get('state'),
        }
    )


if __name__ == '__main__':
    main()
