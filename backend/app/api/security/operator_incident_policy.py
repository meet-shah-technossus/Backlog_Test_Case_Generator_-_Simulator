from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
import math
from threading import Lock
import time
from uuid import uuid4

from app.core import config
from app.infrastructure.store import store
from app.api.security.operator_alert_service import operator_alert_service


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class _SourceState:
    failures: deque[float]
    lockout_until_epoch: float = 0.0


class OperatorIncidentPolicyService:
    """In-memory abuse policy for operator authentication failures by request source."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._source_states: dict[str, _SourceState] = {}
        self._events: deque[dict] = deque(maxlen=1000)

    def _window_seconds(self) -> int:
        return max(1, int(config.OPERATOR_AUTH_FAILURE_WINDOW_SECONDS))

    def _max_failures(self) -> int:
        return max(1, int(config.OPERATOR_AUTH_MAX_FAILURES))

    def _lockout_seconds(self) -> int:
        return max(1, int(config.OPERATOR_AUTH_LOCKOUT_SECONDS))

    def _trim_failures(self, state: _SourceState, now_epoch: float) -> None:
        cutoff = now_epoch - self._window_seconds()
        while state.failures and state.failures[0] < cutoff:
            state.failures.popleft()

    def _append_event(self, event: dict) -> None:
        self._events.append(event)

    @staticmethod
    def _int_or_none(value: object) -> int | None:
        if value is None:
            return None
        try:
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                return int(value.strip())
            return None
        except (TypeError, ValueError):
            return None

    def _persist_security_event(self, event: dict) -> None:
        try:
            store.log_operator_security_event(
                event_id=str(event.get("event_id") or ""),
                source=str(event.get("source") or "unknown"),
                stage=str(event.get("stage") or "operator.auth"),
                status=str(event.get("status") or "n/a"),
                reason=str(event.get("reason") or "") or None,
                failures_recent=self._int_or_none(event.get("failures_recent")),
                lockout_until=str(event.get("lockout_until") or "") or None,
                metadata=event,
                created_at=str(event.get("created_at") or "") or None,
            )
        except Exception:
            return

    def _send_alert_for_event(self, event: dict) -> None:
        payload = {
            "channel": str(config.OPERATOR_ALERT_CHANNEL or "webhook"),
            "event": event,
            "policy": {
                "failure_window_seconds": self._window_seconds(),
                "max_failures": self._max_failures(),
                "lockout_seconds": self._lockout_seconds(),
            },
        }
        result = operator_alert_service.send_incident_alert(payload)
        if result.delivered:
            self._emit_observability_event(
                stage="operator.alert.delivery",
                status="delivered",
                source=str(event.get("source") or "unknown"),
                metadata={
                    "event_id": event.get("event_id"),
                    "alert": result.to_dict(),
                },
            )
            return

        self._emit_observability_event(
            stage="operator.alert.delivery",
            status="failed",
            source=str(event.get("source") or "unknown"),
            metadata={
                "event_id": event.get("event_id"),
                "alert": result.to_dict(),
            },
        )

    def _emit_observability_event(self, *, stage: str, status: str, source: str, metadata: dict) -> None:
        try:
            store.log_event(
                trace_id=f"operator-auth-{uuid4().hex[:12]}",
                run_id=None,
                story_id=source,
                stage=stage,
                status=status,
                metadata=metadata,
            )
        except Exception:
            # Best-effort telemetry: auth enforcement should not fail if audit logging fails.
            return

    def check_lockout(self, source: str) -> dict:
        now_epoch = time.time()
        normalized_source = str(source or "unknown").strip() or "unknown"

        with self._lock:
            state = self._source_states.get(normalized_source)
            if state is None:
                return {
                    "locked": False,
                    "source": normalized_source,
                    "remaining_seconds": 0,
                    "failures_recent": 0,
                }

            self._trim_failures(state, now_epoch)
            remaining_raw = state.lockout_until_epoch - now_epoch
            locked = remaining_raw > 0
            remaining = max(0, math.ceil(remaining_raw))
            if not locked:
                state.lockout_until_epoch = 0.0

            return {
                "locked": locked,
                "source": normalized_source,
                "remaining_seconds": remaining,
                "failures_recent": len(state.failures),
            }

    def record_denied_attempt(self, source: str, reason: str = "invalid_or_missing_key") -> dict:
        now_epoch = time.time()
        now_iso = _utc_now_iso()
        normalized_source = str(source or "unknown").strip() or "unknown"

        with self._lock:
            state = self._source_states.get(normalized_source)
            if state is None:
                state = _SourceState(failures=deque())
                self._source_states[normalized_source] = state

            self._trim_failures(state, now_epoch)
            state.failures.append(now_epoch)
            failures_recent = len(state.failures)

            lockout_applied = failures_recent >= self._max_failures()
            lockout_until_epoch = state.lockout_until_epoch
            if lockout_applied:
                lockout_until_epoch = now_epoch + self._lockout_seconds()
                state.lockout_until_epoch = max(state.lockout_until_epoch, lockout_until_epoch)

            denied_event = {
                "event_id": f"operator-denied-{uuid4().hex[:10]}",
                "created_at": now_iso,
                "stage": "operator.auth_denied",
                "status": "denied",
                "source": normalized_source,
                "reason": reason,
                "failures_recent": failures_recent,
                "lockout_applied": lockout_applied,
                "lockout_until": datetime.fromtimestamp(state.lockout_until_epoch, tz=timezone.utc).isoformat()
                if state.lockout_until_epoch
                else None,
            }
            self._append_event(denied_event)
            self._persist_security_event(denied_event)
            self._send_alert_for_event(denied_event)

            if lockout_applied:
                lockout_event = {
                    "event_id": f"operator-lockout-{uuid4().hex[:10]}",
                    "created_at": now_iso,
                    "stage": "operator.auth_lockout",
                    "status": "locked",
                    "source": normalized_source,
                    "reason": "failure_threshold_reached",
                    "failures_recent": failures_recent,
                    "lockout_until": datetime.fromtimestamp(state.lockout_until_epoch, tz=timezone.utc).isoformat(),
                }
                self._append_event(lockout_event)
                self._persist_security_event(lockout_event)
                self._send_alert_for_event(lockout_event)

        self._emit_observability_event(
            stage="operator.auth_denied",
            status="denied",
            source=normalized_source,
            metadata={
                "source": normalized_source,
                "reason": reason,
                "failures_recent": failures_recent,
                "lockout_applied": lockout_applied,
            },
        )
        if lockout_applied:
            self._emit_observability_event(
                stage="operator.auth_lockout",
                status="locked",
                source=normalized_source,
                metadata={
                    "source": normalized_source,
                    "reason": "failure_threshold_reached",
                    "failures_recent": failures_recent,
                    "lockout_until_epoch": int(lockout_until_epoch),
                },
            )

        return self.check_lockout(normalized_source)

    def record_authorized_success(self, source: str) -> None:
        normalized_source = str(source or "unknown").strip() or "unknown"
        with self._lock:
            state = self._source_states.get(normalized_source)
            if state is None:
                return
            state.failures.clear()

    def get_status(self) -> dict:
        now_epoch = time.time()
        active_lockouts: list[dict] = []
        recent_failures = 0

        with self._lock:
            for source, state in self._source_states.items():
                self._trim_failures(state, now_epoch)
                recent_failures += len(state.failures)

                remaining_raw = state.lockout_until_epoch - now_epoch
                remaining = max(0, math.ceil(remaining_raw))
                if remaining_raw > 0:
                    active_lockouts.append(
                        {
                            "source": source,
                            "remaining_seconds": remaining,
                            "lockout_until": datetime.fromtimestamp(state.lockout_until_epoch, tz=timezone.utc).isoformat(),
                            "failures_recent": len(state.failures),
                        }
                    )

        active_lockouts.sort(key=lambda item: int(item.get("remaining_seconds") or 0), reverse=True)
        return {
            "policy": {
                "enabled": bool(config.OPERATOR_REQUIRE_API_KEY),
                "failure_window_seconds": self._window_seconds(),
                "max_failures": self._max_failures(),
                "lockout_seconds": self._lockout_seconds(),
            },
            "lockout_count": len(active_lockouts),
            "recent_failure_count": recent_failures,
            "active_lockouts": active_lockouts,
        }

    def get_events(self, limit: int = 100) -> list[dict]:
        clamped_limit = max(1, min(int(limit), 500))
        with self._lock:
            events = list(self._events)
        return events[-clamped_limit:]

    def get_history(self, limit: int = 100) -> list[dict]:
        return store.get_recent_operator_security_events(limit=limit)

    def get_summary(self, window_limit: int = 1000) -> dict:
        return store.get_operator_security_summary(window_limit=window_limit)

    def send_test_alert(self, source: str = "operator-test") -> dict:
        event = {
            "event_id": f"operator-alert-test-{uuid4().hex[:10]}",
            "created_at": _utc_now_iso(),
            "stage": "operator.alert_test",
            "status": "test",
            "source": str(source or "operator-test"),
            "reason": "manual_test",
            "failures_recent": 0,
            "lockout_until": None,
        }
        self._persist_security_event(event)
        self._send_alert_for_event(event)
        return {
            "accepted": True,
            "event": event,
        }

    def get_open_incidents(self, limit: int = 200) -> list[dict]:
        return store.get_open_operator_security_incidents(limit=limit)

    def acknowledge_incident(self, incident_id: str, acked_by: str = "operator") -> dict | None:
        return store.acknowledge_operator_security_incident(incident_id, acked_by=acked_by)

    def resolve_incident(
        self,
        incident_id: str,
        *,
        resolved_by: str = "operator",
        resolution_note: str | None = None,
    ) -> dict | None:
        return store.resolve_operator_security_incident(
            incident_id,
            resolved_by=resolved_by,
            resolution_note=resolution_note,
        )


operator_incident_policy_service = OperatorIncidentPolicyService()
