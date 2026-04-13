from __future__ import annotations


def build_step_generation_prompt(
    *,
    story_id: str,
    test_cases: list[dict],
    story_title: str | None = None,
    story_description: str | None = None,
    acceptance_criteria: list[str] | None = None,
    evidence_pages: list[dict] | None = None,
) -> str:
    cases_render = []
    for tc in test_cases:
        cases_render.append(
            "\n".join(
                [
                    f"- case_id: {tc.get('id')}",
                    f"  title: {tc.get('title')}",
                    f"  expected_result: {tc.get('expected_result')}",
                    f"  test_type: {tc.get('test_type')}",
                ]
            )
        )
    cases_text = "\n\n".join(cases_render)

    criteria_text = "\n".join([f"- {c}" for c in (acceptance_criteria or [])])
    if not criteria_text:
        criteria_text = "- (none provided)"

    evidence_lines: list[str] = []
    for page in evidence_pages or []:
        evidence_lines.append(
            f"- url={page.get('url')} depth={page.get('depth')} status={page.get('status_code')}"
        )
        title = (page.get('title') or '').strip()
        excerpt = (page.get('text_excerpt') or '').strip()
        if title:
            evidence_lines.append(f"  title: {title}")
        if excerpt:
            evidence_lines.append(f"  excerpt: {excerpt}")

    evidence_text = "\n".join(evidence_lines) if evidence_lines else "- (none provided)"

    return (
        "You are Agent2 in a QA multi-agent system.\n"
        "Generate detailed executable test steps for each provided test case.\n"
        "Return strict JSON only.\n\n"
        f"Story ID: {story_id}\n"
        f"Story Title: {story_title or '(unknown)'}\n"
        f"Story Description: {story_description or '(none)'}\n\n"
        "Acceptance Criteria:\n"
        f"{criteria_text}\n\n"
        "Observed Evidence Pages:\n"
        f"{evidence_text}\n\n"
        "Input test cases:\n"
        f"{cases_text}\n\n"
        "Output schema:\n"
        "{\n"
        "  \"test_cases\": [\n"
        "    {\n"
        "      \"id\": \"TC001\",\n"
        "      \"steps\": [\n"
        "        {\"number\": 1, \"action\": \"...\"},\n"
        "        {\"number\": 2, \"action\": \"...\"}\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Rules:\n"
        "1. Generate 4 to 8 concrete steps per test case.\n"
        "2. Steps must be action-focused and UI-verifiable.\n"
        "3. Keep step numbers sequential and start at 1.\n"
        "4. Keep case IDs unchanged.\n"
    )
