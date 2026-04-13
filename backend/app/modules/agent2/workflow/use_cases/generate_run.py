from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.modules.agent2.intake.handoff_inbox_service import Agent2HandoffInboxService
from app.modules.agent2.db.run_repository import Agent2RunRepository
from app.modules.agent2.generation.generation_service import Agent2GenerationService
from app.modules.agent2.mcp.agent1_handoff_mcp_service import Agent1HandoffMCPService
from app.modules.agent2.workflow.state_machine import validate_state


async def generate_run(
    *,
    run_id: str,
    run_repo: Agent2RunRepository,
    inbox_service: Agent2HandoffInboxService,
    agent1_handoff_mcp_service: Agent1HandoffMCPService,
    generation_service: Agent2GenerationService,
    model: str | None = None,
    on_token: Callable[[str], Awaitable[None] | None] | None = None,
) -> None:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent2 run '{run_id}' not found")

    if run['state'] not in {'intake_ready', 'review_retry_requested'}:
        raise ValueError(
            f"Agent2 run '{run_id}' not eligible for generation from state '{run['state']}'"
        )

    source_agent1_run_id = run.get('source_agent1_run_id')
    if not source_agent1_run_id:
        raise ValueError(f"Agent2 run '{run_id}' has no source Agent1 run reference")

    source_artifact = agent1_handoff_mcp_service.read_latest_agent1_artifact(source_agent1_run_id)
    source_cases = (source_artifact or {}).get('artifact', {}).get('test_cases', [])
    story_id = (source_artifact or {}).get('artifact', {}).get('backlog_item_id')
    story_title: str | None = None
    story_description: str | None = None
    acceptance_criteria: list[str] | None = None
    evidence_pages: list[dict] | None = None
    source_mode = 'agent1'

    if not source_cases or not story_id:
        inbox_message_id = run.get('inbox_message_id') or ''
        inbox = inbox_service.get(inbox_message_id) if inbox_message_id else None
        payload = (inbox or {}).get('payload') or {}
        context_pack = payload.get('scraper_context_pack') if isinstance(payload, dict) else None
        if not isinstance(context_pack, dict):
            raise ValueError(
                f"Agent2 source artifact not found for Agent1 run '{source_agent1_run_id}'"
            )

        story_raw = context_pack.get('story')
        story = story_raw if isinstance(story_raw, dict) else {}
        story_id = str(story.get('backlog_item_id') or payload.get('backlog_item_id') or source_agent1_run_id)
        story_title = str(story.get('title') or '')
        story_description = str(story.get('description') or '')
        acceptance_criteria = [str(x) for x in (story.get('acceptance_criteria') or []) if str(x).strip()]
        evidence_pages = context_pack.get('llm_input', {}).get('evidence_pages') or context_pack.get('crawl', {}).get('pages') or []

        if acceptance_criteria:
            source_cases = [
                {
                    'id': f"SCR-AC-{index:03d}",
                    'title': criterion,
                    'expected_result': criterion,
                    'test_type': 'functional',
                }
                for index, criterion in enumerate(acceptance_criteria, start=1)
            ]
        else:
            source_cases = [
                {
                    'id': 'SCR-GEN-001',
                    'title': f"Validate story behavior for {story_id}",
                    'expected_result': 'All intended user-facing behavior works correctly.',
                    'test_type': 'functional',
                }
            ]
        source_mode = 'scraper_phase6'

    run_repo.update_state(
        run_id=run_id,
        state=validate_state('agent2_generating'),
        stage='generation',
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage='generation',
        action='generation_started',
        actor='system',
        metadata={
            'model': model,
            'retry_cycle': run['state'] == 'review_retry_requested',
        },
    )

    try:
        artifact = await generation_service.generate_steps_artifact(
            run_id=run_id,
            story_id=story_id,
            source_agent1_run_id=source_agent1_run_id,
            source_test_cases=source_cases,
            story_title=story_title,
            story_description=story_description,
            acceptance_criteria=acceptance_criteria,
            evidence_pages=evidence_pages,
            model=model,
            on_token=on_token,
        )
    except Exception as exc:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state('failed'),
            stage='generation',
            last_error_code='AGENT2_GENERATION_FAILED',
            last_error_message=str(exc),
        )
        run_repo.add_audit_event(
            run_id=run_id,
            stage='generation',
            action='generation_failed',
            actor='system',
            metadata={'error': str(exc)},
        )
        raise

    version = run_repo.add_artifact(
        run_id=run_id,
        source_agent1_run_id=source_agent1_run_id,
        artifact=artifact,
    )

    run_repo.update_state(
        run_id=run_id,
        state=validate_state('review_pending'),
        stage='review',
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage='generation',
        action='generation_completed',
        actor='system',
        metadata={
            'artifact_version': version,
            'case_count': len(source_cases),
            'source_mode': source_mode,
        },
    )
