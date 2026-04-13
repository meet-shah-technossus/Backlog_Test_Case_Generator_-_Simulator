from __future__ import annotations

import pathlib
import sys
from unittest.mock import Mock

import pytest

# Ensure backend package imports resolve when running tests from workspace root.
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.modules.agent5.workflow.gate8_service import Agent5Gate8Service
from app.modules.agent5.workflow.observability_service import Agent5ObservabilityService
from app.modules.agent5.workflow.orchestrator_service import Agent5OrchestratorService
from app.modules.agent5.workflow.reliability_service import Agent5ReliabilityService


class TestAgent5Gate8Service:
    def test_submit_gate8_confirm_persists_and_transitions(self) -> None:
        run_repo = Mock()
        run_repo.get_run.return_value = {"agent5_run_id": "run-1", "state": "gate8_pending"}
        persistence = Mock()
        orchestrator = Mock()
        orchestrator.apply_command.return_value = {"run": {"agent5_run_id": "run-1", "state": "completed"}}

        service = Agent5Gate8Service(run_repo=run_repo, persistence_service=persistence, orchestrator_service=orchestrator)

        result = service.submit_gate8_decision(
            agent5_run_id="run-1",
            reviewer_id="qa-user",
            decision="confirm",
            reason_code="all_good",
            comment="ready to close",
        )

        assert result["run"]["state"] == "completed"
        persistence.persist_gate8_decision.assert_called_once()
        persisted_payload = persistence.persist_gate8_decision.call_args.kwargs["decision"]
        assert persisted_payload["decision"] == "confirm"
        assert persisted_payload["phase"] == "A5.10"

        orchestrator.apply_command.assert_called_once_with(
            agent5_run_id="run-1",
            command="gate8_confirm",
            actor="qa-user",
            context={
                "phase": "A5.10",
                "decision": "confirm",
                "reason_code": "all_good",
                "comment": "ready to close",
            },
        )

    def test_submit_gate8_decision_rejects_invalid_state(self) -> None:
        run_repo = Mock()
        run_repo.get_run.return_value = {"agent5_run_id": "run-1", "state": "writeback_pending"}
        persistence = Mock()
        orchestrator = Mock()

        service = Agent5Gate8Service(run_repo=run_repo, persistence_service=persistence, orchestrator_service=orchestrator)

        with pytest.raises(ValueError, match="gate8_pending"):
            service.submit_gate8_decision(
                agent5_run_id="run-1",
                reviewer_id="qa-user",
                decision="confirm",
                reason_code="all_good",
                comment=None,
            )

        persistence.persist_gate8_decision.assert_not_called()
        orchestrator.apply_command.assert_not_called()


class TestAgent5ObservabilityService:
    def test_observability_payload_shape_and_stage_duration(self) -> None:
        run_repo = Mock()
        run_repo.get_run.return_value = {
            "agent5_run_id": "run-obs",
            "state": "gate8_pending",
            "stage": "a5_gate8_pending",
            "execution_summary": {"evidence_manifest": {"videos": ["v1.mp4", "v1.mp4"]}},
            "step_evidence_refs": [
                {"evidence": {"screenshot_path": "s1.png", "trace_path": "t1.zip", "video_path": "v2.mp4"}},
                {"evidence": {"screenshot_path": "s1.png", "trace_path": "", "video_path": ""}},
            ],
            "stage7_analysis": {"quality": "ok"},
            "gate7_decision": {"decision": "approve"},
            "stage8_writeback": {"items": 3},
            "gate8_decision": {"decision": "confirm"},
        }
        run_repo.get_timeline_events.return_value = [
            {"created_at": "2026-01-01T00:00:00", "stage": "a5_gate7_pending", "actor": "agent5-ui"},
            {"created_at": "2026-01-01T00:00:01", "stage": "a5_gate8_pending", "actor": "agent5-ui"},
        ]
        run_repo.get_artifacts.return_value = [{"artifact_type": "state_transition_audit"}]

        service = Agent5ObservabilityService(run_repo=run_repo)
        result = service.get_run_observability(agent5_run_id="run-obs")

        assert result["phase"] == "A5.11"
        assert result["timeline_count"] == 2
        assert result["artifact_count"] == 1
        assert result["stage_durations"][0]["duration_ms_to_next"] == 1000
        assert result["stage_durations"][1]["duration_ms_to_next"] is None
        assert result["evidence_summary"]["screenshots"] == ["s1.png"]
        assert result["evidence_summary"]["videos"] == ["v2.mp4", "v1.mp4"]

        checksums = result["payload_checksums"]
        for key in [
            "execution_summary",
            "step_evidence_refs",
            "stage7_analysis",
            "gate7_decision",
            "stage8_writeback",
            "gate8_decision",
        ]:
            assert key in checksums
            assert len(checksums[key]) == 64


class TestAgent5ReliabilityService:
    def test_recover_stale_runs_marks_failed(self) -> None:
        run_repo = Mock()
        run_repo.list_runs_by_states.return_value = [
            {"agent5_run_id": "run-a", "state": "running"},
            {"agent5_run_id": "run-b", "state": "gate8_pending"},
        ]
        persistence = Mock()

        service = Agent5ReliabilityService(run_repo=run_repo, persistence_service=persistence)
        result = service.recover_stale_runs(actor="recovery-bot", older_than_seconds=1800, limit=50)

        assert result["phase"] == "A5.12"
        assert result["recovered_count"] == 2
        assert run_repo.update_state.call_count == 2
        assert run_repo.add_timeline_event.call_count == 2

    def test_retry_failed_run_moves_to_expected_retry_state(self) -> None:
        run_repo = Mock()
        run_repo.get_run.return_value = {
            "agent5_run_id": "run-failed",
            "state": "failed",
            "stage": "a5_gate8_pending",
        }
        persistence = Mock()
        persistence.get_run_snapshot.return_value = {"run": {"agent5_run_id": "run-failed", "state": "gate8_pending"}}

        service = Agent5ReliabilityService(run_repo=run_repo, persistence_service=persistence)
        result = service.retry_failed_run(agent5_run_id="run-failed", actor="agent5-ui")

        assert result["run"]["state"] == "gate8_pending"
        run_repo.update_state.assert_called_once_with(
            agent5_run_id="run-failed",
            state="gate8_pending",
            stage="a5_gate8_pending",
            last_error_code=None,
            last_error_message=None,
        )
        run_repo.add_timeline_event.assert_called_once()
        persistence.get_run_snapshot.assert_called_once_with("run-failed")

    def test_retry_failed_run_rejects_non_failed_state(self) -> None:
        run_repo = Mock()
        run_repo.get_run.return_value = {
            "agent5_run_id": "run-ok",
            "state": "gate8_pending",
            "stage": "a5_gate8_pending",
        }
        persistence = Mock()

        service = Agent5ReliabilityService(run_repo=run_repo, persistence_service=persistence)

        with pytest.raises(ValueError, match="only when run state is failed"):
            service.retry_failed_run(agent5_run_id="run-ok", actor="agent5-ui")


class TestAgent5OrchestratorService:
    def test_apply_command_ignores_duplicate_recent_command(self) -> None:
        run_repo = Mock()
        run_repo.get_run.return_value = {
            "agent5_run_id": "run-dup",
            "state": "analysis_pending",
            "stage": "a5_analysis_pending",
        }
        run_repo.get_timeline_events.return_value = [
            {
                "action": "command_applied",
                "actor": "agent5-ui",
                "metadata": {
                    "command": "submit_gate7",
                    "from_state": "analysis_pending",
                },
            }
        ]
        persistence = Mock()
        persistence.get_run_snapshot.return_value = {
            "run": {"agent5_run_id": "run-dup", "state": "analysis_pending"}
        }

        service = Agent5OrchestratorService(run_repo=run_repo, persistence_service=persistence)
        result = service.apply_command(
            agent5_run_id="run-dup",
            command="submit_gate7",
            actor="agent5-ui",
            context={"source": "test"},
        )

        assert result["run"]["state"] == "analysis_pending"
        run_repo.update_state.assert_not_called()
        run_repo.add_artifact.assert_not_called()
        run_repo.add_timeline_event.assert_not_called()
        persistence.get_run_snapshot.assert_called_once_with("run-dup")
