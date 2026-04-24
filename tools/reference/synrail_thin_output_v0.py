#!/usr/bin/env python3
"""Thin default/dev output bridge for core Synrail non-green outcomes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_repair_focus_v0 import focused_repair_action_instruction, focused_repair_summary
except ImportError:
    from synrail_repair_focus_v0 import focused_repair_action_instruction, focused_repair_summary


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


def matching_refresh(refresh: dict | None, *, state: dict) -> dict | None:
    if not refresh:
        return None
    if refresh.get("run_id", "") != state.get("run_id", ""):
        return None
    return refresh


REFRESH_CHANGE_IMPACT = {
    "closure_invalidated_by_doctor": {
        "summary": "A refresh invalidated closure because readiness became stale.",
        "diagnosis": "Repair only readiness before trusting closure again.",
        "action": "Repair only readiness, then rerun synrail check.",
    },
    "closure_invalidated_by_invalid_bundle": {
        "summary": "A refresh invalidated closure because the final-result proof artifact became stale.",
        "diagnosis": "Repair only the final-result proof artifact before trusting closure again.",
        "action": "Repair only the final-result proof artifact, then rerun synrail check.",
    },
    "closure_invalidated_by_semantic_bundle": {
        "summary": "A refresh invalidated closure because semantic proof evidence became stale.",
        "diagnosis": "Strengthen only the stale semantic proof evidence before trusting closure again.",
        "action": "Strengthen only the stale semantic proof evidence, then rerun synrail check.",
    },
    "closure_invalidated_by_partial_bundle": {
        "summary": "A refresh invalidated closure because required proof sections became stale.",
        "diagnosis": "Complete only the stale proof sections before trusting closure again.",
        "action": "Complete only the stale proof sections, then rerun synrail check.",
    },
    "closure_invalidated_by_recovery": {
        "summary": "A refresh invalidated closure because recovery reverification became stale.",
        "diagnosis": "Run only recovery reverification before trusting closure again.",
        "action": "Run only recovery reverification, then rerun synrail check.",
    },
}

PROOF_RELATED_INVALIDATIONS = {
    "closure_invalidated_by_invalid_bundle",
    "closure_invalidated_by_semantic_bundle",
    "closure_invalidated_by_partial_bundle",
}


def selective_refresh_repair_action(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    matched = matching_refresh(refresh, state=state) or {}
    if matched.get("dominant_invalidation", "") not in PROOF_RELATED_INVALIDATIONS:
        return ""
    return current_repair_action_instruction(repair_packet)


def selective_refresh_scope_label(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    matched = matching_refresh(refresh, state=state) or {}
    if matched.get("dominant_invalidation", "") not in PROOF_RELATED_INVALIDATIONS:
        return ""
    packet = repair_packet or {}
    continuation = packet.get("continuation_core", {})
    stale_subsurface_ids = list(continuation.get("next_step_subsurface_ids", [])) or list(
        packet.get("artifact_quality_summary", {}).get("stale_subsurface_ids", [])
    )
    if not stale_subsurface_ids:
        current_step_subsurface_id = continuation.get("current_step_subsurface_id", "")
        if current_step_subsurface_id:
            stale_subsurface_ids = [current_step_subsurface_id]
    labels: list[str] = []
    for subsurface_id in stale_subsurface_ids:
        label = humanize_token(subsurface_id)
        if label and label not in labels:
            labels.append(label)
    return ", ".join(labels)


def selective_refresh_reuse_label(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    matched = matching_refresh(refresh, state=state) or {}
    if matched.get("dominant_invalidation", "") not in PROOF_RELATED_INVALIDATIONS:
        return ""
    proof_bundle = state.get("proof_bundle", {})
    stale_sections = set(proof_bundle.get("missing_sections", [])) | set(proof_bundle.get("semantically_insufficient_sections", []))
    reusable: list[str] = []
    for section, details in proof_bundle.items():
        if section in {"status", "structural_status", "semantic_status", "missing_sections", "semantically_insufficient_sections", "semantic_next_safe_step"}:
            continue
        if section in stale_sections or not isinstance(details, dict):
            continue
        if not (details.get("semantically_sufficient", False) or details.get("structurally_complete", False)):
            continue
        label = humanize_token(section)
        if label and label not in reusable:
            reusable.append(label)
    return ", ".join(reusable)

def refresh_reuse_line(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    reusable = selective_refresh_reuse_label(refresh, state=state, repair_packet=repair_packet)
    if not reusable:
        return ""
    return f"reusable proof surfaces: {reusable}"


def refresh_scope_summary(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    scope = refresh_scope_line(refresh, state=state, repair_packet=repair_packet)
    reuse = refresh_reuse_line(refresh, state=state, repair_packet=repair_packet)
    if scope and reuse:
        return f"{scope}; {reuse}"
    return scope or reuse



def change_impact_guidance(refresh: dict | None, *, state: dict, repair_packet: dict | None = None) -> dict[str, str]:
    matched = matching_refresh(refresh, state=state)
    if not matched:
        return {}
    guidance = dict(REFRESH_CHANGE_IMPACT.get(matched.get("dominant_invalidation", ""), {}))
    if not guidance:
        return {}
    repair_action = selective_refresh_repair_action(refresh, state=state, repair_packet=repair_packet)
    repair_focus = current_repair_focus_summary(repair_packet)
    if repair_action:
        guidance["action"] = f"{repair_action} Then rerun synrail check."
        if repair_focus:
            guidance["diagnosis"] = f"Repair only this stale proof surface before trusting closure again: {repair_focus}."
    return guidance


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


def technical_lines(*, state: dict, report: dict, repair_packet: dict | None, checkpoint: dict | None, refresh: dict | None) -> list[str]:
    packet = repair_packet or {}
    continuation = packet.get("continuation_core", {})
    matched_refresh = matching_refresh(refresh, state=state) or {}
    return [
        f"state={state.get('state', '')}",
        f"result={report.get('result', '')}",
        f"stopping_stage={report.get('stopping_stage', '')}",
        f"reason={report.get('reason', '')}",
        f"closure_status={state.get('closure', {}).get('status', '')}",
        f"proof_bundle_status={state.get('proof_bundle', {}).get('status', '')}",
        f"dominant_invalidation={matched_refresh.get('dominant_invalidation', '')}",
        f"invalidations={','.join(matched_refresh.get('invalidations', []))}",
        f"repair_termination_reason={report.get('repair_termination_reason', '') or packet.get('repair_termination', {}).get('reason', '')}",
        f"current_step_id={continuation.get('current_step_id', '') or packet.get('repair_history', {}).get('current_step_id', '')}",
        f"next_safe_step={report.get('next_safe_step', '') or state.get('next_safe_step', '')}",
        f"checkpoint_restore_available={checkpoint_restore_available(checkpoint, state=state)}",
        f"bootstrap_provenance_reason={state.get('integrity', {}).get('bootstrap_provenance_reason', '')}",
    ]


def maybe_override_summary(summary: str, diagnosis: str, *, refresh: dict | None, state: dict, repair_packet: dict | None) -> tuple[str, str]:
    guidance = change_impact_guidance(refresh, state=state, repair_packet=repair_packet)
    if not guidance:
        return summary, diagnosis
    return guidance.get("summary", summary), guidance.get("diagnosis", diagnosis)


def maybe_override_next_step(what_to_do_next: str, *, refresh: dict | None, state: dict, repair_packet: dict | None) -> str:
    guidance = change_impact_guidance(refresh, state=state, repair_packet=repair_packet)
    if not guidance:
        return what_to_do_next
    return guidance.get("action", what_to_do_next)


def maybe_override_action_now(action_now: str, *, refresh: dict | None, state: dict, next_command: str, repair_packet: dict | None) -> str:
    guidance = change_impact_guidance(refresh, state=state, repair_packet=repair_packet)
    if not guidance:
        return action_now
    if next_command in {"", "synrail check"}:
        return guidance.get("action", action_now)
    return action_now


def dominant_invalidation_text(refresh: dict | None, *, state: dict) -> str:
    matched_refresh = matching_refresh(refresh, state=state) or {}
    return humanize_token(matched_refresh.get("dominant_invalidation", ""))


def invalidation_scope_text(refresh: dict | None, *, state: dict) -> str:
    matched_refresh = matching_refresh(refresh, state=state) or {}
    invalidations = list(matched_refresh.get("invalidations", []))
    if not invalidations:
        return ""
    return ", ".join(humanize_token(value) for value in invalidations)


def invalidation_focus_line(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    guidance = change_impact_guidance(refresh, state=state, repair_packet=repair_packet)
    if not guidance:
        return ""
    return guidance.get("action", "")


def refresh_focus_line(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    dominant = dominant_invalidation_text(refresh, state=state)
    if not dominant:
        return ""
    repair_focus = current_repair_focus_summary(repair_packet)
    if repair_focus and selective_refresh_repair_action(refresh, state=state, repair_packet=repair_packet):
        return f"refresh change impact: {dominant}; repair target: {repair_focus}"
    return f"refresh change impact: {dominant}"


def refresh_scope_line(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    selective_scope = selective_refresh_scope_label(refresh, state=state, repair_packet=repair_packet)
    if selective_scope:
        return f"applicable invalidations: {selective_scope}"
    scope = invalidation_scope_text(refresh, state=state)
    if not scope:
        return ""
    return f"applicable invalidations: {scope}"


def refresh_focus_summary(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    refresh_focus = refresh_focus_line(refresh, state=state, repair_packet=repair_packet)
    repair_focus = current_repair_focus_summary(repair_packet)
    if refresh_focus and repair_focus and "repair target:" not in refresh_focus:
        return f"{refresh_focus}; repair target: {repair_focus}"
    if refresh_focus:
        return refresh_focus
    return repair_focus


def refresh_current_step_action(refresh: dict | None, *, state: dict, repair_packet: dict | None) -> str:
    refresh_action = invalidation_focus_line(refresh, state=state, repair_packet=repair_packet)
    repair_action = current_repair_action_instruction(repair_packet)
    if refresh_action:
        return refresh_action
    return repair_action


def refresh_next_safe_step(refresh: dict | None, *, state: dict, report: dict) -> str:
    matched_refresh = matching_refresh(refresh, state=state) or {}
    return matched_refresh.get("next_safe_step", "") or report.get("next_safe_step", "") or state.get("next_safe_step", "")


def current_repair_focus_summary(repair_packet: dict | None) -> str:
    continuation = (repair_packet or {}).get("continuation_core", {})
    return focused_repair_summary(
        current_step_id=continuation.get("current_step_id", ""),
        current_step_subsurface_id=continuation.get("current_step_subsurface_id", ""),
        current_step_target_path=continuation.get("current_step_target_path", ""),
    )


def current_repair_action_instruction(repair_packet: dict | None) -> str:
    continuation = (repair_packet or {}).get("continuation_core", {})
    return focused_repair_action_instruction(
        current_step_id=continuation.get("current_step_id", ""),
        current_step_subsurface_id=continuation.get("current_step_subsurface_id", ""),
        current_step_target_path=continuation.get("current_step_target_path", ""),
    )


SEMANTIC_SECTION_HINTS = {
    "modified_files": "record the actual changed files in the final result artifact",
    "scope_alignment": "keep the implementation inside the requested additive scope and remove unrelated adjacent rewrites or spacing tweaks",
    "presentation_alignment": "keep the newly added surface visually plain and remove extra emphasis styling unless the task asked for it",
    "diff_provenance": "prove the patch on the changed files with a patch-shaped git_diff or a structured diff_provenance record",
    "verification_corroboration": "tie acceptance to explicit local verification evidence: either structured diff_provenance or a labeled scenario Command plus Observed or Result record, not prose-only proof",
    "readback": "record a concrete readback naming actual file paths, function names, or line contents from the changed surface — do not paraphrase the task description",
    "scenario_proof": "record a scenario-proof with a labeled Command and Observed or Result line, plus explicit pass/fail — do not just restate the task",
    "artifact_identity": "restore baseline, execution surface, prompt, and task identity values for this run",
    "cleanup_status": "record a successful cleanup status for the execution surface",
}


def thin_section_guidance(state: dict) -> list[str]:
    guidance: list[str] = []
    for section in state.get("proof_bundle", {}).get("semantically_insufficient_sections", []):
        guidance.append(f"{section}: {SEMANTIC_SECTION_HINTS.get(section, humanize_token(section))}")
    return guidance


def action_now_text(*, next_command: str, outcome_class: str, report: dict, repair_packet: dict | None) -> str:
    focused_action = current_repair_action_instruction(repair_packet)
    if next_command == "synrail check" and focused_action:
        lowered = focused_action[0].lower() + focused_action[1:].rstrip(".")
        return f"Fix the issue shown below: {lowered}. Then rerun synrail check."
    if next_command == "synrail refresh-acceptance":
        return "Run synrail refresh-acceptance."
    if next_command == "synrail start":
        return "Run synrail start to restart this contour in controlled mode."
    if next_command:
        return f"Run {next_command}."
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "REMOTE_TARGET_UNSUPPORTED":
        return "Move this contour onto a local trusted worktree before retrying."
    if outcome_class in {"NON_GREEN", "NON_RESUMABLE"} and continuation_arbiter_unresolved(repair_packet):
        return "Restore a verified fallback or restart from a clearer continuation boundary."
    return ""


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
        return "Replace the broken final result or proof inputs, then rerun synrail check."
    if outcome_class == "PROOF_THIN":
        return "Strengthen only the thin proof sections shown above, then rerun synrail check."
    if outcome_class == "PROOF_PARTIAL":
        return "Add the missing proof inputs, then rerun synrail check."
    if outcome_class == "REPAIR_STOP":
        return "Stop replaying this contour. Restore a verified restore point or start a new run."
    if outcome_class == "SCOPE_VIOLATION":
        if "dirty-surface unsafe" in failure_classes:
            return "Move back to a clean or clearly verified-safe workspace before continuing."
        return "Restore the original task request or target before continuing."
    if outcome_class == "DOCTOR_BLOCKED":
        if has_doctor_coverage_block(doctor):
            return "Treat this doctor as bounded for now. Close the agreed missing fail modes before trusting readiness."
        return "Repair readiness first, then rerun synrail check."
    if outcome_class in {"NON_GREEN", "NON_RESUMABLE"} and continuation_arbiter_unresolved(repair_packet):
        return "Do not assume resume is safe yet. Restore a verified fallback or rerun from a clearer starting point."
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "CONTINUATION_INPUTS_MISSING":
        return "Finish the current bounded repair, then rerun synrail check."
    if outcome_class == "NON_GREEN" and report.get("reason", "") in {"ACCEPTANCE_CRITERIA_STALE", "ACCEPTANCE_CRITERIA_INVALID"}:
        return "Run synrail refresh-acceptance, then rerun synrail check."
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED":
        return "Start this run through synrail start before trusting any proof or acceptance."
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "REMOTE_TARGET_UNSUPPORTED":
        return "Rerun this alpha lane on a local trusted worktree. The remote or ops contour is not supported yet."
    return human_safe_step_text(raw_next_step)


def build_record(*, state: dict, report: dict, mode: str, repair_packet: dict | None = None, doctor: dict | None = None, checkpoint: dict | None = None, recovery: dict | None = None, refresh: dict | None = None) -> dict:
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
    summary, diagnosis = maybe_override_summary(summary, diagnosis, refresh=refresh, state=state, repair_packet=repair_packet)
    suggested_command = {
        "ACCEPTED": "no next command required",
        "NON_RESUMABLE": "synrail restore or start a new run",
        "CLOSURE_REJECTED": "synrail restore or repair and rerun closure",
        "PROOF_INVALID": "fix only the invalid proof surface named above, then synrail check",
        "PROOF_THIN": "strengthen only the thin proof evidence named above, then synrail check",
        "PROOF_PARTIAL": "supply only the missing proof inputs named above, then synrail check",
        "REPAIR_STOP": "synrail restore or start a new run",
        "SCOPE_VIOLATION": "repair the workspace or intended task target, then synrail check",
        "DOCTOR_BLOCKED": "repair readiness, then synrail check",
        "NON_GREEN": "inspect the blocker, then continue the bounded repair step",
    }[outcome_class]
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        suggested_command = "restore the original task request, then run synrail check"
    if outcome_class == "SCOPE_VIOLATION" and restore_available:
        failure_classes = list((doctor or {}).get("blocking_failure_classes", []))
        if "dirty-surface unsafe" in failure_classes:
            suggested_command = "synrail restore or move to a clean in-scope surface, then synrail check"
    if outcome_class == "NON_GREEN" and report.get("reason", "") == "CONTINUATION_INPUTS_MISSING":
        suggested_command = "finish only the current bounded repair, then synrail check"
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
    thin_guidance = thin_section_guidance(state) if outcome_class == "PROOF_THIN" else []
    if outcome_class == "ACCEPTED":
        next_step = "No repair step is required."
    next_command = ""
    restore_command = ""
    if outcome_class in {"PROOF_INVALID", "PROOF_THIN", "PROOF_PARTIAL", "SCOPE_VIOLATION", "DOCTOR_BLOCKED", "NON_GREEN"} and can_resume:
        next_command = "synrail check"
    if outcome_class == "NON_RESUMABLE" and non_resumable_forward_boundary(report=report, repair_packet=repair_packet):
        next_command = "synrail check"
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
    what_to_do_next = human_next_step(
        outcome_class=outcome_class,
        raw_next_step=next_step,
        report=report,
        repair_packet=repair_packet,
        doctor=doctor,
    )
    what_to_do_next = maybe_override_next_step(what_to_do_next, refresh=refresh, state=state, repair_packet=repair_packet)
    action_now = maybe_override_action_now(
        action_now_text(
            next_command=next_command,
            outcome_class=outcome_class,
            report=report,
            repair_packet=repair_packet,
        ),
        refresh=refresh,
        state=state,
        next_command=next_command,
        repair_packet=repair_packet,
    )
    focused_summary = refresh_focus_summary(refresh, state=state, repair_packet=repair_packet)
    current_step_action = refresh_current_step_action(refresh, state=state, repair_packet=repair_packet)
    if not focused_summary:
        focused_summary = current_repair_focus_summary(repair_packet)
    if not current_step_action:
        current_step_action = current_repair_action_instruction(repair_packet)
    next_step = refresh_next_safe_step(refresh, state=state, report=report)
    if outcome_class == "ACCEPTED":
        next_step = "No repair step is required."
    fields = {
        "change_impact_focus": refresh_focus_line(refresh, state=state, repair_packet=repair_packet),
        "change_impact_scope": refresh_scope_summary(refresh, state=state, repair_packet=repair_packet),
    }
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
        "action_now": action_now,
        "current_step_action_instruction": current_step_action,
        "focused_repair_summary": focused_summary,
        "thin_section_guidance": thin_guidance,
        "resume_available": can_resume,
        "next_command": next_command,
        "restore_command": restore_command,
        "next_step": next_step,
        "restore_available": restore_available,
        "checkpoint_id": checkpoint.get("checkpoint_id", "") if checkpoint else "",
        "recovery_primary_action": matching.get("primary_action", "") if matching else "",
        "recovery_operator_instructions": list(matching.get("operator_instructions", [])) if matching else [],
        "suggested_command": suggested_command,
        "change_impact_focus": fields["change_impact_focus"],
        "change_impact_scope": fields["change_impact_scope"],
        "technical_lines": technical_lines(state=state, report=report, repair_packet=repair_packet, checkpoint=checkpoint, refresh=refresh) if mode == "dev" else [],
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
    parser.add_argument("--refresh-file")
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
        refresh=load_json(Path(args.refresh_file)) if args.refresh_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "outcome_class": record["outcome_class"], "restore_available": record["restore_available"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
