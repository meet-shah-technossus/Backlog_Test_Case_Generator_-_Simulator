from __future__ import annotations

import json
import time
from dataclasses import dataclass, field

import httpx

from app.core import config


@dataclass
class OperatorAlertResult:
    delivered: bool
    attempts: int
    status_code: int | None = None
    error: str | None = None
    channel: str = "webhook"
    attempt_history: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "delivered": bool(self.delivered),
            "attempts": int(self.attempts),
            "status_code": self.status_code,
            "error": self.error,
            "channel": self.channel,
            "attempt_history": list(self.attempt_history),
        }


class OperatorAlertService:
    """Best-effort webhook delivery for operator security incidents."""

    def _channel(self) -> str:
        normalized = str(config.OPERATOR_ALERT_CHANNEL or "webhook").strip().lower()
        if normalized in {"webhook", "slack", "teams"}:
            return normalized
        return "webhook"

    def _webhook_url(self) -> str:
        return str(config.OPERATOR_ALERT_WEBHOOK_URL or "").strip()

    def _timeout_seconds(self) -> int:
        return max(1, int(config.OPERATOR_ALERT_TIMEOUT_SECONDS or 5))

    def _max_retries(self) -> int:
        return max(0, int(config.OPERATOR_ALERT_MAX_RETRIES or 0))

    def _retry_base_seconds(self) -> float:
        return max(0.05, float(int(config.OPERATOR_ALERT_RETRY_BASE_MS or 300)) / 1000.0)

    def _format_payload_for_channel(self, payload: dict, channel: str) -> dict:
        raw_event = payload.get("event")
        event: dict = raw_event if isinstance(raw_event, dict) else {}
        stage = str(event.get("stage") or "operator.auth")
        status = str(event.get("status") or "n/a")
        source = str(event.get("source") or "unknown")
        reason = str(event.get("reason") or "")

        if channel == "slack":
            return {
                "text": f"Operator security incident: {stage} ({status})",
                "attachments": [
                    {
                        "color": "#b63434" if status in {"denied", "locked", "failed"} else "#b87e0f",
                        "fields": [
                            {"title": "Stage", "value": stage, "short": True},
                            {"title": "Status", "value": status, "short": True},
                            {"title": "Source", "value": source, "short": True},
                            {"title": "Reason", "value": reason or "-", "short": True},
                        ],
                        "footer": "agent4-operator-security",
                    }
                ],
            }

        if channel == "teams":
            return {
                "@type": "MessageCard",
                "@context": "http://schema.org/extensions",
                "summary": "Operator security incident",
                "themeColor": "C0392B" if status in {"denied", "locked", "failed"} else "D68910",
                "title": "Operator Security Incident",
                "sections": [
                    {
                        "facts": [
                            {"name": "Stage", "value": stage},
                            {"name": "Status", "value": status},
                            {"name": "Source", "value": source},
                            {"name": "Reason", "value": reason or "-"},
                        ]
                    }
                ],
            }

        return payload

    def send_incident_alert(self, payload: dict) -> OperatorAlertResult:
        channel = self._channel()
        webhook_url = self._webhook_url()
        if not webhook_url:
            return OperatorAlertResult(
                delivered=False,
                attempts=0,
                error="Webhook URL not configured",
                channel=channel,
            )

        attempts = 0
        last_error: str | None = None
        last_status_code: int | None = None
        max_attempts = self._max_retries() + 1
        attempt_history: list[dict] = []
        outbound_payload = self._format_payload_for_channel(payload, channel)

        for attempt in range(1, max_attempts + 1):
            attempts = attempt
            started = time.time()
            try:
                with httpx.Client(timeout=self._timeout_seconds()) as client:
                    response = client.post(
                        webhook_url,
                        headers={"Content-Type": "application/json"},
                        content=json.dumps(outbound_payload),
                    )
                last_status_code = int(response.status_code)
                attempt_history.append(
                    {
                        "attempt": attempt,
                        "status_code": last_status_code,
                        "ok": 200 <= response.status_code < 300,
                        "duration_ms": int((time.time() - started) * 1000),
                    }
                )
                if 200 <= response.status_code < 300:
                    return OperatorAlertResult(
                        delivered=True,
                        attempts=attempts,
                        status_code=last_status_code,
                        channel=channel,
                        attempt_history=attempt_history,
                    )
                last_error = f"HTTP {response.status_code}"
            except Exception as exc:
                last_error = str(exc)
                attempt_history.append(
                    {
                        "attempt": attempt,
                        "status_code": None,
                        "ok": False,
                        "duration_ms": int((time.time() - started) * 1000),
                        "error": last_error,
                    }
                )

            if attempt < max_attempts:
                time.sleep(self._retry_base_seconds() * (2 ** (attempt - 1)))

        return OperatorAlertResult(
            delivered=False,
            attempts=attempts,
            status_code=last_status_code,
            error=last_error or "Alert delivery failed",
            channel=channel,
            attempt_history=attempt_history,
        )


operator_alert_service = OperatorAlertService()
