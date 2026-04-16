#!/usr/bin/env python3
"""Substitute-stack comparison harness for Synrail."""

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


def economics_summary(substitute: dict, synrail: dict) -> dict:
    return {
        "operator_minutes_added": synrail["operator_minutes"] - substitute["operator_minutes"],
        "intervention_count_added": synrail["intervention_count"] - substitute["intervention_count"],
        "repair_cycles_added": synrail["repair_cycles"] - substitute["repair_cycles"],
        "invalidation_count_added": synrail["invalidation_count"] - substitute["invalidation_count"],
        "closure_latency_minutes_added": synrail["closure_latency_minutes"] - substitute["closure_latency_minutes"],
        "blocker_to_closure_cycles_added": synrail["blocker_to_closure_cycles"] - substitute["blocker_to_closure_cycles"],
        "false_green_exposure_reduced": substitute["false_green_exposure"] - synrail["false_green_exposure"],
        "artifact_completeness_percent_gain": synrail["artifact_completeness_percent"] - substitute["artifact_completeness_percent"],
    }


def compare(substitute: dict, synrail: dict) -> tuple[str, list[str], str, dict]:
    reasons: list[str] = []
    economics = economics_summary(substitute, synrail)

    substitute_false = SCORE[substitute["false_success_risk"]]
    synrail_false = SCORE[synrail["false_success_risk"]]
    substitute_proof = SCORE[substitute["proof_completeness"]]
    synrail_proof = SCORE[synrail["proof_completeness"]]
    substitute_recovery = SCORE[substitute["recovery_cost"]]
    synrail_recovery = SCORE[synrail["recovery_cost"]]
    substitute_overhead = SCORE[substitute["coordination_overhead"]]
    synrail_overhead = SCORE[synrail["coordination_overhead"]]

    false_advantage = substitute_false - synrail_false
    proof_advantage = synrail_proof - substitute_proof
    recovery_advantage = substitute_recovery - synrail_recovery
    overhead_penalty = synrail_overhead - substitute_overhead

    if false_advantage >= 1 or economics["false_green_exposure_reduced"] >= 1:
        reasons.append("synrail_reduces_substitute_false_green_exposure")
    if proof_advantage >= 1 or economics["artifact_completeness_percent_gain"] >= 20:
        reasons.append("synrail_improves_substitute_proof_basis")
    if recovery_advantage >= 1:
        reasons.append("synrail_lowers_substitute_repair_cost")
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
            or economics["artifact_completeness_percent_gain"] >= 25
        )
    ):
        why = (
            "Synrail materially outperforms this simpler substitute stack on truth preservation "
            "and repairability, even though it costs more coordination."
        )
        return "SYNRAIL_BETTER", reasons, why, economics

    if (
        false_advantage <= 0
        and economics["false_green_exposure_reduced"] <= 0
        and proof_advantage <= 0
        and economics["artifact_completeness_percent_gain"] < 25
        and recovery_advantage <= 0
        and economics["operator_minutes_added"] >= 8
    ):
        why = (
            "This substitute stack already keeps the path honest enough here, so Synrail "
            "does not yet earn its additional control cost."
        )
        return "SUBSTITUTE_GOOD_ENOUGH", reasons, why, economics

    why = (
        "The current substitute test shows real differences in both truth discipline and cost, "
        "but not enough to claim a decisive winner yet."
    )
    return "UNCLEAR", reasons, why, economics


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-substitute-harness-v0")
    parser.add_argument("--substitute-file", required=True)
    parser.add_argument("--synrail-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    substitute = load_json(Path(args.substitute_file))
    synrail = load_json(Path(args.synrail_file))

    if substitute.get("schema_version") != "comparison_input_v2":
        print(json.dumps({"result": "ERROR", "reason": "SUBSTITUTE_INPUT_SCHEMA_MISMATCH"}, ensure_ascii=True))
        return 2
    if synrail.get("schema_version") != "comparison_input_v2":
        print(json.dumps({"result": "ERROR", "reason": "SYNRAIL_INPUT_SCHEMA_MISMATCH"}, ensure_ascii=True))
        return 2
    if substitute["system"] != "substitute":
        print(json.dumps({"result": "ERROR", "reason": "SUBSTITUTE_INPUT_SYSTEM_MISMATCH"}, ensure_ascii=True))
        return 2
    if synrail["system"] != "synrail":
        print(json.dumps({"result": "ERROR", "reason": "SYNRAIL_INPUT_SYSTEM_MISMATCH"}, ensure_ascii=True))
        return 2
    if substitute["scenario_id"] != synrail["scenario_id"] or substitute["scenario_class"] != synrail["scenario_class"]:
        print(json.dumps({"result": "ERROR", "reason": "SCENARIO_MISMATCH"}, ensure_ascii=True))
        return 2

    verdict, reasons, why, economics = compare(substitute, synrail)
    record = {
        "schema_version": "substitute_comparison_record_v0",
        "scenario_id": substitute["scenario_id"],
        "scenario_class": substitute["scenario_class"],
        "task_class": substitute["task_class"],
        "substitute_stack": substitute.get("substitute_stack", ""),
        "substitute_family": substitute.get("substitute_family", ""),
        "substitute_path": substitute["path_id"],
        "synrail_path": synrail["path_id"],
        "substitute": substitute,
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
