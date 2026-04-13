from __future__ import annotations

from app.modules.agent2.db.run_repository import Agent2RunRepository
from app.modules.agent2.handoff.handoff_service import Agent2HandoffService
from app.modules.agent2.workflow.state_machine import validate_state


def emit_handoff(
    *,
    run_id: str,
    run_repo: Agent2RunRepository,
    handoff_service: Agent2HandoffService,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent2 run '{run_id}' not found")

    if run['state'] not in {'handoff_pending', 'handoff_emitted'}:
        raise ValueError(
            f"Agent2 run '{run_id}' not eligible for handoff from state '{run['state']}'"
        )

    latest_artifact = run_repo.get_latest_artifact(run_id)
    if latest_artifact is None:
        raise ValueError(f"Agent2 run '{run_id}' has no artifact to handoff")

    envelope = handoff_service.build_envelope(run=run, latest_artifact=latest_artifact)

    _, created = run_repo.add_handoff(
        run_id=run_id,
        message_id=envelope.message_id,
        from_agent=envelope.from_agent,
        to_agent=envelope.to_agent,
        task_type=envelope.task_type,
        contract_version=envelope.contract_version,
        payload=envelope.payload,
        delivery_status='queued',
    )

    run_repo.update_state(
        run_id=run_id,
        state=validate_state('handoff_emitted'),
        stage='handoff',
        last_error_code=None,
        last_error_message=None,
    )

    run_repo.add_audit_event(
        run_id=run_id,
        stage='handoff',
        action='a2a_emitted' if created else 'a2a_emit_reused',
        actor='system',
        metadata={'message_id': envelope.message_id},
    )

    return {'created': created, 'message_id': envelope.message_id}
