from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.modules.agent2.contracts.models import Agent2HandoffEnvelope
from app.modules.agent2.db.run_repository import Agent2RunRepository
from app.modules.agent2.generation.generation_service import Agent2GenerationService
from app.modules.agent2.handoff.handoff_service import Agent2HandoffService
from app.modules.agent2.intake.handoff_inbox_service import Agent2HandoffInboxService
from app.modules.agent2.mcp.agent1_handoff_mcp_service import Agent1HandoffMCPService
from app.modules.agent2.review.review_service import Agent2ReviewService
from app.modules.agent2.workflow.use_cases.consume_handoff import consume_handoff
from app.modules.agent2.workflow.use_cases.create_run_from_inbox import create_run_from_inbox
from app.modules.agent2.workflow.use_cases.generate_run import generate_run
from app.modules.agent2.workflow.use_cases.get_blueprint import get_agent2_blueprint
from app.modules.agent2.workflow.use_cases.get_run_snapshot import get_run_snapshot
from app.modules.agent2.workflow.use_cases.handoff_run import emit_handoff
from app.modules.agent2.workflow.use_cases.review_run import get_review_diff, submit_review


class Agent2Orchestrator:
    """Agent2 orchestration boundary with Phase 2 intake use-cases."""

    def __init__(
        self,
        inbox_service: Agent2HandoffInboxService,
        run_repo: Agent2RunRepository,
        generation_service: Agent2GenerationService,
        review_service: Agent2ReviewService,
        handoff_service: Agent2HandoffService,
        agent1_handoff_mcp_service: Agent1HandoffMCPService,
    ):
        self._inbox_service = inbox_service
        self._run_repo = run_repo
        self._generation_service = generation_service
        self._review_service = review_service
        self._handoff_service = handoff_service
        self._agent1_handoff_mcp_service = agent1_handoff_mcp_service

    def get_blueprint(self) -> dict:
        return get_agent2_blueprint()

    def consume_handoff(self, envelope: Agent2HandoffEnvelope) -> dict:
        return consume_handoff(
            envelope=envelope,
            inbox_service=self._inbox_service,
        )

    def consume_agent1_handoff(self, agent1_run_id: str) -> dict:
        envelope = self._agent1_handoff_mcp_service.read_latest_agent1_envelope(agent1_run_id)
        return consume_handoff(
            envelope=envelope,
            inbox_service=self._inbox_service,
        )

    def list_approved_agent1_runs(
        self,
        backlog_item_id: str,
        limit: int = 50,
        *,
        handoff_only: bool = True,
    ) -> dict:
        runs = self._agent1_handoff_mcp_service.list_approved_runs_for_backlog_item(
            backlog_item_id,
            limit=limit,
            handoff_only=handoff_only,
        )
        return {
            'backlog_item_id': backlog_item_id,
            'runs': runs,
        }

    def start_from_agent1_run(self, agent1_run_id: str) -> dict:
        envelope = self._agent1_handoff_mcp_service.read_latest_agent1_envelope(agent1_run_id)
        consume_result = consume_handoff(
            envelope=envelope,
            inbox_service=self._inbox_service,
        )
        create_result = create_run_from_inbox(
            message_id=envelope.message_id,
            inbox_service=self._inbox_service,
            run_repo=self._run_repo,
        )
        run_id = (create_result.get('run') or {}).get('run_id')
        snapshot = self.get_run_snapshot(run_id) if run_id else None
        return {
            'agent1_run_id': agent1_run_id,
            'message_id': envelope.message_id,
            'consume': consume_result,
            'create': create_result,
            'snapshot': snapshot,
        }

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
            'backlog_item_id': backlog_item_id,
            'runs': self._run_repo.list_runs_for_backlog_item(backlog_item_id, limit=limit),
        }

    def get_timeline(self, run_id: str, order: str = 'asc') -> dict:
        run = self._run_repo.get_run(run_id)
        if run is None:
            raise ValueError(f"Agent2 run '{run_id}' not found")
        ascending = order.lower() != 'desc'
        return {
            'run_id': run_id,
            'order': 'asc' if ascending else 'desc',
            'events': self._run_repo.get_timeline_events(run_id, ascending=ascending),
        }

    def get_observability_counters(self, backlog_item_id: str | None = None) -> dict:
        counters = self._run_repo.get_observability_counters(backlog_item_id=backlog_item_id)
        return {
            'scope': {'backlog_item_id': backlog_item_id},
            'counters': counters,
        }

    async def generate(self, run_id: str, model: str | None = None) -> dict:
        await generate_run(
            run_id=run_id,
            run_repo=self._run_repo,
            inbox_service=self._inbox_service,
            agent1_handoff_mcp_service=self._agent1_handoff_mcp_service,
            generation_service=self._generation_service,
            model=model,
        )
        return self.get_run_snapshot(run_id)

    async def generate_stream(
        self,
        *,
        run_id: str,
        model: str | None = None,
        on_token: Callable[[str], Awaitable[None] | None] | None = None,
    ) -> dict:
        await generate_run(
            run_id=run_id,
            run_repo=self._run_repo,
            inbox_service=self._inbox_service,
            agent1_handoff_mcp_service=self._agent1_handoff_mcp_service,
            generation_service=self._generation_service,
            model=model,
            on_token=on_token,
        )
        return self.get_run_snapshot(run_id)

    def review(
        self,
        *,
        run_id: str,
        decision: str,
        reviewer_id: str,
        reason_code: str | None,
        edited_payload: dict | None,
    ) -> dict:
        submit_review(
            run_id=run_id,
            decision=decision,
            reviewer_id=reviewer_id,
            reason_code=reason_code,
            edited_payload=edited_payload,
            run_repo=self._run_repo,
            review_service=self._review_service,
        )
        return self.get_run_snapshot(run_id)

    def review_diff(self, run_id: str) -> dict:
        return get_review_diff(
            run_id=run_id,
            run_repo=self._run_repo,
            review_service=self._review_service,
        )

    def review_reason_codes(self) -> dict:
        return self._review_service.reason_code_catalog()

    def handoff(self, run_id: str) -> dict:
        result = emit_handoff(
            run_id=run_id,
            run_repo=self._run_repo,
            handoff_service=self._handoff_service,
        )
        return {
            "created": result["created"],
            "snapshot": self.get_run_snapshot(run_id),
        }
