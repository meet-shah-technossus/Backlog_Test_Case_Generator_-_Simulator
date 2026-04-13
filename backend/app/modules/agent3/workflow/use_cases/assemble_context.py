from __future__ import annotations

from app.modules.agent3.context.assembler import assemble_reasoning_context
from app.modules.agent3.context.context_source_service import Agent3ContextSourceService
from app.modules.agent3.context.policy import TokenSafeCrawlContextPolicy
from app.modules.agent3.db.run_repository import Agent3RunRepository
from app.modules.agent3.workflow.state_machine import validate_state


def assemble_context_for_run(
    *,
    run_id: str,
    run_repo: Agent3RunRepository,
    context_source: Agent3ContextSourceService,
    policy: TokenSafeCrawlContextPolicy,
    retry_count: int = 0,
) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent3 run '{run_id}' not found")

    if run.get("state") not in {"intake_ready", "review_retry_requested"}:
        raise ValueError(
            f"Agent3 run '{run_id}' cannot assemble context from state '{run.get('state')}'"
        )

    source_agent2_run_id = str(run.get("source_agent2_run_id") or "")
    if not source_agent2_run_id:
        raise ValueError(f"Agent3 run '{run_id}' has no source Agent2 run reference")

    source_agent2_run = context_source.get_agent2_run(source_agent2_run_id)
    if source_agent2_run is None:
        raise ValueError(f"Source Agent2 run '{source_agent2_run_id}' not found")

    latest_artifact = context_source.get_agent2_latest_artifact(source_agent2_run_id)
    if latest_artifact is None:
        raise ValueError(f"Source Agent2 run '{source_agent2_run_id}' has no artifact")

    artifact = (latest_artifact.get("artifact") or {}) if isinstance(latest_artifact, dict) else {}
    generated_steps = (artifact.get("generated_steps") or {}).get("test_cases") or []

    inbox_message_id = str(source_agent2_run.get("inbox_message_id") or "")
    inbox = context_source.get_agent2_inbox(inbox_message_id) if inbox_message_id else None
    payload = (inbox or {}).get("payload") or {}
    scraper_context_pack = payload.get("scraper_context_pack") if isinstance(payload, dict) else None

    evidence_pages = []
    if isinstance(scraper_context_pack, dict):
        llm_input = scraper_context_pack.get("llm_input")
        crawl = scraper_context_pack.get("crawl")
        if isinstance(llm_input, dict):
            evidence_pages = llm_input.get("evidence_pages") or []
        if not evidence_pages and isinstance(crawl, dict):
            evidence_pages = crawl.get("pages") or []

    run_repo.update_state(
        run_id=run_id,
        state=validate_state("context_assembling"),
        stage="phase-3-context-assembly",
        last_error_code=None,
        last_error_message=None,
    )

    try:
        context_version = run_repo.get_next_artifact_version(run_id)
        assembled = assemble_reasoning_context(
            run_id=run_id,
            source_agent2_run_id=source_agent2_run_id,
            source_generated_steps=generated_steps,
            source_pages=evidence_pages,
            context_version=context_version,
            retry_count=retry_count,
            policy=policy,
        )
    except Exception as exc:
        run_repo.update_state(
            run_id=run_id,
            state=validate_state("failed"),
            stage="phase-3-context-assembly",
            last_error_code="A3_CONTEXT_ASSEMBLY_FAILED",
            last_error_message=str(exc),
        )
        run_repo.add_audit_event(
            run_id=run_id,
            stage="phase-3-context-assembly",
            action="context_assembly_failed",
            actor="system",
            metadata={"error": str(exc)},
        )
        raise

    run_repo.add_artifact(run_id=run_id, artifact=assembled.model_dump())
    run_repo.update_state(
        run_id=run_id,
        state=validate_state("review_pending"),
        stage="phase-3-gate-pending",
        last_error_code=None,
        last_error_message=None,
    )
    run_repo.add_audit_event(
        run_id=run_id,
        stage="phase-3-context-assembly",
        action="context_assembled",
        actor="system",
        metadata={
            "context_version": assembled.context_version,
            "input_steps": len(assembled.input_steps),
            "unresolved_count": assembled.unresolved_count,
        },
    )

    return {
        "run": run_repo.get_run(run_id) or run,
        "context_artifact": run_repo.get_latest_artifact(run_id),
    }
