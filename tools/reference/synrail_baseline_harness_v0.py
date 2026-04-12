#!/usr/bin/env python3
"""Minimal baseline comparison harness for Synrail."""

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


def compare(baseline: dict, synrail: dict) -> tuple[str, list[str]]:
    reasons: list[str] = []

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

    if false_advantage >= 1:
        reasons.append("synrail_reduces_false_success_risk")
    if proof_advantage >= 1:
        reasons.append("synrail_improves_proof_completeness")
    if recovery_advantage >= 1:
        reasons.append("synrail_lowers_recovery_cost")
    if overhead_penalty >= 1:
        reasons.append("synrail_adds_coordination_overhead")

    if false_advantage >= 1 and (proof_advantage >= 1 or recovery_advantage >= 1):
        return "SYNRAIL_BETTER", reasons

    if false_advantage <= 0 and proof_advantage <= 0 and recovery_advantage <= 0 and overhead_penalty >= 0:
        return "BASELINE_GOOD_ENOUGH", reasons

    if overhead_penalty >= 1 and false_advantage == 0 and proof_advantage <= 1 and recovery_advantage <= 0:
        return "BASELINE_GOOD_ENOUGH", reasons

    return "UNCLEAR", reasons


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-baseline-harness-v0")
    parser.add_argument("--baseline-file", required=True)
    parser.add_argument("--synrail-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    baseline = load_json(Path(args.baseline_file))
    synrail = load_json(Path(args.synrail_file))

    if baseline["system"] != "baseline":
        print(json.dumps({"result": "ERROR", "reason": "BASELINE_INPUT_SYSTEM_MISMATCH"}, ensure_ascii=True))
        return 2
    if synrail["system"] != "synrail":
        print(json.dumps({"result": "ERROR", "reason": "SYNRAIL_INPUT_SYSTEM_MISMATCH"}, ensure_ascii=True))
        return 2
    if baseline["scenario_id"] != synrail["scenario_id"]:
        print(json.dumps({"result": "ERROR", "reason": "SCENARIO_ID_MISMATCH"}, ensure_ascii=True))
        return 2

    verdict, reasons = compare(baseline, synrail)
    record = {
        "schema_version": "baseline_comparison_record_v0",
        "scenario_id": baseline["scenario_id"],
        "task_class": baseline["task_class"],
        "baseline": baseline,
        "synrail": synrail,
        "verdict": verdict,
        "reasons": reasons,
    }
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": verdict}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
