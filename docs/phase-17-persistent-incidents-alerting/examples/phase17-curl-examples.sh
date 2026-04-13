#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
VIEWER_KEY="${VIEWER_KEY:-viewer-secret}"
ADMIN_KEY="${ADMIN_KEY:-admin-secret}"

echo "1) Security summary"
curl -sS "$BASE_URL/run/operator/security/summary?lookback_limit=500" \
  -H "x-operator-key: $VIEWER_KEY" | python3 -m json.tool

echo "2) Security persistent history"
curl -sS "$BASE_URL/run/operator/security/history?limit=50" \
  -H "x-operator-key: $VIEWER_KEY" | python3 -m json.tool

echo "3) Send test alert (admin only)"
curl -sS -X POST "$BASE_URL/run/operator/security/alerts/test" \
  -H "x-operator-key: $ADMIN_KEY" | python3 -m json.tool
