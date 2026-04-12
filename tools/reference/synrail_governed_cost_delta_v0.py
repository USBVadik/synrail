#!/usr/bin/env python3
"""Compare unprepared vs prepared governed-path cost."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def summarize(unprepared: dict, prepared: dict) -> dict:
    return {
        "operator_minutes_reduced": unprepared["operator_minutes"] - prepared["operator_minutes"],
        "intervention_count_reduced": unprepared["intervention_count"] - prepared["intervention_count"],
        "repair_cycles_reduced": unprepared["repair_cycles"] - prepared["repair_cycles"],
        "closure_latency_minutes_reduced": unprepared["closure_latency_minutes"] - prepared["closure_latency_minutes"],
        "false_green_exposure_change": unprepared["false_green_exposure"] - prepared["false_green_exposure"],
        "artifact_completeness_percent_change": prepared["artifact_completeness_percent"] - unprepared["artifact_completeness_percent"],
        "first_bundle_status_improved": (
            unprepared["first_bundle_status"] != "COMPLETE"
            and prepared["first_bundle_status"] == "COMPLETE"
        ),
        "first_pass_closure_ready_improved": (
            not unprepared["first_pass_closure_ready"]
            and prepared["first_pass_closure_ready"]
        ),
        "safety_regression": (
            prepared["final_closure_status"] != "ACCEPTED"
            or prepared["false_green_exposure"] > unprepared["false_green_exposure"]
            or prepared["artifact_completeness_percent"] < unprepared["artifact_completeness_percent"]
        ),
    }


def compare(unprepared: dict, prepared: dict) -> tuple[str, str, list[str], dict]:
    summary = summarize(unprepared, prepared)
    reasons: list[str] = []

    if summary["operator_minutes_reduced"] > 0:
        reasons.append("preparation_reduces_operator_minutes")
    if summary["intervention_count_reduced"] > 0:
        reasons.append("preparation_reduces_interventions")
    if summary["repair_cycles_reduced"] > 0:
        reasons.append("preparation_reduces_repair_cycles")
    if summary["closure_latency_minutes_reduced"] > 0:
        reasons.append("preparation_reduces_closure_latency")
    if summary["first_bundle_status_improved"]:
        reasons.append("preparation_improves_first_bundle_status")
    if summary["first_pass_closure_ready_improved"]:
        reasons.append("preparation_improves_first_pass_closure_readiness")
    if summary["safety_regression"]:
        reasons.append("preparation_causes_safety_regression")

    if summary["safety_regression"]:
        return (
            "PREPARATION_NOT_JUSTIFIED",
            "The prepared governed path reduces some cost signals, but it also weakens the final safety surface, so the preparation slice is not justified yet.",
            reasons,
            summary,
        )

    if (
        (
            summary["operator_minutes_reduced"] > 0
            or summary["intervention_count_reduced"] > 0
            or summary["repair_cycles_reduced"] > 0
            or summary["closure_latency_minutes_reduced"] > 0
        )
        and (
            summary["first_bundle_status_improved"]
            or summary["first_pass_closure_ready_improved"]
        )
    ):
        return (
            "PREPARATION_REDUCES_GOVERNED_PATH_COST",
            "The prepared governed path stays equally safe while reducing operator tax and improving first-pass proof readiness.",
            reasons,
            summary,
        )

    return (
        "UNCLEAR",
        "The prepared governed path changes some local signals, but the current bounded record is not yet strong enough to claim a decisive governed-path cost win.",
        reasons,
        summary,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-governed-cost-delta-v0")
    parser.add_argument("--unprepared-file", required=True)
    parser.add_argument("--prepared-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    unprepared = load_json(Path(args.unprepared_file))
    prepared = load_json(Path(args.prepared_file))

    if unprepared.get("schema_version") != "governed_path_cost_input_v0":
        print(json.dumps({"result": "ERROR", "reason": "UNPREPARED_INPUT_SCHEMA_MISMATCH"}, ensure_ascii=True))
        return 2
    if prepared.get("schema_version") != "governed_path_cost_input_v0":
        print(json.dumps({"result": "ERROR", "reason": "PREPARED_INPUT_SCHEMA_MISMATCH"}, ensure_ascii=True))
        return 2
    if unprepared["scenario_id"] != prepared["scenario_id"]:
        print(json.dumps({"result": "ERROR", "reason": "SCENARIO_ID_MISMATCH"}, ensure_ascii=True))
        return 2
    if unprepared["scenario_class"] != prepared["scenario_class"]:
        print(json.dumps({"result": "ERROR", "reason": "SCENARIO_CLASS_MISMATCH"}, ensure_ascii=True))
        return 2

    verdict, why, reasons, summary = compare(unprepared, prepared)
    record = {
        "schema_version": "governed_path_cost_delta_v0",
        "scenario_id": unprepared["scenario_id"],
        "scenario_class": unprepared["scenario_class"],
        "task_class": unprepared["task_class"],
        "unprepared_path": unprepared["path_id"],
        "prepared_path": prepared["path_id"],
        "unprepared": unprepared,
        "prepared": prepared,
        "economics_summary": summary,
        "verdict": verdict,
        "why_verdict": why,
        "reasons": reasons,
    }
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": verdict}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
