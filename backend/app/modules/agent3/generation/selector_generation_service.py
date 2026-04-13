from __future__ import annotations


class Agent3SelectorGenerationService:
    """Builds executable selector mappings from Phase 3 reasoning candidates."""

    MIN_SELECTED_SCORE = 0.7
    MIN_UNIQUENESS = 0.65
    MIN_VISIBILITY = 0.65
    AMBIGUITY_GAP_FLOOR = 0.05

    @staticmethod
    def _candidate_score(candidate: dict) -> float:
        text_match = float(candidate.get("supporting_text_match") or 0.0)
        context_match = float(candidate.get("context_match") or 0.0)
        return round((text_match + context_match) / 2.0, 3)

    def _step_quality(self, *, candidates: list[dict], confidence: dict, failure_reason_code: str | None) -> tuple[dict, bool]:
        selected = candidates[0] if candidates else {}
        second = candidates[1] if len(candidates) > 1 else {}
        stability = selected.get("stability_indicators") or {}

        selected_score = self._candidate_score(selected)
        second_score = self._candidate_score(second)
        score_gap = round(selected_score - second_score, 3) if second else None

        uniqueness = float(stability.get("uniqueness") or 0.0)
        visibility = float(stability.get("visibility_interactivity") or 0.0)
        band = str(confidence.get("band") or "")

        ambiguity_flags = {
            "close_score_gap": bool(second) and (selected_score < self.MIN_SELECTED_SCORE) and ((score_gap or 0.0) < self.AMBIGUITY_GAP_FLOOR),
            "duplicate_selector_with_alternate": bool(second) and bool(selected.get("selector")) and (selected.get("selector") == second.get("selector")),
        }

        threshold_checks = {
            "has_selected_candidate": bool(selected),
            "selected_score_ok": selected_score >= self.MIN_SELECTED_SCORE,
            "uniqueness_ok": uniqueness >= self.MIN_UNIQUENESS,
            "visibility_ok": visibility >= self.MIN_VISIBILITY,
            "confidence_band_ok": band == "high_confidence",
            "failure_code_clear": not bool(failure_reason_code),
        }

        ambiguous = any(ambiguity_flags.values())
        pass_quality = all(threshold_checks.values()) and not ambiguous
        return (
            {
                "selected_score": selected_score,
                "second_score": second_score if second else None,
                "score_gap": score_gap,
                "thresholds": {
                    "min_selected_score": self.MIN_SELECTED_SCORE,
                    "min_uniqueness": self.MIN_UNIQUENESS,
                    "min_visibility": self.MIN_VISIBILITY,
                    "ambiguity_gap_floor": self.AMBIGUITY_GAP_FLOOR,
                },
                "checks": threshold_checks,
                "ambiguity_flags": ambiguity_flags,
                "pass": pass_quality,
            },
            pass_quality,
        )

    def build_selector_artifact(
        self,
        *,
        run_id: str,
        source_agent2_run_id: str,
        source_context_artifact_version: int,
        output_steps: list[dict],
    ) -> dict:
        selector_steps: list[dict] = []
        unresolved_count = 0
        quality_blocked_count = 0

        for step in output_steps:
            step_id = str(step.get("step_id") or "")
            candidates = step.get("top3_candidates") or []
            confidence = step.get("confidence") or {}
            rationale = str(step.get("rationale") or "")
            failure_reason_code = step.get("failure_reason_code")

            selected = candidates[0] if candidates else None
            if selected is None:
                unresolved_count += 1

            quality, quality_ok = self._step_quality(
                candidates=candidates,
                confidence=confidence,
                failure_reason_code=failure_reason_code,
            )
            if not quality_ok:
                quality_blocked_count += 1

            selector_steps.append(
                {
                    "step_id": step_id,
                    "selected": {
                        "selector": (selected or {}).get("selector"),
                        "action": (selected or {}).get("action"),
                    },
                    "alternates": candidates[1:] if len(candidates) > 1 else [],
                    "confidence": confidence,
                    "rationale": rationale,
                    "failure_reason_code": failure_reason_code,
                    "quality": quality,
                    "requires_manual_resolution": selected is None or bool(failure_reason_code),
                }
            )

        ready_for_handoff = unresolved_count == 0 and quality_blocked_count == 0

        return {
            "artifact_type": "phase4_selector_plan",
            "run_id": run_id,
            "source_agent2_run_id": source_agent2_run_id,
            "source_context_artifact_version": source_context_artifact_version,
            "selector_steps": selector_steps,
            "selector_steps_count": len(selector_steps),
            "unresolved_count": unresolved_count,
            "quality_blocked_count": quality_blocked_count,
            "quality_review_required": quality_blocked_count > 0,
            "ready_for_handoff": ready_for_handoff,
        }
