from __future__ import annotations

from app.core.config import RETRY_ALLOW_SELF_APPROVAL, RETRY_ALLOWED_REVIEWERS, RETRY_DEFAULT_REVIEWERS
from app.infrastructure.store import store


def _parse_default_reviewer_map(raw: str) -> dict[str, str]:
    pairs = [part.strip() for part in str(raw or "").split(",") if part.strip()]
    mapping: dict[str, str] = {}
    for pair in pairs:
        if ":" not in pair:
            continue
        scope, reviewer = pair.split(":", 1)
        scope_key = str(scope or "").strip().lower()
        reviewer_value = str(reviewer or "").strip()
        if scope_key and reviewer_value:
            mapping[scope_key] = reviewer_value
    return mapping


class RetryGovernancePolicyService:
    def __init__(self) -> None:
        self._allow_self_approval = bool(RETRY_ALLOW_SELF_APPROVAL)
        self._allowed_reviewers = {value.strip() for value in RETRY_ALLOWED_REVIEWERS if value.strip()}
        self._default_reviewer_map = _parse_default_reviewer_map(RETRY_DEFAULT_REVIEWERS)

    def assign_manual(
        self,
        *,
        request_id: str,
        reviewer_id: str,
        assigned_by: str,
        assignment_reason: str | None,
    ) -> dict:
        request = store.get_retry_governance_request(request_id)
        if not request:
            raise ValueError(f"Retry request '{request_id}' not found")

        reviewer = str(reviewer_id or "").strip()
        if not reviewer:
            raise ValueError("reviewer_id is required")

        self._validate_reviewer_identity(reviewer)

        updated = store.assign_retry_governance_reviewer(
            request_id=request_id,
            assigned_reviewer_id=reviewer,
            assignment_mode="manual",
            assigned_by=str(assigned_by or "").strip() or "operator",
            assignment_reason=assignment_reason,
        )
        if not updated:
            raise ValueError(f"Retry request '{request_id}' not found")
        return updated

    def assign_auto(
        self,
        *,
        request_id: str,
        assigned_by: str,
    ) -> dict:
        request = store.get_retry_governance_request(request_id)
        if not request:
            raise ValueError(f"Retry request '{request_id}' not found")

        scope = str(request.get("run_scope") or "").strip().lower()
        requested_by = str(request.get("requested_by") or "").strip()
        default_reviewer = self._default_reviewer_map.get(scope) or "platform-reviewer"

        assignment_mode = "auto"
        assignment_reason = "default_scope_policy"
        escalation_status = None
        assigned_reviewer = default_reviewer

        if assigned_reviewer == requested_by and not self._allow_self_approval:
            assigned_reviewer = "platform-reviewer"
            assignment_mode = "auto_escalated"
            assignment_reason = "default_reviewer_conflict_with_requester"
            escalation_status = "escalated_reviewer_conflict"

        self._validate_reviewer_identity(assigned_reviewer)

        updated = store.assign_retry_governance_reviewer(
            request_id=request_id,
            assigned_reviewer_id=assigned_reviewer,
            assignment_mode=assignment_mode,
            assigned_by=str(assigned_by or "").strip() or "system",
            assignment_reason=assignment_reason,
            escalation_status=escalation_status,
        )
        if not updated:
            raise ValueError(f"Retry request '{request_id}' not found")
        return updated

    def review(
        self,
        *,
        request_id: str,
        reviewer_id: str,
        reviewer_decision: str,
        reviewer_comment: str | None,
    ) -> dict:
        request = store.get_retry_governance_request(request_id)
        if not request:
            raise ValueError(f"Retry request '{request_id}' not found")

        status = str(request.get("status") or "")
        if status not in {"retry_requested", "retry_review_pending"}:
            raise ValueError(f"Retry request '{request_id}' cannot be reviewed from status '{status}'")

        reviewer = str(reviewer_id or "").strip()
        if not reviewer:
            raise ValueError("reviewer_id is required")
        self._validate_reviewer_identity(reviewer)

        assigned_reviewer = str(request.get("assigned_reviewer_id") or "").strip()
        if assigned_reviewer and reviewer != assigned_reviewer:
            raise ValueError("Only assigned reviewer can review this retry request")

        decision = str(reviewer_decision or "").strip().lower()
        if decision not in {"approve", "reject"}:
            raise ValueError("Retry review decision must be 'approve' or 'reject'")

        requested_by = str(request.get("requested_by") or "").strip()
        if decision == "approve" and not self._allow_self_approval and requested_by and requested_by == reviewer:
            raise ValueError("Self-approval is not allowed for retry approvals")

        updated = store.review_retry_governance_request(
            request_id=request_id,
            reviewer_id=reviewer,
            reviewer_decision=decision,
            reviewer_comment=reviewer_comment,
        )
        if not updated:
            raise ValueError(f"Retry request '{request_id}' not found")
        return updated

    @staticmethod
    def list_audit(*, request_id: str) -> list[dict]:
        return store.list_retry_governance_audit_events(request_id=request_id)

    def _validate_reviewer_identity(self, reviewer_id: str) -> None:
        reviewer = str(reviewer_id or "").strip()
        if not reviewer:
            raise ValueError("reviewer_id is required")

        if self._allowed_reviewers and reviewer not in self._allowed_reviewers:
            raise ValueError("reviewer_id is not in allowed reviewer list")

        if not self._allowed_reviewers and "review" not in reviewer.lower():
            raise ValueError("reviewer_id must indicate reviewer role")
