"""
Central configuration module.
Reads all settings from the .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()


def _csv_env(name: str, default: str = "") -> list[str]:
	raw = os.getenv(name, default)
	if not raw:
		return []
	return [value.strip() for value in raw.split(",") if value.strip()]

# --- LLM Provider (OpenAI) ---
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "120"))

# --- Backlog API ---
BACKLOG_API_BASE_URL: str = os.getenv("BACKLOG_API_BASE_URL", "")
BACKLOG_API_KEY: str = os.getenv("BACKLOG_API_KEY", "")

# --- Backend Server ---
BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
BACKEND_CORS_ORIGINS: list[str] = _csv_env(
	"BACKEND_CORS_ORIGINS",
	"http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000",
)

# --- Playwright ---
PLAYWRIGHT_SLOW_MO: int = int(os.getenv("PLAYWRIGHT_SLOW_MO", "1500"))
PLAYWRIGHT_HEADLESS: bool = os.getenv("PLAYWRIGHT_HEADLESS", "false").lower() == "true"

# --- Security / Compliance ---
SECURITY_REQUIRE_DOMAIN_ALLOWLIST: bool = (
	os.getenv("SECURITY_REQUIRE_DOMAIN_ALLOWLIST", "false").lower() == "true"
)
SECURITY_REDACT_SENSITIVE_DATA: bool = (
	os.getenv("SECURITY_REDACT_SENSITIVE_DATA", "true").lower() == "true"
)

# --- Evaluation / Cost Analytics ---
EVAL_INPUT_COST_PER_1K_USD: float = float(os.getenv("EVAL_INPUT_COST_PER_1K_USD", "0.0"))
EVAL_OUTPUT_COST_PER_1K_USD: float = float(os.getenv("EVAL_OUTPUT_COST_PER_1K_USD", "0.0"))

# --- Production Hardening / Queueing ---
EXECUTION_MAX_QUEUE_SIZE: int = int(os.getenv("EXECUTION_MAX_QUEUE_SIZE", "20"))
EXECUTION_QUEUE_POLL_MS: int = int(os.getenv("EXECUTION_QUEUE_POLL_MS", "500"))
EXECUTION_DISPATCHER_WORKERS: int = int(os.getenv("EXECUTION_DISPATCHER_WORKERS", "1"))
EXECUTION_DISPATCHER_AUTO_START: bool = (
	os.getenv("EXECUTION_DISPATCHER_AUTO_START", "true").lower() == "true"
)
EXECUTION_RUN_TIMEOUT_SECONDS: int = int(os.getenv("EXECUTION_RUN_TIMEOUT_SECONDS", "900"))
EXECUTION_SCRIPT_TIMEOUT_SECONDS: int = int(os.getenv("EXECUTION_SCRIPT_TIMEOUT_SECONDS", "12"))
EXECUTION_PENDING_TTL_SECONDS: int = int(os.getenv("EXECUTION_PENDING_TTL_SECONDS", "3600"))

# --- Phase 10 Execution Runtime Policy ---
EXECUTION_VISUAL_SLOW_MO_MS: int = int(os.getenv("EXECUTION_VISUAL_SLOW_MO_MS", "1000"))
EXECUTION_MAX_PARALLEL_WORKERS: int = int(os.getenv("EXECUTION_MAX_PARALLEL_WORKERS", "1"))
EXECUTION_CAPTURE_VIDEO: bool = os.getenv("EXECUTION_CAPTURE_VIDEO", "true").lower() == "true"
EXECUTION_VIDEO_WIDTH: int = int(os.getenv("EXECUTION_VIDEO_WIDTH", "1280"))
EXECUTION_VIDEO_HEIGHT: int = int(os.getenv("EXECUTION_VIDEO_HEIGHT", "720"))

# --- Operator Access Control ---
OPERATOR_REQUIRE_API_KEY: bool = (
	os.getenv("OPERATOR_REQUIRE_API_KEY", "false").lower() == "true"
)
OPERATOR_API_KEY: str = os.getenv("OPERATOR_API_KEY", "")
OPERATOR_VIEWER_KEY: str = os.getenv("OPERATOR_VIEWER_KEY", "")
OPERATOR_EXECUTOR_KEY: str = os.getenv("OPERATOR_EXECUTOR_KEY", "")
OPERATOR_ADMIN_KEY: str = os.getenv("OPERATOR_ADMIN_KEY", "")

# --- Audit Integrity ---
AUDIT_SIGNING_SECRET: str = os.getenv("AUDIT_SIGNING_SECRET", "")

# --- Operator Incident Policy (Phase 16) ---
OPERATOR_AUTH_FAILURE_WINDOW_SECONDS: int = int(
	os.getenv("OPERATOR_AUTH_FAILURE_WINDOW_SECONDS", "300")
)
OPERATOR_AUTH_MAX_FAILURES: int = int(
	os.getenv("OPERATOR_AUTH_MAX_FAILURES", "5")
)
OPERATOR_AUTH_LOCKOUT_SECONDS: int = int(
	os.getenv("OPERATOR_AUTH_LOCKOUT_SECONDS", "600")
)

# --- Operator Incident Alerts (Phase 17) ---
OPERATOR_ALERT_WEBHOOK_URL: str = os.getenv("OPERATOR_ALERT_WEBHOOK_URL", "")
OPERATOR_ALERT_TIMEOUT_SECONDS: int = int(
	os.getenv("OPERATOR_ALERT_TIMEOUT_SECONDS", "5")
)
OPERATOR_ALERT_CHANNEL: str = os.getenv("OPERATOR_ALERT_CHANNEL", "webhook")
OPERATOR_ALERT_MAX_RETRIES: int = int(
	os.getenv("OPERATOR_ALERT_MAX_RETRIES", "3")
)
OPERATOR_ALERT_RETRY_BASE_MS: int = int(
	os.getenv("OPERATOR_ALERT_RETRY_BASE_MS", "300")
)

# --- Final Ops Readiness (Phase 20) ---
OPERATOR_SECURITY_OPEN_INCIDENT_THRESHOLD: int = int(
	os.getenv("OPERATOR_SECURITY_OPEN_INCIDENT_THRESHOLD", "0")
)

# --- Retry Governance Policy (Phase 2) ---
RETRY_ALLOW_SELF_APPROVAL: bool = (
	os.getenv("RETRY_ALLOW_SELF_APPROVAL", "false").lower() == "true"
)
RETRY_ALLOWED_REVIEWERS: list[str] = _csv_env("RETRY_ALLOWED_REVIEWERS", "")
RETRY_DEFAULT_REVIEWERS: str = os.getenv(
	"RETRY_DEFAULT_REVIEWERS",
	"agent1:agent1-reviewer,agent2:agent2-reviewer,agent3:agent3-reviewer,agent4:agent4-reviewer,agent5:agent5-reviewer",
)
