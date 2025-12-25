#!/usr/bin/env bash
set -euo pipefail
source .env
uvicorn orchestrator.main:app --host 0.0.0.0 --port ${API_PORT:-8000}
