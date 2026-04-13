AGENT3_ALLOWED_STATES = {
    "intake_pending",
    "intake_ready",
    "context_assembling",
    "reasoning_generating",
    "reasoning_generated",
    "review_pending",
    "review_approved",
    "review_rejected",
    "review_retry_requested",
    "handoff_pending",
    "handoff_emitted",
    "failed",
}


def validate_state(state: str) -> str:
    if state not in AGENT3_ALLOWED_STATES:
        raise ValueError(f"Invalid Agent3 state: {state}")
    return state
