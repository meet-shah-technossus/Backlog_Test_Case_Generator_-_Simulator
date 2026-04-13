AGENT2_ALLOWED_STATES = {
    "intake_pending",
    "intake_ready",
    "agent2_generating",
    "agent2_generated",
    "review_pending",
    "review_approved",
    "review_rejected",
    "review_retry_requested",
    "handoff_pending",
    "handoff_emitted",
    "failed",
}


def validate_state(state: str) -> str:
    if state not in AGENT2_ALLOWED_STATES:
        raise ValueError(f"Invalid Agent2 state: {state}")
    return state
