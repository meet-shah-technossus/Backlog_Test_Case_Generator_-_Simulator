from __future__ import annotations

from app.modules.agent2.db.run_repository import Agent2RunRepository
from app.modules.agent2.review.review_service import Agent2ReviewService
from app.modules.agent2.workflow.state_machine import validate_state

AGENT2_MAX_RETRIES = 2


def submit_review(
    *,
    run_id: str,
    decision: str,
    reviewer_id: str,
    reason_code: str | None,
    edited_payload: dict | None,
    run_repo: Agent2RunRepository,
    review_service: Agent2ReviewService,
) -> None:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent2 run '{run_id}' not found")

    if run['state'] not in {'review_pending', 'review_rejected', 'review_retry_requested'}:
        raise ValueError(
            f"Agent2 run '{run_id}' not eligible for review from state '{run['state']}'"
        )

    review_service.validate_review_request(
        decision=decision,
        reason_code=reason_code,
        edited_payload=edited_payload,
    )

    latest_artifact = run_repo.get_latest_artifact(run_id)
    if latest_artifact is None:
        raise ValueError(f"Agent2 run '{run_id}' has no artifact to review")

    if decision == 'retry':
        existing_reviews = run_repo.list_reviews(run_id)
        retry_count = sum(1 for review in existing_reviews if review.get('decision') == 'retry')
        if retry_count >= AGENT2_MAX_RETRIES:
            run_repo.update_state(
                run_id=run_id,
                state=validate_state('failed'),
                stage='review',
                last_error_code='AGENT2_RETRY_LIMIT_EXCEEDED',
                last_error_message=(
                    f"Retry limit exceeded ({AGENT2_MAX_RETRIES}) for run '{run_id}'"
                ),
            )
            run_repo.add_audit_event(
                run_id=run_id,
                stage='review',
                action='retry_limit_exceeded',
                actor=reviewer_id,
                metadata={'max_retries': AGENT2_MAX_RETRIES},
            )
            raise ValueError(
                f"Retry limit exceeded ({AGENT2_MAX_RETRIES}) for Agent2 run '{run_id}'"
            )

    if decision == 'edit_approve':
        if edited_payload is None:
            raise ValueError("edited_payload is required for 'edit_approve'")
        run_repo.add_artifact(
            run_id=run_id,
            source_agent1_run_id=run['source_agent1_run_id'],
            artifact=edited_payload,
        )

    run_repo.add_review(
        run_id=run_id,
        stage='agent2_review',
        decision=decision,
        reason_code=reason_code,
        reviewer_id=reviewer_id,
        edited_payload=edited_payload,
    )

    decision_state = {
        'approve': validate_state('review_approved'),
        'edit_approve': validate_state('review_approved'),
        'reject': validate_state('review_rejected'),
        'retry': validate_state('review_retry_requested'),
    }[decision]

    stage = 'review'
    if decision in {'approve', 'edit_approve'}:
        decision_state = validate_state('handoff_pending')
        stage = 'handoff'

    run_repo.update_state(
        run_id=run_id,
        state=decision_state,
        stage=stage,
        last_error_code=None,
        last_error_message=None,
    )

    run_repo.add_audit_event(
        run_id=run_id,
        stage='review',
        action=f'decision_{decision}',
        actor=reviewer_id,
        metadata={'reason_code': reason_code, 'max_retries': AGENT2_MAX_RETRIES},
    )

    if decision == 'retry':
        run_repo.create_retry_request(
            run_id=run_id,
            requested_by=reviewer_id,
            reason_code=reason_code,
            reason_text=reason_code,
        )


def get_review_diff(*, run_id: str, run_repo: Agent2RunRepository, review_service: Agent2ReviewService) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent2 run '{run_id}' not found")

    artifacts = run_repo.list_artifacts(run_id)
    return review_service.build_review_diff(artifacts=artifacts)
