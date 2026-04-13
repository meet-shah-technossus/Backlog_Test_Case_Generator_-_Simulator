AGENT4_ALLOWED_STATES = {
    "intake_pending",
    "intake_ready",
    "context_assembled",
    "generation_ready",
    "generation_completed",
    "review_pending",
    "review_approved",
    "review_rejected",
    "handoff_pending",
    "handoff_emitted",
    "failed",
}


def validate_state(state: str) -> str:
    if state not in AGENT4_ALLOWED_STATES:
        raise ValueError(f"Invalid Agent4 state: {state}")
    return state
