from __future__ import annotations

from app.modules.agent2.workflow.state_machine import AGENT2_ALLOWED_STATES


def get_agent2_blueprint() -> dict:
    return {
        "agent": "agent_2",
        "phase_window": [0, 1],
        "status": "scaffolded",
        "states": sorted(AGENT2_ALLOWED_STATES),
        "modules": [
            "contracts",
            "intake",
            "generation",
            "review",
            "handoff",
            "db",
            "workflow",
        ],
        "next_phase": "phase-2-input-contract-and-inbox",
    }
