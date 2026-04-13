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
import app.infrastructure.store.core as store_core


def _seed_queue_event(story_id: str) -> None:
    store.log_event(
        trace_id=f"phase15-trace-{uuid.uuid4().hex[:8]}",
        run_id=f"phase15-run-{uuid.uuid4().hex[:8]}",
        story_id=story_id,
        stage='queue.enqueue',
        status='queued',
        metadata={'source': 'phase15-sanity'},
    )


def main() -> None:
    old_require_config = config.OPERATOR_REQUIRE_API_KEY
    old_key_config = config.OPERATOR_API_KEY
    old_require_auth = operator_auth.OPERATOR_REQUIRE_API_KEY
    old_key_auth = operator_auth.OPERATOR_API_KEY
    old_signing_config = config.AUDIT_SIGNING_SECRET
    old_signing_core = store_core.AUDIT_SIGNING_SECRET

    try:
        config.OPERATOR_REQUIRE_API_KEY = True
        config.OPERATOR_API_KEY = 'phase15-admin-key'
        operator_auth.OPERATOR_REQUIRE_API_KEY = True
        operator_auth.OPERATOR_API_KEY = 'phase15-admin-key'

        config.AUDIT_SIGNING_SECRET = 'phase15-signing-secret'
        store_core.AUDIT_SIGNING_SECRET = 'phase15-signing-secret'

        story_id = f"phase15-story-{uuid.uuid4().hex[:8]}"
        _seed_queue_event(story_id)

        client = TestClient(app)
        headers = {'X-Operator-Key': 'phase15-admin-key'}

        whoami_resp = client.get('/agent4/phase15/operator/whoami', headers=headers)
        assert whoami_resp.status_code == 200, whoami_resp.text
        whoami = (whoami_resp.json() or {}).get('identity') or {}
        assert whoami.get('role') in {'admin', 'executor', 'viewer'}, whoami

        verify_resp = client.get(
            f'/agent4/phase15/queue/audit/verify?limit=200&story_id={story_id}',
            headers=headers,
        )
        assert verify_resp.status_code == 200, verify_resp.text
        verification = (verify_resp.json() or {}).get('verification') or {}
        assert verification.get('secret_configured') is True, verification
        assert isinstance(verification.get('valid'), bool), verification
        assert isinstance(verification.get('invalid_event_ids'), list), verification

        print(
            {
                'story_id': story_id,
                'role': whoami.get('role'),
                'verification_valid': verification.get('valid'),
                'invalid_event_count': len(verification.get('invalid_event_ids') or []),
            }
        )
    finally:
        config.OPERATOR_REQUIRE_API_KEY = old_require_config
        config.OPERATOR_API_KEY = old_key_config
        operator_auth.OPERATOR_REQUIRE_API_KEY = old_require_auth
        operator_auth.OPERATOR_API_KEY = old_key_auth
        config.AUDIT_SIGNING_SECRET = old_signing_config
        store_core.AUDIT_SIGNING_SECRET = old_signing_core


if __name__ == '__main__':
    main()
