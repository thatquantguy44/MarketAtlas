#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p .dagster
if [[ ! -f .dagster/dagster.yaml ]]; then
  cp orchestration/dagster.yaml .dagster/dagster.yaml
fi
export DAGSTER_HOME="$PWD/.dagster"
export PYTHONPATH="$PWD/src${PYTHONPATH:+:$PYTHONPATH}"
exec .venv-dagster/bin/dagster dev -m market_atlas.orchestration.definitions --host 127.0.0.1 --port 3001
