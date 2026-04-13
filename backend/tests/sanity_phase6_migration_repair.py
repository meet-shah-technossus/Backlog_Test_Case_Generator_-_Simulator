from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.infrastructure.store import store
from app.main import app


def main() -> None:
    client = TestClient(app)

    orphan_execution_run_id = f"orphan-exec-{uuid4().hex[:10]}"

    with sqlite3.connect(store.db_path) as conn:
        conn.execute(
            """
            INSERT INTO execution_evidence(
                execution_run_id, script_path, step_index, status, duration_ms,
                metadata_json, business_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                orphan_execution_run_id,
                'tests/generated/orphan.spec.ts',
                1,
                'failed',
                1,
                '{}',
                f"EVD-ORPHAN-{uuid4().hex[:6].upper()}",
            ),
        )
        conn.commit()

    before = client.get('/business-ids/migration/status', headers={'X-Retry-Role': 'reviewer'})
    assert before.status_code == 200, before.text
    before_orphans = (before.json().get('summary') or {}).get('orphan_link_count')
    assert isinstance(before_orphans, int), before.text

    repair = client.post(
        '/business-ids/migration/repair',
        json={'actor': 'phase6_sanity'},
        headers={'X-Retry-Role': 'operator'},
    )
    assert repair.status_code == 200, repair.text
    repair_payload = repair.json()

    repaired_total = repair_payload.get('total_repaired')
    assert isinstance(repaired_total, int) and repaired_total >= 1, repair_payload

    after = client.get('/business-ids/migration/status', headers={'X-Retry-Role': 'reviewer'})
    assert after.status_code == 200, after.text
    after_orphans = (after.json().get('summary') or {}).get('orphan_link_count')
    assert isinstance(after_orphans, int), after.text
    assert after_orphans <= before_orphans - 1, {
        'before_orphans': before_orphans,
        'after_orphans': after_orphans,
        'repair_payload': repair_payload,
    }

    print(
        {
            'before_orphans': before_orphans,
            'after_orphans': after_orphans,
            'repaired_total': repaired_total,
        }
    )


if __name__ == '__main__':
    main()
