#!/usr/bin/env python3
"""Refresh an existing local report while retaining its identity and URL."""

import argparse
import json

from market_atlas.reporting.refresh import refresh_report

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--project", default="data/generated/reports/browser")
parser.add_argument("--pack", required=True)
parser.add_argument("--run-id", required=True)
args = parser.parse_args()
print(json.dumps(refresh_report(args.project, args.pack, run_id=args.run_id)))
