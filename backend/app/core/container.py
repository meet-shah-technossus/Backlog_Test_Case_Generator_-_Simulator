from __future__ import annotations

from dataclasses import dataclass, field

from app.infrastructure.openai_client import OpenAIClient
from app.infrastructure.store import store
from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository
from app.modules.agent1.db.run_repository import Agent1RunRepository
from app.modules.agent1.mcp.backlog_intake_service import MCPBacklogIntakeService
from app.modules.agent1.workflow.orchestrator import Agent1Orchestrator
from app.modules.agent2.db.inbox_repository import Agent2InboxRepository
from app.modules.agent2.db.run_repository import Agent2RunRepository
from app.modules.agent2.generation.generation_service import Agent2GenerationService
from app.modules.agent2.handoff.handoff_service import Agent2HandoffService
from app.modules.agent2.intake.handoff_inbox_service import Agent2HandoffInboxService
from app.modules.agent2.mcp.agent1_handoff_mcp_service import Agent1HandoffMCPService
from app.modules.agent2.review.review_service import Agent2ReviewService
from app.modules.agent2.workflow.orchestrator import Agent2Orchestrator
from app.modules.agent3.context.context_source_service import Agent3ContextSourceService
from app.modules.agent3.context.policy import TokenSafeCrawlContextPolicy
from app.modules.agent3.db.inbox_repository import Agent3InboxRepository
from app.modules.agent3.db.run_repository import Agent3RunRepository
from app.modules.agent3.feedback.execution_feedback_service import Agent3ExecutionFeedbackService
from app.modules.agent3.generation.selector_generation_service import Agent3SelectorGenerationService
from app.modules.agent3.handoff.handoff_service import Agent3HandoffService
from app.modules.agent3.intake.handoff_inbox_service import Agent3HandoffInboxService
from app.modules.agent3.review.review_service import Agent3ReviewService
from app.modules.agent3.review.selector_review_service import Agent3SelectorReviewService
from app.modules.agent3.workflow.orchestrator import Agent3Orchestrator
from app.modules.agent4.db.inbox_repository import Agent4InboxRepository
from app.modules.agent4.db.run_repository import Agent4RunRepository
from app.modules.agent4.feedback.execution_feedback_service import Agent4ExecutionFeedbackService
from app.modules.agent4.generation.script_generation_service import Agent4ScriptGenerationService
from app.modules.agent4.handoff.handoff_service import Agent4HandoffService
from app.modules.agent4.intake.handoff_inbox_service import Agent4HandoffInboxService
from app.modules.agent4.planning.script_blueprint_service import Agent4ScriptBlueprintService
from app.modules.agent4.review.review_service import Agent4ReviewService
from app.modules.agent4.review.script_review_service import Agent4ScriptReviewService
from app.modules.agent4.workflow.orchestrator import Agent4Orchestrator
from app.modules.agent5.db.run_repository import Agent5RunRepository
from app.modules.agent5.workflow.analysis_service import Agent5AnalysisService
from app.modules.agent5.workflow.gate_service import Agent5GateService
from app.modules.agent5.workflow.gate8_service import Agent5Gate8Service
from app.modules.agent5.workflow.observability_service import Agent5ObservabilityService
from app.modules.agent5.workflow.reliability_service import Agent5ReliabilityService
from app.modules.agent5.workflow.orchestrator_service import Agent5OrchestratorService
from app.modules.agent5.workflow.persistence_service import Agent5PersistenceService
from app.modules.agent5.workflow.writeback_service import Agent5WritebackService
from app.modules.execution.db.execution_run_repository import ExecutionRunRepository
from app.modules.execution.runtime.playwright_runtime_service import PlaywrightRuntimeService
from app.modules.execution.workflow.dispatcher_service import ExecutionDispatcherService
from app.modules.execution.workflow.lifecycle_service import ExecutionLifecycleService
from app.modules.agent1.services.backlog_service import BacklogService
from app.modules.scraper.fetch.fetch_service import ScraperFetchService
from app.modules.scraper.db.job_repository import ScraperJobRepository
from app.modules.scraper.workflow.orchestrator import ScraperOrchestrator


@dataclass
class AppContainer:
    store: object = store
    _openai_client: OpenAIClient = field(default_factory=OpenAIClient)
    _backlog_service: BacklogService = field(default_factory=BacklogService)
    _agent1_backlog_repository: Agent1BacklogRepository = field(default_factory=Agent1BacklogRepository)
    _agent1_run_repository: Agent1RunRepository = field(default_factory=Agent1RunRepository)
    _agent1_mcp_backlog_intake_service: MCPBacklogIntakeService | None = None
    _agent1_orchestrator: Agent1Orchestrator | None = None
    _agent2_inbox_repository: Agent2InboxRepository = field(default_factory=Agent2InboxRepository)
    _agent2_run_repository: Agent2RunRepository = field(default_factory=Agent2RunRepository)
    _agent2_generation_service: Agent2GenerationService | None = None
    _agent2_review_service: Agent2ReviewService | None = None
    _agent2_handoff_service: Agent2HandoffService | None = None
    _agent2_agent1_handoff_mcp_service: Agent1HandoffMCPService | None = None
    _agent2_handoff_inbox_service: Agent2HandoffInboxService | None = None
    _agent2_orchestrator: Agent2Orchestrator | None = None
    _agent3_inbox_repository: Agent3InboxRepository = field(default_factory=Agent3InboxRepository)
    _agent3_run_repository: Agent3RunRepository = field(default_factory=Agent3RunRepository)
    _agent3_context_source: Agent3ContextSourceService = field(default_factory=Agent3ContextSourceService)
    _agent3_token_policy: TokenSafeCrawlContextPolicy = field(default_factory=TokenSafeCrawlContextPolicy)
    _agent3_review_service: Agent3ReviewService = field(default_factory=Agent3ReviewService)
    _agent3_generation_service: Agent3SelectorGenerationService = field(default_factory=Agent3SelectorGenerationService)
    _agent3_selector_review_service: Agent3SelectorReviewService = field(default_factory=Agent3SelectorReviewService)
    _agent3_handoff_service: Agent3HandoffService = field(default_factory=Agent3HandoffService)
    _agent3_execution_feedback_service: Agent3ExecutionFeedbackService = field(default_factory=Agent3ExecutionFeedbackService)
    _agent3_handoff_inbox_service: Agent3HandoffInboxService | None = None
    _agent3_orchestrator: Agent3Orchestrator | None = None
    _agent4_inbox_repository: Agent4InboxRepository = field(default_factory=Agent4InboxRepository)
    _agent4_run_repository: Agent4RunRepository = field(default_factory=Agent4RunRepository)
    _agent4_planning_service: Agent4ScriptBlueprintService = field(default_factory=Agent4ScriptBlueprintService)
    _agent4_generation_service: Agent4ScriptGenerationService = field(default_factory=Agent4ScriptGenerationService)
    _agent4_review_service: Agent4ReviewService = field(default_factory=Agent4ReviewService)
    _agent4_script_review_service: Agent4ScriptReviewService = field(default_factory=Agent4ScriptReviewService)
    _agent4_handoff_service: Agent4HandoffService = field(default_factory=Agent4HandoffService)
    _agent4_execution_feedback_service: Agent4ExecutionFeedbackService = field(default_factory=Agent4ExecutionFeedbackService)
    _agent4_handoff_inbox_service: Agent4HandoffInboxService | None = None
    _agent4_orchestrator: Agent4Orchestrator | None = None
    _agent5_run_repository: Agent5RunRepository = field(default_factory=Agent5RunRepository)
    _agent5_persistence_service: Agent5PersistenceService | None = None
    _agent5_analysis_service: Agent5AnalysisService | None = None
    _agent5_orchestrator_service: Agent5OrchestratorService | None = None
    _agent5_gate_service: Agent5GateService | None = None
    _agent5_gate8_service: Agent5Gate8Service | None = None
    _agent5_writeback_service: Agent5WritebackService | None = None
    _agent5_observability_service: Agent5ObservabilityService | None = None
    _agent5_reliability_service: Agent5ReliabilityService | None = None
    _execution_run_repository: ExecutionRunRepository = field(default_factory=ExecutionRunRepository)
    _execution_runtime_service: PlaywrightRuntimeService = field(default_factory=PlaywrightRuntimeService)
    _execution_lifecycle_service: ExecutionLifecycleService | None = None
    _execution_dispatcher_service: ExecutionDispatcherService | None = None
    _scraper_job_repository: ScraperJobRepository = field(default_factory=ScraperJobRepository)
    _scraper_fetch_service: ScraperFetchService = field(default_factory=ScraperFetchService)
    _scraper_orchestrator: ScraperOrchestrator | None = None

    def get_backlog_service(self) -> BacklogService:
        return self._backlog_service

    def get_agent1_mcp_backlog_intake_service(self) -> MCPBacklogIntakeService:
        if self._agent1_mcp_backlog_intake_service is None:
            self._agent1_mcp_backlog_intake_service = MCPBacklogIntakeService(
                backlog_service=self._backlog_service,
                backlog_repo=self._agent1_backlog_repository,
            )
        return self._agent1_mcp_backlog_intake_service

    def get_agent1_orchestrator(self) -> Agent1Orchestrator:
        if self._agent1_orchestrator is None:
            self._agent1_orchestrator = Agent1Orchestrator(
                backlog_repo=self._agent1_backlog_repository,
                run_repo=self._agent1_run_repository,
                openai_client=self._openai_client,
            )
        return self._agent1_orchestrator

    def get_openai_client(self) -> OpenAIClient:
        return self._openai_client

    def get_agent2_handoff_inbox_service(self) -> Agent2HandoffInboxService:
        if self._agent2_handoff_inbox_service is None:
            self._agent2_handoff_inbox_service = Agent2HandoffInboxService(
                inbox_repo=self._agent2_inbox_repository,
            )
        return self._agent2_handoff_inbox_service

    def get_agent2_generation_service(self) -> Agent2GenerationService:
        if self._agent2_generation_service is None:
            self._agent2_generation_service = Agent2GenerationService(
                openai_client=self._openai_client,
            )
        return self._agent2_generation_service

    def get_agent2_review_service(self) -> Agent2ReviewService:
        if self._agent2_review_service is None:
            self._agent2_review_service = Agent2ReviewService()
        return self._agent2_review_service

    def get_agent2_handoff_service(self) -> Agent2HandoffService:
        if self._agent2_handoff_service is None:
            self._agent2_handoff_service = Agent2HandoffService()
        return self._agent2_handoff_service

    def get_agent2_agent1_handoff_mcp_service(self) -> Agent1HandoffMCPService:
        if self._agent2_agent1_handoff_mcp_service is None:
            self._agent2_agent1_handoff_mcp_service = Agent1HandoffMCPService()
        return self._agent2_agent1_handoff_mcp_service

    def get_agent2_orchestrator(self) -> Agent2Orchestrator:
        if self._agent2_orchestrator is None:
            self._agent2_orchestrator = Agent2Orchestrator(
                inbox_service=self.get_agent2_handoff_inbox_service(),
                run_repo=self._agent2_run_repository,
                generation_service=self.get_agent2_generation_service(),
                review_service=self.get_agent2_review_service(),
                handoff_service=self.get_agent2_handoff_service(),
                agent1_handoff_mcp_service=self.get_agent2_agent1_handoff_mcp_service(),
            )
        return self._agent2_orchestrator

    def get_scraper_orchestrator(self) -> ScraperOrchestrator:
        if self._scraper_orchestrator is None:
            self._scraper_orchestrator = ScraperOrchestrator(
                backlog_repo=self._agent1_backlog_repository,
                job_repo=self._scraper_job_repository,
                fetch_service=self._scraper_fetch_service,
            )
        return self._scraper_orchestrator

    def get_agent3_orchestrator(self) -> Agent3Orchestrator:
        if self._agent3_orchestrator is None:
            self._agent3_orchestrator = Agent3Orchestrator(
                inbox_service=self.get_agent3_handoff_inbox_service(),
                run_repo=self._agent3_run_repository,
                context_source=self._agent3_context_source,
                token_policy=self._agent3_token_policy,
                review_service=self._agent3_review_service,
                generation_service=self._agent3_generation_service,
                selector_review_service=self._agent3_selector_review_service,
                handoff_service=self._agent3_handoff_service,
                execution_feedback_service=self._agent3_execution_feedback_service,
            )
        return self._agent3_orchestrator

    def get_agent3_handoff_inbox_service(self) -> Agent3HandoffInboxService:
        if self._agent3_handoff_inbox_service is None:
            self._agent3_handoff_inbox_service = Agent3HandoffInboxService(
                inbox_repo=self._agent3_inbox_repository,
            )
        return self._agent3_handoff_inbox_service

    def get_agent4_orchestrator(self) -> Agent4Orchestrator:
        if self._agent4_orchestrator is None:
            self._agent4_orchestrator = Agent4Orchestrator(
                inbox_service=self.get_agent4_handoff_inbox_service(),
                run_repo=self._agent4_run_repository,
                planning_service=self._agent4_planning_service,
                generation_service=self._agent4_generation_service,
                review_service=self._agent4_review_service,
                script_review_service=self._agent4_script_review_service,
                handoff_service=self._agent4_handoff_service,
                execution_feedback_service=self._agent4_execution_feedback_service,
            )
        return self._agent4_orchestrator

    def get_agent4_handoff_inbox_service(self) -> Agent4HandoffInboxService:
        if self._agent4_handoff_inbox_service is None:
            self._agent4_handoff_inbox_service = Agent4HandoffInboxService(
                inbox_repo=self._agent4_inbox_repository,
            )
        return self._agent4_handoff_inbox_service

    def get_execution_runtime_service(self) -> PlaywrightRuntimeService:
        return self._execution_runtime_service

    def get_execution_lifecycle_service(self) -> ExecutionLifecycleService:
        if self._execution_lifecycle_service is None:
            self._execution_lifecycle_service = ExecutionLifecycleService(
                execution_repo=self._execution_run_repository,
                agent4_run_repo=self._agent4_run_repository,
                runtime_service=self._execution_runtime_service,
            )
        return self._execution_lifecycle_service

    def get_execution_dispatcher_service(self) -> ExecutionDispatcherService:
        if self._execution_dispatcher_service is None:
            self._execution_dispatcher_service = ExecutionDispatcherService(
                lifecycle_service=self.get_execution_lifecycle_service(),
            )
        return self._execution_dispatcher_service

    def get_agent5_persistence_service(self) -> Agent5PersistenceService:
        if self._agent5_persistence_service is None:
            self._agent5_persistence_service = Agent5PersistenceService(
                run_repo=self._agent5_run_repository,
                agent4_run_repo=self._agent4_run_repository,
                execution_repo=self._execution_run_repository,
            )
        return self._agent5_persistence_service

    def get_agent5_orchestrator_service(self) -> Agent5OrchestratorService:
        if self._agent5_orchestrator_service is None:
            self._agent5_orchestrator_service = Agent5OrchestratorService(
                run_repo=self._agent5_run_repository,
                persistence_service=self.get_agent5_persistence_service(),
            )
        return self._agent5_orchestrator_service

    def get_agent5_analysis_service(self) -> Agent5AnalysisService:
        if self._agent5_analysis_service is None:
            self._agent5_analysis_service = Agent5AnalysisService(
                run_repo=self._agent5_run_repository,
                persistence_service=self.get_agent5_persistence_service(),
            )
        return self._agent5_analysis_service

    def get_agent5_gate_service(self) -> Agent5GateService:
        if self._agent5_gate_service is None:
            self._agent5_gate_service = Agent5GateService(
                run_repo=self._agent5_run_repository,
                persistence_service=self.get_agent5_persistence_service(),
                orchestrator_service=self.get_agent5_orchestrator_service(),
            )
        return self._agent5_gate_service

    def get_agent5_writeback_service(self) -> Agent5WritebackService:
        if self._agent5_writeback_service is None:
            self._agent5_writeback_service = Agent5WritebackService(
                run_repo=self._agent5_run_repository,
                persistence_service=self.get_agent5_persistence_service(),
                orchestrator_service=self.get_agent5_orchestrator_service(),
            )
        return self._agent5_writeback_service

    def get_agent5_gate8_service(self) -> Agent5Gate8Service:
        if self._agent5_gate8_service is None:
            self._agent5_gate8_service = Agent5Gate8Service(
                run_repo=self._agent5_run_repository,
                persistence_service=self.get_agent5_persistence_service(),
                orchestrator_service=self.get_agent5_orchestrator_service(),
            )
        return self._agent5_gate8_service

    def get_agent5_observability_service(self) -> Agent5ObservabilityService:
        if self._agent5_observability_service is None:
            self._agent5_observability_service = Agent5ObservabilityService(
                run_repo=self._agent5_run_repository,
            )
        return self._agent5_observability_service

    def get_agent5_reliability_service(self) -> Agent5ReliabilityService:
        if self._agent5_reliability_service is None:
            self._agent5_reliability_service = Agent5ReliabilityService(
                run_repo=self._agent5_run_repository,
                persistence_service=self.get_agent5_persistence_service(),
            )
        return self._agent5_reliability_service


_container = AppContainer()


def get_container() -> AppContainer:
    return _container
