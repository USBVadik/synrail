#!/usr/bin/env python3
"""Machine-readable observability record builder for Synrail runtime surfaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_state_transition_log(state: dict, report: dict) -> list[dict]:
    from_state = report.get("resume_from_state", "") or report.get("repair_handoff_from_state", "")
    trigger = "resume" if report.get("resume_applied", False) else report.get("stopping_stage", "runtime")
    if not from_state and not report.get("resume_applied", False):
        return []
    return [
        {
            "transition_id": 1,
            "from_state": from_state or state["state"],
            "to_state": state["state"],
            "trigger": trigger,
            "outcome": report.get("result", ""),
            "why": report.get("reason", ""),
        }
    ]


def build_repair_attempt_log(repair_packet: dict | None, repair_receipt: dict | None) -> list[dict]:
    history = repair_packet.get("repair_history", {}) if repair_packet else {}
    results = list(history.get("history_chain_results", []))
    step_ids = list(history.get("history_chain_step_ids", []))
    attempts: list[dict] = []
    for index, result in enumerate(results, start=1):
        attempts.append(
            {
                "attempt_number": index,
                "step_id": step_ids[index - 1] if index - 1 < len(step_ids) else "",
                "result": result,
            }
        )
    if not attempts and repair_receipt:
        attempts.append(
            {
                "attempt_number": 1,
                "step_id": repair_receipt.get("next_step_id", ""),
                "result": repair_receipt.get("result", ""),
            }
        )
    return attempts


def build_rejection_log(report: dict, refresh_report: dict | None = None) -> list[dict]:
    events: list[dict] = []
    if report.get("result") in {"BLOCKED", "ERROR"} or report.get("closure_status") == "REJECTED":
        events.append(
            {
                "stage": report.get("stopping_stage", ""),
                "reason": report.get("reason", ""),
                "dominant_blocker": report.get("dominant_blocker", ""),
                "next_safe_step": report.get("next_safe_step", ""),
            }
        )
    if refresh_report and refresh_report.get("dominant_invalidation"):
        events.append(
            {
                "stage": "refresh",
                "reason": refresh_report.get("dominant_invalidation", ""),
                "dominant_blocker": refresh_report.get("dominant_invalidation", ""),
                "next_safe_step": report.get("next_safe_step", ""),
            }
        )
    return events


def build_sanitized_session_export(
    *,
    state: dict,
    report: dict,
    repair_packet: dict | None,
    repair_receipt: dict | None,
    output_files: dict | None,
) -> dict:
    return {
        "sensitive_values_redacted": True,
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "state": state["state"],
        "result": report.get("result", ""),
        "reason": report.get("reason", ""),
        "next_safe_step": report.get("next_safe_step", ""),
        "resumability_family": report.get("resumability_family", ""),
        "repair_current_step_id": (repair_packet or {}).get("repair_policy", {}).get("next_step_id", ""),
        "repair_last_result": (repair_receipt or {}).get("result", ""),
        "artifact_files": sorted(output_files.values()) if output_files else [],
    }


def build_record(
    *,
    state: dict,
    report: dict,
    repair_packet: dict | None = None,
    repair_receipt: dict | None = None,
    refresh_report: dict | None = None,
    output_files: dict | None = None,
) -> dict:
    state_transition_log = build_state_transition_log(state, report)
    repair_attempt_log = build_repair_attempt_log(repair_packet, repair_receipt)
    rejection_log = build_rejection_log(report, refresh_report)
    return {
        "schema_version": "observability_record_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "resulting_state": state["state"],
        "report_summary": {
            "result": report.get("result", ""),
            "stopping_stage": report.get("stopping_stage", ""),
            "reason": report.get("reason", ""),
            "next_safe_step": report.get("next_safe_step", ""),
        },
        "event_counts": {
            "transition_count": len(state_transition_log),
            "repair_attempt_count": len(repair_attempt_log),
            "rejection_count": len(rejection_log),
        },
        "state_transition_log": state_transition_log,
        "repair_attempt_log": repair_attempt_log,
        "rejection_log": rejection_log,
        "sanitized_session_export": build_sanitized_session_export(
            state=state,
            report=report,
            repair_packet=repair_packet,
            repair_receipt=repair_receipt,
            output_files=output_files,
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-observability-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repair-packet-file")
    parser.add_argument("--repair-receipt-file")
    parser.add_argument("--refresh-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    state = load_json(Path(args.state_file))
    report = load_json(Path(args.report_file))
    output_files = {"report": Path(args.report_file).name, "state": Path(args.state_file).name}
    if args.repair_packet_file:
        output_files["repair_packet"] = Path(args.repair_packet_file).name
    if args.repair_receipt_file:
        output_files["repair_receipt"] = Path(args.repair_receipt_file).name
    if args.refresh_file:
        output_files["refresh"] = Path(args.refresh_file).name
    record = build_record(
        state=state,
        report=report,
        repair_packet=load_json(Path(args.repair_packet_file)) if args.repair_packet_file else None,
        repair_receipt=load_json(Path(args.repair_receipt_file)) if args.repair_receipt_file else None,
        refresh_report=load_json(Path(args.refresh_file)) if args.refresh_file else None,
        output_files=output_files,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "transition_count": record["event_counts"]["transition_count"], "repair_attempt_count": record["event_counts"]["repair_attempt_count"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
