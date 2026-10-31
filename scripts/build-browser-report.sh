#!/usr/bin/env bash
# Build a local report with the installed Data plugin's bundled browser runtime.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -ne 2 ]]; then
  echo 'Usage: scripts/build-browser-report.sh PACK_DIRECTORY NEW_OUTPUT_DIRECTORY' >&2
  exit 2
fi
plugin="${MARKETATLAS_DATA_PLUGIN:-$HOME/.codex/plugins/cache/openai-curated-remote/data-analytics/1.1.0-exp-homepage}"
if [[ ! -f "$plugin/scripts/prepare-data-app.mjs" ]]; then
  echo 'Data plugin runtime missing; set MARKETATLAS_DATA_PLUGIN to its installed directory.' >&2
  exit 1
fi
pack="$1"
output="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "$2")"
if [[ -e "$output" ]]; then
  echo 'Output already exists; choose a new directory to preserve edits.' >&2
  exit 1
fi
snapshot="$(mktemp -t marketatlas-browser)"
trap 'rm -f "$snapshot"' EXIT
PYTHONPATH=src python3 - "$pack" "$snapshot" <<'PY'
import json,sys
from pathlib import Path
from market_atlas.reporting.browser import browser_snapshot
Path(sys.argv[2]).write_text(json.dumps(browser_snapshot(sys.argv[1]),indent=2))
PY
node "$plugin/scripts/prepare-data-app.mjs" --surface dashboard --output "$output" --snapshot "$snapshot"
cp powerbi/browser/*.jsx "$output/src/content/dashboard/"
PYTHONPATH=src python3 - "$output" <<'PY'
import json,sys
from pathlib import Path
path=Path(sys.argv[1])/'src/data.json'
data=json.loads(path.read_text());data['buildStatus']='complete';path.write_text(json.dumps(data,indent=2))
PY
node "$plugin/scripts/data-app.mjs" build --project-dir "$output" --separate-data
