#!/usr/bin/env python3
"""Inspect whether a packet-first continuation path is followable by a second operator without author memory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from synrail_continuation_arbiter_v0 import build_record as build_continuation_arbiter


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_record(*, state: dict, packet: dict, run_artifact: dict) -> dict:
    core = packet.get("continuation_core", {})
    report = run_artifact.get("report", {})
    repair_packet = run_artifact.get("repair_packet", {})
    embedded_arbiter = packet.get("continuation_arbiter", {})
    if isinstance(embedded_arbiter, dict) and embedded_arbiter.get("schema_version") == "continuation_arbiter_record_v0":
        arbiter = embedded_arbiter
    else:
        arbiter = build_continuation_arbiter(
            state=state,
            packet=packet,
            repair_receipt=packet.get("repair_receipt"),
        )
    resolved = arbiter.get("resolved_decision", {})
    visible_entry_artifacts = ["state_file", "repair_packet"]
    resumability_status = resolved.get("resumability_status", repair_packet.get("resumability_status", core.get("resumability_status", "")))
    has_explicit_next_step = bool(resolved.get("next_safe_step", ""))
    has_explicit_required_inputs = bool(resolved.get("next_step_required_inputs", []))
    no_input_boundary = resumability_status == "NOT_RESUMABLE" and not resolved.get("next_step_required_inputs", [])
    has_explicit_focus = bool(resolved.get("operator_focus", ""))
    has_explicit_precedence = bool(arbiter.get("precedence_order", []))
    packet_replay_ready = bool(resolved.get("packet_replay_ready", False))
    packet_only_entry = visible_entry_artifacts == ["state_file", "repair_packet"]
    requires_author_intuition = not (
        arbiter.get("resolution_status", "") == "RESOLVED"
        and has_explicit_next_step
        and has_explicit_focus
        and (has_explicit_required_inputs or no_input_boundary)
        and has_explicit_precedence
        and packet_replay_ready
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
        "has_explicit_precedence": has_explicit_precedence,
        "packet_replay_ready": packet_replay_ready,
        "arbiter_resolution_status": arbiter.get("resolution_status", ""),
        "arbiter_conflict_count": arbiter.get("conflict_count", 0),
        "arbiter_ignored_sources": list(arbiter.get("ignored_sources", [])),
        "requires_author_intuition": requires_author_intuition,
        "expected_result": report.get("result", ""),
        "expected_reason": report.get("reason", ""),
        "expected_next_safe_step": report.get("next_safe_step", ""),
        "repair_family": resolved.get("resumability_family", repair_packet.get("resumability_family", core.get("resumability_family", ""))),
        "verdict": verdict,
        "why": (
            "the packet-first continuation path now resolves conflicts through the arbiter, so a second operator can follow the same next step without author memory"
            if verdict == "FOLLOWABLE_BY_SECOND_OPERATOR"
            else "the continuation path still leaves too much continuation conflict unresolved after explicit arbitration"
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
