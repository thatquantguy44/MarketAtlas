#!/usr/bin/env python3
"""Refresh an existing local report while retaining its identity and URL."""

import argparse
import json

from market_atlas.reporting.refresh import refresh_report

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--project", default="data/generated/reports/browser")
parser.add_argument("--pack", required=True)
parser.add_argument("--run-id", required=True)
parser.add_argument(
    "--analytics-pack", help="attach an independently validated macro research pack"
)
parser.add_argument(
    "--update-content",
    action="store_true",
    help="install the repository's authored report views atomically",
)
parser.add_argument(
    "--build-status", choices=["updating", "complete", "paused"], default="complete"
)
args = parser.parse_args()
print(
    json.dumps(
        refresh_report(
            args.project,
            args.pack,
            run_id=args.run_id,
            analytics_pack=args.analytics_pack,
            update_content=args.update_content,
            build_status=args.build_status,
        )
    )
)
