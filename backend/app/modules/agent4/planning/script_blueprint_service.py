from __future__ import annotations


class Agent4ScriptBlueprintService:
    """Builds a deterministic script-generation blueprint from Agent3 handoff payload."""

    def _extract_selector_steps(self, payload: dict) -> list[dict]:
        selector_plan = payload.get("selector_plan") if isinstance(payload, dict) else {}
        if not isinstance(selector_plan, dict):
            return []
        steps = selector_plan.get("selector_steps")
        return steps if isinstance(steps, list) else []

    @staticmethod
    def _case_id_from_step(step_id: str) -> str:
        # Expected formats include TC001-S1, TC010-S7, etc.
        if "-" in step_id:
            return step_id.split("-", 1)[0]
        return step_id or "UNMAPPED"

    def build_phase4_blueprint(
        self,
        *,
        run_id: str,
        source_agent3_run_id: str,
        inbox_message_id: str,
        payload: dict,
    ) -> dict:
        selector_steps = self._extract_selector_steps(payload)
        case_map: dict[str, list[dict]] = {}
        for step in selector_steps:
            step_id = str((step or {}).get("step_id") or "")
            case_id = self._case_id_from_step(step_id)
            case_map.setdefault(case_id, []).append(step)

        script_suites = []
        for case_id, steps in sorted(case_map.items(), key=lambda item: item[0]):
            script_suites.append(
                {
                    "case_id": case_id,
                    "steps_count": len(steps),
                    "selectors": [
                        {
                            "step_id": s.get("step_id"),
                            "selector": ((s.get("selected") or {}).get("selector") if isinstance(s, dict) else None),
                            "action": ((s.get("selected") or {}).get("action") if isinstance(s, dict) else None),
                        }
                        for s in steps
                    ],
                }
            )

        missing_inputs: list[str] = []
        if not payload.get("acceptance_criteria"):
            missing_inputs.append("acceptance_criteria")
        if not payload.get("test_cases"):
            missing_inputs.append("test_cases")
        if not payload.get("test_steps") and not selector_steps:
            missing_inputs.append("test_steps_or_selector_steps")

        return {
            "artifact_type": "phase4_script_blueprint",
            "run_id": run_id,
            "source_agent3_run_id": source_agent3_run_id,
            "source_message_id": inbox_message_id,
            "source_trace_id": payload.get("trace_id"),
            "target_framework": payload.get("target_framework") or "playwright",
            "target_language": payload.get("target_language") or "python",
            "script_suites": script_suites,
            "script_suite_count": len(script_suites),
            "selector_step_count": len(selector_steps),
            "missing_inputs": missing_inputs,
            "needs_human_review": len(missing_inputs) > 0,
        }
