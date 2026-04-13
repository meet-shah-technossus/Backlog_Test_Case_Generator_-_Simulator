from __future__ import annotations

from app.modules.agent3.context.context_source_service import Agent3ContextSourceService
from app.modules.agent3.context.policy import TokenSafeCrawlContextPolicy
from app.modules.agent3.contracts.models import Agent3HandoffEnvelope
from app.modules.agent3.db.run_repository import Agent3RunRepository
from app.modules.agent3.feedback.execution_feedback_service import Agent3ExecutionFeedbackService
from app.modules.agent3.generation.selector_generation_service import Agent3SelectorGenerationService
from app.modules.agent3.handoff.handoff_service import Agent3HandoffService
from app.modules.agent3.intake.handoff_inbox_service import Agent3HandoffInboxService
from app.modules.agent3.review.review_service import Agent3ReviewService
from app.modules.agent3.review.selector_review_service import Agent3SelectorReviewService
from app.modules.agent3.workflow.use_cases.assemble_context import assemble_context_for_run
from app.modules.agent3.workflow.use_cases.apply_execution_feedback import apply_execution_feedback
from app.modules.agent3.workflow.use_cases.consume_handoff import consume_handoff
from app.modules.agent3.workflow.use_cases.create_run_from_inbox import create_run_from_inbox
from app.modules.agent3.workflow.use_cases.emit_handoff import emit_phase5_handoff
from app.modules.agent3.workflow.use_cases.get_blueprint import get_agent3_blueprint
from app.modules.agent3.workflow.use_cases.get_phase8_integrity_report import get_phase8_integrity_report
from app.modules.agent3.workflow.use_cases.get_phase7_observability import get_phase7_observability
from app.modules.agent3.workflow.use_cases.get_run_snapshot import get_run_snapshot
from app.modules.agent3.workflow.use_cases.generate_selectors import generate_selectors_for_run
from app.modules.agent3.workflow.use_cases.review_selectors import submit_selector_review
from app.modules.agent3.workflow.use_cases.submit_gate import submit_gate_decision


class Agent3Orchestrator:
    """Agent3 orchestration boundary with Phase 2 intake use-cases."""

    def __init__(
        self,
        inbox_service: Agent3HandoffInboxService,
        run_repo: Agent3RunRepository,
        context_source: Agent3ContextSourceService,
        token_policy: TokenSafeCrawlContextPolicy,
        review_service: Agent3ReviewService,
        generation_service: Agent3SelectorGenerationService,
        selector_review_service: Agent3SelectorReviewService,
        handoff_service: Agent3HandoffService,
        execution_feedback_service: Agent3ExecutionFeedbackService,
    ):
        self._inbox_service = inbox_service
        self._run_repo = run_repo
        self._context_source = context_source
        self._token_policy = token_policy
        self._review_service = review_service
        self._generation_service = generation_service
        self._selector_review_service = selector_review_service
        self._handoff_service = handoff_service
        self._execution_feedback_service = execution_feedback_service

    def _resolve_retry_count(self, run_id: str) -> int:
        run = self._run_repo.get_run(run_id) or {}
        message_id = str(run.get("inbox_message_id") or "")
        inbox = self._inbox_service.get(message_id) if message_id else None
        payload = (inbox or {}).get("payload") or {}
        a2a = payload.get("_a2a") if isinstance(payload, dict) else {}
        base_retry = int((a2a or {}).get("retry_count") or 0)
        retries = sum(
            1
            for event in self._run_repo.get_timeline_events(run_id, ascending=False)
            if event.get("action") == "gate_retry_requested"
        )
        return base_retry + retries

    def get_blueprint(self) -> dict:
        return get_agent3_blueprint()

    def consume_handoff(self, envelope: Agent3HandoffEnvelope) -> dict:
        return consume_handoff(
            envelope=envelope,
            inbox_service=self._inbox_service,
        )

    def create_run_from_inbox(self, message_id: str) -> dict:
        return create_run_from_inbox(
            message_id=message_id,
            inbox_service=self._inbox_service,
            run_repo=self._run_repo,
        )

    def get_run_snapshot(self, run_id: str) -> dict:
        return get_run_snapshot(
            run_id=run_id,
            run_repo=self._run_repo,
        )

    def list_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> dict:
        return {
            "backlog_item_id": backlog_item_id,
            "runs": self._run_repo.list_runs_for_backlog_item(backlog_item_id, limit=limit),
        }

    def assemble_context(self, run_id: str) -> dict:
        return assemble_context_for_run(
            run_id=run_id,
            run_repo=self._run_repo,
            context_source=self._context_source,
            policy=self._token_policy,
            retry_count=self._resolve_retry_count(run_id),
        )

    def submit_phase3_gate(
        self,
        *,
        run_id: str,
        decision: str,
        gate_mode: str,
        reviewer_id: str,
        reason_code: str | None = None,
        auto_retry: bool = True,
    ) -> dict:
        return submit_gate_decision(
            run_id=run_id,
            decision=decision,
            gate_mode=gate_mode,
            reviewer_id=reviewer_id,
            reason_code=reason_code,
            auto_retry=auto_retry,
            run_repo=self._run_repo,
            inbox_service=self._inbox_service,
            review_service=self._review_service,
            context_source=self._context_source,
            policy=self._token_policy,
        )

    def gate_reason_codes(self) -> dict[str, list[str]]:
        return self._review_service.reason_code_catalog()

    def generate_phase4_selectors(self, run_id: str) -> dict:
        return generate_selectors_for_run(
            run_id=run_id,
            run_repo=self._run_repo,
            generation_service=self._generation_service,
        )

    def review_phase5_selectors(
        self,
        *,
        run_id: str,
        decision: str,
        reviewer_id: str,
        reason_code: str | None,
        edited_selector_steps: list[dict] | None,
    ) -> dict:
        return submit_selector_review(
            run_id=run_id,
            decision=decision,
            reviewer_id=reviewer_id,
            reason_code=reason_code,
            edited_selector_steps=edited_selector_steps,
            run_repo=self._run_repo,
            review_service=self._selector_review_service,
        )

    def phase5_review_reason_codes(self) -> dict[str, list[str]]:
        return self._selector_review_service.reason_code_catalog()

    def emit_phase5_handoff(self, run_id: str) -> dict:
        return emit_phase5_handoff(
            run_id=run_id,
            run_repo=self._run_repo,
            handoff_service=self._handoff_service,
        )

    def apply_phase6_feedback(
        self,
        *,
        run_id: str,
        message_id: str,
        source_agent4_run_id: str,
        outcome: str,
        recommended_action: str,
        step_results: list[dict],
        summary: dict,
        metadata: dict,
    ) -> dict:
        return apply_execution_feedback(
            run_id=run_id,
            message_id=message_id,
            source_agent4_run_id=source_agent4_run_id,
            outcome=outcome,
            recommended_action=recommended_action,
            step_results=step_results,
            summary=summary,
            metadata=metadata,
            run_repo=self._run_repo,
            feedback_service=self._execution_feedback_service,
        )

    def phase6_feedback_reason_codes(self) -> dict[str, list[str]]:
        return self._execution_feedback_service.reason_code_catalog()

    def get_phase7_observability(self, run_id: str) -> dict:
        return get_phase7_observability(
            run_id=run_id,
            run_repo=self._run_repo,
        )

    def get_phase8_integrity_report(self, run_id: str) -> dict:
        return get_phase8_integrity_report(
            run_id=run_id,
            run_repo=self._run_repo,
        )
