#!/usr/bin/env bash
# Manage the optional local browser report's persistent preview.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ $# -gt 2 ]]; then
  echo 'Usage: scripts/report-preview.sh [start|status|stop] [REPORT_PROJECT_DIRECTORY]' >&2
  exit 2
fi
action="${1:-start}"
case "$action" in
  start|status|stop) ;;
  *) echo 'Usage: scripts/report-preview.sh [start|status|stop] [REPORT_PROJECT_DIRECTORY]' >&2; exit 2 ;;
esac
for dependency in node python3; do
  if ! command -v "$dependency" >/dev/null 2>&1; then
    echo "Missing prerequisite: $dependency" >&2
    exit 1
  fi
done
plugin="${MARKETATLAS_DATA_PLUGIN:-$HOME/.codex/plugins/cache/openai-curated-remote/data-analytics/1.1.0-exp-homepage}"
if [[ ! -f "$plugin/scripts/data-app-preview.mjs" ]]; then
  echo 'Data preview runtime missing; set MARKETATLAS_DATA_PLUGIN to the installed Data plugin directory.' >&2
  exit 1
fi
report_project="$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve())' "${2:-data/generated/reports/browser}")"
if [[ "$action" == start && ! -f "$report_project/dist/index.html" ]]; then
  echo "No compiled report at $report_project/dist/index.html" >&2
  echo 'Build a report with scripts/build-browser-report.sh PACK_DIRECTORY NEW_REPORT_PROJECT_DIRECTORY, then start that project.' >&2
  exit 1
fi
exec node "$plugin/scripts/data-app-preview.mjs" "$action" --project-dir "$report_project"
