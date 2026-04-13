from __future__ import annotations

import sys
from pathlib import Path

from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.modules.agent2.contracts.models import Agent2HandoffEnvelope, Agent2ToAgent3HandoffEnvelope


def main() -> None:
    a1_to_a2_valid = Agent2HandoffEnvelope(
        message_id='msg-1',
        run_id='run-1',
        trace_id='trace-1',
        from_agent='agent_1',
        to_agent='agent_2',
        task_type='generate_steps',
        contract_version='v1',
        payload={'backlog_item_id': 'story_1'},
    )

    a2_to_a3_valid = Agent2ToAgent3HandoffEnvelope(
        message_id='msg-2',
        run_id='run-2',
        trace_id='trace-2',
        stage_id='reasoning',
        retry_count=0,
        dedupe_key='run-2-v0',
        payload={'generated_steps': {'test_cases': []}},
    )

    invalid_a1_to_a2 = False
    invalid_a2_to_a3 = False

    try:
        Agent2HandoffEnvelope(
            message_id='bad-1',
            run_id='run-1',
            trace_id='trace-1',
            from_agent='agent_2',
            to_agent='agent_2',
            task_type='generate_steps',
            contract_version='v1',
            payload={},
        )
    except ValidationError:
        invalid_a1_to_a2 = True

    try:
        Agent2ToAgent3HandoffEnvelope(
            message_id='bad-2',
            run_id='run-2',
            trace_id='trace-2',
            from_agent='agent_2',
            to_agent='agent_3',
            task_type='execute_steps',
            contract_version='v1',
            stage_id='reasoning',
            retry_count=0,
            dedupe_key='run-2-v1',
            payload={},
        )
    except ValidationError:
        invalid_a2_to_a3 = True

    print(
        {
            'a1_to_a2_valid': bool(a1_to_a2_valid.message_id),
            'a2_to_a3_valid': bool(a2_to_a3_valid.message_id),
            'invalid_a1_to_a2_rejected': invalid_a1_to_a2,
            'invalid_a2_to_a3_rejected': invalid_a2_to_a3,
        }
    )


if __name__ == '__main__':
    main()
