from __future__ import annotations

import json
import socket
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core import config
from app.api.security.operator_alert_service import operator_alert_service


class _FlakyWebhookHandler(BaseHTTPRequestHandler):
    attempts = 0
    payloads: list[dict] = []

    def do_POST(self):
        _FlakyWebhookHandler.attempts += 1
        length = int(self.headers.get('Content-Length', '0') or 0)
        body = self.rfile.read(length) if length > 0 else b'{}'
        try:
            payload = json.loads(body.decode('utf-8') or '{}')
        except Exception:
            payload = {'raw': body.decode('utf-8', errors='ignore')}
        _FlakyWebhookHandler.payloads.append(payload)

        # Fail first two attempts, then succeed.
        if _FlakyWebhookHandler.attempts < 3:
            self.send_response(502)
        else:
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
    old_url = config.OPERATOR_ALERT_WEBHOOK_URL
    old_timeout = config.OPERATOR_ALERT_TIMEOUT_SECONDS
    old_channel = config.OPERATOR_ALERT_CHANNEL
    old_retries = config.OPERATOR_ALERT_MAX_RETRIES
    old_retry_base_ms = config.OPERATOR_ALERT_RETRY_BASE_MS

    server = None
    thread = None
    try:
        port = _free_port()
        server = HTTPServer(('127.0.0.1', port), _FlakyWebhookHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()

        _FlakyWebhookHandler.attempts = 0
        _FlakyWebhookHandler.payloads.clear()

        config.OPERATOR_ALERT_WEBHOOK_URL = f'http://127.0.0.1:{port}/alerts'
        config.OPERATOR_ALERT_TIMEOUT_SECONDS = 2
        config.OPERATOR_ALERT_CHANNEL = 'slack'
        config.OPERATOR_ALERT_MAX_RETRIES = 3
        config.OPERATOR_ALERT_RETRY_BASE_MS = 10

        payload = {
            'event': {
                'event_id': 'phase18-test-event',
                'stage': 'operator.auth_lockout',
                'status': 'locked',
                'source': 'phase18-sanity',
                'reason': 'threshold_reached',
            },
            'policy': {
                'failure_window_seconds': 60,
                'max_failures': 3,
                'lockout_seconds': 600,
            },
        }

        result = operator_alert_service.send_incident_alert(payload)
        as_dict = result.to_dict()

        assert as_dict.get('delivered') is True, as_dict
        assert int(as_dict.get('attempts') or 0) >= 3, as_dict
        history = as_dict.get('attempt_history') or []
        assert len(history) >= 3, as_dict
        assert any(int(row.get('status_code') or 0) == 502 for row in history), history
        assert int(history[-1].get('status_code') or 0) == 200, history
        assert as_dict.get('channel') == 'slack', as_dict

        first_payload = _FlakyWebhookHandler.payloads[0] if _FlakyWebhookHandler.payloads else {}
        assert 'attachments' in first_payload, first_payload

        print(
            {
                'delivered': as_dict.get('delivered'),
                'attempts': as_dict.get('attempts'),
                'channel': as_dict.get('channel'),
                'history_len': len(history),
                'webhook_posts': _FlakyWebhookHandler.attempts,
            }
        )
    finally:
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=1)

        config.OPERATOR_ALERT_WEBHOOK_URL = old_url
        config.OPERATOR_ALERT_TIMEOUT_SECONDS = old_timeout
        config.OPERATOR_ALERT_CHANNEL = old_channel
        config.OPERATOR_ALERT_MAX_RETRIES = old_retries
        config.OPERATOR_ALERT_RETRY_BASE_MS = old_retry_base_ms


if __name__ == '__main__':
    main()
