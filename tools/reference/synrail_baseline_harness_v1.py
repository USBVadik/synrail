#!/usr/bin/env python3
"""Economic baseline comparison harness for Synrail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SCORE = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def non_negative_int(record: dict, field: str) -> int:
    value = record.get(field, 0)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(0, value)
    return 0


def required_visible_surface_count(record: dict) -> int:
    visible = non_negative_int(record, "visible_surface_count")
    skippable = non_negative_int(record, "skippable_visible_surface_count")
    return max(0, visible - skippable)


def economics_summary(baseline: dict, synrail: dict) -> dict:
    return {
        "operator_minutes_added": synrail["operator_minutes"] - baseline["operator_minutes"],
        "intervention_count_added": synrail["intervention_count"] - baseline["intervention_count"],
        "repair_cycles_added": synrail["repair_cycles"] - baseline["repair_cycles"],
        "invalidation_count_added": synrail["invalidation_count"] - baseline["invalidation_count"],
        "closure_latency_minutes_added": synrail["closure_latency_minutes"] - baseline["closure_latency_minutes"],
        "blocker_to_closure_cycles_added": synrail["blocker_to_closure_cycles"] - baseline["blocker_to_closure_cycles"],
        "false_green_exposure_reduced": baseline["false_green_exposure"] - synrail["false_green_exposure"],
        "artifact_completeness_percent_gain": synrail["artifact_completeness_percent"] - baseline["artifact_completeness_percent"],
        "mandatory_mental_steps_added": non_negative_int(synrail, "mandatory_mental_steps") - non_negative_int(baseline, "mandatory_mental_steps"),
        "trust_bearing_artifacts_added": non_negative_int(synrail, "trust_bearing_artifact_count") - non_negative_int(baseline, "trust_bearing_artifact_count"),
        "required_visible_surfaces_added": required_visible_surface_count(synrail) - required_visible_surface_count(baseline),
        "skippable_visible_surfaces_added": non_negative_int(synrail, "skippable_visible_surface_count") - non_negative_int(baseline, "skippable_visible_surface_count"),
        "fixed_control_mass_added": (
            (non_negative_int(synrail, "mandatory_mental_steps") - non_negative_int(baseline, "mandatory_mental_steps"))
            + (non_negative_int(synrail, "trust_bearing_artifact_count") - non_negative_int(baseline, "trust_bearing_artifact_count"))
            + (required_visible_surface_count(synrail) - required_visible_surface_count(baseline))
        ),
    }


def validate_inputs(baseline: dict, synrail: dict) -> None:
    if baseline.get("schema_version") != "comparison_input_v1":
        raise ValueError("BASELINE_INPUT_SCHEMA_MISMATCH")
    if synrail.get("schema_version") != "comparison_input_v1":
        raise ValueError("SYNRAIL_INPUT_SCHEMA_MISMATCH")
    if baseline["system"] != "baseline":
        raise ValueError("BASELINE_INPUT_SYSTEM_MISMATCH")
    if synrail["system"] != "synrail":
        raise ValueError("SYNRAIL_INPUT_SYSTEM_MISMATCH")
    if baseline["scenario_id"] != synrail["scenario_id"]:
        raise ValueError("SCENARIO_ID_MISMATCH")
    if baseline["scenario_class"] != synrail["scenario_class"]:
        raise ValueError("SCENARIO_CLASS_MISMATCH")


def compare(baseline: dict, synrail: dict) -> tuple[str, list[str], str, dict]:
    reasons: list[str] = []
    economics = economics_summary(baseline, synrail)

    baseline_false = SCORE[baseline["false_success_risk"]]
    synrail_false = SCORE[synrail["false_success_risk"]]
    baseline_proof = SCORE[baseline["proof_completeness"]]
    synrail_proof = SCORE[synrail["proof_completeness"]]
    baseline_recovery = SCORE[baseline["recovery_cost"]]
    synrail_recovery = SCORE[synrail["recovery_cost"]]
    baseline_overhead = SCORE[baseline["coordination_overhead"]]
    synrail_overhead = SCORE[synrail["coordination_overhead"]]

    false_advantage = baseline_false - synrail_false
    proof_advantage = synrail_proof - baseline_proof
    recovery_advantage = baseline_recovery - synrail_recovery
    overhead_penalty = synrail_overhead - baseline_overhead

    if false_advantage >= 1 or economics["false_green_exposure_reduced"] >= 1:
        reasons.append("synrail_reduces_false_green_exposure")
    if proof_advantage >= 1 or economics["artifact_completeness_percent_gain"] >= 15:
        reasons.append("synrail_improves_artifact_completeness")
    if recovery_advantage >= 1:
        reasons.append("synrail_lowers_recovery_cost")
    if overhead_penalty >= 1 or economics["operator_minutes_added"] > 0:
        reasons.append("synrail_adds_control_overhead")
    if economics["fixed_control_mass_added"] > 0:
        reasons.append("synrail_adds_fixed_control_mass")
    if economics["intervention_count_added"] > 0:
        reasons.append("synrail_requires_more_operator_interventions")
    if economics["closure_latency_minutes_added"] > 0:
        reasons.append("synrail_increases_closure_latency")

    if (
        (false_advantage >= 1 or economics["false_green_exposure_reduced"] >= 2)
        and (
            proof_advantage >= 1
            or recovery_advantage >= 1
            or economics["artifact_completeness_percent_gain"] >= 30
        )
    ):
        why = (
            "Synrail materially reduces false-green exposure and improves proof basis, "
            "even though it costs more operator time."
        )
        return "SYNRAIL_BETTER", reasons, why, economics

    if (
        economics["false_green_exposure_reduced"] >= 1
        and economics["artifact_completeness_percent_gain"] >= 30
        and economics["operator_minutes_added"] <= 1
        and economics["intervention_count_added"] <= 0
        and economics["closure_latency_minutes_added"] <= 1
        and economics["required_visible_surfaces_added"] <= 0
        and economics["trust_bearing_artifacts_added"] <= 0
        and economics["fixed_control_mass_added"] <= 1
    ):
        why = (
            "Synrail earns a low-drag trust win here: it reduces false-green exposure "
            "and improves proof basis without adding a meaningful operator burden."
        )
        return "SYNRAIL_BETTER", reasons, why, economics

    if (
        false_advantage <= 0
        and economics["false_green_exposure_reduced"] <= 0
        and recovery_advantage <= 0
        and economics["artifact_completeness_percent_gain"] <= 35
        and economics["operator_minutes_added"] <= 1
        and economics["intervention_count_added"] <= 0
        and economics["closure_latency_minutes_added"] <= 1
        and economics["trust_bearing_artifacts_added"] >= 1
        and economics["fixed_control_mass_added"] >= 2
    ):
        why = (
            "The baseline already keeps false-green exposure low enough here, so Synrail's "
            "extra proof richness does not earn the added trust-bearing control burden."
        )
        return "BASELINE_GOOD_ENOUGH", reasons, why, economics

    if (
        false_advantage <= 0
        and economics["false_green_exposure_reduced"] <= 0
        and economics["artifact_completeness_percent_gain"] < 35
        and recovery_advantage <= 0
        and economics["operator_minutes_added"] >= 10
    ):
        why = (
            "The simpler baseline already keeps false-green exposure low enough here, "
            "so Synrail mostly adds control cost without a decisive safety gain."
        )
        return "BASELINE_GOOD_ENOUGH", reasons, why, economics

    if (
        overhead_penalty >= 0
        and economics["operator_minutes_added"] > 0
        and economics["false_green_exposure_reduced"] == 0
        and economics["artifact_completeness_percent_gain"] < 35
        and recovery_advantage <= 0
    ):
        why = (
            "Synrail adds some discipline on this path, but the current economics still "
            "look too expensive relative to the observed gain."
        )
        return "BASELINE_GOOD_ENOUGH", reasons, why, economics

    why = (
        "The current numbers show real signal on both truth discipline and control cost, "
        "but not enough to claim a decisive winner yet."
    )
    return "UNCLEAR", reasons, why, economics


def build_record(baseline: dict, synrail: dict) -> dict:
    validate_inputs(baseline, synrail)
    verdict, reasons, why, economics = compare(baseline, synrail)
    return {
        "schema_version": "baseline_comparison_record_v1",
        "scenario_id": baseline["scenario_id"],
        "scenario_class": baseline["scenario_class"],
        "task_class": baseline["task_class"],
        "baseline_path": baseline["path_id"],
        "synrail_path": synrail["path_id"],
        "baseline": baseline,
        "synrail": synrail,
        "economics_summary": economics,
        "verdict": verdict,
        "why_verdict": why,
        "reasons": reasons,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-baseline-harness-v1")
    parser.add_argument("--baseline-file", required=True)
    parser.add_argument("--synrail-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    baseline = load_json(Path(args.baseline_file))
    synrail = load_json(Path(args.synrail_file))

    try:
        record = build_record(baseline, synrail)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2

    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
