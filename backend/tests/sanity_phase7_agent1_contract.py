from __future__ import annotations

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

    suffix = uuid4().hex[:10]
    backlog_item_id = f"story-phase7-contract-{suffix}"
    run_id = f"agent1-phase7-contract-{suffix}"
    store.upsert_agent1_run(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        trace_id=f"trace-phase7-contract-{suffix}",
        state='completed',
        source_type='manual',
        source_ref=None,
    )

    store.add_agent1_artifact(
        run_id=run_id,
        backlog_item_id=backlog_item_id,
        artifact_version=1,
        artifact={
            'backlog_item_id': backlog_item_id,
            'test_cases': [{'id': 'TC001', 'title': 'Phase7 Contract'}],
        },
    )
    store.add_agent1_review(
        run_id=run_id,
        stage='phase7_contract_sanity',
        decision='approve',
        reason_code=None,
        reviewer_id='phase7_sanity',
        edited_payload=None,
    )
    store.add_retry_governance_request(
        request_id=f'phase7-req-{suffix}',
        run_scope='agent1',
        run_id=run_id,
        requested_by='phase7_sanity',
        reason_code='manual_retry',
        reason_text='phase7 contract sanity',
    )

    response = client.get(f'/agent1/runs/{run_id}/contract/v1')
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload.get('contract_version') == 'v1', payload
    assert payload.get('run_scope') == 'agent1', payload
    assert payload.get('internal_id') == run_id, payload
    assert isinstance(payload.get('business_id'), str) and payload.get('business_id'), payload

    current_revision = payload.get('current_revision') or {}
    assert current_revision.get('artifact_version') == 1, current_revision
    assert isinstance(current_revision.get('business_id'), str) and current_revision.get('business_id'), current_revision

    retry_status = payload.get('retry_status') or {}
    total_requests = retry_status.get('total_requests')
    assert retry_status.get('latest_request_id'), retry_status
    assert isinstance(total_requests, int) and total_requests >= 1, retry_status

    review_status = payload.get('review_status') or {}
    total_reviews = review_status.get('total_reviews')
    assert review_status.get('latest_decision') == 'approve', review_status
    assert isinstance(total_reviews, int) and total_reviews >= 1, review_status

    print(
        {
            'run_id': run_id,
            'run_business_id': payload.get('business_id'),
            'current_revision': current_revision,
            'retry_status': retry_status,
            'review_status': review_status,
        }
    )


if __name__ == '__main__':
    main()
