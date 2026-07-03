#!/usr/bin/env bash
# Render web service entrypoint (repo root).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
export PYTHONPATH="${ROOT}:${ROOT}/phases/phase-3${PYTHONPATH:+:${PYTHONPATH}}"
exec python -m uvicorn app.main:create_app --factory --host 0.0.0.0 --port "${PORT:?PORT is not set}" --app-dir phases/phase-3
