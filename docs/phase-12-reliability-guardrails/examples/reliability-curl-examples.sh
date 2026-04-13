#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
STORY_ID="${STORY_ID:-US-1234}"

echo "1) Queue a run"
QUEUE_ID=$(curl -sS -X POST "$BASE_URL/run/tests" \
  -H "Content-Type: application/json" \
  -d "{\"story_id\": \"$STORY_ID\"}" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("queue_id",""))')

echo "Queued: $QUEUE_ID"

echo "2) Queue health"
curl -sS "$BASE_URL/run/queue/health" | python3 -m json.tool

echo "3) Queue snapshot"
curl -sS "$BASE_URL/run/queue?limit=20" | python3 -m json.tool

echo "4) Queue item"
curl -sS "$BASE_URL/run/queue/$QUEUE_ID" | python3 -m json.tool

# Cancel only while still pending
# curl -sS -X DELETE "$BASE_URL/run/queue/$QUEUE_ID" | python3 -m json.tool
