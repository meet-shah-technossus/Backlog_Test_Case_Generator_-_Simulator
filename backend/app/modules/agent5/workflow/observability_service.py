from __future__ import annotations

import hashlib
import json
from datetime import datetime

from app.modules.agent5.db.run_repository import Agent5RunRepository


class Agent5ObservabilityService:
    def __init__(self, run_repo: Agent5RunRepository) -> None:
        self._run_repo = run_repo

    def get_run_observability(self, *, agent5_run_id: str) -> dict:
        run = self._run_repo.get_run(agent5_run_id)
        if not run:
            raise ValueError(f"Agent5 run '{agent5_run_id}' not found")

        timeline = self._run_repo.get_timeline_events(agent5_run_id, ascending=True)
        artifacts = self._run_repo.get_artifacts(agent5_run_id)

        payload_checksums = self._payload_checksums(run)
        evidence = self._evidence_summary(run)
        stage_durations = self._stage_duration_rows(timeline)

        return {
            "agent5_run_id": agent5_run_id,
            "state": str(run.get("state") or ""),
            "stage": str(run.get("stage") or ""),
            "timeline": timeline,
            "stage_durations": stage_durations,
            "payload_checksums": payload_checksums,
            "evidence_summary": evidence,
            "artifact_count": len(artifacts),
            "timeline_count": len(timeline),
            "phase": "A5.11",
        }

    @staticmethod
    def _payload_checksums(run: dict) -> dict:
        def checksum(value: object) -> str:
            raw = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
            return hashlib.sha256(raw).hexdigest()

        payloads = {
            "execution_summary": run.get("execution_summary") if isinstance(run.get("execution_summary"), dict) else {},
            "step_evidence_refs": run.get("step_evidence_refs") if isinstance(run.get("step_evidence_refs"), list) else [],
            "stage7_analysis": run.get("stage7_analysis") if isinstance(run.get("stage7_analysis"), dict) else {},
            "gate7_decision": run.get("gate7_decision") if isinstance(run.get("gate7_decision"), dict) else {},
            "stage8_writeback": run.get("stage8_writeback") if isinstance(run.get("stage8_writeback"), dict) else {},
            "gate8_decision": run.get("gate8_decision") if isinstance(run.get("gate8_decision"), dict) else {},
        }
        return {name: checksum(value) for name, value in payloads.items()}

    @staticmethod
    def _evidence_summary(run: dict) -> dict:
        execution_summary = run.get("execution_summary") if isinstance(run.get("execution_summary"), dict) else {}
        evidence_manifest = execution_summary.get("evidence_manifest") if isinstance(execution_summary.get("evidence_manifest"), dict) else {}
        steps = run.get("step_evidence_refs") if isinstance(run.get("step_evidence_refs"), list) else []

        screenshot_paths: list[str] = []
        trace_paths: list[str] = []
        video_paths: list[str] = []
        for row in steps:
            evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
            screenshot = str(evidence.get("screenshot_path") or "").strip()
            trace = str(evidence.get("trace_path") or "").strip()
            video = str(evidence.get("video_path") or "").strip()
            if screenshot:
                screenshot_paths.append(screenshot)
            if trace:
                trace_paths.append(trace)
            if video:
                video_paths.append(video)

        manifest_videos = evidence_manifest.get("videos") if isinstance(evidence_manifest.get("videos"), list) else []
        for path in manifest_videos:
            value = str(path or "").strip()
            if value:
                video_paths.append(value)

        # preserve order while deduplicating
        def unique(values: list[str]) -> list[str]:
            seen: set[str] = set()
            result: list[str] = []
            for value in values:
                if value in seen:
                    continue
                seen.add(value)
                result.append(value)
            return result

        return {
            "screenshots": unique(screenshot_paths),
            "traces": unique(trace_paths),
            "videos": unique(video_paths),
        }

    @staticmethod
    def _stage_duration_rows(timeline: list[dict]) -> list[dict]:
        rows: list[dict] = []
        if not timeline:
            return rows

        timestamps: list[tuple[str, datetime | None, str, str]] = []
        for event in timeline:
            created_at = str(event.get("created_at") or "")
            parsed = Agent5ObservabilityService._parse_datetime(created_at)
            timestamps.append((created_at, parsed, str(event.get("stage") or ""), str(event.get("actor") or "")))

        for idx, (_, current_ts, stage, actor) in enumerate(timestamps):
            next_ts = timestamps[idx + 1][1] if idx + 1 < len(timestamps) else None
            duration_ms = None
            if current_ts is not None and next_ts is not None:
                duration_ms = max(0, int((next_ts - current_ts).total_seconds() * 1000))

            rows.append(
                {
                    "index": idx,
                    "stage": stage,
                    "actor": actor,
                    "duration_ms_to_next": duration_ms,
                    "status": "terminal" if idx == len(timestamps) - 1 else "completed",
                }
            )
        return rows

    @staticmethod
    def _parse_datetime(value: str) -> datetime | None:
        if not value:
            return None
        normalized = value.replace(" ", "T")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None
