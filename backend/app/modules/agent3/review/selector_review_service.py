from __future__ import annotations


class Agent3SelectorReviewService:
    """Human review rules for Phase 5 selector-plan approval."""

    _REASON_CODES = {
        "reject": [
            "selector_plan_invalid",
            "insufficient_evidence",
            "unsafe_interactions",
            "other",
        ],
        "approve_override": [
            "manual_override_confirmed",
            "business_exception",
            "other",
        ],
    }

    def supported_decisions(self) -> list[str]:
        return ["approve", "edit_approve", "reject"]

    def reason_code_catalog(self) -> dict[str, list[str]]:
        return self._REASON_CODES

    def validate_review_request(
        self,
        *,
        decision: str,
        reason_code: str | None,
        edited_selector_steps: list[dict] | None,
        selector_artifact: dict,
    ) -> None:
        if decision not in self.supported_decisions():
            raise ValueError(f"Unsupported decision '{decision}'")

        if decision == "reject":
            if not reason_code:
                raise ValueError("reason_code is required for 'reject'")
            if reason_code not in self._REASON_CODES["reject"]:
                raise ValueError(f"Invalid reason_code '{reason_code}' for decision 'reject'")

        ready_for_handoff = bool(selector_artifact.get("ready_for_handoff"))
        if decision == "approve" and not ready_for_handoff:
            if not reason_code:
                raise ValueError(
                    "reason_code is required for 'approve' when selector quality is blocked"
                )
            if reason_code not in self._REASON_CODES["approve_override"]:
                raise ValueError(
                    f"Invalid reason_code '{reason_code}' for decision 'approve' with quality override"
                )

        if decision == "edit_approve":
            if not isinstance(edited_selector_steps, list) or not edited_selector_steps:
                raise ValueError("edited_selector_steps is required for 'edit_approve'")

    def build_edited_artifact(self, *, base_artifact: dict, edited_selector_steps: list[dict]) -> dict:
        unresolved_count = 0
        quality_blocked_count = 0

        for step in edited_selector_steps:
            selected = (step.get("selected") or {}) if isinstance(step, dict) else {}
            requires_manual = bool(step.get("requires_manual_resolution")) if isinstance(step, dict) else True
            quality = (step.get("quality") or {}) if isinstance(step, dict) else {}
            pass_quality = bool(quality.get("pass")) if isinstance(quality, dict) else False

            if requires_manual or not selected.get("selector"):
                unresolved_count += 1
            if not pass_quality:
                quality_blocked_count += 1

        next_artifact = dict(base_artifact)
        next_artifact["selector_steps"] = edited_selector_steps
        next_artifact["selector_steps_count"] = len(edited_selector_steps)
        next_artifact["unresolved_count"] = unresolved_count
        next_artifact["quality_blocked_count"] = quality_blocked_count
        next_artifact["quality_review_required"] = quality_blocked_count > 0
        next_artifact["ready_for_handoff"] = unresolved_count == 0 and quality_blocked_count == 0
        next_artifact["review_override"] = True
        return next_artifact

    def build_approved_override_artifact(self, *, base_artifact: dict, reason_code: str | None) -> dict:
        next_artifact = dict(base_artifact)
        # Human explicitly accepted quality risk in Phase 5.
        next_artifact["ready_for_handoff"] = True
        next_artifact["quality_review_required"] = False
        next_artifact["review_override"] = True
        next_artifact["review_override_reason_code"] = reason_code
        return next_artifact
