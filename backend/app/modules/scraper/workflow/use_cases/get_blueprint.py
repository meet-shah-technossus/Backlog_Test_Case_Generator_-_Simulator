from __future__ import annotations


def get_scraper_blueprint() -> dict:
    return {
        "module": "scraper",
        "phase_window": [0, 8],
        "status": "phase8_pipeline_complete_ready",
        "states": [
            "created",
            "queued",
            "running",
            "partial_success",
            "success",
            "failed",
            "cancelled",
        ],
        "next_phase": "completed",
    }
