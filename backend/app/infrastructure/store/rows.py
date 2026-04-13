from __future__ import annotations

import json
import sqlite3


def safe_json_load(value: str | None, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def backlog_row_to_dict(row: sqlite3.Row) -> dict:
    keys = set(row.keys())
    return {
        "backlog_item_id": row["backlog_item_id"],
        "story_title": row["story_title"],
        "story_description": row["story_description"],
        "acceptance_criteria": safe_json_load(row["acceptance_json"], []),
        "target_url": row["target_url"] if "target_url" in keys else None,
        "epic_id": row["epic_id"],
        "epic_title": row["epic_title"],
        "feature_id": row["feature_id"],
        "feature_title": row["feature_title"],
        "source_type": row["source_type"],
        "source_ref": row["source_ref"],
        "updated_at": row["updated_at"],
    }


def obs_event_row_to_dict(row: sqlite3.Row) -> dict:
    keys = set(row.keys())
    return {
        "event_id": row["event_id"],
        "trace_id": row["trace_id"],
        "run_id": row["run_id"],
        "story_id": row["story_id"],
        "stage": row["stage"],
        "status": row["status"],
        "model_provider": row["model_provider"],
        "model_name": row["model_name"],
        "prompt_template": row["prompt_template"],
        "prompt_chars": row["prompt_chars"],
        "response_chars": row["response_chars"],
        "duration_ms": row["duration_ms"],
        "error_code": row["error_code"],
        "error_message": row["error_message"],
        "metadata": safe_json_load(row["metadata_json"], {}),
        "prev_signature": row["prev_signature"] if "prev_signature" in keys else None,
        "event_signature": row["event_signature"] if "event_signature" in keys else None,
        "created_at": row["created_at"],
    }
