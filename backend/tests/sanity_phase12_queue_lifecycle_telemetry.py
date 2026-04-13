from __future__ import annotations

import asyncio
import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.dependencies import get_container
from app.main import app
from app.infrastructure.store import store


def _seed_agent4_run(story_id: str) -> str:
    message_id = f"phase12-msg-{uuid.uuid4().hex[:8]}"
    source_agent3_run_id = f"phase12-agent3-{uuid.uuid4().hex[:8]}"
    trace_id = f"phase12-trace-{uuid.uuid4().hex[:8]}"
    run_id = f"phase12-agent4-{uuid.uuid4().hex[:8]}"

    store.upsert_agent4_inbox(
        message_id=message_id,
        source_agent3_run_id=source_agent3_run_id,
        trace_id=trace_id,
        contract_version='phase12-sanity',
        task_type='phase12-sanity',
        payload={'story_id': story_id, 'backlog_item_id': story_id},
        intake_status='accepted',
    )

    store.create_agent4_run_from_inbox(
        run_id=run_id,
        inbox_message_id=message_id,
        source_agent3_run_id=source_agent3_run_id,
        trace_id=trace_id,
        state='running',
        stage='phase7_handoff_accepted',
    )
    return run_id


def _set_queued_created_at(execution_run_id: str, offset_expression: str) -> None:
    with store._lock, store._conn() as conn:  # pylint: disable=protected-access
        conn.execute(
            """
            UPDATE execution_runs
            SET created_at = datetime('now', ?),
                updated_at = datetime('now', ?)
            WHERE execution_run_id = ?
            """,
            (offset_expression, offset_expression, execution_run_id),
        )
        conn.commit()


def main() -> None:
    client = TestClient(app)
    lifecycle = get_container().get_execution_lifecycle_service()

    story_id = f"phase12-story-{uuid.uuid4().hex[:8]}"
    agent4_run_id = _seed_agent4_run(story_id)

    queued_for_cancel = lifecycle.enqueue_execution(
        agent4_run_id=agent4_run_id,
        requested_by='phase12-sanity',
        reason='cancel-check',
    )
    lifecycle.cancel_execution(str(queued_for_cancel.get('execution_run_id') or ''), canceled_by='phase12-sanity')

    queued_for_run = lifecycle.enqueue_execution(
        agent4_run_id=agent4_run_id,
        requested_by='phase12-sanity',
        reason='run-check',
    )
    execution_run_id = str(queued_for_run.get('execution_run_id') or '')

    original_run_bundle = lifecycle._run_bundle  # pylint: disable=protected-access

    async def _fake_run_bundle(*, execution_run_id: str, started_by: str, on_event):  # noqa: ANN001
        _ = (execution_run_id, started_by, on_event)
        return {
            'failed_count': 0,
            'passed_count': 1,
            'script_count': 1,
            'summary': {'total': 1, 'passed': 1, 'failed': 0, 'skipped': 0, 'final_verdict': 'passed'},
            'per_script_status': [],
            'step_results': [],
        }

    try:
        lifecycle._run_bundle = _fake_run_bundle  # type: ignore[attr-defined]  # pylint: disable=protected-access
        asyncio.run(lifecycle.process_execution(execution_run_id, started_by='phase12-sanity'))
    finally:
        lifecycle._run_bundle = original_run_bundle  # type: ignore[attr-defined]  # pylint: disable=protected-access

    queued_for_expire = lifecycle.enqueue_execution(
        agent4_run_id=agent4_run_id,
        requested_by='phase12-sanity',
        reason='expire-check',
    )
    expire_id = str(queued_for_expire.get('execution_run_id') or '')
    _set_queued_created_at(expire_id, '-2 hours')
    lifecycle.expire_pending_executions(ttl_seconds=120)

    resp = client.get('/evaluation/queue-lifecycle?hours=48&bucket_minutes=60&limit=20000')
    assert resp.status_code == 200, resp.text
    payload = resp.json() or {}
    totals = payload.get('totals') or {}

    assert int(totals.get('queue.enqueue') or 0) >= 3, totals
    assert int(totals.get('queue.run_start') or 0) >= 1, totals
    assert int(totals.get('queue.run_end') or 0) >= 1, totals
    assert int(totals.get('queue.cancel') or 0) >= 1, totals
    assert int(totals.get('queue.expire') or 0) >= 1, totals

    print({'story_id': story_id, 'lifecycle_totals': totals})


if __name__ == '__main__':
    main()
