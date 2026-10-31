#!/usr/bin/env python3
"""Build an editable native Power BI project; no Power BI/license required to author source."""

import argparse
import json

from market_atlas.reporting.project import build_project

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "--pack", required=True, help="one validated immutable pack directory"
)
parser.add_argument(
    "--output", required=True, help="new project directory (never overwritten)"
)
args = parser.parse_args()
print(json.dumps(build_project(args.pack, args.output)))
