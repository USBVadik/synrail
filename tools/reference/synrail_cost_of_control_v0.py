#!/usr/bin/env python3
"""Aggregate economics records into one cost-of-control reading."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json
from statistics import median


VERDICTS = ["SYNRAIL_BETTER", "BASELINE_GOOD_ENOUGH", "UNCLEAR"]






def average(records: list[dict], key: str) -> int:
    if not records:
        return 0
    total = sum(record["economics_summary"].get(key, 0) for record in records)
    return round(total / len(records))


def median_value(records: list[dict], key: str) -> int | float:
    if not records:
        return 0
    return median([record["economics_summary"].get(key, 0) for record in records])


def spread_value(records: list[dict], key: str) -> int | float:
    if not records:
        return 0
    values = [record["economics_summary"].get(key, 0) for record in records]
    return max(values) - min(values)


def hotspot(records: list[dict], key: str) -> dict:
    if not records:
        return {}
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


def aggregate_verdict_for_task_class(records: list[dict], task_class: str) -> str:
    task_records = [record for record in records if record["task_class"] == task_class]
    if not task_records:
        return "UNKNOWN"

    verdicts = {record["verdict"] for record in task_records}
    if "BASELINE_GOOD_ENOUGH" in verdicts:
        return "BASELINE_GOOD_ENOUGH"
    if "UNCLEAR" in verdicts:
        return "UNCLEAR"
    if "SYNRAIL_BETTER" in verdicts:
        return "SYNRAIL_BETTER"
    return "UNKNOWN"


def focused_task_class(records: list[dict]) -> str:
    scenario_id = strongest_justified_path(records)
    for record in records:
        if record["scenario_id"] == scenario_id:
            return record["task_class"]
    return ""


def focused_task_class_records(records: list[dict], task_class: str) -> list[dict]:
    if not task_class:
        return []
    return [record for record in records if record["task_class"] == task_class]


def focused_task_class_stability(records: list[dict], task_class: str) -> str:
    task_records = focused_task_class_records(records, task_class)
    if not task_records:
        return "NO_FOCUS_TASK_CLASS"
    if len(task_records) == 1:
        return "SINGLE_PATH_ONLY"
    if any(record["verdict"] != "SYNRAIL_BETTER" for record in task_records):
        return "MIXED_OR_NOT_YET_WINNING"
    if any(record["economics_summary"]["checks_per_accepted_closure_added"] > 0 for record in task_records):
        return "WINS_BUT_NOT_YET_LOW_VARIANCE"
    if any(record["economics_summary"]["got_lost_moments_added"] > 0 for record in task_records):
        return "WINS_BUT_NOT_YET_LOW_VARIANCE"
    if any(record["economics_summary"]["total_control_burden_added"] > 1 for record in task_records):
        return "WINS_BUT_NOT_YET_LOW_VARIANCE"
    return "LOW_VARIANCE_REPEATABLE"


def focus_task_class_priority_one_barrier(records: list[dict], task_class: str) -> str:
    if not task_class:
        return "NO_FOCUS_TASK_CLASS"
    task_records = focused_task_class_records(records, task_class)
    if not task_records:
        return "NO_FOCUS_TASK_CLASS"
    if aggregate_verdict_for_task_class(records, task_class) != "SYNRAIL_BETTER":
        return "FOCUSED_CLASS_NOT_YET_WINNING"
    if focused_task_class_stability(records, task_class) != "LOW_VARIANCE_REPEATABLE":
        return "FOCUSED_CLASS_NOT_YET_LOW_VARIANCE"

    median_thresholds = [
        ("operator_minutes_added", 1, "FOCUSED_CLASS_MEDIAN_OPERATOR_MINUTES_TOO_HIGH"),
        ("closure_latency_minutes_added", 1, "FOCUSED_CLASS_MEDIAN_CLOSURE_LATENCY_TOO_HIGH"),
        ("checks_per_accepted_closure_added", 0, "FOCUSED_CLASS_MEDIAN_CHECKS_TOO_HIGH"),
        ("operator_visible_actions_added", 0, "FOCUSED_CLASS_MEDIAN_OPERATOR_VISIBLE_ACTIONS_TOO_HIGH"),
        ("got_lost_moments_added", 0, "FOCUSED_CLASS_MEDIAN_GOT_LOST_MOMENTS_TOO_HIGH"),
        ("fixed_control_mass_added", 1, "FOCUSED_CLASS_MEDIAN_FIXED_CONTROL_MASS_TOO_HIGH"),
        ("behavioral_control_tax_added", 0, "FOCUSED_CLASS_MEDIAN_BEHAVIORAL_TAX_TOO_HIGH"),
        ("total_control_burden_added", 1, "FOCUSED_CLASS_MEDIAN_TOTAL_CONTROL_BURDEN_TOO_HIGH"),
    ]
    for key, limit, barrier in median_thresholds:
        if median_value(task_records, key) > limit:
            return barrier

    spread_thresholds = [
        ("operator_minutes_added", 0, "FOCUSED_CLASS_SPREAD_OPERATOR_MINUTES_TOO_HIGH"),
        ("closure_latency_minutes_added", 0, "FOCUSED_CLASS_SPREAD_CLOSURE_LATENCY_TOO_HIGH"),
        ("checks_per_accepted_closure_added", 0, "FOCUSED_CLASS_SPREAD_CHECKS_TOO_HIGH"),
        ("operator_visible_actions_added", 0, "FOCUSED_CLASS_SPREAD_OPERATOR_VISIBLE_ACTIONS_TOO_HIGH"),
        ("got_lost_moments_added", 0, "FOCUSED_CLASS_SPREAD_GOT_LOST_MOMENTS_TOO_HIGH"),
        ("fixed_control_mass_added", 0, "FOCUSED_CLASS_SPREAD_FIXED_CONTROL_MASS_TOO_HIGH"),
        ("behavioral_control_tax_added", 0, "FOCUSED_CLASS_SPREAD_BEHAVIORAL_TAX_TOO_HIGH"),
        ("total_control_burden_added", 0, "FOCUSED_CLASS_SPREAD_TOTAL_CONTROL_BURDEN_TOO_HIGH"),
    ]
    for key, limit, barrier in spread_thresholds:
        if spread_value(task_records, key) > limit:
            return barrier
    return ""


def focus_task_class_priority_one_status(records: list[dict], task_class: str) -> str:
    return "FOCUSED_CLASS_CHEAP_ENOUGH" if not focus_task_class_priority_one_barrier(records, task_class) else "FOCUSED_CLASS_NOT_YET_CHEAP_ENOUGH"


def focus_task_class_kernel_cheapness_barrier(records: list[dict], task_class: str) -> str:
    if not task_class:
        return "NO_FOCUS_TASK_CLASS"
    task_records = focused_task_class_records(records, task_class)
    if not task_records:
        return "NO_FOCUS_TASK_CLASS"
    if aggregate_verdict_for_task_class(records, task_class) != "SYNRAIL_BETTER":
        return "FOCUSED_CLASS_NOT_YET_WINNING"
    if focused_task_class_stability(records, task_class) != "LOW_VARIANCE_REPEATABLE":
        return "FOCUSED_CLASS_NOT_YET_LOW_VARIANCE"

    median_thresholds = [
        ("operator_minutes_added", 1, "FOCUSED_CLASS_MEDIAN_OPERATOR_MINUTES_TOO_HIGH"),
        ("closure_latency_minutes_added", 1, "FOCUSED_CLASS_MEDIAN_CLOSURE_LATENCY_TOO_HIGH"),
        ("checks_per_accepted_closure_added", 0, "FOCUSED_CLASS_MEDIAN_CHECKS_TOO_HIGH"),
        ("fixed_control_mass_added", 1, "FOCUSED_CLASS_MEDIAN_FIXED_CONTROL_MASS_TOO_HIGH"),
    ]
    for key, limit, barrier in median_thresholds:
        if median_value(task_records, key) > limit:
            return barrier

    spread_thresholds = [
        ("operator_minutes_added", 0, "FOCUSED_CLASS_SPREAD_OPERATOR_MINUTES_TOO_HIGH"),
        ("closure_latency_minutes_added", 0, "FOCUSED_CLASS_SPREAD_CLOSURE_LATENCY_TOO_HIGH"),
        ("checks_per_accepted_closure_added", 0, "FOCUSED_CLASS_SPREAD_CHECKS_TOO_HIGH"),
        ("fixed_control_mass_added", 0, "FOCUSED_CLASS_SPREAD_FIXED_CONTROL_MASS_TOO_HIGH"),
    ]
    for key, limit, barrier in spread_thresholds:
        if spread_value(task_records, key) > limit:
            return barrier
    return ""


def focus_task_class_kernel_cheapness_status(records: list[dict], task_class: str) -> str:
    return (
        "FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH"
        if not focus_task_class_kernel_cheapness_barrier(records, task_class)
        else "FOCUSED_CLASS_KERNEL_NOT_YET_CHEAP_ENOUGH"
    )


def focus_task_class_behavior_cheapness_barrier(records: list[dict], task_class: str) -> str:
    if not task_class:
        return "NO_FOCUS_TASK_CLASS"
    task_records = focused_task_class_records(records, task_class)
    if not task_records:
        return "NO_FOCUS_TASK_CLASS"

    kernel_barrier = focus_task_class_kernel_cheapness_barrier(records, task_class)
    if kernel_barrier:
        return kernel_barrier

    median_thresholds = [
        ("skippable_visible_surfaces_added", 0, "FOCUSED_CLASS_MEDIAN_SKIPPABLE_VISIBLE_SURFACES_TOO_HIGH"),
        ("operator_visible_actions_added", 0, "FOCUSED_CLASS_MEDIAN_OPERATOR_VISIBLE_ACTIONS_TOO_HIGH"),
        ("got_lost_moments_added", 0, "FOCUSED_CLASS_MEDIAN_GOT_LOST_MOMENTS_TOO_HIGH"),
        ("behavioral_control_tax_added", 0, "FOCUSED_CLASS_MEDIAN_BEHAVIORAL_TAX_TOO_HIGH"),
    ]
    for key, limit, barrier in median_thresholds:
        if median_value(task_records, key) > limit:
            return barrier

    spread_thresholds = [
        ("skippable_visible_surfaces_added", 0, "FOCUSED_CLASS_SPREAD_SKIPPABLE_VISIBLE_SURFACES_TOO_HIGH"),
        ("operator_visible_actions_added", 0, "FOCUSED_CLASS_SPREAD_OPERATOR_VISIBLE_ACTIONS_TOO_HIGH"),
        ("got_lost_moments_added", 0, "FOCUSED_CLASS_SPREAD_GOT_LOST_MOMENTS_TOO_HIGH"),
        ("behavioral_control_tax_added", 0, "FOCUSED_CLASS_SPREAD_BEHAVIORAL_TAX_TOO_HIGH"),
    ]
    for key, limit, barrier in spread_thresholds:
        if spread_value(task_records, key) > limit:
            return barrier
    return ""


def focus_task_class_behavior_cheapness_status(records: list[dict], task_class: str) -> str:
    return (
        "FOCUSED_CLASS_BEHAVIOR_CHEAP_BY_DEFAULT"
        if not focus_task_class_behavior_cheapness_barrier(records, task_class)
        else "FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT"
    )


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


def primary_scenario_class(records: list[dict]) -> str:
    scenario_classes = sorted({record["scenario_class"] for record in records})
    if len(scenario_classes) != 1:
        return ""
    return scenario_classes[0]


def primary_scenario_class_status(records: list[dict]) -> str:
    scenario_class = primary_scenario_class(records)
    if not scenario_class:
        return "UNKNOWN"
    return aggregate_verdict_for_class(records, scenario_class)


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
    provenance_mix = sorted(
        {
            provenance
            for record in records
            for provenance in [record.get("baseline_data_provenance", ""), record.get("synrail_data_provenance", "")]
            if provenance
        }
    )
    focus_task_class = focused_task_class(records)
    focus_task_records = focused_task_class_records(records, focus_task_class)

    return {
        "schema_version": "cost_of_control_record_v0",
        "scenario_count": len(records),
        "source_records": source_records,
        "provenance_mix": provenance_mix,
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
            "primary_scenario_class": primary_scenario_class(records),
            "primary_scenario_class_status": primary_scenario_class_status(records),
            "focus_task_class": focus_task_class,
            "focus_task_class_record_count": len(focus_task_records),
            "focus_task_class_verdict": aggregate_verdict_for_task_class(records, focus_task_class),
            "focus_task_class_stability": focused_task_class_stability(records, focus_task_class),
            "focus_task_class_median_operator_minutes_added": median_value(focus_task_records, "operator_minutes_added"),
            "focus_task_class_median_closure_latency_minutes_added": median_value(focus_task_records, "closure_latency_minutes_added"),
            "focus_task_class_median_checks_per_accepted_closure_added": median_value(focus_task_records, "checks_per_accepted_closure_added"),
            "focus_task_class_median_operator_visible_actions_added": median_value(focus_task_records, "operator_visible_actions_added"),
            "focus_task_class_median_got_lost_moments_added": median_value(focus_task_records, "got_lost_moments_added"),
            "focus_task_class_median_fixed_control_mass_added": median_value(focus_task_records, "fixed_control_mass_added"),
            "focus_task_class_median_behavioral_control_tax_added": median_value(focus_task_records, "behavioral_control_tax_added"),
            "focus_task_class_median_total_control_burden_added": median_value(focus_task_records, "total_control_burden_added"),
            "focus_task_class_spread_operator_minutes_added": spread_value(focus_task_records, "operator_minutes_added"),
            "focus_task_class_spread_closure_latency_minutes_added": spread_value(focus_task_records, "closure_latency_minutes_added"),
            "focus_task_class_spread_checks_per_accepted_closure_added": spread_value(focus_task_records, "checks_per_accepted_closure_added"),
            "focus_task_class_spread_operator_visible_actions_added": spread_value(focus_task_records, "operator_visible_actions_added"),
            "focus_task_class_spread_got_lost_moments_added": spread_value(focus_task_records, "got_lost_moments_added"),
            "focus_task_class_spread_fixed_control_mass_added": spread_value(focus_task_records, "fixed_control_mass_added"),
            "focus_task_class_spread_behavioral_control_tax_added": spread_value(focus_task_records, "behavioral_control_tax_added"),
            "focus_task_class_spread_total_control_burden_added": spread_value(focus_task_records, "total_control_burden_added"),
            "focus_task_class_priority_one_status": focus_task_class_priority_one_status(records, focus_task_class),
            "focus_task_class_priority_one_barrier": focus_task_class_priority_one_barrier(records, focus_task_class),
            "focus_task_class_kernel_cheapness_status": focus_task_class_kernel_cheapness_status(records, focus_task_class),
            "focus_task_class_kernel_cheapness_barrier": focus_task_class_kernel_cheapness_barrier(records, focus_task_class),
            "focus_task_class_behavior_cheapness_status": focus_task_class_behavior_cheapness_status(records, focus_task_class),
            "focus_task_class_behavior_cheapness_barrier": focus_task_class_behavior_cheapness_barrier(records, focus_task_class),
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
