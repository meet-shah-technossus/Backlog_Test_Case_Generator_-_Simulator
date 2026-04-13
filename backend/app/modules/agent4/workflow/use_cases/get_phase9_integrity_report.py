from __future__ import annotations

import hashlib
import json

from app.modules.agent4.db.run_repository import Agent4RunRepository


def _sha(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def get_phase9_integrity_report(*, run_id: str, run_repo: Agent4RunRepository) -> dict:
    run = run_repo.get_run(run_id)
    if run is None:
        raise ValueError(f"Agent4 run '{run_id}' not found")

    artifacts = run_repo.get_artifacts(run_id)
    timeline = run_repo.get_timeline_events(run_id, ascending=True)

    artifact_hashes = []
    feedback_message_ids: set[str] = set()
    duplicate_feedback_message_ids: set[str] = set()

    for row in artifacts:
        artifact = row.get("artifact") if isinstance(row, dict) else None
        artifact_hashes.append(
            {
                "artifact_version": row.get("artifact_version"),
                "artifact_type": (artifact or {}).get("artifact_type") if isinstance(artifact, dict) else "unknown",
                "sha256": _sha(artifact or {}),
            }
        )
        if isinstance(artifact, dict) and artifact.get("artifact_type") == "phase8_execution_feedback":
            msg = str(artifact.get("message_id") or "")
            if msg in feedback_message_ids:
                duplicate_feedback_message_ids.add(msg)
            elif msg:
                feedback_message_ids.add(msg)

    timeline_hash = _sha(timeline)
    artifacts_hash = _sha([row.get("artifact") for row in artifacts])
    run_hash = _sha(run)

    return {
        "run": run,
        "integrity": {
            "run_sha256": run_hash,
            "timeline_sha256": timeline_hash,
            "artifacts_sha256": artifacts_hash,
            "artifact_hashes": artifact_hashes,
            "feedback_message_ids_count": len(feedback_message_ids),
            "duplicate_feedback_message_ids": sorted(duplicate_feedback_message_ids),
        },
    }
