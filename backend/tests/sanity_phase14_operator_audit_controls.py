from __future__ import annotations

import sys
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.infrastructure.store import store
from app.core import config
from app.api.security import operator_auth


def _seed_queue_audit_events(story_id: str) -> None:
    trace_id = f"phase14-trace-{uuid.uuid4().hex[:8]}"
    run_id = f"phase14-run-{uuid.uuid4().hex[:8]}"

    store.log_event(
        trace_id=trace_id,
        run_id=run_id,
        story_id=story_id,
        stage='queue.enqueue',
        status='queued',
        metadata={'source': 'phase14-sanity'},
    )
    store.log_event(
        trace_id=trace_id,
        run_id=run_id,
        story_id=story_id,
        stage='queue.run_end',
        status='failed',
        error_code='phase14_sanity_failed',
        error_message='phase14 sanity failed event',
        metadata={'source': 'phase14-sanity'},
    )


def _seed_queued_execution() -> str:
    execution_run_id = f"phase14-exec-{uuid.uuid4().hex[:8]}"
    store.create_execution_run(
        execution_run_id=execution_run_id,
        source_agent4_run_id=f"phase14-agent4-{uuid.uuid4().hex[:8]}",
        backlog_item_id=f"phase14-story-{uuid.uuid4().hex[:8]}",
        trace_id=f"phase14-trace-{uuid.uuid4().hex[:8]}",
        state='queued',
        stage='phase10_execution_queued',
        request_payload={'started_by': 'phase14-sanity'},
        runtime_policy={'worker_count': 1},
        max_attempts=1,
    )
    return execution_run_id


def main() -> None:
    # Save globals to restore after test.
    old_require_config = config.OPERATOR_REQUIRE_API_KEY
    old_key_config = config.OPERATOR_API_KEY
    old_require_auth = operator_auth.OPERATOR_REQUIRE_API_KEY
    old_key_auth = operator_auth.OPERATOR_API_KEY

    try:
        config.OPERATOR_REQUIRE_API_KEY = True
        config.OPERATOR_API_KEY = 'phase14-key'
        operator_auth.OPERATOR_REQUIRE_API_KEY = True
        operator_auth.OPERATOR_API_KEY = 'phase14-key'

        client = TestClient(app)

        story_id = f"phase14-story-{uuid.uuid4().hex[:8]}"
        _seed_queue_audit_events(story_id)

        denied_audit = client.get('/agent4/phase14/queue/audit?limit=50')
        assert denied_audit.status_code == 403, denied_audit.text

        allowed_audit = client.get(
            f'/agent4/phase14/queue/audit?limit=50&story_id={story_id}&status=error',
            headers={'X-Operator-Key': 'phase14-key'},
        )
        assert allowed_audit.status_code == 200, allowed_audit.text
        payload = allowed_audit.json() or {}
        events = payload.get('events') or []
        assert events, payload
        assert all(str(event.get('stage') or '').startswith('queue.') for event in events), payload

        queued_execution_id = _seed_queued_execution()

        denied_cancel = client.delete(
            f'/agent4/phase11/queue/{queued_execution_id}?canceled_by=phase14-sanity'
        )
        assert denied_cancel.status_code == 403, denied_cancel.text

        allowed_cancel = client.delete(
            f'/agent4/phase11/queue/{queued_execution_id}?canceled_by=phase14-sanity',
            headers={'X-Operator-Key': 'phase14-key'},
        )
        assert allowed_cancel.status_code == 200, allowed_cancel.text

        print(
            {
                'story_id': story_id,
                'audit_event_count': len(events),
                'cancel_execution_id': queued_execution_id,
                'auth_enforced': True,
            }
        )
    finally:
        config.OPERATOR_REQUIRE_API_KEY = old_require_config
        config.OPERATOR_API_KEY = old_key_config
        operator_auth.OPERATOR_REQUIRE_API_KEY = old_require_auth
        operator_auth.OPERATOR_API_KEY = old_key_auth


if __name__ == '__main__':
    main()
