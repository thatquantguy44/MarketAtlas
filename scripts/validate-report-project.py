#!/usr/bin/env python3
"""Validate PBIP/PBIR JSON against official Microsoft schemas (requires jsonschema 4.25.1 and curl).

Usage: python scripts/validate-report-project.py PROJECT_DIRECTORY [...]
This does not execute Power BI, DAX or the semantic model.
"""

import argparse
import hashlib
import json
import pathlib
import subprocess
import tempfile

import jsonschema
from referencing import Registry, Resource

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("projects", nargs="+", type=pathlib.Path)
args = parser.parse_args()

cache = pathlib.Path(tempfile.gettempdir()) / "marketatlas-schema-cache"
cache.mkdir(exist_ok=True)


def retrieve(uri):
    url = uri.split("#")[0]
    if not url.startswith("https://developer.microsoft.com/json-schemas/"):
        raise ValueError("unexpected schema host")
    path = cache / hashlib.sha256(url.encode()).hexdigest()
    if not path.exists():
        subprocess.run(
            ["curl", "-fsSL", "--max-time", "30", url, "-o", str(path)], check=True
        )
    return Resource.from_contents(json.loads(path.read_text()))


registry = Registry(retrieve=retrieve)
for root in args.projects:
    if not (root / "MarketAtlas.pbip").is_file():
        raise SystemExit(f"No MarketAtlas.pbip in {root}")
    count = 0
    for p in (
        list(root.rglob("*.json"))
        + list(root.rglob("*.pbip"))
        + list(root.rglob("*.pbir"))
    ):
        d = json.loads(p.read_text())
        if "$schema" not in d:
            continue
        schema = retrieve(d["$schema"]).contents
        validator = jsonschema.Draft7Validator(schema, registry=registry)
        errors = list(validator.iter_errors(d))
        if errors:
            for e in errors:
                print(p, e.json_path, e.message)
            raise SystemExit(1)
        count += 1
    print(root, count, "Power BI files passed official schemas")
