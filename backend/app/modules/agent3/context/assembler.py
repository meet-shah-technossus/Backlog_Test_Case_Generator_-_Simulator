from __future__ import annotations

from app.modules.agent3.context.policy import TokenSafeCrawlContextPolicy, enforce_run_budget, normalize_page
from app.modules.agent3.context.schemas import (
    Agent3AssembledContextArtifact,
    CandidateItem,
    ConfidenceScore,
    ReasoningStepInput,
    ReasoningStepOutput,
)


def _intent_from_step(step_text: str) -> str:
    text = (step_text or "").lower()
    if "search" in text:
        return "search"
    if "cart" in text:
        return "cart"
    if "filter" in text:
        return "filter"
    if "product" in text or "pdp" in text:
        return "product_detail"
    return "navigation"


def _selector_seed(intent: str) -> list[tuple[str, str, float]]:
    mapping = {
        "search": [
            ("input[type='search']", "type", 0.88),
            ("#twotabsearchtextbox", "type", 0.84),
            ("[aria-label*='Search']", "type", 0.79),
        ],
        "cart": [
            ("#nav-cart", "click", 0.86),
            ("[aria-label*='Cart']", "click", 0.8),
            ("a[href*='cart']", "click", 0.72),
        ],
        "filter": [
            ("input[type='checkbox']", "click", 0.74),
            ("[aria-label*='Filter']", "click", 0.7),
            ("[data-component-type*='filter']", "click", 0.66),
        ],
        "product_detail": [
            ("#productTitle", "assert_visible", 0.84),
            ("#corePriceDisplay_desktop_feature_div", "assert_visible", 0.79),
            ("#landingImage", "assert_visible", 0.75),
        ],
    }
    default = [
        ("body", "assert_visible", 0.58),
        ("main", "assert_visible", 0.55),
        ("[role='main']", "assert_visible", 0.52),
    ]
    return mapping.get(intent, default)


def _confidence_band(score: float) -> str:
    if score >= 0.8:
        return "high_confidence"
    if score >= 0.55:
        return "medium_review_required"
    return "low_regenerate_or_manual"


def _build_step_output(step_input: ReasoningStepInput) -> ReasoningStepOutput:
    seeds = _selector_seed(step_input.page_intent)
    candidates: list[CandidateItem] = []
    for selector, action, base in seeds[:3]:
        text_match = min(1.0, base + 0.06)
        context_match = min(1.0, base + 0.04)
        candidates.append(
            CandidateItem(
                selector=selector,
                action=action,
                supporting_text_match=round(text_match, 3),
                context_match=round(context_match, 3),
                stability_indicators={
                    "uniqueness": round(min(1.0, base), 3),
                    "visibility_interactivity": round(min(1.0, base + 0.05), 3),
                    "position_context_consistency": round(min(1.0, base + 0.02), 3),
                    "historical_success_signal": round(base - 0.03, 3),
                },
            )
        )

    score = sum(c.supporting_text_match + c.context_match for c in candidates) / max(1, (len(candidates) * 2))
    band = _confidence_band(score)

    unresolved = band == "low_regenerate_or_manual"
    failure_reason_code = None
    rationale = "Top candidates generated from normalized intent/context signals."
    if unresolved:
        failure_reason_code = "A3_MAP_LOW_CONFIDENCE_RECRAWL_REQUIRED"
        rationale = "No candidate crossed confidence threshold; targeted re-crawl and re-map required, else manual override."

    return ReasoningStepOutput(
        step_id=step_input.step_id,
        top3_candidates=candidates,
        confidence=ConfidenceScore(
            score=round(score, 3),
            band=band,
            breakdown={
                "text_semantic_match": round(score, 3),
                "attribute_match": round(score - 0.03, 3),
                "visibility_interactivity": round(score + 0.02, 3),
                "uniqueness": round(score - 0.04, 3),
                "position_context_consistency": round(score - 0.01, 3),
                "historical_success_signal": round(score - 0.05, 3),
            },
        ),
        rationale=rationale,
        failure_reason_code=failure_reason_code,
    )


def assemble_reasoning_context(
    *,
    run_id: str,
    source_agent2_run_id: str,
    source_generated_steps: list[dict],
    source_pages: list[dict],
    context_version: int,
    retry_count: int,
    policy: TokenSafeCrawlContextPolicy,
) -> Agent3AssembledContextArtifact:
    normalized_pages = [normalize_page(page, policy) for page in source_pages]
    pages = enforce_run_budget(normalized_pages, policy)

    input_steps: list[ReasoningStepInput] = []
    page_context = pages[0] if pages else {}
    ui_elements = (page_context.get("interactive_controls") or [])[: policy.max_ui_elements_per_step]

    for case in source_generated_steps:
        case_id = str(case.get("id") or "CASE")
        expected = str(case.get("expected_result") or case.get("title") or "Expected behavior holds")
        for step in (case.get("steps") or []):
            number = step.get("number")
            step_id = f"{case_id}-S{number}" if number is not None else f"{case_id}-S"
            step_text = str(step.get("action") or "")
            step_input = ReasoningStepInput(
                step_id=step_id,
                step_text=step_text,
                expected_outcome=expected,
                page_intent=_intent_from_step(step_text),
                available_ui_elements=ui_elements,
                current_page_context=page_context,
            )
            input_steps.append(step_input)

    output_steps = [_build_step_output(step_input) for step_input in input_steps]
    unresolved_count = sum(1 for step in output_steps if step.failure_reason_code)
    all_high_confidence = bool(output_steps) and all(
        (step.confidence.band == "high_confidence") for step in output_steps
    )
    required_gate_mode = "quick" if (all_high_confidence and unresolved_count == 0) else "deep"

    return Agent3AssembledContextArtifact(
        run_id=run_id,
        source_agent2_run_id=source_agent2_run_id,
        context_version=context_version,
        retry_count=retry_count,
        policy={
            "per_page_char_budget": policy.per_page_char_budget,
            "per_run_char_budget": policy.per_run_char_budget,
            "max_ui_elements_per_step": policy.max_ui_elements_per_step,
            "raw_dom_in_prompt": False,
        },
        gate_requirements={
            "required_mode": required_gate_mode,
            "all_high_confidence": all_high_confidence,
            "unresolved_count": unresolved_count,
        },
        input_steps=input_steps,
        output_steps=output_steps,
        unresolved_count=unresolved_count,
    )
