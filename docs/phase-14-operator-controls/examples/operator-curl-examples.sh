#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
OP_KEY="${OPERATOR_API_KEY:-change-me}"

echo "1) Queue health (public)"
curl -sS "$BASE_URL/run/queue/health" | python3 -m json.tool

echo "2) Queue audit (operator protected if enabled)"
curl -sS "$BASE_URL/run/queue/audit?limit=20&status=error" \
  -H "x-operator-key: $OP_KEY" | python3 -m json.tool

echo "3) Stop active run (operator protected if enabled)"
curl -sS -X DELETE "$BASE_URL/run/tests/stop" \
  -H "x-operator-key: $OP_KEY" | python3 -m json.tool
