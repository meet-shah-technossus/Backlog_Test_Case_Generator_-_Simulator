from __future__ import annotations

from app.modules.agent3.workflow.state_machine import AGENT3_ALLOWED_STATES


def get_agent3_blueprint() -> dict:
    return {
        "agent": "agent_3",
        "phase_window": [0, 8],
        "status": "phase8_started",
        "states": sorted(AGENT3_ALLOWED_STATES),
        "modules": [
            "contracts",
            "intake",
            "context",
            "generation",
            "review",
            "handoff",
            "db",
            "workflow",
        ],
        "next_phase": "phase-9-release-readiness",
    }
