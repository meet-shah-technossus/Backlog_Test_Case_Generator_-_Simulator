SCRAPER_ALLOWED_STATES = {
    "created",
    "queued",
    "running",
    "partial_success",
    "success",
    "failed",
    "cancelled",
}


def validate_state(state: str) -> str:
    if state not in SCRAPER_ALLOWED_STATES:
        raise ValueError(f"Invalid scraper state: {state}")
    return state
