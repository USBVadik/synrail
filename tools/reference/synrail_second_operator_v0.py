#!/usr/bin/env python3
"""Inspect whether a packet-first continuation path is followable by a second operator without author memory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_record(*, state: dict, packet: dict, run_artifact: dict) -> dict:
    core = packet.get("continuation_core", {})
    report = run_artifact.get("report", {})
    repair_packet = run_artifact.get("repair_packet", {})
    visible_entry_artifacts = ["state_file", "repair_packet"]
    resumability_status = repair_packet.get("resumability_status", core.get("resumability_status", ""))
    has_explicit_next_step = bool(core.get("next_safe_step", ""))
    has_explicit_required_inputs = bool(core.get("next_step_required_inputs", []))
    no_input_boundary = resumability_status == "NOT_RESUMABLE" and not core.get("next_step_required_inputs", [])
    has_explicit_focus = bool(core.get("operator_focus", ""))
    packet_only_entry = visible_entry_artifacts == ["state_file", "repair_packet"]
    requires_author_intuition = not (
        has_explicit_next_step
        and has_explicit_focus
        and (has_explicit_required_inputs or no_input_boundary)
    )
    verdict = "FOLLOWABLE_BY_SECOND_OPERATOR" if packet_only_entry and not requires_author_intuition else "AUTHOR_INTUITION_STILL_REQUIRED"
    return {
        "schema_version": "second_operator_record_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "entrypoint": "resume",
        "entry_state": state["state"],
        "visible_entry_artifacts": visible_entry_artifacts,
        "packet_only_entry": packet_only_entry,
        "has_explicit_next_step": has_explicit_next_step,
        "has_explicit_required_inputs": has_explicit_required_inputs,
        "has_explicit_operator_focus": has_explicit_focus,
        "requires_author_intuition": requires_author_intuition,
        "expected_result": report.get("result", ""),
        "expected_reason": report.get("reason", ""),
        "expected_next_safe_step": report.get("next_safe_step", ""),
        "repair_family": repair_packet.get("resumability_family", core.get("resumability_family", "")),
        "verdict": verdict,
        "why": (
            "the packet-first continuation path exposes enough next-step and input truth to be followed without author memory"
            if verdict == "FOLLOWABLE_BY_SECOND_OPERATOR"
            else "the continuation path still hides too much decision-making in author memory"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-second-operator-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--run-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        state=load_json(Path(args.state_file)),
        packet=load_json(Path(args.repair_packet_file)),
        run_artifact=load_json(Path(args.run_file)),
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
