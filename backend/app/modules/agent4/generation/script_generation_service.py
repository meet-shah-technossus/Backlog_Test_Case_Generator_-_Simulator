from __future__ import annotations

import re
from collections import defaultdict


class Agent4ScriptGenerationService:
    """Builds deterministic Playwright-ready Python scripts from Phase4 blueprint and handoff payload."""

    @staticmethod
    def _sanitize_identifier(value: str) -> str:
        normalized = re.sub(r"[^a-zA-Z0-9_]", "_", value or "")
        normalized = re.sub(r"_+", "_", normalized).strip("_")
        if not normalized:
            return "generated"
        if normalized[0].isdigit():
            return f"case_{normalized}"
        return normalized.lower()

    @staticmethod
    def _step_key(step: dict) -> str:
        return str((step or {}).get("step_id") or "")

    @staticmethod
    def _action_to_playwright(action: str, selector: str, fallback_text: str) -> str:
        safe_selector = selector or "body"
        safe_text = (fallback_text or "sample-input").replace("\"", "'")
        normalized_action = (action or "").lower()
        if normalized_action in {"click", "tap", "press"}:
            return f'    await page.locator("{safe_selector}").click()'
        if normalized_action in {"fill", "type", "input", "enter_text"}:
            return f'    await page.locator("{safe_selector}").fill("{safe_text}")'
        if normalized_action in {"check", "tick"}:
            return f'    await page.locator("{safe_selector}").check()'
        if normalized_action in {"select", "select_option"}:
            return f'    await page.locator("{safe_selector}").select_option("{safe_text}")'
        if normalized_action in {"assert_visible", "verify_visible", "expect_visible"}:
            return f'    await expect(page.locator("{safe_selector}")).to_be_visible()'
        return f'    await page.locator("{safe_selector}").click()'

    @staticmethod
    def _build_case_step_lookup(payload: dict) -> dict[str, list[dict]]:
        test_steps = payload.get("test_steps") if isinstance(payload, dict) else []
        if not isinstance(test_steps, list):
            return {}

        by_case: dict[str, list[dict]] = defaultdict(list)
        for step in test_steps:
            if not isinstance(step, dict):
                continue
            case_id = str(step.get("test_case_id") or step.get("case_id") or "")
            if case_id:
                by_case[case_id].append(step)
        return dict(by_case)

    def _build_script_source(
        self,
        *,
        case_id: str,
        selectors: list[dict],
        case_steps: list[dict],
    ) -> str:
        test_name = self._sanitize_identifier(case_id)
        lines = [
            "import pytest",
            "from playwright.async_api import Page, expect",
            "",
            "",
            "@pytest.mark.asyncio",
            f"async def test_{test_name}(page: Page):",
            "    # Placeholder route; test runner can inject environment-specific URL.",
            '    await page.goto("/")',
        ]

        step_text_lookup = {
            self._step_key(step): str(step.get("action") or step.get("expected_result") or "")
            for step in case_steps
            if isinstance(step, dict)
        }

        for selector_step in selectors:
            if not isinstance(selector_step, dict):
                continue
            step_id = str(selector_step.get("step_id") or "")
            selector = str(selector_step.get("selector") or "")
            action = str(selector_step.get("action") or "")
            fallback_text = step_text_lookup.get(step_id, "")
            lines.append(f"    # {step_id or 'unnamed-step'}")
            lines.append(self._action_to_playwright(action, selector, fallback_text))

        return "\n".join(lines)

    def build_phase5_script_bundle(
        self,
        *,
        run_id: str,
        source_agent3_run_id: str,
        source_message_id: str,
        source_blueprint_artifact_version: int,
        payload: dict,
        blueprint_artifact: dict,
    ) -> dict:
        blueprint_raw = blueprint_artifact.get("artifact") if isinstance(blueprint_artifact, dict) else {}
        blueprint: dict = blueprint_raw if isinstance(blueprint_raw, dict) else {}
        script_suites = blueprint.get("script_suites") if isinstance(blueprint, dict) else []
        if not isinstance(script_suites, list) or not script_suites:
            raise ValueError("Phase4 blueprint does not include script suites")

        case_steps_lookup = self._build_case_step_lookup(payload)
        generated_scripts: list[dict] = []

        for suite in script_suites:
            if not isinstance(suite, dict):
                continue
            case_id = str(suite.get("case_id") or "UNMAPPED")
            selectors_raw = suite.get("selectors")
            selectors = [selector for selector in selectors_raw if isinstance(selector, dict)] if isinstance(selectors_raw, list) else []
            case_steps = case_steps_lookup.get(case_id, [])
            file_stem = self._sanitize_identifier(case_id)
            generated_scripts.append(
                {
                    "case_id": case_id,
                    "path": f"tests/generated/test_{file_stem}.py",
                    "framework": blueprint.get("target_framework") or "playwright",
                    "language": blueprint.get("target_language") or "python",
                    "content": self._build_script_source(
                        case_id=case_id,
                        selectors=selectors,
                        case_steps=case_steps,
                    ),
                    "selector_count": len(selectors),
                    "step_count": len(case_steps),
                }
            )

        return {
            "artifact_type": "phase5_generated_script_bundle",
            "run_id": run_id,
            "source_agent3_run_id": source_agent3_run_id,
            "source_message_id": source_message_id,
            "source_blueprint_artifact_version": source_blueprint_artifact_version,
            "framework": (blueprint.get("target_framework") or "playwright"),
            "language": (blueprint.get("target_language") or "python"),
            "script_count": len(generated_scripts),
            "scripts": generated_scripts,
            "ready_for_review": True,
        }
