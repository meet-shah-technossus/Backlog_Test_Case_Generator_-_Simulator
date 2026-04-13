from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.infrastructure.openai_client import OpenAIClient
from app.modules.agent2.generation.parser import extract_json_object, normalize_steps_payload
from app.modules.agent2.generation.prompt_builder import build_step_generation_prompt

class Agent2GenerationService:
    """Phase 3 step-generation implementation."""

    def __init__(self, openai_client: OpenAIClient):
        self._openai_client = openai_client

    async def _repair_malformed_json(
        self,
        *,
        raw_output: str,
        validation_error: Exception,
        model: str | None = None,
    ) -> str | None:
        if not (raw_output or '').strip():
            return None

        repair_prompt = (
            "The following model output is intended to be one JSON object but is malformed. "
            "Repair it and return strict JSON only. Do not add markdown.\n\n"
            f"Validation error: {validation_error}\n\n"
            "Malformed output:\n"
            f"{raw_output}"
        )

        repaired = await self._openai_client.generate(
            prompt=repair_prompt,
            system="You are a strict JSON repair assistant. Return one valid JSON object only.",
            model=model,
            temperature=0.0,
            json_mode=True,
        )
        return (repaired or '').strip() or None

    async def generate_steps_artifact(
        self,
        *,
        run_id: str,
        story_id: str,
        source_agent1_run_id: str,
        source_test_cases: list[dict],
        story_title: str | None = None,
        story_description: str | None = None,
        acceptance_criteria: list[str] | None = None,
        evidence_pages: list[dict] | None = None,
        model: str | None = None,
        on_token: Callable[[str], Awaitable[None] | None] | None = None,
    ) -> dict:
        if not source_test_cases:
            raise ValueError("Agent2 generation requires source Agent1 test cases")

        prompt = build_step_generation_prompt(
            story_id=story_id,
            test_cases=source_test_cases,
            story_title=story_title,
            story_description=story_description,
            acceptance_criteria=acceptance_criteria,
            evidence_pages=evidence_pages,
        )
        max_attempts = 3
        last_error: Exception | None = None
        normalized: dict | None = None

        for attempt in range(1, max_attempts + 1):
            if attempt == 1:
                prompt_for_attempt = prompt
            else:
                prompt_for_attempt = (
                    f"{prompt}\n\n"
                    "Previous output was rejected by strict validator.\n"
                    f"Validation error: {last_error}\n"
                    "Regenerate complete output from scratch and satisfy all rules exactly."
                )

            if on_token is None:
                raw = await self._openai_client.generate(
                    prompt=prompt_for_attempt,
                    system="Return strict JSON only. No markdown.",
                    model=model,
                    temperature=0.2,
                    json_mode=True,
                )
            else:
                chunks: list[str] = []
                async for token in self._openai_client.generate_stream(
                    prompt=prompt_for_attempt,
                    system="Return strict JSON only. No markdown.",
                    model=model,
                    temperature=0.2,
                    json_mode=True,
                ):
                    chunks.append(token)
                    maybe_awaitable = on_token(token)
                    if maybe_awaitable is not None:
                        await maybe_awaitable
                raw = ''.join(chunks)

            try:
                parsed = extract_json_object(raw)
                normalized = normalize_steps_payload(
                    payload=parsed,
                    input_case_ids={str(tc.get('id')) for tc in source_test_cases},
                )
                break
            except ValueError as exc:
                repaired_error: Exception | None = None
                try:
                    repaired_raw = await self._repair_malformed_json(
                        raw_output=raw,
                        validation_error=exc,
                        model=model,
                    )
                    if repaired_raw:
                        repaired_parsed = extract_json_object(repaired_raw)
                        normalized = normalize_steps_payload(
                            payload=repaired_parsed,
                            input_case_ids={str(tc.get('id')) for tc in source_test_cases},
                        )
                        break
                except ValueError as repair_exc:
                    repaired_error = repair_exc

                last_error = repaired_error or exc
                if attempt == max_attempts:
                    raise ValueError(
                        f"Agent2 generation failed strict validation after {max_attempts} attempts: {last_error}"
                    )
                continue

        if normalized is None:
            raise ValueError("Agent2 generation failed: no normalized output produced")

        return {
            "run_id": run_id,
            "source_agent1_run_id": source_agent1_run_id,
            "story_id": story_id,
            "model_used": model or "agent2_default",
            "generated_steps": normalized,
        }

    def capability_summary(self) -> dict:
        return {
            "phase": "phase-3",
            "ready": True,
            "next": "phase-4-human-review-edit-loop",
        }
