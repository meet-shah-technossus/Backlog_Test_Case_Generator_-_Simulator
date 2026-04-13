from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.main import app


def main() -> None:
    client = TestClient(app)

    intake = client.post('/agent1/intake/load', json={'source_type': 'sample_db'})
    items = intake.json().get('items', [])
    if not items:
        print({'stream_status': 'no_items'})
        return

    story_id = items[0]['backlog_item_id']
    run_resp = client.post('/agent1/runs', json={'backlog_item_id': story_id})
    run_id = run_resp.json().get('run', {}).get('run_id')
    if not run_id:
        print({'stream_status': 'no_run'})
        return

    token_count = 0
    done = False
    with client.stream('POST', f'/agent1/runs/{run_id}/generate/stream', json={'model': None}) as resp:
        for line in resp.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode('utf-8', errors='ignore')
            if not line.startswith('data: '):
                continue
            payload = json.loads(line[6:])
            if payload.get('type') == 'token':
                token_count += 1
            if payload.get('type') == 'done':
                done = True

    print({'stream_http_status': 200, 'token_events': token_count, 'done_event': done})


if __name__ == '__main__':
    main()
