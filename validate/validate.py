"""
Validate manifests and canonical CSVs against their JSON schemas.

Usage:
  python validate/validate.py
"""

from __future__ import annotations

import csv
import json
import pathlib
import sys

import jsonschema
import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST_DIR = REPO_ROOT / "manifest"
CANONICAL_DIR = REPO_ROOT / "canonical"


def load_schema(name: str) -> dict:
    return json.loads((MANIFEST_DIR / "schema" / f"{name}.json").read_text())


def validate_sources() -> int:
    schema = load_schema("source-entry")
    data = yaml.safe_load((MANIFEST_DIR / "sources.yaml").read_text())
    errors = 0
    for src in data["sources"]:
        try:
            jsonschema.validate(src, schema)
        except jsonschema.ValidationError as e:
            print(f"sources.yaml :: {src.get('id', '?')} :: {e.message}")
            errors += 1
    print(f"sources.yaml: {len(data['sources'])} entries, {errors} error(s)")
    return errors


def validate_metrics() -> int:
    schema = load_schema("metric-entry")
    data = yaml.safe_load((MANIFEST_DIR / "metrics.yaml").read_text())
    errors = 0
    for m in data["metrics"]:
        try:
            jsonschema.validate(m, schema)
        except jsonschema.ValidationError as e:
            print(f"metrics.yaml :: {m.get('id', '?')} :: {e.message}")
            errors += 1
    print(f"metrics.yaml: {len(data['metrics'])} entries, {errors} error(s)")
    return errors


def validate_canonical() -> int:
    schema = load_schema("canonical")
    errors = 0
    for csv_path in sorted(CANONICAL_DIR.glob("*.csv")):
        n_rows = 0
        file_errors = 0
        with csv_path.open() as f:
            for i, row in enumerate(csv.DictReader(f), start=2):
                n_rows += 1
                # Coerce types per the schema
                typed = {**row}
                for k in ("value", "ci_lower", "ci_upper"):
                    if typed.get(k) not in ("", None):
                        typed[k] = float(typed[k])
                    else:
                        typed[k] = None
                if typed.get("sample_size") in ("", None):
                    typed["sample_size"] = None
                else:
                    typed["sample_size"] = int(typed["sample_size"])
                typed["year"] = int(typed["year"])
                for k in ("denominator", "methodology_note"):
                    if typed.get(k) in ("", None):
                        typed[k] = None
                if typed.get("break_flag") in ("", "false", "False"):
                    typed["break_flag"] = False
                elif typed["break_flag"] in ("true", "True"):
                    typed["break_flag"] = True
                try:
                    jsonschema.validate(typed, schema)
                except jsonschema.ValidationError as e:
                    print(f"{csv_path.name} :: row {i} :: {e.message}")
                    file_errors += 1
        print(f"{csv_path.name}: {n_rows} rows, {file_errors} error(s)")
        errors += file_errors
    return errors


def main() -> None:
    e1 = validate_sources()
    e2 = validate_metrics()
    e3 = validate_canonical()
    total = e1 + e2 + e3
    print(f"\nTOTAL: {total} error(s)")
    sys.exit(1 if total else 0)


if __name__ == "__main__":
    main()
