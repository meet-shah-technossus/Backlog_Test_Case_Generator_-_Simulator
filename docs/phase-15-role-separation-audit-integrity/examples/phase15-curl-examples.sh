#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
VIEWER_KEY="${VIEWER_KEY:-viewer-secret}"
EXECUTOR_KEY="${EXECUTOR_KEY:-executor-secret}"

echo "1) Role introspection (viewer)"
curl -sS "$BASE_URL/run/operator/whoami" \
  -H "x-operator-key: $VIEWER_KEY" | python3 -m json.tool

echo "2) Queue audit verify (viewer)"
curl -sS "$BASE_URL/run/queue/audit/verify?limit=200" \
  -H "x-operator-key: $VIEWER_KEY" | python3 -m json.tool

echo "3) Queue stop (executor)"
curl -sS -X DELETE "$BASE_URL/run/tests/stop" \
  -H "x-operator-key: $EXECUTOR_KEY" | python3 -m json.tool
