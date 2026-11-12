#!/usr/bin/env python3
"""Entry point: build the star schema, validate it, print a vote-share summary.

Usage:
    python main.py [--data-dir sample_data] [--out out]

Exits non-zero if any reconciliation check fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.prep import build_model, load_raw, write_model
from pipeline.summary import format_swing_table, swing_table
from pipeline.validate import ValidationError, validate_model, validate_raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="US elections vote-share data pipeline")
    parser.add_argument("--data-dir", default="sample_data", help="Directory with results_*.csv extracts")
    parser.add_argument("--out", default="out", help="Directory for modeled CSV tables")
    args = parser.parse_args(argv)

    try:
        rows = load_raw(args.data_dir)
        print(f"Loaded {len(rows)} raw result rows from {args.data_dir}/")

        print("\n== Raw data validation ==")
        for check in validate_raw(rows):
            print(f"  PASS: {check}")

        dim_state, dim_candidate, fact = build_model(rows)
        written = write_model(args.out, dim_state, dim_candidate, fact)
        print(f"\nWrote star schema to {args.out}/:")
        for name, path in written.items():
            print(f"  - {path}")

        print("\n== Model validation ==")
        for check in validate_model(rows, dim_state, dim_candidate, fact):
            print(f"  PASS: {check}")
    except (ValidationError, FileNotFoundError) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        return 1

    print("\n== Vote share by state (%) ==")
    print(format_swing_table(swing_table(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
