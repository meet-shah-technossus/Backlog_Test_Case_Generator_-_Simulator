from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.infrastructure.openai_client import OpenAIClient
from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.agent1.db.run_repository import Agent1RunRepository
from app.modules.agent1.workflow.use_cases.create_run import create_run
from app.modules.agent1.workflow.use_cases.generate_run import generate_run
from app.modules.agent1.workflow.use_cases.get_snapshot import get_run_snapshot
from app.modules.agent1.workflow.use_cases.handoff_run import emit_handoff
from app.modules.agent1.workflow.use_cases.retry_run import retry_run
from app.modules.agent1.workflow.use_cases.review_run import submit_review


class Agent1Orchestrator:
    def __init__(
        self,
        backlog_repo: Agent1BacklogRepository,
        run_repo: Agent1RunRepository,
        openai_client: OpenAIClient,
    ):
        self._backlog_repo = backlog_repo
        self._run_repo = run_repo
        self._openai_client = openai_client

    def create_run(self, *, backlog_item_id: str) -> dict:
        run_id = create_run(
            backlog_item_id=backlog_item_id,
            backlog_repo=self._backlog_repo,
            run_repo=self._run_repo,
        )
        return self.get_run_snapshot(run_id)

    async def generate(self, *, run_id: str, model: str | None = None) -> dict:
        await generate_run(
            run_id=run_id,
            backlog_repo=self._backlog_repo,
            run_repo=self._run_repo,
            openai_client=self._openai_client,
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
            backlog_repo=self._backlog_repo,
            run_repo=self._run_repo,
            openai_client=self._openai_client,
            model=model,
            on_token=on_token,
        )
        return self.get_run_snapshot(run_id)

    def submit_review(
        self,
        *,
        run_id: str,
        decision: str,
        reviewer_id: str,
        reason_code: str | None = None,
        edited_payload: dict | None = None,
    ) -> dict:
        submit_review(
            run_id=run_id,
            decision=decision,
            reviewer_id=reviewer_id,
            reason_code=reason_code,
            edited_payload=edited_payload,
            backlog_repo=self._backlog_repo,
            run_repo=self._run_repo,
        )

        return self.get_run_snapshot(run_id)

    def retry(self, *, run_id: str, reason_code: str | None = None, actor: str = "human") -> dict:
        retry_run(
            run_id=run_id,
            reason_code=reason_code,
            actor=actor,
            run_repo=self._run_repo,
        )
        return self.get_run_snapshot(run_id)

    def emit_handoff(self, *, run_id: str) -> dict:
        emit_handoff(run_id=run_id, run_repo=self._run_repo)
        return self.get_run_snapshot(run_id)

    def get_run_snapshot(self, run_id: str) -> dict:
        return get_run_snapshot(run_id=run_id, backlog_repo=self._backlog_repo, run_repo=self._run_repo)

    def list_runs_for_backlog_item(self, backlog_item_id: str, limit: int = 50) -> list[dict]:
        return self._run_repo.list_runs_for_backlog_item(backlog_item_id, limit=limit)
