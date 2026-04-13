from __future__ import annotations

from fastapi import Header, HTTPException, Request

from app.core.config import (
    OPERATOR_ADMIN_KEY,
    OPERATOR_API_KEY,
    OPERATOR_EXECUTOR_KEY,
    OPERATOR_REQUIRE_API_KEY,
    OPERATOR_VIEWER_KEY,
)
from app.api.security.operator_incident_policy import operator_incident_policy_service


def _forbidden(detail: str) -> None:
    raise HTTPException(status_code=403, detail=detail)


def _request_source(request: Request | None) -> str:
    if request is None:
        return "unknown"
    if request.client and request.client.host:
        return str(request.client.host)
    return "unknown"


def _enforce_lockout_policy(request: Request | None) -> None:
    if not OPERATOR_REQUIRE_API_KEY:
        return
    lockout = operator_incident_policy_service.check_lockout(_request_source(request))
    if lockout.get("locked"):
        raise HTTPException(
            status_code=423,
            detail={
                "code": "OPERATOR_LOCKED_OUT",
                "message": "Operator source temporarily locked due to repeated auth failures",
                "source": lockout.get("source"),
                "remaining_seconds": int(lockout.get("remaining_seconds") or 0),
            },
        )


def _record_denied_attempt(request: Request | None, reason: str) -> None:
    if not OPERATOR_REQUIRE_API_KEY:
        return
    operator_incident_policy_service.record_denied_attempt(_request_source(request), reason=reason)


def _resolve_access_level(operator_key: str | None, request: Request | None = None) -> str:
    key = str(operator_key or "").strip()
    if not OPERATOR_REQUIRE_API_KEY:
        return "admin"

    _enforce_lockout_policy(request)

    if key and OPERATOR_ADMIN_KEY and key == OPERATOR_ADMIN_KEY:
        operator_incident_policy_service.record_authorized_success(_request_source(request))
        return "admin"
    if key and OPERATOR_EXECUTOR_KEY and key == OPERATOR_EXECUTOR_KEY:
        operator_incident_policy_service.record_authorized_success(_request_source(request))
        return "operator"
    if key and OPERATOR_API_KEY and key == OPERATOR_API_KEY:
        operator_incident_policy_service.record_authorized_success(_request_source(request))
        return "admin"
    if key and OPERATOR_VIEWER_KEY and key == OPERATOR_VIEWER_KEY:
        operator_incident_policy_service.record_authorized_success(_request_source(request))
        return "viewer"

    _record_denied_attempt(request, reason="invalid_or_missing_key")
    _forbidden("Operator key is missing or invalid")
    return "viewer"


def require_retry_view(
    request: Request,
    x_retry_role: str | None = Header(default=None, alias="X-Retry-Role"),
    x_operator_key: str | None = Header(default=None, alias="X-Operator-Key"),
) -> None:
    role = str(x_retry_role or "").strip().lower()
    if role not in {"reviewer", "operator", "admin"}:
        _forbidden("X-Retry-Role must be one of: reviewer, operator, admin")

    level = _resolve_access_level(x_operator_key, request=request)
    if level not in {"viewer", "operator", "admin"}:
        _record_denied_attempt(request, reason="insufficient_access_level")
        _forbidden("Access denied")


def require_retry_operator(
    request: Request,
    x_retry_role: str | None = Header(default=None, alias="X-Retry-Role"),
    x_operator_key: str | None = Header(default=None, alias="X-Operator-Key"),
) -> None:
    role = str(x_retry_role or "").strip().lower()
    if role not in {"operator", "admin"}:
        _forbidden("Operator role is required")

    level = _resolve_access_level(x_operator_key, request=request)
    if level not in {"operator", "admin"}:
        _record_denied_attempt(request, reason="insufficient_access_level")
        _forbidden("Operator access required")


def require_retry_reviewer(
    request: Request,
    x_retry_role: str | None = Header(default=None, alias="X-Retry-Role"),
    x_operator_key: str | None = Header(default=None, alias="X-Operator-Key"),
) -> None:
    role = str(x_retry_role or "").strip().lower()
    if role not in {"reviewer", "admin"}:
        _forbidden("Reviewer role is required")

    level = _resolve_access_level(x_operator_key, request=request)
    if level not in {"viewer", "operator", "admin"}:
        _record_denied_attempt(request, reason="insufficient_access_level")
        _forbidden("Reviewer access required")


def require_operator_action(
    request: Request,
    x_operator_key: str | None = Header(default=None, alias="X-Operator-Key"),
) -> None:
    """Require operator/admin key when OPERATOR_REQUIRE_API_KEY is enabled."""
    level = _resolve_access_level(x_operator_key, request=request)
    if level not in {"operator", "admin"}:
        _record_denied_attempt(request, reason="insufficient_role_for_action")
        _forbidden("Operator access required")


def require_operator_view(
    request: Request,
    x_operator_key: str | None = Header(default=None, alias="X-Operator-Key"),
) -> None:
    level = _resolve_access_level(x_operator_key, request=request)
    if level not in {"viewer", "operator", "admin"}:
        _record_denied_attempt(request, reason="insufficient_role_for_view")
        _forbidden("Viewer access required")


def require_operator_admin(
    request: Request,
    x_operator_key: str | None = Header(default=None, alias="X-Operator-Key"),
) -> None:
    level = _resolve_access_level(x_operator_key, request=request)
    if level != "admin":
        _record_denied_attempt(request, reason="insufficient_role_for_admin")
        _forbidden("Admin access required")


def resolve_operator_identity(
    request: Request,
    x_operator_key: str | None = Header(default=None, alias="X-Operator-Key"),
) -> dict:
    level = _resolve_access_level(x_operator_key, request=request)
    role = "executor" if level == "operator" else level

    permission_matrix = {
        "viewer": ["audit:read", "audit:verify", "operator:whoami"],
        "executor": [
            "audit:read",
            "audit:verify",
            "operator:whoami",
            "execution:stop",
            "queue:cancel",
            "queue:expire",
            "dispatcher:stop",
        ],
        "admin": [
            "audit:read",
            "audit:verify",
            "operator:whoami",
            "execution:stop",
            "queue:cancel",
            "queue:expire",
            "dispatcher:stop",
            "operator:admin",
        ],
    }
    return {
        "role": role,
        "requires_api_key": bool(OPERATOR_REQUIRE_API_KEY),
        "permissions": permission_matrix.get(role, []),
    }
