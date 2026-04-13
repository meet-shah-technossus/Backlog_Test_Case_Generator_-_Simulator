from __future__ import annotations


RETRY_LIFECYCLE: list[str] = [
    "retry_requested",
    "retry_review_pending",
    "retry_approved",
    "retry_rejected",
    "retry_running",
    "retry_completed",
    "retry_failed",
]

RETRY_REQUIRED_METADATA: list[str] = [
    "requested_by",
    "requested_at",
    "reason_code",
    "reason_text",
    "reviewer_id",
    "reviewer_decision",
    "reviewer_comment",
    "approved_at",
    "retry_attempt_number",
    "cooldown_until",
]


def get_retry_governance_spec() -> dict:
    return {
        "phase": "phase23",
        "scope": "agent5_execution_analysis",
        "lifecycle": RETRY_LIFECYCLE,
        "required_metadata": RETRY_REQUIRED_METADATA,
        "applicable_run_scopes": ["agent1", "agent2", "agent3", "agent4", "agent5"],
        "rules": [
            "retry_request_does_not_execute_work",
            "retry_execution_requires_reviewer_approval",
            "requester_self_approval_is_policy_controlled",
            "every_transition_must_emit_audit_event",
            "retry_limits_and_cooldown_are_policy_driven",
        ],
    }