#!/usr/bin/env python3
"""Aggregate economics records into one cost-of-control reading."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


VERDICTS = ["SYNRAIL_BETTER", "BASELINE_GOOD_ENOUGH", "UNCLEAR"]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def average(records: list[dict], key: str) -> int:
    if not records:
        return 0
    total = sum(record["economics_summary"][key] for record in records)
    return round(total / len(records))


def hotspot(records: list[dict], key: str) -> dict:
    winner = max(records, key=lambda record: record["economics_summary"][key])
    return {
        "scenario_id": winner["scenario_id"],
        "path": winner["synrail_path"],
        "value": winner["economics_summary"][key],
    }


def strongest_justified_path(records: list[dict]) -> str:
    justified = [record for record in records if record["verdict"] == "SYNRAIL_BETTER"]
    if not justified:
        return ""
    winner = max(
        justified,
        key=lambda record: (
            record["economics_summary"]["false_green_exposure_reduced"],
            record["economics_summary"]["artifact_completeness_percent_gain"],
        ),
    )
    return winner["scenario_id"]


def clearest_overhead_path(records: list[dict]) -> str:
    non_wins = [record for record in records if record["verdict"] != "SYNRAIL_BETTER"]
    if not non_wins:
        return ""
    winner = max(
        non_wins,
        key=lambda record: (
            record["economics_summary"]["operator_minutes_added"],
            record["economics_summary"]["closure_latency_minutes_added"],
        ),
    )
    return winner["scenario_id"]


def find_verdict_for_class(records: list[dict], scenario_class: str) -> str:
    for record in records:
        if record["scenario_class"] == scenario_class:
            return record["verdict"]
    return "UNKNOWN"


def build_cost_record(paths: list[Path]) -> dict:
    records = [load_json(path) for path in paths]
    for record in records:
        if record.get("schema_version") != "baseline_comparison_record_v1":
            raise ValueError("all input records must use baseline_comparison_record_v1")

    verdict_counts = {verdict: 0 for verdict in VERDICTS}
    for record in records:
        verdict_counts[record["verdict"]] += 1

    source_records = [
        {
            "path": str(path),
            "scenario_id": record["scenario_id"],
            "scenario_class": record["scenario_class"],
            "verdict": record["verdict"],
        }
        for path, record in zip(paths, records)
    ]

    return {
        "schema_version": "cost_of_control_record_v0",
        "scenario_count": len(records),
        "source_records": source_records,
        "verdict_counts": verdict_counts,
        "aggregate_deltas": {
            "avg_operator_minutes_added": average(records, "operator_minutes_added"),
            "avg_intervention_count_added": average(records, "intervention_count_added"),
            "avg_repair_cycles_added": average(records, "repair_cycles_added"),
            "avg_invalidation_count_added": average(records, "invalidation_count_added"),
            "avg_closure_latency_minutes_added": average(records, "closure_latency_minutes_added"),
            "avg_false_green_exposure_reduced": average(records, "false_green_exposure_reduced"),
            "avg_artifact_completeness_percent_gain": average(records, "artifact_completeness_percent_gain"),
        },
        "hotspots": {
            "highest_operator_minutes_added": hotspot(records, "operator_minutes_added"),
            "highest_closure_latency_minutes_added": hotspot(records, "closure_latency_minutes_added"),
            "highest_false_green_exposure_reduced": hotspot(records, "false_green_exposure_reduced"),
            "highest_artifact_completeness_percent_gain": hotspot(records, "artifact_completeness_percent_gain"),
        },
        "path_buckets": {
            "justified_cost_paths": [record["scenario_id"] for record in records if record["verdict"] == "SYNRAIL_BETTER"],
            "baseline_sufficient_paths": [record["scenario_id"] for record in records if record["verdict"] == "BASELINE_GOOD_ENOUGH"],
            "under_proven_paths": [record["scenario_id"] for record in records if record["verdict"] == "UNCLEAR"],
        },
        "reading": {
            "strongest_justified_path": strongest_justified_path(records),
            "clearest_overhead_path": clearest_overhead_path(records),
            "hybrid_status": find_verdict_for_class(records, "medium_risk_ambiguous_closure"),
            "compound_status": find_verdict_for_class(records, "compound_proof_sensitive_repair"),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-cost-of-control-v0")
    parser.add_argument("--record", action="append", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        cost_record = build_cost_record([Path(record) for record in args.record])
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2

    save_json(Path(args.output), cost_record)
    print(json.dumps({"result": "OK", "scenario_count": cost_record["scenario_count"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
