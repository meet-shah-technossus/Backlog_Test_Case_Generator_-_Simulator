from __future__ import annotations

from app.modules.agent4.workflow.state_machine import AGENT4_ALLOWED_STATES


def get_agent4_blueprint() -> dict:
    return {
        "agent": "agent_4",
        "phase_window": [0, 9],
        "status": "phase9_started",
        "states": sorted(AGENT4_ALLOWED_STATES),
        "modules": [
            "contracts",
            "intake",
            "feedback",
            "generation",
            "handoff",
            "review",
            "planning",
            "db",
            "workflow",
        ],
        "next_phase": "phase-10-hardening-and-automation",
    }
