from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from app.modules.agent2.contracts.models import Agent2ToAgent3HandoffEnvelope


class Agent2HandoffService:
    """Agent2 -> Agent3 contract emission boundary."""

    def build_envelope(self, *, run: dict, latest_artifact: dict) -> Agent2ToAgent3HandoffEnvelope:
        run_id = str(run.get("run_id"))
        trace_id = str(run.get("trace_id"))
        source_agent1_run_id = str(run.get("source_agent1_run_id"))
        artifact = latest_artifact.get("artifact", {}) if isinstance(latest_artifact, dict) else {}
        artifact_version = latest_artifact.get("artifact_version") if isinstance(latest_artifact, dict) else None

        message_id = str(uuid5(NAMESPACE_URL, f"agent2-agent3:{run_id}"))
        dedupe_key = str(uuid5(NAMESPACE_URL, f"agent2-agent3:{run_id}:{artifact_version}"))

        payload = {
            "run_id": run_id,
            "trace_id": trace_id,
            "source_agent1_run_id": source_agent1_run_id,
            "artifact_version": artifact_version,
            "story_id": artifact.get("story_id"),
            "generated_steps": artifact.get("generated_steps", {}),
        }

        return Agent2ToAgent3HandoffEnvelope(
            message_id=message_id,
            run_id=run_id,
            trace_id=trace_id,
            stage_id="reasoning",
            retry_count=0,
            dedupe_key=dedupe_key,
            payload=payload,
        )

    def capability_summary(self) -> dict:
        return {
            "phase": "phase-5",
            "ready": True,
            "next": "phase-6-frontend-integration",
        }
