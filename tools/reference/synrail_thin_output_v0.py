#!/usr/bin/env python3
"""Thin default/dev output bridge for core Synrail non-green outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_repair_focus_v0 import focused_repair_summary
except ImportError:
    from synrail_repair_focus_v0 import focused_repair_summary


def humanize_token(value: str) -> str:
    if not value:
        return ""
    return value.replace("_", " ").replace("-", " ").lower()


def human_reason(report: dict, repair_packet: dict | None = None) -> str:
    raw = (
        report.get("reason", "")
        or (repair_packet or {}).get("runtime_truth", {}).get("report_reason", "")
        or (repair_packet or {}).get("repair_termination", {}).get("reason", "")
    )
    labels = {
        "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED": "this run was not started in controlled mode",
        "REMOTE_TARGET_UNSUPPORTED": "the current alpha lane does not support remote or ops targets yet",
        "EXACT_TASK_IDENTITY_NOT_CONFIRMED": "the original task request is not confirmed",
        "INVALID_PROOF_BUNDLE": "the final result proof could not be trusted",
        "SEMANTIC_PROOF_INSUFFICIENT": "the proof is present but still too thin to trust",
        "MISSING_PROOF_SECTIONS": "the proof is still missing required sections",
        "ARTIFACT_BUNDLE_MISSING": "the result bundle is missing required proof files",
        "DOCTOR_NOT_GREEN": "the current workspace is not ready yet",
        "ACCEPTANCE_CRITERIA_STALE": "the acceptance rules no longer match this project state",
        "ACCEPTANCE_CRITERIA_INVALID": "the acceptance rules could not be trusted",
        "STATE_NOT_RESUMABLE": "this run cannot safely continue from the current state",
        "TERMINAL_STATE_NOT_RESUMABLE": "this run cannot safely continue from the current state",
        "NON_RESUMABLE": "this run cannot safely continue from the current state",
        "MAX_REPAIR_ATTEMPTS": "the bounded repair limit was reached",
        "NO_PROGRESS_DETECTED": "the repair loop stopped making progress",
        "CONTINUATION_INPUTS_MISSING": "the next repair step is still missing required inputs",
        "RECOVERY_REVERIFICATION_INCOMPLETE": "recovery reverification is still incomplete",
        "NONE": "no blocking issue remains",
    }
    return labels.get(raw, humanize_token(raw))


def has_doctor_coverage_block(doctor: dict | None) -> bool:
    failure_classes = list((doctor or {}).get("blocking_failure_classes", []))
    return "doctor-coverage incomplete" in failure_classes


def continuation_arbiter_unresolved(repair_packet: dict | None) -> bool:
    arbiter = (repair_packet or {}).get("continuation_arbiter", {})
    return arbiter.get("resolution_status", "") == "CONFLICT_UNRESOLVED"


def human_safe_step_text(value: str) -> str:
    labels = {
        "restore exact prompt and task identity": "restore the original task request and intended target",
        "move to a clean or explicitly observed-safe execution surface": "move back to a clean or clearly verified-safe workspace",
    }
    return labels.get(value, value)


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
    if report.get("reason", "") in {"ACCEPTANCE_CRITERIA_STALE", "ACCEPTANCE_CRITERIA_INVALID"}:
        return "NON_GREEN"
    if report.get("reason", "") == "INVALID_PROOF_BUNDLE" or state.get("proof_bundle", {}).get("status", "") == "INVALID":
        return "PROOF_INVALID"
    if report.get("reason", "") == "SEMANTIC_PROOF_INSUFFICIENT" or state.get("proof_bundle", {}).get("status", "") == "STRUCTURALLY_COMPLETE":
        return "PROOF_THIN"
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
            "This run is not ready for the next bounded attempt yet.",
            f"Synrail needs one more bounded setup step before the next synrail check.{suffix}{recovery_suffix}",
        )
    reason = (
        report.get("reason", "")
        or (repair_packet or {}).get("runtime_truth", {}).get("report_reason", "")
        or (repair_packet or {}).get("repair_termination", {}).get("reason", "")
    )
    if outcome_class == "NON_GREEN" and reason == "CONTINUATION_INPUTS_MISSING":
        return (
            "The current repair step is still incomplete.",
            f"Finish only the current bounded repair step before trying synrail retry again.{recovery_suffix}",
        )
    if outcome_class == "NON_GREEN" and reason in {"ACCEPTANCE_CRITERIA_STALE", "ACCEPTANCE_CRITERIA_INVALID"}:
        return (
            "The acceptance rules for this run are not trustworthy yet.",
            "Refresh the acceptance rules for the current project state before trusting closure again.",
        )
    if outcome_class == "NON_GREEN" and reason == "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED":
        return (
            "This run was not started through Synrail controlled mode.",
            "Synrail can inspect this run, but it cannot treat acceptance as trustworthy until the run starts through controlled bootstrap provenance.",
        )
    if outcome_class == "NON_GREEN" and reason == "REMOTE_TARGET_UNSUPPORTED":
        return (
            "This alpha lane does not support remote or ops targets yet.",
            "Run this contour on a local trusted worktree on the machine where the agent acts, or wait for an explicitly supported remote lane.",
        )
    if outcome_class in {"NON_GREEN", "NON_RESUMABLE"} and continuation_arbiter_unresolved(repair_packet):
        return (
            "Synrail cannot resolve the current continuation path confidently yet.",
            f"The current continuation inputs still conflict after explicit precedence, so this recovery path still needs operator judgment.{suffix}{recovery_suffix}",
        )
    if outcome_class == "DOCTOR_BLOCKED" and has_doctor_coverage_block(doctor):
        return (
            "Doctor is still using a bounded fail-mode corpus that does not justify trust yet.",
            "Do not treat this readiness reading as complete until the agreed critical fail modes are covered.",
        )
    failure_classes = list((doctor or {}).get("blocking_failure_classes", []))
    messages = {
        "ACCEPTED": (
            "The run reached accepted closure under the current criteria.",
            "Synrail accepted the result based on the current acceptance, proof, and closure surfaces.",
        ),
        "NON_RESUMABLE": (
            "This run cannot continue from the current state.",
            f"Start a new run or restore a verified restore point before trying again.{suffix}{recovery_suffix}",
        ),
        "CLOSURE_REJECTED": (
            "Closure was rejected and cannot be treated as accepted work under the current criteria.",
            f"Inspect the closure blocker and repair or restart from a verified restore point.{suffix}{recovery_suffix}",
        ),
        "PROOF_INVALID": (
            "The proof bundle is invalid, so closure is not trustworthy.",
            f"Repair the proof surface before attempting closure again.{recovery_suffix}",
        ),
        "PROOF_THIN": (
            "The proof bundle is present, but still not strong enough under the current proof rules.",
            f"Strengthen the semantic proof evidence before attempting closure again. This is not enough evidence for accepted closure yet.{recovery_suffix}",
        ),
        "PROOF_PARTIAL": (
            "The proof bundle is still incomplete.",
            f"Supply the missing proof sections and continue only the current bounded repair step.{recovery_suffix}",
        ),
        "REPAIR_STOP": (
            "The repair loop has reached a bounded stop condition.",
            f"Stop replaying this contour and start a new run or restore a verified restore point.{suffix}{recovery_suffix}",
        ),
        "SCOPE_VIOLATION": (
            "Doctor blocked this run because the workspace or intended task target is not trustworthy.",
            (
                f"Move back to a clean in-scope workspace before continuing this run.{suffix}{recovery_suffix}"
                if "dirty-surface unsafe" in failure_classes
                else f"Restore the original task target before continuing this run.{recovery_suffix}"
            ),
        ),
        "DOCTOR_BLOCKED": (
            "Doctor has not cleared this workspace under the current readiness checks yet.",
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
        f"bootstrap_provenance_reason={state.get('integrity', {}).get('bootstrap_provenance_reason', '')}",
    ]


def current_repair_focus_summary(repair_packet: dict | None) -> str:
    continuation = (repair_packet or {}).get("continuation_core", {})
    return focused_repair_summary(
        current_step_id=continuation.get("current_step_id", ""),
        current_step_subsurface_id=continuation.get("current_step_subsurface_id", ""),
        current_step_target_path=continuation.get("current_step_target_path", ""),
    )


def status_label(outcome_class: str, *, report: dict, repair_packet: dict | None) -> str:
    reason = (
        report.get("reason", "")
        or (repair_packet or {}).get("runtime_truth", {}).get("report_reason", "")
        or (repair_packet or {}).get("repair_termination", {}).get("reason", "")
    )
    if outcome_class == "ACCEPTED":
        return "Accepted"
    if outcome_class == "CLOSURE_REJECTED":
        return "Closure Rejected"
    if outcome_class == "PROOF_INVALID":
        return "Proof Invalid"
    if outcome_class == "PROOF_THIN":
        return "Proof Too Thin To Trust"
    if outcome_class == "PROOF_PARTIAL":
        return "Proof Incomplete"
    if outcome_class == "REPAIR_STOP":
        return "Repair Stopped"
    if outcome_class == "SCOPE_VIOLATION":
        return "Workspace Not Trusted"
    if outcome_class == "DOCTOR_BLOCKED":
        return "Workspace Not Ready"
    if outcome_class in {"NON_GREEN", "NON_RESUMABLE"} and continuation_arbiter_unresolved(repair_packet):
        return "Continuation Still Ambiguous"
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        return "Not Ready For The Next Attempt"
    if outcome_class == "NON_RESUMABLE":
        return "Cannot Continue This Run"
    if outcome_class == "NON_GREEN" and reason == "CONTINUATION_INPUTS_MISSING":
        return "Finish This Repair First"
    if outcome_class == "NON_GREEN" and reason in {"ACCEPTANCE_CRITERIA_STALE", "ACCEPTANCE_CRITERIA_INVALID"}:
        return "Acceptance Rules Need Refresh"
    if outcome_class == "NON_GREEN" and reason == "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED":
        return "Controlled Run Required"
    if outcome_class == "NON_GREEN" and reason == "REMOTE_TARGET_UNSUPPORTED":
        return "Remote Target Not Supported Yet"
    return "Needs Review"


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
            return "Restore the original task request and intended task target, then run synrail check for the next bounded attempt."
        return "Run the next bounded forward attempt through synrail check."
    if outcome_class == "PROOF_INVALID":
        return "Replace the broken final result or proof inputs, then ask Synrail for the next bounded repair step."
    if outcome_class == "PROOF_THIN":
        return "Strengthen only the thin proof evidence, then ask Synrail for the next bounded repair step."
    if outcome_class == "PROOF_PARTIAL":
        return "Add the missing proof inputs, then ask Synrail for the next bounded repair step."
    if outcome_class == "REPAIR_STOP":
        return "Stop replaying this contour. Restore a verified restore point or start a new run."
    if outcome_class == "SCOPE_VIOLATION":
        if "dirty-surface unsafe" in failure_classes:
            return "Move back to a clean or clearly verified-safe workspace before continuing."
        return "Restore the original task request or target before continuing."
    if outcome_class == "DOCTOR_BLOCKED":
        if has_doctor_coverage_block(doctor):
            return "Treat this doctor as bounded for now. Close the agreed missing fail modes before trusting readiness."
        return "Repair readiness first, then retry only the current bounded step."
    if outcome_class in {"NON_GREEN", "NON_RESUMABLE"} and continuation_arbiter_unresolved(repair_packet):
        return "Do not assume resume is safe yet. Restore a verified fallback or rerun from a clearer starting point."
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "CONTINUATION_INPUTS_MISSING":
        return "Finish the current bounded repair from synrail repair-step, then run synrail retry."
    if outcome_class == "NON_GREEN" and report.get("reason", "") in {"ACCEPTANCE_CRITERIA_STALE", "ACCEPTANCE_CRITERIA_INVALID"}:
        return "Run synrail refresh-acceptance, then rerun synrail check."
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED":
        return "Start this run through synrail start before trusting any proof or acceptance."
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "REMOTE_TARGET_UNSUPPORTED":
        return "Rerun this alpha lane on a local trusted worktree. The remote or ops contour is not supported yet."
    return human_safe_step_text(raw_next_step)


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
        "NON_RESUMABLE": "synrail restore or start a new run",
        "CLOSURE_REJECTED": "synrail restore or repair and rerun closure",
        "PROOF_INVALID": "run synrail repair-step, apply only that repair, then synrail retry",
        "PROOF_THIN": "run synrail repair-step, strengthen only the thin proof evidence, then synrail retry",
        "PROOF_PARTIAL": "run synrail repair-step, supply only the missing proof inputs, then synrail retry",
        "REPAIR_STOP": "synrail restore or start a new run",
        "SCOPE_VIOLATION": "repair the workspace or intended task target, then synrail retry",
        "DOCTOR_BLOCKED": "repair readiness, then synrail retry",
        "NON_GREEN": "inspect the blocker, then continue the bounded repair step",
    }[outcome_class]
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        suggested_command = "restore the original task request, then run synrail check"
    if outcome_class == "SCOPE_VIOLATION" and restore_available:
        failure_classes = list((doctor or {}).get("blocking_failure_classes", []))
        if "dirty-surface unsafe" in failure_classes:
            suggested_command = "synrail restore or move to a clean in-scope surface, then synrail retry"
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "CONTINUATION_INPUTS_MISSING":
        suggested_command = "run synrail repair-step, finish only that repair, then synrail retry"
    if outcome_class == "NON_GREEN" and report.get("reason", "") in {"ACCEPTANCE_CRITERIA_STALE", "ACCEPTANCE_CRITERIA_INVALID"}:
        suggested_command = "run synrail refresh-acceptance, then rerun synrail check"
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED":
        suggested_command = "run synrail start before acting on this run"
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "REMOTE_TARGET_UNSUPPORTED":
        suggested_command = "rerun this alpha lane on a local trusted worktree"
    if outcome_class == "DOCTOR_BLOCKED" and has_doctor_coverage_block(doctor):
        suggested_command = "treat doctor as bounded, close the agreed missing fail modes, then rerun readiness"
    if outcome_class in {"NON_GREEN", "NON_RESUMABLE"} and continuation_arbiter_unresolved(repair_packet):
        suggested_command = "use synrail restore or rerun from a clearer starting point before trusting continuation"
    next_step = report.get("next_safe_step", "") or state.get("next_safe_step", "")
    focused_summary = current_repair_focus_summary(repair_packet)
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
    if outcome_class in {"PROOF_INVALID", "PROOF_THIN", "PROOF_PARTIAL", "SCOPE_VIOLATION", "DOCTOR_BLOCKED", "NON_GREEN"} and can_resume:
        next_command = "synrail repair-step"
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        next_command = "synrail repair-step"
    if outcome_class == "NON_GREEN" and report.get("reason", "") in {"ACCEPTANCE_CRITERIA_STALE", "ACCEPTANCE_CRITERIA_INVALID"}:
        next_command = "synrail refresh-acceptance"
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED":
        next_command = "synrail start"
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "REMOTE_TARGET_UNSUPPORTED":
        next_command = ""
    if outcome_class in {"NON_GREEN", "NON_RESUMABLE"} and continuation_arbiter_unresolved(repair_packet):
        next_command = ""
    if outcome_class in {"NON_RESUMABLE", "CLOSURE_REJECTED", "REPAIR_STOP", "SCOPE_VIOLATION"} and restore_available:
        restore_command = "synrail restore"
    if outcome_class in {"NON_GREEN", "NON_RESUMABLE"} and continuation_arbiter_unresolved(repair_packet) and restore_available:
        restore_command = "synrail restore"
    return {
        "schema_version": "thin_output_record_v0",
        "mode": mode,
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "outcome_class": outcome_class,
        "status_label": status_label(outcome_class, report=report, repair_packet=repair_packet),
        "summary": summary,
        "diagnosis": diagnosis,
        "what_happened": summary,
        "what_it_means": diagnosis,
        "what_to_do_next": what_to_do_next,
        "focused_repair_summary": focused_summary,
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
