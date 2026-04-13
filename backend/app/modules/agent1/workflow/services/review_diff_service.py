from __future__ import annotations


def build_review_diff(artifacts: list[dict]) -> dict:
    """
    Compare the latest two artifacts and return a compact diff summary for UI.
    """
    if len(artifacts) < 2:
        return {
            "available": False,
            "message": "Need at least two artifact versions to compute diff",
            "added_ids": [],
            "removed_ids": [],
            "changed_ids": [],
            "counts": {"added": 0, "removed": 0, "changed": 0},
        }

    latest = artifacts[0].get("artifact") or {}
    previous = artifacts[1].get("artifact") or {}

    latest_cases = {tc.get("id"): tc for tc in (latest.get("test_cases") or []) if tc.get("id")}
    previous_cases = {tc.get("id"): tc for tc in (previous.get("test_cases") or []) if tc.get("id")}

    latest_ids = set(latest_cases.keys())
    previous_ids = set(previous_cases.keys())

    added_ids = sorted(latest_ids - previous_ids)
    removed_ids = sorted(previous_ids - latest_ids)

    changed_ids = []
    for case_id in sorted(latest_ids & previous_ids):
        if latest_cases[case_id] != previous_cases[case_id]:
            changed_ids.append(case_id)

    return {
        "available": True,
        "base_version": artifacts[1].get("artifact_version"),
        "target_version": artifacts[0].get("artifact_version"),
        "added_ids": added_ids,
        "removed_ids": removed_ids,
        "changed_ids": changed_ids,
        "counts": {
            "added": len(added_ids),
            "removed": len(removed_ids),
            "changed": len(changed_ids),
        },
    }
