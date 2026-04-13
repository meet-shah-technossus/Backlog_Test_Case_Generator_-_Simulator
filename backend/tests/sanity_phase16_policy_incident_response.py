from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.core import config
from app.api.security import operator_auth
from app.api.security.operator_incident_policy import operator_incident_policy_service


def main() -> None:
    old_require_config = config.OPERATOR_REQUIRE_API_KEY
    old_key_config = config.OPERATOR_API_KEY
    old_require_auth = operator_auth.OPERATOR_REQUIRE_API_KEY
    old_key_auth = operator_auth.OPERATOR_API_KEY
    old_window = config.OPERATOR_AUTH_FAILURE_WINDOW_SECONDS
    old_max_failures = config.OPERATOR_AUTH_MAX_FAILURES
    old_lockout = config.OPERATOR_AUTH_LOCKOUT_SECONDS

    try:
        config.OPERATOR_REQUIRE_API_KEY = True
        config.OPERATOR_API_KEY = 'phase16-admin-key'
        operator_auth.OPERATOR_REQUIRE_API_KEY = True
        operator_auth.OPERATOR_API_KEY = 'phase16-admin-key'

        config.OPERATOR_AUTH_FAILURE_WINDOW_SECONDS = 60
        config.OPERATOR_AUTH_MAX_FAILURES = 3
        config.OPERATOR_AUTH_LOCKOUT_SECONDS = 1

        before_status = operator_incident_policy_service.get_status()
        before_failures = int(before_status.get('recent_failure_count') or 0)

        client = TestClient(app)

        ok_status_resp = client.get('/agent4/phase16/operator/security/status', headers={'X-Operator-Key': 'phase16-admin-key'})
        assert ok_status_resp.status_code == 200, ok_status_resp.text

        for _ in range(3):
            denied = client.get('/agent4/phase15/operator/whoami', headers={'X-Operator-Key': 'wrong-key'})
            assert denied.status_code == 403, denied.text

        locked = client.get('/agent4/phase15/operator/whoami', headers={'X-Operator-Key': 'wrong-key'})
        assert locked.status_code == 423, locked.text

        during_lockout = operator_incident_policy_service.get_status()
        assert int(during_lockout.get('recent_failure_count') or 0) >= before_failures + 3, during_lockout
        assert int(during_lockout.get('lockout_count') or 0) >= 1, during_lockout

        time.sleep(1.2)

        status_resp = client.get('/agent4/phase16/operator/security/status', headers={'X-Operator-Key': 'phase16-admin-key'})
        events_resp = client.get('/agent4/phase16/operator/security/events?limit=50', headers={'X-Operator-Key': 'phase16-admin-key'})

        assert status_resp.status_code == 200, status_resp.text
        assert events_resp.status_code == 200, events_resp.text

        status_payload = (status_resp.json() or {}).get('security') or {}
        events = (events_resp.json() or {}).get('events') or []

        assert any(str(event.get('stage') or '') == 'operator.auth_denied' for event in events), events
        assert any(str(event.get('stage') or '') == 'operator.auth_lockout' for event in events), events

        print(
            {
                'recent_failure_count': status_payload.get('recent_failure_count'),
                'lockout_count': status_payload.get('lockout_count'),
                'events_returned': len(events),
                'saw_denied_event': any(str(event.get('stage') or '') == 'operator.auth_denied' for event in events),
                'saw_lockout_event': any(str(event.get('stage') or '') == 'operator.auth_lockout' for event in events),
            }
        )
    finally:
        config.OPERATOR_REQUIRE_API_KEY = old_require_config
        config.OPERATOR_API_KEY = old_key_config
        operator_auth.OPERATOR_REQUIRE_API_KEY = old_require_auth
        operator_auth.OPERATOR_API_KEY = old_key_auth
        config.OPERATOR_AUTH_FAILURE_WINDOW_SECONDS = old_window
        config.OPERATOR_AUTH_MAX_FAILURES = old_max_failures
        config.OPERATOR_AUTH_LOCKOUT_SECONDS = old_lockout


if __name__ == '__main__':
    main()
