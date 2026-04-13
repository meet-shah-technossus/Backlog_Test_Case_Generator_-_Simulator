from __future__ import annotations


AGENT3_MAX_RETRIES = 2


class Agent3ReviewService:
    """Human gate validation and policy rules for Agent3 Phase 3."""

    _REASON_CODES = {
        "reject": [
            "selector_mapping_invalid",
            "missing_reasoning_coverage",
            "unsafe_interaction",
            "other",
        ],
        "retry": [
            "confidence_too_low",
            "context_incomplete",
            "candidate_instability",
            "other",
        ],
    }

    def supported_decisions(self) -> list[str]:
        return ["approve", "reject", "retry"]

    def reason_code_catalog(self) -> dict[str, list[str]]:
        return self._REASON_CODES

    def validate_gate_request(
        self,
        *,
        decision: str,
        gate_mode: str,
        required_mode: str,
        reason_code: str | None,
    ) -> None:
        if decision not in self.supported_decisions():
            raise ValueError(f"Unsupported decision '{decision}'")

        if gate_mode not in {"quick", "deep"}:
            raise ValueError("gate_mode must be one of: quick, deep")

        if required_mode not in {"quick", "deep"}:
            raise ValueError(f"Invalid required gate mode '{required_mode}'")

        if gate_mode != required_mode:
            raise ValueError(
                f"gate_mode '{gate_mode}' not allowed for this artifact; required_mode is '{required_mode}'"
            )

        if decision in {"reject", "retry"}:
            if not reason_code:
                raise ValueError(f"reason_code is required for decision '{decision}'")
            if reason_code not in self._REASON_CODES[decision]:
                raise ValueError(
                    f"Invalid reason_code '{reason_code}' for decision '{decision}'"
                )
