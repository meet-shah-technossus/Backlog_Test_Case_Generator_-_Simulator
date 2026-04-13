from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.api.security import operator_auth
from app.core import config
from app.main import app


def main() -> None:
    old_require_config = config.OPERATOR_REQUIRE_API_KEY
    old_key_config = config.OPERATOR_API_KEY
    old_require_auth = operator_auth.OPERATOR_REQUIRE_API_KEY
    old_key_auth = operator_auth.OPERATOR_API_KEY

    try:
        config.OPERATOR_REQUIRE_API_KEY = True
        config.OPERATOR_API_KEY = "phase23-admin-key"
        operator_auth.OPERATOR_REQUIRE_API_KEY = True
        operator_auth.OPERATOR_API_KEY = "phase23-admin-key"

        client = TestClient(app)
        headers = {
            "X-Operator-Key": "phase23-admin-key",
            "X-Retry-Role": "admin",
        }

        response = client.get("/retry-governance/spec", headers=headers)
        assert response.status_code == 200, response.text

        payload = response.json() or {}
        spec = payload.get("spec") or {}

        lifecycle = spec.get("lifecycle") or []
        metadata_fields = spec.get("required_metadata") or []
        scopes = spec.get("applicable_run_scopes") or []

        expected_lifecycle = {
            "retry_requested",
            "retry_review_pending",
            "retry_approved",
            "retry_rejected",
            "retry_running",
            "retry_completed",
            "retry_failed",
        }
        expected_metadata = {
            "requested_by",
            "requested_at",
            "reason_code",
            "reason_text",
            "reviewer_id",
            "reviewer_decision",
            "reviewer_comment",
            "approved_at",
            "retry_attempt_number",
            "cooldown_until",
        }

        assert spec.get("phase") == "phase23", spec
        assert spec.get("scope") == "agent5_execution_analysis", spec
        assert set(lifecycle) == expected_lifecycle, lifecycle
        assert set(metadata_fields) == expected_metadata, metadata_fields
        assert "agent5" in scopes, scopes

        print(
            {
                "phase": spec.get("phase"),
                "scope": spec.get("scope"),
                "lifecycle_count": len(lifecycle),
                "metadata_count": len(metadata_fields),
                "includes_agent5": "agent5" in scopes,
            }
        )
    finally:
        config.OPERATOR_REQUIRE_API_KEY = old_require_config
        config.OPERATOR_API_KEY = old_key_config
        operator_auth.OPERATOR_REQUIRE_API_KEY = old_require_auth
        operator_auth.OPERATOR_API_KEY = old_key_auth


if __name__ == "__main__":
    main()
