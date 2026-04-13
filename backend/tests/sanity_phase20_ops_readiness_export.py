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
    old_signing_secret = config.AUDIT_SIGNING_SECRET
    old_webhook_url = config.OPERATOR_ALERT_WEBHOOK_URL
    old_open_threshold = config.OPERATOR_SECURITY_OPEN_INCIDENT_THRESHOLD

    try:
        config.OPERATOR_REQUIRE_API_KEY = True
        config.OPERATOR_API_KEY = 'phase20-admin-key'
        operator_auth.OPERATOR_REQUIRE_API_KEY = True
        operator_auth.OPERATOR_API_KEY = 'phase20-admin-key'
        config.AUDIT_SIGNING_SECRET = 'phase20-signing-secret'
        config.OPERATOR_ALERT_WEBHOOK_URL = 'https://example.com/webhook'
        config.OPERATOR_SECURITY_OPEN_INCIDENT_THRESHOLD = 100

        client = TestClient(app)
        headers = {'X-Operator-Key': 'phase20-admin-key'}

        for _ in range(2):
            client.get('/agent4/phase15/operator/whoami', headers={'X-Operator-Key': 'wrong-key'})

        export_resp = client.get('/agent4/phase20/operator/security/export?limit=50&state=open', headers=headers)
        readiness_resp = client.get('/agent4/phase20/operator/security/readiness', headers=headers)

        assert export_resp.status_code == 200, export_resp.text
        assert readiness_resp.status_code == 200, readiness_resp.text

        export_payload = (export_resp.json() or {}).get('export') or {}
        export_summary = export_payload.get('summary') or {}
        incidents = export_payload.get('incidents') or []

        readiness = (readiness_resp.json() or {}).get('readiness') or {}
        checks = readiness.get('checks') or {}

        assert export_summary.get('state_filter') in {'open', None}, export_summary
        assert isinstance(incidents, list), export_payload
        assert isinstance(checks.get('operator_auth_enabled'), bool), readiness
        assert isinstance(checks.get('audit_signing_enabled'), bool), readiness
        assert isinstance(checks.get('webhook_configured'), bool), readiness
        assert isinstance(checks.get('open_incidents_within_threshold'), bool), readiness

        print(
            {
                'export_count': len(incidents),
                'export_state_filter': export_summary.get('state_filter'),
                'ready': readiness.get('ready'),
                'open_incident_count': readiness.get('open_incident_count'),
                'threshold': readiness.get('open_incident_threshold'),
            }
        )
    finally:
        config.OPERATOR_REQUIRE_API_KEY = old_require_config
        config.OPERATOR_API_KEY = old_key_config
        operator_auth.OPERATOR_REQUIRE_API_KEY = old_require_auth
        operator_auth.OPERATOR_API_KEY = old_key_auth
        config.AUDIT_SIGNING_SECRET = old_signing_secret
        config.OPERATOR_ALERT_WEBHOOK_URL = old_webhook_url
        config.OPERATOR_SECURITY_OPEN_INCIDENT_THRESHOLD = old_open_threshold


if __name__ == '__main__':
    main()
