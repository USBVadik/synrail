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
    total = sum(record["economics_summary"].get(key, 0) for record in records)
    return round(total / len(records))


def hotspot(records: list[dict], key: str) -> dict:
    winner = max(records, key=lambda record: record["economics_summary"].get(key, 0))
    return {
        "scenario_id": winner["scenario_id"],
        "path": winner["synrail_path"],
        "value": winner["economics_summary"].get(key, 0),
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


def aggregate_verdict_for_class(records: list[dict], scenario_class: str) -> str:
    class_records = [record for record in records if record["scenario_class"] == scenario_class]
    if not class_records:
        return "UNKNOWN"

    verdicts = {record["verdict"] for record in class_records}
    if "BASELINE_GOOD_ENOUGH" in verdicts:
        return "BASELINE_GOOD_ENOUGH"
    if "UNCLEAR" in verdicts:
        return "UNCLEAR"
    if "SYNRAIL_BETTER" in verdicts:
        return "SYNRAIL_BETTER"
    return "UNKNOWN"


def build_cost_record_from_records(records: list[dict], *, source_paths: list[str] | None = None) -> dict:
    for record in records:
        if record.get("schema_version") != "baseline_comparison_record_v1":
            raise ValueError("all input records must use baseline_comparison_record_v1")
    paths = source_paths or ["" for _ in records]
    if len(paths) != len(records):
        raise ValueError("source_paths must match record count")

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
            "avg_checks_per_accepted_closure_added": average(records, "checks_per_accepted_closure_added"),
            "avg_false_green_exposure_reduced": average(records, "false_green_exposure_reduced"),
            "avg_artifact_completeness_percent_gain": average(records, "artifact_completeness_percent_gain"),
            "avg_mandatory_mental_steps_added": average(records, "mandatory_mental_steps_added"),
            "avg_trust_bearing_artifacts_added": average(records, "trust_bearing_artifacts_added"),
            "avg_required_visible_surfaces_added": average(records, "required_visible_surfaces_added"),
            "avg_skippable_visible_surfaces_added": average(records, "skippable_visible_surfaces_added"),
            "avg_operator_visible_actions_added": average(records, "operator_visible_actions_added"),
            "avg_got_lost_moments_added": average(records, "got_lost_moments_added"),
            "avg_kernel_control_mass_added": average(records, "kernel_control_mass_added"),
            "avg_behavioral_control_tax_added": average(records, "behavioral_control_tax_added"),
            "avg_fixed_control_mass_added": average(records, "fixed_control_mass_added"),
            "avg_total_control_burden_added": average(records, "total_control_burden_added"),
        },
        "hotspots": {
            "highest_operator_minutes_added": hotspot(records, "operator_minutes_added"),
            "highest_closure_latency_minutes_added": hotspot(records, "closure_latency_minutes_added"),
            "highest_checks_per_accepted_closure_added": hotspot(records, "checks_per_accepted_closure_added"),
            "highest_false_green_exposure_reduced": hotspot(records, "false_green_exposure_reduced"),
            "highest_artifact_completeness_percent_gain": hotspot(records, "artifact_completeness_percent_gain"),
            "highest_operator_visible_actions_added": hotspot(records, "operator_visible_actions_added"),
            "highest_got_lost_moments_added": hotspot(records, "got_lost_moments_added"),
            "highest_kernel_control_mass_added": hotspot(records, "kernel_control_mass_added"),
            "highest_behavioral_control_tax_added": hotspot(records, "behavioral_control_tax_added"),
            "highest_fixed_control_mass_added": hotspot(records, "fixed_control_mass_added"),
            "highest_total_control_burden_added": hotspot(records, "total_control_burden_added"),
        },
        "path_buckets": {
            "justified_cost_paths": [record["scenario_id"] for record in records if record["verdict"] == "SYNRAIL_BETTER"],
            "baseline_sufficient_paths": [record["scenario_id"] for record in records if record["verdict"] == "BASELINE_GOOD_ENOUGH"],
            "under_proven_paths": [record["scenario_id"] for record in records if record["verdict"] == "UNCLEAR"],
        },
        "reading": {
            "strongest_justified_path": strongest_justified_path(records),
            "clearest_overhead_path": clearest_overhead_path(records),
            "everyday_status": aggregate_verdict_for_class(records, "repeatable_everyday_local"),
            "hybrid_status": aggregate_verdict_for_class(records, "medium_risk_ambiguous_closure"),
            "compound_status": aggregate_verdict_for_class(records, "compound_proof_sensitive_repair"),
        },
    }


def build_cost_record(paths: list[Path]) -> dict:
    records = [load_json(path) for path in paths]
    return build_cost_record_from_records(records, source_paths=[str(path) for path in paths])


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
