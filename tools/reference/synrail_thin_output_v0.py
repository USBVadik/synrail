#!/usr/bin/env python3
"""Thin default/dev output bridge for core Synrail non-green outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def checkpoint_restore_available(checkpoint: dict | None) -> bool:
    if not checkpoint:
        return False
    verification = checkpoint.get("verification", {})
    return checkpoint.get("safe_point_eligible", False) and verification.get("status", "") == "PASSED"


def classify_outcome(*, state: dict, report: dict, repair_packet: dict | None, doctor: dict | None) -> str:
    termination_reason = report.get("repair_termination_reason", "") or (repair_packet or {}).get("repair_termination", {}).get("reason", "")
    if termination_reason == "NON_RESUMABLE" or report.get("reason", "") in {"NON_RESUMABLE", "STATE_NOT_RESUMABLE", "TERMINAL_STATE_NOT_RESUMABLE"}:
        return "NON_RESUMABLE"
    if state.get("closure", {}).get("status", "") == "REJECTED" or report.get("closure_status", "") == "REJECTED":
        return "CLOSURE_REJECTED"
    if report.get("reason", "") == "INVALID_PROOF_BUNDLE" or state.get("proof_bundle", {}).get("status", "") == "INVALID":
        return "PROOF_INVALID"
    if report.get("reason", "") in {"MISSING_PROOF_SECTIONS", "ARTIFACT_BUNDLE_MISSING"} or state.get("proof_bundle", {}).get("status", "") == "PARTIAL":
        return "PROOF_PARTIAL"
    if termination_reason in {"MAX_REPAIR_ATTEMPTS", "NO_PROGRESS_DETECTED"}:
        return "REPAIR_STOP"
    if report.get("reason", "") == "DOCTOR_NOT_GREEN":
        failure_classes = list((doctor or {}).get("blocking_failure_classes", []))
        if any(value in failure_classes for value in ["dirty-surface unsafe", "baseline-identity ambiguous", "exact-prompt-artifact-missing"]):
            return "SCOPE_VIOLATION"
        return "DOCTOR_BLOCKED"
    return "NON_GREEN"


def summary_for(outcome_class: str, *, restore_available: bool) -> tuple[str, str]:
    suffix = " A verified checkpoint is available." if restore_available else ""
    messages = {
        "NON_RESUMABLE": (
            "This contour should not continue through resume.",
            f"Follow the named non-resumable boundary or start a new run.{suffix}",
        ),
        "CLOSURE_REJECTED": (
            "Closure was rejected and cannot be treated as accepted work.",
            f"Inspect the closure blocker and repair or restart from a verified safe point.{suffix}",
        ),
        "PROOF_INVALID": (
            "The proof bundle is invalid, so closure is not trustworthy.",
            "Repair the proof surface before attempting closure again.",
        ),
        "PROOF_PARTIAL": (
            "The proof bundle is still incomplete.",
            "Supply the missing proof sections and resume only the current repair step.",
        ),
        "REPAIR_STOP": (
            "The repair loop has reached a bounded stop condition.",
            f"Stop replaying this contour and start a new run or restore a verified safe point.{suffix}",
        ),
        "SCOPE_VIOLATION": (
            "Doctor blocked the contour because scope or target identity is not trustworthy.",
            "Restore the trusted baseline or exact target identity before resuming.",
        ),
        "DOCTOR_BLOCKED": (
            "Doctor has not cleared the contour for continuation.",
            "Repair readiness before continuing this run.",
        ),
        "NON_GREEN": (
            "The runtime is still in a non-green outcome.",
            "Read the next safe step and repair only the current blocker.",
        ),
    }
    return messages[outcome_class]


def technical_lines(*, state: dict, report: dict, repair_packet: dict | None, checkpoint: dict | None) -> list[str]:
    packet = repair_packet or {}
    continuation = packet.get("continuation_core", {})
    return [
        f"state={state.get('state', '')}",
        f"result={report.get('result', '')}",
        f"stopping_stage={report.get('stopping_stage', '')}",
        f"reason={report.get('reason', '')}",
        f"closure_status={state.get('closure', {}).get('status', '')}",
        f"proof_bundle_status={state.get('proof_bundle', {}).get('status', '')}",
        f"repair_termination_reason={report.get('repair_termination_reason', '') or packet.get('repair_termination', {}).get('reason', '')}",
        f"current_step_id={continuation.get('current_step_id', '') or packet.get('repair_history', {}).get('current_step_id', '')}",
        f"next_safe_step={report.get('next_safe_step', '') or state.get('next_safe_step', '')}",
        f"checkpoint_restore_available={checkpoint_restore_available(checkpoint)}",
    ]


def build_record(*, state: dict, report: dict, mode: str, repair_packet: dict | None = None, doctor: dict | None = None, checkpoint: dict | None = None) -> dict:
    restore_available = checkpoint_restore_available(checkpoint)
    outcome_class = classify_outcome(state=state, report=report, repair_packet=repair_packet, doctor=doctor)
    summary, diagnosis = summary_for(outcome_class, restore_available=restore_available)
    suggested_command = {
        "NON_RESUMABLE": "restore-checkpoint or start a new run",
        "CLOSURE_REJECTED": "restore-checkpoint or repair and rerun closure",
        "PROOF_INVALID": "generate-prompt then resume after proof repair",
        "PROOF_PARTIAL": "generate-prompt then resume after supplying proof inputs",
        "REPAIR_STOP": "restore-checkpoint or start a new run",
        "SCOPE_VIOLATION": "repair target or scope, then resume",
        "DOCTOR_BLOCKED": "repair readiness, then resume",
        "NON_GREEN": "inspect report and repair packet, then resume",
    }[outcome_class]
    return {
        "schema_version": "thin_output_record_v0",
        "mode": mode,
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "outcome_class": outcome_class,
        "summary": summary,
        "diagnosis": diagnosis,
        "next_step": report.get("next_safe_step", "") or state.get("next_safe_step", ""),
        "restore_available": restore_available,
        "checkpoint_id": checkpoint.get("checkpoint_id", "") if checkpoint else "",
        "suggested_command": suggested_command,
        "technical_lines": technical_lines(state=state, report=report, repair_packet=repair_packet, checkpoint=checkpoint) if mode == "dev" else [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-thin-output-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--mode", required=True, choices=["default", "dev"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--repair-packet-file")
    parser.add_argument("--doctor-file")
    parser.add_argument("--checkpoint-record-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        state=load_json(Path(args.state_file)),
        report=load_json(Path(args.report_file)),
        mode=args.mode,
        repair_packet=load_json(Path(args.repair_packet_file)) if args.repair_packet_file else None,
        doctor=load_json(Path(args.doctor_file)) if args.doctor_file else None,
        checkpoint=load_json(Path(args.checkpoint_record_file)) if args.checkpoint_record_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "outcome_class": record["outcome_class"], "restore_available": record["restore_available"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
