#!/usr/bin/env python3
"""Aggregate substitute comparison records into one pressure reading."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json

VERDICTS = ["SYNRAIL_BETTER", "SUBSTITUTE_GOOD_ENOUGH", "UNCLEAR"]






def build_record(paths: list[Path]) -> dict:
    records = [load_json(path) for path in paths]
    for record in records:
        if record.get("schema_version") != "substitute_comparison_record_v0":
            raise ValueError("all input records must use substitute_comparison_record_v0")
    verdict_counts = {verdict: 0 for verdict in VERDICTS}
    stack_counts: dict[str, int] = {}
    for record in records:
        verdict_counts[record["verdict"]] += 1
        stack = record["substitute_stack"]
        stack_counts[stack] = stack_counts.get(stack, 0) + 1
    strongest = ""
    if records:
        winner = max(records, key=lambda r: (r["economics_summary"]["false_green_exposure_reduced"], r["economics_summary"]["artifact_completeness_percent_gain"]))
        strongest = winner["scenario_id"]
    substitute_sufficient = [r for r in records if r["verdict"] == "SUBSTITUTE_GOOD_ENOUGH"]
    return {
        "schema_version": "substitute_pressure_record_v0",
        "record_count": len(records),
        "source_records": [
            {
                "path": str(path),
                "scenario_id": record["scenario_id"],
                "substitute_stack": record["substitute_stack"],
                "verdict": record["verdict"],
            }
            for path, record in zip(paths, records)
        ],
        "verdict_counts": verdict_counts,
        "substitute_stack_counts": stack_counts,
        "reading": {
            "strongest_synrail_edge": strongest,
            "clearest_substitute_sufficient_path": substitute_sufficient[0]["scenario_id"] if substitute_sufficient else "",
            "winning_substitute_stacks": sorted({r["substitute_stack"] for r in records if r["verdict"] == "SYNRAIL_BETTER"}),
            "non_winning_substitute_stacks": sorted({r["substitute_stack"] for r in records if r["verdict"] != "SYNRAIL_BETTER"}),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='synrail-substitute-pressure-v0')
    parser.add_argument('--record', action='append', required=True)
    parser.add_argument('--output', required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        record = build_record([Path(p) for p in args.record])
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "record_count": record["record_count"]}, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
