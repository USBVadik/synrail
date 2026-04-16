#!/usr/bin/env python3
"""Build one compact operator-facing brief from current Synrail runtime truth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_repair_focus_v0 import focused_repair_action_instruction
except ImportError:
    from synrail_repair_focus_v0 import focused_repair_action_instruction


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def normalize_report(payload: dict) -> dict:
    embedded = payload.get("report")
    if isinstance(embedded, dict) and (embedded.get("schema_version") == "report_record_v0" or "result" in embedded or "reason" in embedded):
        return embedded
    return payload


def display_cli_path(value: str) -> str:
    if not value:
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    try:
        return str(path.resolve().relative_to(Path.cwd().resolve()))
    except ValueError:
        return value


def determine_primary_action(packet: dict, report: dict) -> tuple[str, str]:
    resumability = packet.get("resumability", {})
    termination = packet.get("repair_termination", {})
    continuation_core = packet.get("continuation_core", {})

    if resumability.get("status", "") != "REPAIRABLE":
        return (
            "FOLLOW_NON_RESUMABLE_BOUNDARY",
            "this contour is no longer resumable, so the operator should follow the named boundary instead of replaying resume",
        )

    if termination.get("status", "") == "TERMINATE":
        return (
            "STOP_AND_START_NEW_RUN",
            "the repair loop already hit a bounded termination rule, so the next move is to stop replaying this contour",
        )

    if continuation_core.get("next_step_required_inputs", []):
        return (
            "REPAIR_CURRENT_STEP",
            "the packet still names one current repair step, its required inputs, and the stale sub-surfaces to tighten next",
        )

    if report.get("result", "") == "OK":
        return (
            "CONTINUE_RUNTIME",
            "the contour is still progressing and the next bounded runtime move remains explicit",
        )

    return (
        "INSPECT_RUNTIME_TRUTH",
        "the runtime truth is still bounded, but the operator should inspect the current packet and report before choosing the next move",
    )


def suggested_cli(primary_action: str, state_file: str, repair_packet_file: str) -> dict:
    if primary_action in {"REPAIR_CURRENT_STEP", "CONTINUE_RUNTIME"}:
        return {
            "command": "synrail resume",
            "args": [
                "--state-file",
                display_cli_path(state_file),
                "--repair-packet-file",
                display_cli_path(repair_packet_file),
            ],
        }
    return {
        "command": "NONE",
        "args": [],
    }


def build_record(*, state: dict, report: dict, packet: dict, doctor: dict | None, state_file: str, repair_packet_file: str) -> dict:
    continuation_core = packet.get("continuation_core", {})
    repair_policy = packet.get("repair_policy", {})
    repair_history = packet.get("repair_history", {})
    termination = packet.get("repair_termination", {})
    primary_action, why_action = determine_primary_action(packet, report)

    return {
        "schema_version": "operator_brief_record_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "entrypoint": "resume" if report.get("resume_applied", False) else report.get("stopping_stage", "runtime"),
        "entry_state": report.get("resume_from_state") or report.get("entry_state") or state.get("state", ""),
        "resulting_state": state.get("state", ""),
        "result": report.get("result", ""),
        "stopping_stage": report.get("stopping_stage", ""),
        "reason": report.get("reason", ""),
        "doctor_verdict": doctor.get("final_verdict", "") if doctor else report.get("doctor_verdict", ""),
        "closure_status": report.get("closure_status", state.get("closure", {}).get("status", "")),
        "resumability_family": packet.get("resumability", {}).get("family", ""),
        "active_pressures": list(packet.get("resumability", {}).get("active_pressures", [])),
        "primary_action": primary_action,
        "why_action": why_action,
        "next_safe_step": continuation_core.get("next_safe_step", report.get("next_safe_step", state.get("next_safe_step", ""))),
        "operator_focus": continuation_core.get("operator_focus", ""),
        "current_step_id": continuation_core.get("current_step_id", repair_policy.get("next_step_id", "")),
        "current_step_subsurface_id": continuation_core.get("current_step_subsurface_id", ""),
        "current_step_target_path": continuation_core.get("current_step_target_path", ""),
        "current_step_action_instruction": focused_repair_action_instruction(
            current_step_id=continuation_core.get("current_step_id", repair_policy.get("next_step_id", "")),
            current_step_subsurface_id=continuation_core.get("current_step_subsurface_id", ""),
            current_step_target_path=continuation_core.get("current_step_target_path", ""),
        ),
        "ready_now_step_ids": list(repair_policy.get("ready_now_step_ids", [])),
        "next_step_required_inputs": list(continuation_core.get("next_step_required_inputs", [])),
        "next_step_subsurface_ids": list(continuation_core.get("next_step_subsurface_ids", [])),
        "blockers": list(report.get("blockers", [])),
        "dominant_blocker": report.get("dominant_blocker", ""),
        "termination_status": termination.get("status", "CONTINUE"),
        "termination_reason": termination.get("reason", ""),
        "attempt_count": termination.get("attempt_count", 0),
        "history_chain_length": repair_history.get("history_chain_length", continuation_core.get("history_chain_length", 0)),
        "completed_step_ids": list(repair_history.get("completed_step_ids", [])),
        "stale_artifact_ids": list(packet.get("artifact_quality_summary", {}).get("stale_artifact_ids", [])),
        "stale_subsurface_ids": list(packet.get("artifact_quality_summary", {}).get("stale_subsurface_ids", [])),
        "entry_artifacts": ["state_file", "repair_packet"],
        "suggested_cli": suggested_cli(primary_action, state_file, repair_packet_file),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-operator-brief-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--doctor-file")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    state = load_json(Path(args.state_file))
    report = normalize_report(load_json(Path(args.report_file)))
    packet = load_json(Path(args.repair_packet_file))
    doctor = load_json(Path(args.doctor_file)) if args.doctor_file else None
    record = build_record(
        state=state,
        report=report,
        packet=packet,
        doctor=doctor,
        state_file=args.state_file,
        repair_packet_file=args.repair_packet_file,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "primary_action": record["primary_action"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
