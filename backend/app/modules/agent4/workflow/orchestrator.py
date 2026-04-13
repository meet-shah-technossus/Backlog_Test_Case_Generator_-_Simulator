from __future__ import annotations

from app.modules.agent4.contracts.models import Agent4HandoffEnvelope
from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.feedback.execution_feedback_service import Agent4ExecutionFeedbackService
from app.modules.agent4.generation.script_generation_service import Agent4ScriptGenerationService
from app.modules.agent4.handoff.handoff_service import Agent4HandoffService
from app.modules.agent4.intake.handoff_inbox_service import Agent4HandoffInboxService
from app.modules.agent4.planning.script_blueprint_service import Agent4ScriptBlueprintService
from app.modules.agent4.review.review_service import Agent4ReviewService
from app.modules.agent4.review.script_review_service import Agent4ScriptReviewService
from app.modules.agent4.workflow.use_cases.consume_handoff import consume_handoff
from app.modules.agent4.workflow.use_cases.create_run_from_inbox import create_run_from_inbox
from app.modules.agent4.workflow.use_cases.apply_phase8_feedback import apply_phase8_feedback
from app.modules.agent4.workflow.use_cases.emit_phase7_handoff import emit_phase7_handoff
from app.modules.agent4.workflow.use_cases.generate_scripts import generate_phase5_scripts
from app.modules.agent4.workflow.use_cases.get_blueprint import get_agent4_blueprint
from app.modules.agent4.workflow.use_cases.get_phase9_integrity_report import get_phase9_integrity_report
from app.modules.agent4.workflow.use_cases.get_phase9_observability import get_phase9_observability
from app.modules.agent4.workflow.use_cases.get_run_snapshot import get_run_snapshot
from app.modules.agent4.workflow.use_cases.plan_scripts import plan_phase4_scripts
from app.modules.agent4.workflow.use_cases.preview_phase6_readiness import preview_phase6_readiness
from app.modules.agent4.workflow.use_cases.preview_gate_readiness import preview_phase3_gate_readiness
from app.modules.agent4.workflow.use_cases.submit_phase6_review import submit_phase6_review
from app.modules.agent4.workflow.use_cases.submit_gate import submit_phase3_gate


class Agent4Orchestrator:
    """Agent4 orchestration boundary with Phase 0/1 intake use-cases."""

    def __init__(
        self,
        inbox_service: Agent4HandoffInboxService,
        run_repo: Agent4RunRepository,
        planning_service: Agent4ScriptBlueprintService,
        generation_service: Agent4ScriptGenerationService,
        review_service: Agent4ReviewService,
        script_review_service: Agent4ScriptReviewService,
        handoff_service: Agent4HandoffService,
        execution_feedback_service: Agent4ExecutionFeedbackService,
    ):
        self._inbox_service = inbox_service
        self._run_repo = run_repo
        self._planning_service = planning_service
        self._generation_service = generation_service
        self._review_service = review_service
        self._script_review_service = script_review_service
        self._handoff_service = handoff_service
        self._execution_feedback_service = execution_feedback_service

    def get_blueprint(self) -> dict:
        return get_agent4_blueprint()

    def consume_handoff(self, envelope: Agent4HandoffEnvelope) -> dict:
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
        return submit_phase3_gate(
            run_id=run_id,
            decision=decision,
            gate_mode=gate_mode,
            reviewer_id=reviewer_id,
            reason_code=reason_code,
            auto_retry=auto_retry,
            run_repo=self._run_repo,
            inbox_service=self._inbox_service,
            review_service=self._review_service,
        )

    def gate_reason_codes(self) -> dict[str, list[str]]:
        return self._review_service.reason_code_catalog()

    def preview_phase3_gate_readiness(self, run_id: str) -> dict:
        return preview_phase3_gate_readiness(
            run_id=run_id,
            run_repo=self._run_repo,
            inbox_service=self._inbox_service,
            review_service=self._review_service,
        )

    def plan_phase4_scripts(self, run_id: str) -> dict:
        return plan_phase4_scripts(
            run_id=run_id,
            run_repo=self._run_repo,
            inbox_service=self._inbox_service,
            planning_service=self._planning_service,
        )

    def generate_phase5_scripts(self, run_id: str) -> dict:
        return generate_phase5_scripts(
            run_id=run_id,
            run_repo=self._run_repo,
            inbox_service=self._inbox_service,
            generation_service=self._generation_service,
        )

    def preview_phase6_readiness(self, run_id: str) -> dict:
        return preview_phase6_readiness(
            run_id=run_id,
            run_repo=self._run_repo,
            review_service=self._script_review_service,
        )

    def submit_phase6_review(
        self,
        *,
        run_id: str,
        decision: str,
        reviewer_id: str,
        reason_code: str | None = None,
        edited_scripts: list[dict] | None = None,
    ) -> dict:
        return submit_phase6_review(
            run_id=run_id,
            decision=decision,
            reviewer_id=reviewer_id,
            reason_code=reason_code,
            edited_scripts=edited_scripts,
            run_repo=self._run_repo,
            review_service=self._script_review_service,
        )

    def phase6_review_reason_codes(self) -> dict[str, list[str]]:
        return self._script_review_service.reason_code_catalog()

    def emit_phase7_handoff(self, run_id: str) -> dict:
        return emit_phase7_handoff(
            run_id=run_id,
            run_repo=self._run_repo,
            handoff_service=self._handoff_service,
        )

    def apply_phase8_feedback(
        self,
        *,
        run_id: str,
        message_id: str,
        source_agent5_run_id: str,
        outcome: str,
        recommended_action: str,
        step_results: list[dict],
        summary: dict,
        metadata: dict,
    ) -> dict:
        return apply_phase8_feedback(
            run_id=run_id,
            message_id=message_id,
            source_agent5_run_id=source_agent5_run_id,
            outcome=outcome,
            recommended_action=recommended_action,
            step_results=step_results,
            summary=summary,
            metadata=metadata,
            run_repo=self._run_repo,
            feedback_service=self._execution_feedback_service,
        )

    def phase8_feedback_reason_codes(self) -> dict[str, list[str]]:
        return self._execution_feedback_service.reason_code_catalog()

    def get_phase9_observability(self, run_id: str) -> dict:
        return get_phase9_observability(
            run_id=run_id,
            run_repo=self._run_repo,
        )

    def get_phase9_integrity_report(self, run_id: str) -> dict:
        return get_phase9_integrity_report(
            run_id=run_id,
            run_repo=self._run_repo,
        )
