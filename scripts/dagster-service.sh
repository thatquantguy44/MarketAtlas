#!/usr/bin/env bash
# Install/start, inspect or stop the local macOS user login service.
set -euo pipefail
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m market_atlas.orchestration.service "${1:-status}"
