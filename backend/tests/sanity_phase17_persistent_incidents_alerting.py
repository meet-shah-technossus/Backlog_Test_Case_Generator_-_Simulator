from __future__ import annotations

import json
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app
from app.core import config
from app.api.security import operator_auth


class _WebhookRecorder(BaseHTTPRequestHandler):
    payloads: list[dict] = []

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0') or 0)
        body = self.rfile.read(length) if length > 0 else b'{}'
        try:
            payload = json.loads(body.decode('utf-8') or '{}')
        except Exception:
            payload = {'raw': body.decode('utf-8', errors='ignore')}
        _WebhookRecorder.payloads.append(payload)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'ok')

    def log_message(self, format, *args):
        return


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return int(s.getsockname()[1])


def main() -> None:
    old_require_config = config.OPERATOR_REQUIRE_API_KEY
    old_key_config = config.OPERATOR_API_KEY
    old_require_auth = operator_auth.OPERATOR_REQUIRE_API_KEY
    old_key_auth = operator_auth.OPERATOR_API_KEY
    old_window = config.OPERATOR_AUTH_FAILURE_WINDOW_SECONDS
    old_max_failures = config.OPERATOR_AUTH_MAX_FAILURES
    old_lockout = config.OPERATOR_AUTH_LOCKOUT_SECONDS
    old_webhook = config.OPERATOR_ALERT_WEBHOOK_URL
    old_timeout = config.OPERATOR_ALERT_TIMEOUT_SECONDS
    old_max_retries = config.OPERATOR_ALERT_MAX_RETRIES
    old_retry_base_ms = config.OPERATOR_ALERT_RETRY_BASE_MS

    server = None
    thread = None
    try:
        port = _free_port()
        server = HTTPServer(('127.0.0.1', port), _WebhookRecorder)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        _WebhookRecorder.payloads.clear()

        config.OPERATOR_REQUIRE_API_KEY = True
        config.OPERATOR_API_KEY = 'phase17-admin-key'
        operator_auth.OPERATOR_REQUIRE_API_KEY = True
        operator_auth.OPERATOR_API_KEY = 'phase17-admin-key'
        config.OPERATOR_AUTH_FAILURE_WINDOW_SECONDS = 60
        config.OPERATOR_AUTH_MAX_FAILURES = 3
        config.OPERATOR_AUTH_LOCKOUT_SECONDS = 1
        config.OPERATOR_ALERT_WEBHOOK_URL = f'http://127.0.0.1:{port}/alerts'
        config.OPERATOR_ALERT_TIMEOUT_SECONDS = 2
        config.OPERATOR_ALERT_MAX_RETRIES = 0
        config.OPERATOR_ALERT_RETRY_BASE_MS = 50

        client = TestClient(app)

        # Trigger denied and lockout events.
        for _ in range(3):
            client.get('/agent4/phase15/operator/whoami', headers={'X-Operator-Key': 'wrong-key'})

        time.sleep(1.2)

        history_resp = client.get('/agent4/phase17/operator/security/history?limit=50', headers={'X-Operator-Key': 'phase17-admin-key'})
        summary_resp = client.get('/agent4/phase17/operator/security/summary?window_limit=1000', headers={'X-Operator-Key': 'phase17-admin-key'})
        test_alert_resp = client.post('/agent4/phase17/operator/security/alerts/test?source=sanity-phase17', headers={'X-Operator-Key': 'phase17-admin-key'})

        assert history_resp.status_code == 200, history_resp.text
        assert summary_resp.status_code == 200, summary_resp.text
        assert test_alert_resp.status_code == 200, test_alert_resp.text

        history = (history_resp.json() or {}).get('events') or []
        summary = (summary_resp.json() or {}).get('summary') or {}
        test_alert = (test_alert_resp.json() or {}).get('alert_test') or {}

        assert any(str(row.get('stage') or '') == 'operator.auth_denied' for row in history), history
        assert int(summary.get('events_count') or 0) >= 1, summary
        assert bool(test_alert.get('accepted')) is True, test_alert

        # At least one webhook payload should have been posted.
        assert len(_WebhookRecorder.payloads) >= 1, _WebhookRecorder.payloads

        print(
            {
                'history_count': len(history),
                'summary_events_count': summary.get('events_count'),
                'summary_denied_count': summary.get('denied_count'),
                'webhook_posts': len(_WebhookRecorder.payloads),
                'test_alert_accepted': test_alert.get('accepted'),
            }
        )
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=1)

        config.OPERATOR_REQUIRE_API_KEY = old_require_config
        config.OPERATOR_API_KEY = old_key_config
        operator_auth.OPERATOR_REQUIRE_API_KEY = old_require_auth
        operator_auth.OPERATOR_API_KEY = old_key_auth
        config.OPERATOR_AUTH_FAILURE_WINDOW_SECONDS = old_window
        config.OPERATOR_AUTH_MAX_FAILURES = old_max_failures
        config.OPERATOR_AUTH_LOCKOUT_SECONDS = old_lockout
        config.OPERATOR_ALERT_WEBHOOK_URL = old_webhook
        config.OPERATOR_ALERT_TIMEOUT_SECONDS = old_timeout
        config.OPERATOR_ALERT_MAX_RETRIES = old_max_retries
        config.OPERATOR_ALERT_RETRY_BASE_MS = old_retry_base_ms


if __name__ == '__main__':
    main()
