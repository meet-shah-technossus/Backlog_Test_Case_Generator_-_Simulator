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

    response = client.get('/business-ids/migration/status', headers={'X-Retry-Role': 'reviewer'})
    assert response.status_code == 200, response.text

    payload = response.json()
    summary = payload.get('summary') or {}
    tables = payload.get('tables') or []
    links = payload.get('links') or []
    rollback = payload.get('rollback') or {}

    total_rows_checked = summary.get('total_rows_checked')
    rows_missing_business_id = summary.get('rows_missing_business_id')
    duplicate_business_id_groups = summary.get('duplicate_business_id_groups')
    orphan_link_count = summary.get('orphan_link_count')

    assert isinstance(payload.get('generated_at'), str) and payload.get('generated_at'), payload
    assert isinstance(total_rows_checked, int) and total_rows_checked >= 0, summary
    assert isinstance(rows_missing_business_id, int) and rows_missing_business_id >= 0, summary
    assert isinstance(duplicate_business_id_groups, int) and duplicate_business_id_groups >= 0, summary
    assert isinstance(orphan_link_count, int) and orphan_link_count >= 0, summary
    assert summary.get('status') in {'ok', 'attention_required'}, summary

    assert isinstance(tables, list) and tables, payload
    table_names = {row.get('table') for row in tables if isinstance(row, dict)}
    assert 'agent1_artifacts' in table_names, table_names
    assert 'execution_evidence' in table_names, table_names

    for row in tables:
        assert isinstance(row.get('total_rows'), int), row
        assert isinstance(row.get('rows_with_business_id'), int), row
        assert isinstance(row.get('rows_missing_business_id'), int), row
        assert isinstance(row.get('duplicate_business_id_groups'), int), row

    assert isinstance(links, list) and links, payload
    for link in links:
        assert isinstance(link.get('orphan_count'), int) and link.get('orphan_count') >= 0, link
        assert link.get('status') in {'ok', 'orphaned'}, link

    assert rollback.get('rollback_ready') is True, rollback
    assert isinstance(rollback.get('database_path'), str) and rollback.get('database_path'), rollback

    print(
        {
            'summary': summary,
            'table_count': len(tables),
            'link_count': len(links),
            'rollback_ready': rollback.get('rollback_ready'),
        }
    )


if __name__ == '__main__':
    main()
