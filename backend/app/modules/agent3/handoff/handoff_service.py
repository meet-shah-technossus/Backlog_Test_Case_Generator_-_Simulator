from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5


class Agent3HandoffService:
    """Phase 5 Agent3 -> Agent4 handoff envelope builder."""

    def build_envelope(self, *, run: dict, selector_artifact_row: dict) -> dict:
        run_id = str(run.get("run_id") or "")
        trace_id = str(run.get("trace_id") or "")
        source_agent2_run_id = str(run.get("source_agent2_run_id") or "")
        artifact_version = int(selector_artifact_row.get("artifact_version") or 0)
        artifact = selector_artifact_row.get("artifact") if isinstance(selector_artifact_row, dict) else {}

        message_id = str(uuid5(NAMESPACE_URL, f"agent3-agent4:{run_id}:{artifact_version}"))
        dedupe_key = str(uuid5(NAMESPACE_URL, f"agent3-agent4:{run_id}:{artifact_version}:execute"))

        return {
            "message_id": message_id,
            "run_id": run_id,
            "trace_id": trace_id,
            "from_agent": "agent_3",
            "to_agent": "agent_4",
            "stage_id": "execute",
            "task_type": "execute_selectors",
            "contract_version": "v1",
            "retry_count": 0,
            "dedupe_key": dedupe_key,
            "payload": {
                "run_id": run_id,
                "trace_id": trace_id,
                "source_agent2_run_id": source_agent2_run_id,
                "artifact_version": artifact_version,
                "selector_plan": artifact,
            },
        }
