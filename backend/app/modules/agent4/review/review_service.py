from __future__ import annotations


class Agent4ReviewService:
    """Human gate validation and policy rules for Agent4 Phase 3."""

    _REASON_CODES = {
        "reject": [
            "missing_required_context",
            "inconsistent_handoff_payload",
            "unsafe_script_scope",
            "other",
        ],
        "retry": [
            "upstream_handoff_update_required",
            "selector_plan_incomplete",
            "other",
        ],
        "approve_override": [
            "manual_override_confirmed",
            "business_exception",
            "other",
        ],
    }

    REQUIRED_INPUT_KEYS = [
        "acceptance_criteria",
        "test_cases",
        "test_steps",
        "scraper_context_pack",
        "selector_plan",
    ]

    def supported_decisions(self) -> list[str]:
        return ["approve", "reject", "retry"]

    def supported_gate_modes(self) -> list[str]:
        return ["quick", "deep"]

    def reason_code_catalog(self) -> dict[str, list[str]]:
        return self._REASON_CODES

    def assess_payload_readiness(self, *, payload: dict) -> dict:
        missing_keys = []
        for key in self.REQUIRED_INPUT_KEYS:
            value = payload.get(key) if isinstance(payload, dict) else None
            if value is None:
                missing_keys.append(key)
                continue
            if isinstance(value, (list, dict)) and len(value) == 0:
                missing_keys.append(key)

        selector_plan = payload.get("selector_plan") if isinstance(payload, dict) else {}
        selector_steps = selector_plan.get("selector_steps") if isinstance(selector_plan, dict) else []
        selector_steps_count = len(selector_steps) if isinstance(selector_steps, list) else 0

        acceptance_criteria_count = len(payload.get("acceptance_criteria") or []) if isinstance(payload, dict) and isinstance(payload.get("acceptance_criteria"), list) else 0
        test_cases_count = len(payload.get("test_cases") or []) if isinstance(payload, dict) and isinstance(payload.get("test_cases"), list) else 0
        test_steps_count = len(payload.get("test_steps") or []) if isinstance(payload, dict) and isinstance(payload.get("test_steps"), list) else 0

        ready = len(missing_keys) == 0
        return {
            "ready": ready,
            "missing_keys": missing_keys,
            "acceptance_criteria_count": acceptance_criteria_count,
            "test_cases_count": test_cases_count,
            "test_steps_count": test_steps_count,
            "selector_steps_count": selector_steps_count,
        }

    def validate_gate_request(
        self,
        *,
        decision: str,
        gate_mode: str,
        reason_code: str | None,
        readiness: dict,
    ) -> None:
        if decision not in self.supported_decisions():
            raise ValueError(f"Unsupported decision '{decision}'")

        if gate_mode not in self.supported_gate_modes():
            raise ValueError(f"Unsupported gate_mode '{gate_mode}'")

        if decision == "reject":
            if not reason_code:
                raise ValueError("reason_code is required for 'reject'")
            if reason_code not in self._REASON_CODES["reject"]:
                raise ValueError(f"Invalid reason_code '{reason_code}' for decision 'reject'")

        if decision == "retry":
            if not reason_code:
                raise ValueError("reason_code is required for 'retry'")
            if reason_code not in self._REASON_CODES["retry"]:
                raise ValueError(f"Invalid reason_code '{reason_code}' for decision 'retry'")

        if decision == "approve" and not bool(readiness.get("ready")):
            if not reason_code:
                raise ValueError(
                    "reason_code is required for 'approve' when handoff context is incomplete"
                )
            if reason_code not in self._REASON_CODES["approve_override"]:
                raise ValueError(
                    f"Invalid reason_code '{reason_code}' for decision 'approve' with incomplete context"
                )
