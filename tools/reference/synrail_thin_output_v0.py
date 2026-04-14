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


def checkpoint_restore_available(checkpoint: dict | None, *, state: dict) -> bool:
    if not checkpoint:
        return False
    verification = checkpoint.get("verification", {})
    return (
        checkpoint.get("safe_point_eligible", False)
        and verification.get("status", "") == "PASSED"
        and checkpoint.get("run_id", "") == state.get("run_id", "")
        and checkpoint.get("task_class", "") == state.get("task_class", "")
    )


def matching_recovery(recovery: dict | None, *, state: dict) -> dict | None:
    if not recovery:
        return None
    if recovery.get("run_id", "") != state.get("run_id", ""):
        return None
    if recovery.get("task_class", "") != state.get("task_class", ""):
        return None
    return recovery


def classify_outcome(*, state: dict, report: dict, repair_packet: dict | None, doctor: dict | None) -> str:
    termination_reason = report.get("repair_termination_reason", "") or (repair_packet or {}).get("repair_termination", {}).get("reason", "")
    if state.get("state", "") == "CLOSURE_ACCEPTED" or report.get("closure_status", "") == "ACCEPTED":
        return "ACCEPTED"
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


def resume_available(report: dict, repair_packet: dict | None) -> bool:
    packet = repair_packet or {}
    continuation = packet.get("continuation_core", {})
    termination = packet.get("repair_termination", {})
    resumability = packet.get("resumability", {})
    current_step = continuation.get("current_step_id", "") or packet.get("repair_policy", {}).get("next_step_id", "")
    return (
        resumability.get("status", "") == "REPAIRABLE"
        and termination.get("status", "CONTINUE") != "TERMINATE"
        and bool(current_step)
        and report.get("reason", "") not in {"NON_RESUMABLE", "STATE_NOT_RESUMABLE", "TERMINAL_STATE_NOT_RESUMABLE"}
    )


def non_resumable_forward_boundary(*, report: dict, repair_packet: dict | None) -> bool:
    packet = repair_packet or {}
    return (
        report.get("resumability_policy_next_step", "") == "continue_forward_orchestration"
        or report.get("resumability_family", "") == "NOT_RESUMABLE_FRESH_ORCHESTRATION"
        or packet.get("resumability_family", "") == "NOT_RESUMABLE_FRESH_ORCHESTRATION"
        or packet.get("current_step_id", "") == "continue_forward_orchestration"
    )


def summary_for(outcome_class: str, *, restore_available: bool, recovery: dict | None, report: dict, repair_packet: dict | None, doctor: dict | None = None) -> tuple[str, str]:
    suffix = " A verified checkpoint is available." if restore_available else ""
    recovery_suffix = ""
    if recovery and recovery.get("primary_action", "") != "KEEP_CURRENT_ARTIFACTS":
        instructions = "; ".join(recovery.get("operator_instructions", [])[:2])
        recovery_suffix = f" Recovery path: {instructions}."
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        return (
            "This contour should not continue through resume.",
            f"Continue through the governed forward path instead of named resume.{suffix}{recovery_suffix}",
        )
    failure_classes = list((doctor or {}).get("blocking_failure_classes", []))
    messages = {
        "ACCEPTED": (
            "The run reached accepted closure.",
            "Synrail accepted the result based on the current proof and closure surfaces.",
        ),
        "NON_RESUMABLE": (
            "This contour should not continue through resume.",
            f"Follow the named non-resumable boundary or start a new run.{suffix}{recovery_suffix}",
        ),
        "CLOSURE_REJECTED": (
            "Closure was rejected and cannot be treated as accepted work.",
            f"Inspect the closure blocker and repair or restart from a verified safe point.{suffix}{recovery_suffix}",
        ),
        "PROOF_INVALID": (
            "The proof bundle is invalid, so closure is not trustworthy.",
            f"Repair the proof surface before attempting closure again.{recovery_suffix}",
        ),
        "PROOF_PARTIAL": (
            "The proof bundle is still incomplete.",
            f"Supply the missing proof sections and resume only the current repair step.{recovery_suffix}",
        ),
        "REPAIR_STOP": (
            "The repair loop has reached a bounded stop condition.",
            f"Stop replaying this contour and start a new run or restore a verified safe point.{suffix}{recovery_suffix}",
        ),
        "SCOPE_VIOLATION": (
            "Doctor blocked the contour because scope or target identity is not trustworthy.",
            (
                f"Move back to a clean in-scope execution surface before resuming.{suffix}{recovery_suffix}"
                if "dirty-surface unsafe" in failure_classes
                else f"Restore the trusted baseline or exact target identity before resuming.{recovery_suffix}"
            ),
        ),
        "DOCTOR_BLOCKED": (
            "Doctor has not cleared the contour for continuation.",
            f"Repair readiness before continuing this run.{recovery_suffix}",
        ),
        "NON_GREEN": (
            "The runtime is still in a non-green outcome.",
            f"Read the next safe step and repair only the current blocker.{recovery_suffix}",
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
        f"checkpoint_restore_available={checkpoint_restore_available(checkpoint, state=state)}",
    ]


def human_next_step(
    *,
    outcome_class: str,
    raw_next_step: str,
    report: dict,
    repair_packet: dict | None,
    doctor: dict | None,
) -> str:
    failure_classes = list((doctor or {}).get("blocking_failure_classes", []))
    if outcome_class == "ACCEPTED":
        return "No repair step is required."
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        if report.get("reason", "") == "EXACT_TASK_IDENTITY_NOT_CONFIRMED":
            return "Restore the exact task prompt and task identity, then start the next bounded attempt through synrail check."
        return "Continue through the next bounded forward attempt instead of named resume."
    if outcome_class == "PROOF_INVALID":
        return "Replace the broken final result or proof inputs, then ask Synrail for the next bounded repair step."
    if outcome_class == "PROOF_PARTIAL":
        return "Add the missing proof inputs, then ask Synrail for the next bounded repair step."
    if outcome_class == "REPAIR_STOP":
        return "Stop replaying this contour. Restore a verified checkpoint or start a new run."
    if outcome_class == "SCOPE_VIOLATION":
        if "dirty-surface unsafe" in failure_classes:
            return "Move back to a clean in-scope working surface before continuing."
        return "Restore the trusted target identity before continuing."
    if outcome_class == "DOCTOR_BLOCKED":
        return "Repair readiness first, then continue only the current bounded step."
    return raw_next_step


def build_record(*, state: dict, report: dict, mode: str, repair_packet: dict | None = None, doctor: dict | None = None, checkpoint: dict | None = None, recovery: dict | None = None) -> dict:
    restore_available = checkpoint_restore_available(checkpoint, state=state)
    matching = matching_recovery(recovery, state=state)
    outcome_class = classify_outcome(state=state, report=report, repair_packet=repair_packet, doctor=doctor)
    can_resume = resume_available(report, repair_packet)
    summary, diagnosis = summary_for(
        outcome_class,
        restore_available=restore_available,
        recovery=matching,
        report=report,
        repair_packet=repair_packet,
        doctor=doctor,
    )
    suggested_command = {
        "ACCEPTED": "no next command required",
        "NON_RESUMABLE": "restore-checkpoint or start a new run",
        "CLOSURE_REJECTED": "restore-checkpoint or repair and rerun closure",
        "PROOF_INVALID": "generate-prompt then resume after proof repair",
        "PROOF_PARTIAL": "generate-prompt then resume after supplying proof inputs",
        "REPAIR_STOP": "restore-checkpoint or start a new run",
        "SCOPE_VIOLATION": "repair target or scope, then resume",
        "DOCTOR_BLOCKED": "repair readiness, then resume",
        "NON_GREEN": "inspect report and repair packet, then resume",
    }[outcome_class]
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        suggested_command = "continue governed forward path, not resume"
    if outcome_class == "SCOPE_VIOLATION" and restore_available:
        failure_classes = list((doctor or {}).get("blocking_failure_classes", []))
        if "dirty-surface unsafe" in failure_classes:
            suggested_command = "restore-checkpoint or move to a clean in-scope surface, then resume"
    next_step = report.get("next_safe_step", "") or state.get("next_safe_step", "")
    if outcome_class == "ACCEPTED":
        next_step = "No repair step is required."
    what_to_do_next = human_next_step(
        outcome_class=outcome_class,
        raw_next_step=next_step,
        report=report,
        repair_packet=repair_packet,
        doctor=doctor,
    )
    next_command = ""
    restore_command = ""
    if outcome_class in {"PROOF_INVALID", "PROOF_PARTIAL", "DOCTOR_BLOCKED", "NON_GREEN"} and can_resume:
        next_command = "synrail generate-prompt"
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        next_command = "synrail generate-prompt"
    if outcome_class in {"NON_RESUMABLE", "CLOSURE_REJECTED", "REPAIR_STOP", "SCOPE_VIOLATION"} and restore_available:
        restore_command = "synrail restore"
    return {
        "schema_version": "thin_output_record_v0",
        "mode": mode,
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "outcome_class": outcome_class,
        "summary": summary,
        "diagnosis": diagnosis,
        "what_happened": summary,
        "what_it_means": diagnosis,
        "what_to_do_next": what_to_do_next,
        "resume_available": can_resume,
        "next_command": next_command,
        "restore_command": restore_command,
        "next_step": next_step,
        "restore_available": restore_available,
        "checkpoint_id": checkpoint.get("checkpoint_id", "") if checkpoint else "",
        "recovery_primary_action": matching.get("primary_action", "") if matching else "",
        "recovery_operator_instructions": list(matching.get("operator_instructions", [])) if matching else [],
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
    parser.add_argument("--consistency-recovery-file")
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
        recovery=load_json(Path(args.consistency_recovery_file)) if args.consistency_recovery_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "outcome_class": record["outcome_class"], "restore_available": record["restore_available"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
