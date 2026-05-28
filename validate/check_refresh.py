"""
Source refresh-cadence tracker.

Reads manifest/sources.yaml. For each source with a `next_expected` date,
checks whether we're past it. Prints a punch list of sources that are
overdue for a refresh.

Non-zero exit if any source is more than 60 days past its next_expected date
(soft alert — CI runs this `continue-on-error: true`).

Usage:
  python validate/check_refresh.py
"""

from __future__ import annotations

import datetime as dt
import pathlib
import sys

import yaml

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
MANIFEST = REPO_ROOT / "manifest" / "sources.yaml"
OVERDUE_THRESHOLD_DAYS = 60


def main() -> None:
    today = dt.date.today()
    with MANIFEST.open() as f:
        data = yaml.safe_load(f)

    overdue: list[tuple[str, str, int]] = []
    upcoming: list[tuple[str, str, int]] = []
    no_date: list[str] = []

    for src in data["sources"]:
        sid = src["id"]
        ne = src.get("next_expected")
        if not ne:
            no_date.append(sid)
            continue
        # ne could be a date string ("2026-11-01") or already a date object
        if isinstance(ne, str):
            try:
                ne = dt.date.fromisoformat(ne)
            except ValueError:
                no_date.append(sid)
                continue
        days = (ne - today).days
        if days < 0:
            overdue.append((sid, ne.isoformat(), -days))
        else:
            upcoming.append((sid, ne.isoformat(), days))

    print(f"Source refresh check  ·  today = {today.isoformat()}")
    print("=" * 60)

    if overdue:
        overdue.sort(key=lambda x: -x[2])
        print(f"\nOVERDUE ({len(overdue)} source(s)):")
        for sid, when, days_late in overdue:
            tag = " 🔴" if days_late > OVERDUE_THRESHOLD_DAYS else " 🟡"
            print(f"  {tag} {sid:<32}  expected {when}, {days_late} days ago")
    else:
        print("\nOVERDUE:  none ✓")

    if upcoming:
        upcoming.sort(key=lambda x: x[2])
        print(f"\nUPCOMING ({len(upcoming)} source(s)):")
        for sid, when, days_until in upcoming[:10]:
            print(f"  · {sid:<32}  expected {when} (in {days_until} days)")

    if no_date:
        print(f"\nNO next_expected SET ({len(no_date)} source(s)):")
        for sid in no_date:
            print(f"  · {sid}")

    print()
    hard_overdue = [o for o in overdue if o[2] > OVERDUE_THRESHOLD_DAYS]
    if hard_overdue:
        print(f"FAIL: {len(hard_overdue)} source(s) more than {OVERDUE_THRESHOLD_DAYS} days overdue")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
