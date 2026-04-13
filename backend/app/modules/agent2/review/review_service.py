from __future__ import annotations


class Agent2ReviewService:
    """Human review boundary for Agent2 artifacts."""

    _REASON_CODES = {
        "reject": [
            "incorrect_steps",
            "missing_coverage",
            "invalid_ordering",
            "unsafe_assumption",
            "other",
        ],
        "retry": [
            "llm_quality_low",
            "format_invalid",
            "missing_cases",
            "other",
        ],
    }

    def supported_decisions(self) -> list[str]:
        return ["approve", "edit_approve", "reject", "retry"]

    def reason_code_catalog(self) -> dict[str, list[str]]:
        return self._REASON_CODES

    def validate_review_request(
        self,
        *,
        decision: str,
        reason_code: str | None,
        edited_payload: dict | None,
    ) -> None:
        if decision not in self.supported_decisions():
            raise ValueError(f"Unsupported decision '{decision}'")

        if decision in {"reject", "retry"}:
            if not reason_code:
                raise ValueError(f"reason_code is required for decision '{decision}'")
            if reason_code not in self._REASON_CODES[decision]:
                raise ValueError(
                    f"Invalid reason_code '{reason_code}' for decision '{decision}'"
                )

        if decision == "edit_approve":
            if not isinstance(edited_payload, dict):
                raise ValueError("edited_payload is required for 'edit_approve'")
            cases = (
                edited_payload.get("generated_steps", {})
                .get("test_cases", [])
            )
            if not isinstance(cases, list) or not cases:
                raise ValueError("edited_payload.generated_steps.test_cases is required")

    def build_review_diff(self, *, artifacts: list[dict]) -> dict:
        if len(artifacts) < 2:
            return {
                "has_diff": False,
                "latest_version": artifacts[0]["artifact_version"] if artifacts else None,
                "previous_version": None,
                "summary": {"cases_delta": 0, "steps_delta": 0},
            }

        latest = artifacts[0].get("artifact", {})
        previous = artifacts[1].get("artifact", {})

        latest_cases = latest.get("generated_steps", {}).get("test_cases", [])
        prev_cases = previous.get("generated_steps", {}).get("test_cases", [])

        latest_steps = sum(len(c.get("steps", [])) for c in latest_cases if isinstance(c, dict))
        prev_steps = sum(len(c.get("steps", [])) for c in prev_cases if isinstance(c, dict))

        return {
            "has_diff": True,
            "latest_version": artifacts[0].get("artifact_version"),
            "previous_version": artifacts[1].get("artifact_version"),
            "summary": {
                "cases_delta": len(latest_cases) - len(prev_cases),
                "steps_delta": latest_steps - prev_steps,
            },
        }
