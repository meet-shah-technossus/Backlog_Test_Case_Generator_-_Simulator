from __future__ import annotations

import sys
from collections import Counter
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
        print({'status': 'no_items'})
        return

    story_id = items[0]['backlog_item_id']
    run = client.post('/agent1/runs', json={'backlog_item_id': story_id})
    run_id = run.json().get('run', {}).get('run_id')
    if not run_id:
        print({'status': 'no_run'})
        return

    generated = client.post(f'/agent1/runs/{run_id}/generate', json={'model': None})
    payload = generated.json()
    if generated.status_code != 200:
        print({'status': 'failed', 'error': payload.get('detail')})
        return

    cases = payload.get('latest_artifact', {}).get('artifact', {}).get('test_cases', [])
    by_criterion = {}
    for tc in cases:
        cid = tc.get('criterion_id')
        by_criterion.setdefault(cid, Counter())
        by_criterion[cid][str(tc.get('test_type', '')).lower()] += 1

    summary = {cid: dict(counter) for cid, counter in by_criterion.items()}
    print({'case_total': len(cases), 'type_breakdown_by_criterion': summary})


if __name__ == '__main__':
    main()
