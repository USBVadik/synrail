#!/usr/bin/env python3
"""Check that a restored contour is readable without operator ambiguity."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_record(*, second_operator: dict, thin_output: dict, repair_packet: dict) -> dict:
    expected_next_step = repair_packet.get("continuation_core", {}).get("next_safe_step", "")
    missing_markers: list[str] = []
    outcome_class = thin_output.get("outcome_class", "")
    repair_family = second_operator.get("repair_family", "")

    if second_operator.get("verdict", "") != "FOLLOWABLE_BY_SECOND_OPERATOR":
        missing_markers.append("second_operator_followability")
    if thin_output.get("next_step", "") != expected_next_step:
        missing_markers.append("next_step")
    if not thin_output.get("restore_available", False):
        missing_markers.append("restore_available")

    diagnosis = thin_output.get("diagnosis", "")
    suggested_command = thin_output.get("suggested_command", "")
    if repair_family == "NOT_RESUMABLE_FRESH_ORCHESTRATION":
        if outcome_class != "NON_RESUMABLE":
            missing_markers.append("outcome_class")
        if "governed forward path" not in diagnosis:
            missing_markers.append("diagnosis_forward_boundary")
        if suggested_command != "continue governed forward path, not resume":
            missing_markers.append("suggested_command")
    elif repair_family == "REPAIRABLE_DOCTOR_BLOCKED":
        if outcome_class != "SCOPE_VIOLATION":
            missing_markers.append("outcome_class")
        if "clean in-scope execution surface" not in diagnosis:
            missing_markers.append("diagnosis_scope_boundary")
        if suggested_command != "restore-checkpoint or move to a clean in-scope surface, then resume":
            missing_markers.append("suggested_command")
    else:
        missing_markers.append("repair_family")

    verdict = "FOLLOWABLE_WITHOUT_OPERATOR_AMBIGUITY" if not missing_markers else "OPERATOR_AMBIGUITY_REMAINS"
    return {
        "schema_version": "checkpoint_operator_reading_record_v0",
        "run_id": second_operator["run_id"],
        "task_class": second_operator["task_class"],
        "repair_family": repair_family,
        "outcome_class": outcome_class,
        "next_step": thin_output.get("next_step", ""),
        "restore_available": thin_output.get("restore_available", False),
        "suggested_command": suggested_command,
        "missing_markers": missing_markers,
        "verdict": verdict,
        "why": (
            "the checkpoint-backed contour stays followable and the operator-facing output names the correct recovery boundary without suggesting the wrong next move"
            if verdict == "FOLLOWABLE_WITHOUT_OPERATOR_AMBIGUITY"
            else "the restored contour still leaves one or more operator-facing ambiguities in the combined reading surface"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-checkpoint-operator-reading-v0")
    parser.add_argument("--second-operator-file", required=True)
    parser.add_argument("--thin-output-file", required=True)
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        second_operator=load_json(Path(args.second_operator_file)),
        thin_output=load_json(Path(args.thin_output_file)),
        repair_packet=load_json(Path(args.repair_packet_file)),
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0 if record["verdict"] == "FOLLOWABLE_WITHOUT_OPERATOR_AMBIGUITY" else 2


if __name__ == "__main__":
    sys.exit(main())
