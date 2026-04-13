from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5


class Agent4HandoffService:
    """Phase 7 Agent4 -> Agent5 handoff envelope builder."""

    def build_envelope(self, *, run: dict, script_bundle_row: dict) -> dict:
        run_id = str(run.get("run_id") or "")
        trace_id = str(run.get("trace_id") or "")
        source_agent3_run_id = str(run.get("source_agent3_run_id") or "")

        artifact_version = int(script_bundle_row.get("artifact_version") or 0)
        artifact = script_bundle_row.get("artifact") if isinstance(script_bundle_row, dict) else {}
        artifact = artifact if isinstance(artifact, dict) else {}

        message_id = str(uuid5(NAMESPACE_URL, f"agent4-agent5:{run_id}:{artifact_version}"))
        dedupe_key = str(uuid5(NAMESPACE_URL, f"agent4-agent5:{run_id}:{artifact_version}:execute"))

        return {
            "message_id": message_id,
            "run_id": run_id,
            "trace_id": trace_id,
            "from_agent": "agent_4",
            "to_agent": "agent_5",
            "stage_id": "execution",
            "task_type": "execute_generated_scripts",
            "contract_version": "v1",
            "retry_count": 0,
            "dedupe_key": dedupe_key,
            "payload": {
                "run_id": run_id,
                "trace_id": trace_id,
                "source_agent3_run_id": source_agent3_run_id,
                "artifact_version": artifact_version,
                "script_bundle": artifact,
            },
        }
