#!/bin/bash
# Start backend safely for Playwright runs.
# Default: NO reload (best for demos and stable execution).
# Optional dev mode: RELOAD=1 ./start.sh

cd "$(dirname "$0")"

if [ "${RELOAD:-0}" = "1" ]; then
  .venv/bin/uvicorn app.main:app \
    --reload \
    --reload-dir . \
    --reload-exclude "artifacts/*" \
    --reload-exclude "artifacts/**" \
    --host 0.0.0.0 \
    --port 8000
else
  .venv/bin/uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000
fi
