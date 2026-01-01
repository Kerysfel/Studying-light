#!/usr/bin/env sh
set -e

UVICORN_HOST="${UVICORN_HOST:-0.0.0.0}"
UVICORN_PORT="${UVICORN_PORT:-8000}"
UVICORN_LOG_LEVEL="${UVICORN_LOG_LEVEL:-info}"

exec uv run uvicorn studying_light.main:app \
  --host "$UVICORN_HOST" \
  --port "$UVICORN_PORT" \
  --log-level "$UVICORN_LOG_LEVEL"
