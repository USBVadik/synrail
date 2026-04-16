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
    }


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

    if baseline.get("schema_version") != "comparison_input_v1":
        print(json.dumps({"result": "ERROR", "reason": "BASELINE_INPUT_SCHEMA_MISMATCH"}, ensure_ascii=True))
        return 2
    if synrail.get("schema_version") != "comparison_input_v1":
        print(json.dumps({"result": "ERROR", "reason": "SYNRAIL_INPUT_SCHEMA_MISMATCH"}, ensure_ascii=True))
        return 2
    if baseline["system"] != "baseline":
        print(json.dumps({"result": "ERROR", "reason": "BASELINE_INPUT_SYSTEM_MISMATCH"}, ensure_ascii=True))
        return 2
    if synrail["system"] != "synrail":
        print(json.dumps({"result": "ERROR", "reason": "SYNRAIL_INPUT_SYSTEM_MISMATCH"}, ensure_ascii=True))
        return 2
    if baseline["scenario_id"] != synrail["scenario_id"]:
        print(json.dumps({"result": "ERROR", "reason": "SCENARIO_ID_MISMATCH"}, ensure_ascii=True))
        return 2
    if baseline["scenario_class"] != synrail["scenario_class"]:
        print(json.dumps({"result": "ERROR", "reason": "SCENARIO_CLASS_MISMATCH"}, ensure_ascii=True))
        return 2

    verdict, reasons, why, economics = compare(baseline, synrail)
    record = {
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
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": verdict}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
