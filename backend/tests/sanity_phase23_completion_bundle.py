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
        config.OPERATOR_API_KEY = "phase23-complete-key"
        operator_auth.OPERATOR_REQUIRE_API_KEY = True
        operator_auth.OPERATOR_API_KEY = "phase23-complete-key"

        client = TestClient(app)
        headers = {
            "X-Operator-Key": "phase23-complete-key",
            "X-Retry-Role": "admin",
        }

        spec_resp = client.get("/retry-governance/spec", headers=headers)
        preflight_resp = client.get("/retry-governance/phase23/preflight", headers=headers)

        assert spec_resp.status_code == 200, spec_resp.text
        assert preflight_resp.status_code == 200, preflight_resp.text

        spec = (spec_resp.json() or {}).get("spec") or {}
        preflight = preflight_resp.json() or {}
        checklist = preflight.get("checklist") or []

        assert preflight.get("phase") == "phase23", preflight
        assert preflight.get("completion_status") == "complete", preflight

        phase_map = {str(item.get("phase") or ""): item for item in checklist}
        for phase in ["2", "3", "4", "5", "6", "7", "8", "9", "10", "11"]:
            assert phase in phase_map, phase_map
            assert (phase_map[phase] or {}).get("status") == "complete", phase_map

        lifecycle = set(spec.get("lifecycle") or [])
        expected_lifecycle = {
            "retry_requested",
            "retry_review_pending",
            "retry_approved",
            "retry_rejected",
            "retry_running",
            "retry_completed",
            "retry_failed",
        }
        assert lifecycle == expected_lifecycle, spec

        print(
            {
                "phase": preflight.get("phase"),
                "completion_status": preflight.get("completion_status"),
                "checklist_items": len(checklist),
                "lifecycle_count": len(lifecycle),
            }
        )
    finally:
        config.OPERATOR_REQUIRE_API_KEY = old_require_config
        config.OPERATOR_API_KEY = old_key_config
        operator_auth.OPERATOR_REQUIRE_API_KEY = old_require_auth
        operator_auth.OPERATOR_API_KEY = old_key_auth


if __name__ == "__main__":
    main()
