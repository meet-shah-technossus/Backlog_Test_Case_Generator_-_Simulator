from __future__ import annotations

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
    story_id = items[0]['backlog_item_id'] if items else None

    print({'intake_status': intake.status_code, 'story_id': story_id})

    if not story_id:
        return

    run_resp = client.post('/agent1/runs', json={'backlog_item_id': story_id})
    run_id = run_resp.json().get('run', {}).get('run_id')
    print({'create_status': run_resp.status_code, 'run_id': run_id})

    if not run_id:
        return

    gen_resp = client.post(f'/agent1/runs/{run_id}/generate', json={'model': None})
    payload = gen_resp.json()
    result = {'generate_status': gen_resp.status_code}

    if gen_resp.status_code == 200:
        latest = payload.get('latest_artifact', {}).get('artifact', {})
        result['case_count'] = len(latest.get('test_cases', []))
    else:
        result['error'] = payload.get('detail')

    print(result)


if __name__ == '__main__':
    main()
