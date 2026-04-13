from __future__ import annotations


class Agent3ExecutionFeedbackService:
    """Validates and interprets Agent4 execution feedback for Phase 6."""

    _OUTCOMES = {"passed", "partial", "failed"}
    _RECOMMENDED_ACTIONS = {"none", "retry_selectors", "manual_review", "abort"}
    _MAX_STEP_RESULTS = 500

    def reason_code_catalog(self) -> dict[str, list[str]]:
        return {
            "outcome": sorted(self._OUTCOMES),
            "recommended_action": sorted(self._RECOMMENDED_ACTIONS),
        }

    def validate_feedback_request(
        self,
        *,
        outcome: str,
        recommended_action: str,
        step_results: list[dict],
    ) -> None:
        if outcome not in self._OUTCOMES:
            raise ValueError(f"Unsupported feedback outcome '{outcome}'")

        if recommended_action not in self._RECOMMENDED_ACTIONS:
            raise ValueError(f"Unsupported recommended_action '{recommended_action}'")

        if not isinstance(step_results, list):
            raise ValueError("step_results must be a list")

        if len(step_results) > self._MAX_STEP_RESULTS:
            raise ValueError(
                f"step_results exceeds max allowed items ({self._MAX_STEP_RESULTS})"
            )

        for item in step_results:
            if not isinstance(item, dict):
                raise ValueError("Each step_results item must be an object")
            if not str(item.get("step_id") or "").strip():
                raise ValueError("Each step_results item requires step_id")

    def summarize(self, *, step_results: list[dict]) -> dict:
        total = len(step_results)
        passed = 0
        failed = 0
        unknown = 0
        for step in step_results:
            status = str((step or {}).get("status") or "").lower()
            if status == "passed":
                passed += 1
            elif status == "failed":
                failed += 1
            else:
                unknown += 1
        return {
            "total_steps": total,
            "passed_steps": passed,
            "failed_steps": failed,
            "unknown_steps": unknown,
        }

    def derive_transition(
        self,
        *,
        outcome: str,
        recommended_action: str,
        failed_steps: int,
    ) -> dict:
        if recommended_action == "abort":
            return {
                "state": "failed",
                "stage": "phase-6-feedback-aborted",
                "last_error_code": "A3_EXECUTION_ABORTED",
                "last_error_message": "Execution feedback requested abort",
                "action": "execution_feedback_abort",
            }

        if recommended_action == "retry_selectors":
            return {
                "state": "review_retry_requested",
                "stage": "phase-6-feedback-retry-requested",
                "last_error_code": "A3_EXECUTION_RETRY_REQUESTED",
                "last_error_message": "Execution feedback requested selector retry",
                "action": "execution_feedback_retry_requested",
            }

        if outcome == "passed" and failed_steps == 0:
            return {
                "state": "handoff_emitted",
                "stage": "phase-6-feedback-accepted",
                "last_error_code": None,
                "last_error_message": None,
                "action": "execution_feedback_accepted",
            }

        return {
            "state": "review_pending",
            "stage": "phase-6-feedback-review-required",
            "last_error_code": "A3_EXECUTION_FEEDBACK_REVIEW_REQUIRED",
            "last_error_message": "Execution feedback indicates failures requiring review",
            "action": "execution_feedback_review_required",
        }
