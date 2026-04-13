from __future__ import annotations

import hashlib
import json

from app.modules.agent5.db.run_repository import Agent5RunRepository
from app.modules.agent5.workflow.persistence_service import Agent5PersistenceService


class Agent5AnalysisService:
    def __init__(
        self,
        run_repo: Agent5RunRepository,
        persistence_service: Agent5PersistenceService,
    ) -> None:
        self._run_repo = run_repo
        self._persistence_service = persistence_service

    def generate_stage7_analysis(
        self,
        *,
        agent5_run_id: str,
        actor: str,
        force_regenerate: bool = False,
    ) -> dict:
        run = self._run_repo.get_run(agent5_run_id)
        if not run:
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")

        existing = run.get("stage7_analysis") if isinstance(run.get("stage7_analysis"), dict) else {}
        if existing and not force_regenerate:
            return self._persistence_service.get_run_snapshot(agent5_run_id)

        analysis = self._build_analysis(run)
        return self._persistence_service.persist_stage7_analysis(
            agent5_run_id=agent5_run_id,
            analysis=analysis,
            actor=actor,
        )

    def _build_analysis(self, run: dict) -> dict:
        execution_summary = run.get("execution_summary") if isinstance(run.get("execution_summary"), dict) else {}
        summary = execution_summary.get("summary") if isinstance(execution_summary.get("summary"), dict) else {}
        execution_run_id = str(execution_summary.get("execution_run_id") or run.get("source_execution_run_id") or "")

        raw_refs = run.get("step_evidence_refs")
        step_refs = raw_refs if isinstance(raw_refs, list) else []
        failed_steps = [item for item in step_refs if str(item.get("status") or "").lower() == "failed"]

        failed_total = int(summary.get("failed") or len(failed_steps) or 0)
        total_steps = int(summary.get("total") or len(step_refs) or 0)
        failure_rate = float(failed_total / total_steps) if total_steps > 0 else 0.0

        failure_classification = self._classify_failures(failed_steps)
        severity = self._severity_from_failure_rate(failure_rate=failure_rate, failed_total=failed_total)
        urgency = self._urgency_from_severity(severity)
        probable_cause = self._probable_cause(failure_classification)
        remediation = self._remediation_recommendation(failure_classification)
        confidence = self._confidence_payload(
            failure_classification=failure_classification,
            failed_total=failed_total,
            total_steps=total_steps,
        )

        fingerprint_input = {
            "agent5_run_id": run.get("agent5_run_id"),
            "execution_run_id": execution_run_id,
            "summary": summary,
            "failure_classification": failure_classification,
            "severity": severity,
            "urgency": urgency,
            "probable_cause": probable_cause,
            "remediation": remediation,
            "confidence": confidence,
        }
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()

        analysis = {
            "analysis_version": "a5.7.v1",
            "agent5_run_id": str(run.get("agent5_run_id") or ""),
            "execution_run_id": execution_run_id,
            "summary": summary,
            "failure_classification": failure_classification,
            "severity": severity,
            "urgency": urgency,
            "probable_cause": probable_cause,
            "remediation": remediation,
            "confidence": confidence,
            "approved_defect_analysis_artifact": {
                "draft": {
                    "status": "draft",
                    "analysis_version": "a5.7.v1",
                    "agent5_run_id": str(run.get("agent5_run_id") or ""),
                    "execution_run_id": execution_run_id,
                    "severity": severity,
                    "urgency": urgency,
                    "probable_cause": probable_cause,
                    "remediation": remediation,
                    "confidence": confidence,
                },
                "approved": None,
            },
            "deterministic_fingerprint": fingerprint,
        }
        return analysis

    @staticmethod
    def _classify_failures(failed_steps: list[dict]) -> list[dict]:
        buckets: dict[str, dict] = {}
        for step in failed_steps:
            code = str(step.get("error_code") or "unknown").strip().lower() or "unknown"
            message = str(step.get("error_message") or "").strip().lower()

            if code in {"selector_timeout", "element_not_found"} or "selector" in message:
                label = "selector_resolution_failure"
            elif code in {"navigation_timeout", "timeout"} or "timeout" in message:
                label = "navigation_or_timing_failure"
            elif code in {"assertion_failed", "expectation_mismatch"} or "assert" in message:
                label = "assertion_failure"
            elif code in {"target_closed", "browser_closed"} or "target closed" in message:
                label = "runtime_instability"
            else:
                label = "unknown_failure"

            current = buckets.get(label)
            if current is None:
                buckets[label] = {"class": label, "count": 1, "examples": [code]}
            else:
                current["count"] = int(current.get("count") or 0) + 1
                examples = current.get("examples") if isinstance(current.get("examples"), list) else []
                if code not in examples and len(examples) < 3:
                    examples.append(code)
                    current["examples"] = examples

        return sorted(buckets.values(), key=lambda item: (-(int(item.get("count") or 0)), str(item.get("class") or "")))

    @staticmethod
    def _severity_from_failure_rate(*, failure_rate: float, failed_total: int) -> str:
        if failed_total == 0:
            return "none"
        if failure_rate >= 0.5:
            return "critical"
        if failure_rate >= 0.2:
            return "high"
        if failure_rate >= 0.05:
            return "medium"
        return "low"

    @staticmethod
    def _urgency_from_severity(severity: str) -> str:
        mapping = {
            "none": "none",
            "low": "normal",
            "medium": "elevated",
            "high": "urgent",
            "critical": "immediate",
        }
        return mapping.get(severity, "normal")

    @staticmethod
    def _probable_cause(failure_classification: list[dict]) -> str:
        top = failure_classification[0] if failure_classification else {"class": "unknown_failure"}
        label = str(top.get("class") or "unknown_failure")
        mapping = {
            "selector_resolution_failure": "Selector drift likely due to DOM or attribute changes.",
            "navigation_or_timing_failure": "Environment or timing instability causing waits/timeouts.",
            "assertion_failure": "Behavior/output divergence from expected business outcomes.",
            "runtime_instability": "Browser/runtime process instability during execution.",
            "unknown_failure": "Insufficient signal; requires manual triage on evidence artifacts.",
        }
        return mapping.get(label, mapping["unknown_failure"])

    @staticmethod
    def _remediation_recommendation(failure_classification: list[dict]) -> list[str]:
        labels = {str(item.get("class") or "") for item in failure_classification}
        recommendations: list[str] = []
        if "selector_resolution_failure" in labels:
            recommendations.append("Regenerate selectors from latest crawl context and prioritize stable attributes.")
        if "navigation_or_timing_failure" in labels:
            recommendations.append("Increase deterministic waits around route transitions and verify test environment health.")
        if "assertion_failure" in labels:
            recommendations.append("Review acceptance criteria mapping and update assertions for current product behavior.")
        if "runtime_instability" in labels:
            recommendations.append("Capture additional runtime diagnostics and verify browser binary/runtime compatibility.")
        if not recommendations:
            recommendations.append("Run targeted reproduction with trace and screenshot artifacts to refine classification.")
        return recommendations

    @staticmethod
    def _confidence_payload(
        *,
        failure_classification: list[dict],
        failed_total: int,
        total_steps: int,
    ) -> dict:
        if failed_total <= 0:
            score = 0.9
        else:
            coverage = min(1.0, float(len(failure_classification)) / float(max(1, failed_total)))
            volume = min(1.0, float(failed_total) / float(max(1, total_steps)))
            score = round(0.45 + 0.35 * volume + 0.20 * coverage, 3)

        if score >= 0.85:
            level = "high"
        elif score >= 0.65:
            level = "medium"
        else:
            level = "low"

        return {
            "score": score,
            "level": level,
            "rationale": [
                f"failed_total={failed_total}",
                f"total_steps={total_steps}",
                f"classes={len(failure_classification)}",
            ],
        }
