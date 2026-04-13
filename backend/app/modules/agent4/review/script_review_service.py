from __future__ import annotations


class Agent4ScriptReviewService:
    """Human review policy and readiness checks for Agent4 Phase 6."""

    _REASON_CODES = {
        "reject": [
            "script_bundle_invalid",
            "unsafe_actions_detected",
            "coverage_incomplete",
            "other",
        ],
        "retry": [
            "regenerate_required",
            "selector_mapping_incomplete",
            "other",
        ],
        "approve_override": [
            "manual_override_confirmed",
            "business_exception",
            "other",
        ],
    }

    def supported_decisions(self) -> list[str]:
        return ["approve", "edit_approve", "reject", "retry"]

    def reason_code_catalog(self) -> dict[str, list[str]]:
        return self._REASON_CODES

    def assess_script_bundle_readiness(self, *, script_bundle: dict) -> dict:
        scripts = script_bundle.get("scripts") if isinstance(script_bundle, dict) else []
        scripts = scripts if isinstance(scripts, list) else []

        missing_content_paths = [
            str(script.get("path") or "unknown")
            for script in scripts
            if isinstance(script, dict) and not str(script.get("content") or "").strip()
        ]
        empty_script_count = len(missing_content_paths)
        script_count = len(scripts)

        has_supported_framework = str(script_bundle.get("framework") or "").lower() in {"playwright"}
        has_supported_language = str(script_bundle.get("language") or "").lower() in {"python"}

        ready = script_count > 0 and empty_script_count == 0 and has_supported_framework and has_supported_language
        return {
            "ready": ready,
            "script_count": script_count,
            "empty_script_count": empty_script_count,
            "missing_content_paths": missing_content_paths,
            "framework": script_bundle.get("framework"),
            "language": script_bundle.get("language"),
            "framework_supported": has_supported_framework,
            "language_supported": has_supported_language,
        }

    def validate_review_request(
        self,
        *,
        decision: str,
        reason_code: str | None,
        edited_scripts: list[dict] | None,
        readiness: dict,
    ) -> None:
        if decision not in self.supported_decisions():
            raise ValueError(f"Unsupported decision '{decision}'")

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

        if decision in {"approve", "edit_approve"} and not bool(readiness.get("ready")):
            if not reason_code:
                raise ValueError(
                    "reason_code is required for 'approve'/'edit_approve' when script readiness is incomplete"
                )
            if reason_code not in self._REASON_CODES["approve_override"]:
                raise ValueError(
                    f"Invalid reason_code '{reason_code}' for decision '{decision}' with readiness override"
                )

        if decision == "edit_approve":
            if not isinstance(edited_scripts, list) or not edited_scripts:
                raise ValueError("edited_scripts is required for 'edit_approve'")

    def build_edited_artifact(self, *, base_artifact: dict, edited_scripts: list[dict]) -> dict:
        next_artifact = dict(base_artifact)
        next_artifact["scripts"] = edited_scripts
        next_artifact["script_count"] = len(edited_scripts)
        next_artifact["review_override"] = True
        next_artifact["ready_for_review"] = True
        return next_artifact

    def build_approved_override_artifact(self, *, base_artifact: dict, reason_code: str | None) -> dict:
        next_artifact = dict(base_artifact)
        next_artifact["review_override"] = True
        next_artifact["review_override_reason_code"] = reason_code
        next_artifact["ready_for_review"] = True
        return next_artifact
