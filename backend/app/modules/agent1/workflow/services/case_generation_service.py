from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from app.domain.models import GeneratedTestSuite, TestCase
from app.infrastructure.openai_client import OpenAIClient
from app.modules.agent1.db.backlog_repository import Agent1BacklogRepository


def _build_generation_prompt(backlog_item_id: str, title: str, description: str, criteria: list[str]) -> str:
    criteria_lines = "\n".join([f"{idx}. {text}" for idx, text in enumerate(criteria, start=1)])
    return (
        "You are Agent 1 in a multi-agent testing pipeline.\n"
        "Generate ONLY high-quality test case shells for each acceptance criterion.\n"
        "Do NOT generate execution steps. Agent 2 will generate detailed steps later.\n"
        "Return STRICT JSON only, no markdown, no explanation.\n\n"
        f"Story ID: {backlog_item_id}\n"
        f"Story Title: {title}\n"
        f"Story Description: {description}\n\n"
        "Acceptance Criteria:\n"
        f"{criteria_lines}\n\n"
        "Output schema:\n"
        "{\n"
        "  \"criteria\": [\n"
        "    {\n"
        "      \"criterion_index\": 1,\n"
        "      \"test_cases\": [\n"
        "        {\n"
        "          \"title\": \"...\",\n"
        "          \"preconditions\": [\"...\"],\n"
        "          \"expected_result\": \"...\",\n"
        "          \"test_type\": \"positive|negative|edge\"\n"
        "        }\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "1. Generate 3 to 5 test cases for EACH acceptance criterion.\n"
        "2. For each acceptance criterion, include at least one positive, one negative, and one edge test case.\n"
        "3. Titles must be specific and executable, max 100 characters, and must not use generic words like validate/check/perform alone.\n"
        "4. Preconditions must be minimal and realistic for that criterion only.\n"
        "5. expected_result must be measurable and unambiguous.\n"
        "6. Do not generate execution steps; keep test shell only for Agent2 step generation.\n"
        "7. Do not include fields outside schema."
    )


def _extract_json_object(raw: str) -> dict:
    text = (raw or "").strip()
    if not text:
        raise ValueError("LLM response was empty")

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain a valid JSON object")

    return json.loads(text[start : end + 1])


def _contains_any(text: str, terms: list[str]) -> bool:
    base = text.lower()
    return any(term in base for term in terms)


def _has_unrequested_assumptions(*, criterion_text: str, case_text: str) -> str | None:
    criterion_l = criterion_text.lower()
    case_l = case_text.lower()

    assumption_policies = [
        (
            "refresh persistence",
            ["refresh", "reload", "page reload", "page refresh", "re-open"],
            ["refresh", "reload", "re-open", "persist after refresh"],
        ),
        (
            "viewport-specific expectation",
            ["desktop", "mobile", "tablet", "without scrolling", "above the fold", "viewport"],
            ["desktop", "mobile", "tablet", "viewport", "responsive", "without scrolling"],
        ),
        (
            "network-condition expectation",
            ["slow network", "network delay", "latency", "offline", "packet loss", "timeout"],
            ["slow network", "delay", "latency", "offline", "timeout", "network"],
        ),
    ]

    for label, case_terms, criterion_allow_terms in assumption_policies:
        if _contains_any(case_l, case_terms) and not _contains_any(criterion_l, criterion_allow_terms):
            return label
    return None


def _infer_case_type_from_text(text: str) -> str:
    t = text.lower()
    negative_markers = [
        " not ", "cannot", "can't", "does not", "invalid", "error", "fail", "denied", "unavailable", "zero",
    ]
    edge_markers = [
        "max", "minimum", "minimum", "boundary", "limit", "empty", "long", "large", "special",
        "slow", "timeout", "concurrent", "multiple", "retry", "duplicate",
    ]

    if any(marker in t for marker in negative_markers):
        return "negative"
    if any(marker in t for marker in edge_markers):
        return "edge"
    return "positive"


def _rebalance_case_types(candidates: list[dict]) -> list[dict]:
    required = {"positive", "negative", "edge"}
    by_type = {
        "positive": [c for c in candidates if c["test_type"] == "positive"],
        "negative": [c for c in candidates if c["test_type"] == "negative"],
        "edge": [c for c in candidates if c["test_type"] == "edge"],
    }

    missing = [k for k in required if not by_type[k]]
    if not missing:
        return candidates

    for missing_type in missing:
        donor = None
        if len(by_type["positive"]) > 1:
            donor = by_type["positive"][0]
            by_type["positive"].remove(donor)
        elif len(by_type["edge"]) > 1:
            donor = by_type["edge"][0]
            by_type["edge"].remove(donor)
        elif len(by_type["negative"]) > 1:
            donor = by_type["negative"][0]
            by_type["negative"].remove(donor)

        if donor is None:
            continue

        donor["test_type"] = missing_type
        by_type[missing_type].append(donor)

    return candidates


def _normalize_test_cases(*, payload: dict, backlog_item_id: str, criteria: list[str]) -> list[TestCase]:
    criteria_payload = payload.get("criteria")
    if not isinstance(criteria_payload, list):
        raise ValueError("Invalid LLM payload: missing criteria list")

    by_index: dict[int, list[dict]] = {}
    for entry in criteria_payload:
        if not isinstance(entry, dict):
            continue
        idx = entry.get("criterion_index")
        test_cases = entry.get("test_cases")
        if isinstance(idx, int) and isinstance(test_cases, list):
            by_index[idx] = test_cases

    cases: list[TestCase] = []
    case_counter = 1

    for idx, _criterion_text in enumerate(criteria, start=1):
        criterion_text = str(criteria[idx - 1] or "")
        raw_cases = by_index.get(idx, [])
        if len(raw_cases) < 3:
            raise ValueError(f"LLM returned fewer than 3 test cases for criterion {idx}")

        normalized_candidates: list[dict] = []
        seen_titles: set[str] = set()

        for tc in raw_cases:
            if not isinstance(tc, dict):
                continue

            title = str(tc.get("title") or "").strip()
            expected_result = str(tc.get("expected_result") or "").strip()
            preconditions_raw = tc.get("preconditions")
            preconditions = (
                [str(v).strip() for v in preconditions_raw if str(v).strip()]
                if isinstance(preconditions_raw, list)
                else []
            )
            raw_test_type = str(tc.get("test_type") or "").strip().lower()
            inferred = _infer_case_type_from_text(f"{title} {expected_result}")
            test_type = raw_test_type or inferred
            if test_type == "functional":
                test_type = "positive"
            if test_type not in {"positive", "negative", "edge"}:
                test_type = inferred

            if not title or not expected_result:
                continue

            if len(title) > 100:
                title = title[:100].rstrip()

            title_key = title.lower()
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            combined_case_text = " ".join(
                [
                    title,
                    expected_result,
                    " ".join(preconditions),
                ]
            )
            assumption = _has_unrequested_assumptions(
                criterion_text=criterion_text,
                case_text=combined_case_text,
            )
            if assumption is not None:
                continue

            normalized_candidates.append(
                {
                    "title": title,
                    "expected_result": expected_result,
                    "preconditions": preconditions,
                    "test_type": test_type,
                }
            )

        normalized_candidates = _rebalance_case_types(normalized_candidates)

        by_type = {
            "positive": [c for c in normalized_candidates if c["test_type"] == "positive"],
            "negative": [c for c in normalized_candidates if c["test_type"] == "negative"],
            "edge": [c for c in normalized_candidates if c["test_type"] == "edge"],
        }
        if not by_type["positive"] or not by_type["negative"] or not by_type["edge"]:
            raise ValueError(
                f"Criterion {idx} must include at least one positive, negative, and edge case"
            )

        selected = [by_type["positive"][0], by_type["negative"][0], by_type["edge"][0]]

        extras = []
        for candidate in normalized_candidates:
            if len(extras) + len(selected) >= 5:
                break
            if candidate in selected:
                continue
            extras.append(candidate)

        final_cases = (selected + extras)[:5]
        if len(final_cases) < 3:
            raise ValueError(
                f"Criterion {idx} did not produce at least 3 valid test cases after quality filtering"
            )

        for tc in final_cases:
            criterion_id = f"{backlog_item_id}_ac_{idx}"
            case_id = f"TC{case_counter:03d}"
            case_counter += 1

            cases.append(
                TestCase(
                    id=case_id,
                    title=tc["title"],
                    criterion_id=criterion_id,
                    story_id=backlog_item_id,
                    preconditions=tc["preconditions"],
                    steps=[],
                    expected_result=tc["expected_result"],
                    test_type=tc["test_type"],
                )
            )

        criterion_case_count = len([c for c in cases if c.criterion_id == f"{backlog_item_id}_ac_{idx}"])
        if criterion_case_count < 3:
            raise ValueError(
                f"LLM output for criterion {idx} did not produce at least 3 valid test cases"
            )

    return cases


async def generate_suite_from_backlog_item(
    *,
    backlog_item_id: str,
    backlog_repo: Agent1BacklogRepository,
    openai_client: OpenAIClient,
    model: str | None = None,
    on_token: Callable[[str], Awaitable[None] | None] | None = None,
) -> GeneratedTestSuite:
    item = backlog_repo.get_item(backlog_item_id)
    if item is None:
        raise ValueError(f"Backlog item '{backlog_item_id}' not found")

    criteria = item.acceptance_criteria or []
    if not criteria:
        raise ValueError("Backlog item has no acceptance criteria; Agent1 generation requires explicit criteria")

    prompt = _build_generation_prompt(
        backlog_item_id=backlog_item_id,
        title=item.title or backlog_item_id,
        description=item.description or "",
        criteria=criteria,
    )

    max_attempts = 3
    last_error: Exception | None = None
    test_cases: list[TestCase] = []

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

        try:
            if on_token is None:
                raw = await openai_client.generate(
                    prompt=prompt_for_attempt,
                    system="Return only valid JSON according to the user schema.",
                    model=model,
                    temperature=0.2,
                )
            else:
                chunks: list[str] = []
                async for token in openai_client.generate_stream(
                    prompt=prompt_for_attempt,
                    system="Return only valid JSON according to the user schema.",
                    model=model,
                    temperature=0.2,
                ):
                    chunks.append(token)
                    maybe_awaitable = on_token(token)
                    if maybe_awaitable is not None:
                        await maybe_awaitable
                raw = "".join(chunks)

            payload = _extract_json_object(raw)
            test_cases = _normalize_test_cases(
                payload=payload,
                backlog_item_id=backlog_item_id,
                criteria=criteria,
            )
            break
        except ValueError as exc:
            last_error = exc
            if attempt == max_attempts:
                raise ValueError(f"Agent1 generation failed strict validation after {max_attempts} attempts: {exc}")
            continue

    suite = GeneratedTestSuite(
        story_id=backlog_item_id,
        story_title=item.title or backlog_item_id,
        feature_title=item.feature_title,
        epic_title=item.epic_title,
        model_used=model or "agent1_baseline",
        test_cases=test_cases,
    )
    return suite
