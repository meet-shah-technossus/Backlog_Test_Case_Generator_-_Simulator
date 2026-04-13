from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.core import config
from app.api.security import operator_auth


def main() -> None:
    old_require_config = config.OPERATOR_REQUIRE_API_KEY
    old_key_config = config.OPERATOR_API_KEY
    old_require_auth = operator_auth.OPERATOR_REQUIRE_API_KEY
    old_key_auth = operator_auth.OPERATOR_API_KEY

    try:
        config.OPERATOR_REQUIRE_API_KEY = True
        config.OPERATOR_API_KEY = 'phase19-admin-key'
        operator_auth.OPERATOR_REQUIRE_API_KEY = True
        operator_auth.OPERATOR_API_KEY = 'phase19-admin-key'

        client = TestClient(app)
        headers = {'X-Operator-Key': 'phase19-admin-key'}

        # Seed incidents via denied attempts.
        for _ in range(3):
            client.get('/agent4/phase15/operator/whoami', headers={'X-Operator-Key': 'wrong-key'})

        open_resp = client.get('/agent4/phase19/operator/security/incidents/open?limit=50', headers=headers)
        assert open_resp.status_code == 200, open_resp.text
        incidents = (open_resp.json() or {}).get('incidents') or []
        assert incidents, incidents

        target = incidents[-1]
        incident_id = str(target.get('event_id') or '')
        assert incident_id, target

        ack_resp = client.post(
            f'/agent4/phase19/operator/security/incidents/{incident_id}/ack?acked_by=sanity-phase19',
            headers=headers,
        )
        assert ack_resp.status_code == 200, ack_resp.text
        acked = (ack_resp.json() or {}).get('incident') or {}
        assert str(acked.get('state') or '') in {'acknowledged', 'resolved'}, acked

        resolve_resp = client.post(
            f'/agent4/phase19/operator/security/incidents/{incident_id}/resolve?resolved_by=sanity-phase19&resolution_note=validated',
            headers=headers,
        )
        assert resolve_resp.status_code == 200, resolve_resp.text
        resolved = (resolve_resp.json() or {}).get('incident') or {}
        assert str(resolved.get('state') or '') == 'resolved', resolved

        open_after_resp = client.get('/agent4/phase19/operator/security/incidents/open?limit=200', headers=headers)
        assert open_after_resp.status_code == 200, open_after_resp.text
        open_after = (open_after_resp.json() or {}).get('incidents') or []
        assert all(str(item.get('event_id') or '') != incident_id for item in open_after), open_after

        print(
            {
                'incident_id': incident_id,
                'acked_state': acked.get('state'),
                'resolved_state': resolved.get('state'),
                'remaining_open_incidents': len(open_after),
            }
        )
    finally:
        config.OPERATOR_REQUIRE_API_KEY = old_require_config
        config.OPERATOR_API_KEY = old_key_config
        operator_auth.OPERATOR_REQUIRE_API_KEY = old_require_auth
        operator_auth.OPERATOR_API_KEY = old_key_auth


if __name__ == '__main__':
    main()
