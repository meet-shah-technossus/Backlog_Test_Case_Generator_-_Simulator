from __future__ import annotations

from app.modules.agent5.state_machine import (
    AGENT5_COMMAND_TRANSITIONS,
    AGENT5_STATES,
    AGENT5_TERMINAL_STATES,
    AGENT5_TRANSITIONS,
)


def get_agent5_contract_spec() -> dict:
    return {
        "phase": "A5.0",
        "status": "frozen",
        "contract_version": "a5.v1",
        "signed": {
            "signed_by": "system",
            "signed_at": "2026-04-03T00:00:00Z",
            "signature_scope": "agent5-contract-and-state-machine",
        },
        "boundaries": {
            "purpose": "Agent5 executes Playwright outputs from Agent4 and drives analysis/gates/writeback.",
            "in_scope": [
                "execution control in agent5 context",
                "stage7 result analysis artifact",
                "gate7 decisions",
                "stage8 backlog writeback artifact",
                "gate8 decisions",
                "run-id keyed persistence and retrieval",
            ],
            "out_of_scope": [
                "agent4 script generation logic",
                "non-run-id historical identity schemes",
                "gate bypass without persisted reviewer record",
            ],
            "primary_identity": {
                "key": "agent5_run_id",
                "rule": "Every artifact and event must reference exactly one agent5_run_id.",
            },
        },
        "input_contract": {
            "source": "agent4 handoff-emitted run",
            "required": [
                "agent4_run_id",
                "trace_id",
                "handoff_envelope.message_id",
                "phase5_generated_script_bundle.scripts[]",
            ],
            "optional": [
                "phase10_execution_history[]",
                "phase10_execution_normalized",
            ],
        },
        "output_contracts": {
            "stage7_analysis_artifact": {
                "required": [
                    "agent5_run_id",
                    "execution_run_id",
                    "summary",
                    "failure_classification",
                    "severity",
                    "probable_cause",
                    "remediation",
                    "confidence",
                ]
            },
            "stage8_writeback_artifact": {
                "required": [
                    "agent5_run_id",
                    "writeback_plan",
                    "request_snapshot",
                    "response_snapshot",
                    "idempotency_key",
                ]
            },
            "gate7_decision": {
                "required": [
                    "agent5_run_id",
                    "decision",
                    "reviewer_id",
                    "reason_code",
                    "comment",
                    "timestamp",
                ]
            },
            "gate8_decision": {
                "required": [
                    "agent5_run_id",
                    "decision",
                    "reviewer_id",
                    "reason_code",
                    "comment",
                    "timestamp",
                ]
            },
        },
        "api_shapes": {
            "get_contract": "GET /agent5/contract",
            "get_state_machine": "GET /agent5/state-machine",
            "validate_transition": "POST /agent5/state-machine/validate-transition",
            "get_orchestration": "GET /agent5/runs/{agent5_run_id}/orchestration",
            "get_observability": "GET /agent5/runs/{agent5_run_id}/observability",
            "generate_stage7_analysis": "POST /agent5/runs/{agent5_run_id}/stage7-analysis/generate",
            "submit_gate7_decision": "POST /agent5/runs/{agent5_run_id}/gate7/decision",
            "generate_stage8_writeback": "POST /agent5/runs/{agent5_run_id}/stage8-writeback/generate",
            "submit_gate8_decision": "POST /agent5/runs/{agent5_run_id}/gate8/decision",
            "recover_stale": "POST /agent5/reliability/recover-stale",
            "retry_failed": "POST /agent5/runs/{agent5_run_id}/reliability/retry",
            "apply_command": "POST /agent5/runs/{agent5_run_id}/commands",
            "advance_to_gate7_pending": "POST /agent5/runs/{agent5_run_id}/advance-to-gate7-pending",
        },
    }


def get_agent5_state_machine_spec() -> dict:
    transition_rows: list[dict] = []
    for from_state, targets in AGENT5_TRANSITIONS.items():
        for to_state in targets:
            transition_rows.append(
                {
                    "from_state": from_state,
                    "to_state": to_state,
                }
            )

    return {
        "phase": "A5.1",
        "contract_version": "a5.v1",
        "states": list(AGENT5_STATES),
        "terminal_states": list(AGENT5_TERMINAL_STATES),
        "transitions": transition_rows,
        "commands": AGENT5_COMMAND_TRANSITIONS,
        "mermaid": _state_machine_mermaid(),
        "rules": {
            "determinism": "Transitions are valid only if declared in commands and allowed transition map.",
            "guards": "Invalid transitions must be rejected before state update.",
            "audit": "Every accepted transition emits one immutable transition event with actor and timestamp.",
        },
    }


def _state_machine_mermaid() -> str:
    return "\n".join(
        [
            "stateDiagram-v2",
            "    [*] --> queued",
            "    queued --> running: start_execution",
            "    queued --> canceled: cancel_execution",
            "    running --> paused: pause_execution",
            "    paused --> running: resume_execution",
            "    running --> canceled: cancel_execution",
            "    paused --> canceled: cancel_execution",
            "    running --> execution_completed: execution_finished",
            "    execution_completed --> analysis_pending: begin_analysis",
            "    analysis_pending --> gate7_pending: submit_gate7",
            "    gate7_pending --> gate7_approved: gate7_approve",
            "    gate7_pending --> analysis_pending: gate7_request_revision",
            "    gate7_approved --> writeback_pending: start_writeback",
            "    writeback_pending --> gate8_pending: submit_gate8",
            "    gate8_pending --> completed: gate8_confirm",
            "    gate8_pending --> writeback_pending: gate8_followup",
            "    running --> failed: fail_execution",
            "    analysis_pending --> failed: fail_analysis",
            "    gate7_pending --> failed: fail_gate7",
            "    writeback_pending --> failed: fail_writeback",
            "    gate8_pending --> failed: fail_gate8",
        ]
    )
