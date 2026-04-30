#!/usr/bin/env python3
"""Compare two Synrail run artifacts for key-truth reproducibility."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json






def build_key_truth(run_artifact: dict) -> dict:
    report = run_artifact.get("report", {})
    resulting_state = run_artifact.get("resulting_state", {})
    repair_history = run_artifact.get("repair_history", {})
    repair_packet = run_artifact.get("repair_packet", {})
    return {
        "result": report.get("result", ""),
        "stopping_stage": report.get("stopping_stage", ""),
        "reason": report.get("reason", ""),
        "resulting_state": resulting_state.get("state", ""),
        "closure_status": resulting_state.get("closure_status", ""),
        "repair_history_chain_length": repair_history.get("chain_length", 0),
        "repair_history_termination_reason": repair_history.get("termination_reason", ""),
        "repair_packet_family": repair_packet.get("resumability_family", ""),
        "repair_packet_termination_reason": repair_packet.get("repair_termination_reason", ""),
        "next_safe_step": report.get("next_safe_step", ""),
    }


def build_record(*, run_a: dict, run_b: dict, run_a_path: str, run_b_path: str) -> dict:
    key_a = build_key_truth(run_a)
    key_b = build_key_truth(run_b)
    mismatches = []
    for key in key_a:
        if key_a[key] != key_b[key]:
            mismatches.append(key)
    verdict = "REPRODUCIBLE_ON_KEY_TRUTH" if not mismatches else "DRIFT_ON_KEY_TRUTH"
    return {
        "schema_version": "reproducibility_record_v0",
        "run_id": run_a.get("run_id", ""),
        "task_class": run_a.get("task_class", ""),
        "run_a_path": run_a_path,
        "run_b_path": run_b_path,
        "key_truth_a": key_a,
        "key_truth_b": key_b,
        "mismatches": mismatches,
        "verdict": verdict,
        "why": (
            "the paired runs preserve the same blocking, state, repair-history, and next-step truth"
            if verdict == "REPRODUCIBLE_ON_KEY_TRUTH"
            else "one or more key runtime truths drifted between repeated runs"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-reproducibility-v0")
    parser.add_argument("--run-a", required=True)
    parser.add_argument("--run-b", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    run_a = load_json(Path(args.run_a))
    run_b = load_json(Path(args.run_b))
    record = build_record(run_a=run_a, run_b=run_b, run_a_path=args.run_a, run_b_path=args.run_b)
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0 if record["verdict"] == "REPRODUCIBLE_ON_KEY_TRUTH" else 2


if __name__ == "__main__":
    sys.exit(main())
