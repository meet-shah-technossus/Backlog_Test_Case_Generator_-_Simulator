from __future__ import annotations

import json


def extract_json_object(raw: str) -> dict:
    text = (raw or '').strip()
    if not text:
        raise ValueError('Agent2 LLM response was empty')

    if text.startswith('```'):
        lines = text.splitlines()
        if lines and lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()
        if text.lower().startswith('json'):
            text = text[4:].strip()

    start = text.find('{')
    end = text.rfind('}')
    if start == -1 or end == -1 or end <= start:
        raise ValueError('Agent2 LLM response did not contain valid JSON object')

    return json.loads(text[start:end + 1])


def normalize_steps_payload(*, payload: dict, input_case_ids: set[str]) -> dict:
    raw_cases = payload.get('test_cases')
    if not isinstance(raw_cases, list):
        raise ValueError('Agent2 payload requires test_cases array')

    mapped: dict[str, list[dict]] = {}
    for case in raw_cases:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get('id') or '').strip()
        steps = case.get('steps')
        if case_id not in input_case_ids or not isinstance(steps, list):
            continue

        normalized_steps = []
        for idx, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            action = str(step.get('action') or '').strip()
            if not action:
                continue
            number = step.get('number')
            normalized_steps.append(
                {
                    'number': number if isinstance(number, int) and number > 0 else idx,
                    'action': action,
                }
            )

        if len(normalized_steps) < 4:
            raise ValueError(f'Agent2 produced fewer than 4 valid steps for case {case_id}')

        mapped[case_id] = normalized_steps[:8]

    missing = [cid for cid in sorted(input_case_ids) if cid not in mapped]
    if missing:
        raise ValueError(f'Agent2 step generation missing cases: {missing}')

    return {'test_cases': [{'id': cid, 'steps': mapped[cid]} for cid in sorted(mapped.keys())]}
