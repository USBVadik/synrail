#!/usr/bin/env python3
"""Machine-readable repair handoff generator for Synrail continuation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


INPUT_SPECS = {
    "prompt_identity": {
        "kind": "string",
        "cli_flag": "--prompt-identity",
        "description": "restore the prompt identity used for continuation",
        "required_value": "",
    },
    "task_identity": {
        "kind": "string",
        "cli_flag": "--task-identity",
        "description": "restore the exact task identity used for continuation",
        "required_value": "",
    },
    "target_identity_file": {
        "kind": "file",
        "cli_flag": "--target-identity-file",
        "description": "supply target identity evidence for readiness verification",
        "required_value": "",
    },
    "clean_surface_confirmation": {
        "kind": "flag",
        "cli_flag": "--clean-surface",
        "description": "confirm continuation is running on a clean or explicitly safe execution surface",
        "required_value": "true",
    },
    "artifact_path": {
        "kind": "file",
        "cli_flag": "--artifact-path",
        "description": "restore a viable machine-readable artifact path for readiness",
        "required_value": "",
    },
    "helper_path": {
        "kind": "file",
        "cli_flag": "--helper-path",
        "description": "supply the helper entrypoint needed for readiness verification",
        "required_value": "",
    },
    "credential_surface": {
        "kind": "runtime_input",
        "cli_flag": "--credentials-ok / --credential-env",
        "description": "restore the credential surface needed for continuation readiness",
        "required_value": "",
    },
    "final_result": {
        "kind": "file",
        "cli_flag": "--final-result",
        "description": "supply the final result artifact for bundle repair or closure continuation",
        "required_value": "",
    },
    "readback": {
        "kind": "file",
        "cli_flag": "--readback",
        "description": "supply readback from the changed sections on the attested surface",
        "required_value": "",
    },
    "scenario_proof": {
        "kind": "file",
        "cli_flag": "--scenario-proof",
        "description": "supply scenario proof for the continuation bundle",
        "required_value": "",
    },
    "refresh_recovery_complete": {
        "kind": "enum",
        "cli_flag": "--refresh-recovery-status",
        "description": "mark recovery as complete before resuming closure acceptance",
        "required_value": "COMPLETE",
    },
    "refresh_reverification_complete": {
        "kind": "flag",
        "cli_flag": "--refresh-reverification-complete",
        "description": "confirm recovery reverification is complete before refresh reconciliation",
        "required_value": "true",
    },
}


DOCTOR_FAILURE_INPUTS = {
    "baseline-identity ambiguous": ["target_identity_file"],
    "dirty-surface unsafe": ["clean_surface_confirmation"],
    "helper-integrity unknown": ["helper_path"],
    "credential-surface missing": ["credential_surface"],
    "artifact-viability missing": ["artifact_path"],
    "exact-prompt-artifact-missing": ["prompt_identity", "task_identity"],
}

PROOF_SECTION_INPUTS = {
    "readback": "readback",
    "scenario_proof": "scenario_proof",
}

STEP_ARTIFACTS = {
    "restore_readiness_truth": ["readiness_surface"],
    "repair_final_result_artifact": ["final_result_artifact"],
    "complete_missing_proof_sections": ["supporting_proof_artifacts"],
    "rebuild_proof_bundle": ["proof_bundle_snapshot"],
    "complete_recovery_reverification": ["recovery_reverification_surface"],
    "run_refresh_reconciliation": ["closure_refresh_surface"],
    "rerun_closure": ["closure_verdict_surface"],
    "switch_to_lighter_mode": ["mode_selection_receipt"],
    "continue_forward_orchestration": ["runtime_entrypoint_state"],
    "start_new_run": ["terminal_run_state"],
    "inspect_runtime_state": ["runtime_state"],
}

STEP_PRESSURES = {
    "restore_readiness_truth": ["DOCTOR_BLOCKED"],
    "repair_final_result_artifact": ["INVALID_PROOF"],
    "complete_missing_proof_sections": ["PARTIAL_PROOF"],
    "rebuild_proof_bundle": ["INVALID_PROOF", "PARTIAL_PROOF"],
    "complete_recovery_reverification": ["RECOVERY_PENDING"],
    "run_refresh_reconciliation": ["RECOVERY_PENDING"],
    "rerun_closure": ["DOCTOR_BLOCKED", "INVALID_PROOF", "PARTIAL_PROOF", "RECOVERY_PENDING"],
    "switch_to_lighter_mode": ["SELECTION_BLOCKED"],
    "continue_forward_orchestration": ["FRESH_ORCHESTRATION"],
    "start_new_run": ["TERMINAL_STATE", "TERMINAL_ACCEPTED", "TERMINAL_REJECTED"],
    "inspect_runtime_state": [],
}

REPAIRABLE_PRESSURE_ORDER = [
    "DOCTOR_BLOCKED",
    "INVALID_PROOF",
    "PARTIAL_PROOF",
    "RECOVERY_PENDING",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def add_unique(target: list[str], value: str) -> None:
    if value not in target:
        target.append(value)


def make_subsurface(subsurface_id: str, *, status: str, mapped_inputs: list[str], why: str) -> dict:
    return {
        "subsurface_id": subsurface_id,
        "status": status,
        "mapped_inputs": list(mapped_inputs),
        "why": why,
    }


def make_hint(
    artifact_id: str,
    *,
    quality: str,
    still_stale_parts: list[str],
    mapped_inputs: list[str],
    repair_step: str,
    why: str,
    stale_subsurfaces: list[dict] | None = None,
) -> dict:
    return {
        "artifact_id": artifact_id,
        "quality": quality,
        "still_stale_parts": list(still_stale_parts),
        "mapped_inputs": list(mapped_inputs),
        "repair_step": repair_step,
        "why": why,
        "stale_subsurfaces": list(stale_subsurfaces or []),
    }


def merged_missing_sections(state: dict) -> list[str]:
    missing_sections = list(state.get("proof_bundle", {}).get("missing_sections", []))
    for section in state.get("closure", {}).get("missing_sections", []):
        if section not in missing_sections:
            missing_sections.append(section)
    return missing_sections


def build_required_input_ids(repair_policy: dict, artifact_quality_hints: list[dict]) -> list[str]:
    required: list[str] = []
    ready_steps = set(repair_policy.get("ready_now_step_ids", []))
    for hint in artifact_quality_hints:
        if hint["repair_step"] not in ready_steps:
            continue
        for input_id in hint.get("mapped_inputs", []):
            add_unique(required, input_id)
    return required


def build_runtime_defaults(state: dict, required_inputs: list[str]) -> dict:
    defaults = {
        "refresh_event_type": "",
        "refresh_use_bundle": False,
        "refresh_use_closure": False,
    }
    if "refresh_recovery_complete" in required_inputs or "refresh_reverification_complete" in required_inputs:
        defaults["refresh_event_type"] = "RECOVERY_EVENT"
        defaults["refresh_use_bundle"] = True
        defaults["refresh_use_closure"] = True
    return defaults


def collect_active_pressures(state: dict) -> list[str]:
    pressures: list[str] = []
    if state.get("state") in {"INITIALIZED", "TARGET_SURFACE_ATTESTED", "READY"}:
        add_unique(pressures, "FRESH_ORCHESTRATION")
    if state.get("state") == "CLOSURE_ACCEPTED" or state.get("closure", {}).get("status") == "ACCEPTED":
        add_unique(pressures, "TERMINAL_ACCEPTED")
        add_unique(pressures, "TERMINAL_STATE")
    elif state.get("state") == "CLOSURE_REJECTED" or state.get("closure", {}).get("status") == "REJECTED":
        add_unique(pressures, "TERMINAL_REJECTED")
        add_unique(pressures, "TERMINAL_STATE")
    if state.get("closure", {}).get("blocking_reason") == "MODE_SELECTION_NOT_GOVERNED":
        add_unique(pressures, "SELECTION_BLOCKED")
    if state.get("state") == "DOCTOR_BLOCKED" or state.get("doctor", {}).get("status") == "FAIL" or state.get("doctor", {}).get("blocking_failure_classes"):
        add_unique(pressures, "DOCTOR_BLOCKED")
    if (
        state.get("state") == "PROOF_BUNDLE_INVALID"
        or state.get("proof_bundle", {}).get("status") == "INVALID"
        or state.get("closure", {}).get("blocking_reason") in {"ARTIFACT_BUNDLE_MISSING", "INVALID_PROOF_BUNDLE"}
    ):
        add_unique(pressures, "INVALID_PROOF")
    if (
        state.get("state") == "PROOF_BUNDLE_PARTIAL"
        or state.get("proof_bundle", {}).get("status") == "PARTIAL"
        or state.get("proof_bundle", {}).get("missing_sections")
        or state.get("closure", {}).get("blocking_reason") == "MISSING_PROOF_SECTIONS"
    ):
        add_unique(pressures, "PARTIAL_PROOF")
    if (
        state.get("state") == "RECOVERY_PENDING"
        or state.get("recovery", {}).get("status") == "PENDING"
        or state.get("closure", {}).get("blocking_reason") == "RECOVERY_REVERIFICATION_INCOMPLETE"
    ):
        add_unique(pressures, "RECOVERY_PENDING")
    return pressures


def continuation_allowed(state: dict) -> bool:
    if state.get("state") in {"INITIALIZED", "TARGET_SURFACE_ATTESTED", "READY"}:
        return False
    if state.get("state") in {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}:
        return False
    if state.get("closure", {}).get("status") == "ACCEPTED":
        return False
    if state.get("closure", {}).get("blocking_reason") == "MODE_SELECTION_NOT_GOVERNED":
        return False
    return True


def resumability_family(state: dict, active_pressures: list[str], allowed: bool) -> str:
    if "FRESH_ORCHESTRATION" in active_pressures:
        return "NOT_RESUMABLE_FRESH_ORCHESTRATION"
    if state.get("state") == "CLOSURE_ACCEPTED" or state.get("closure", {}).get("status") == "ACCEPTED":
        return "NOT_RESUMABLE_TERMINAL_ACCEPTED"
    if state.get("state") == "CLOSURE_REJECTED" or state.get("closure", {}).get("status") == "REJECTED":
        return "NOT_RESUMABLE_TERMINAL_REJECTED"
    if "TERMINAL_STATE" in active_pressures:
        return "NOT_RESUMABLE_TERMINAL"
    if "SELECTION_BLOCKED" in active_pressures:
        return "NOT_RESUMABLE_SELECTION_BLOCKED"
    if not allowed:
        return "NOT_RESUMABLE_UNKNOWN"

    repairable = [pressure for pressure in REPAIRABLE_PRESSURE_ORDER if pressure in active_pressures]
    if len(repairable) > 1:
        return "REPAIRABLE_COMPOUND"
    if "DOCTOR_BLOCKED" in repairable:
        return "REPAIRABLE_DOCTOR_BLOCKED"
    if "INVALID_PROOF" in repairable:
        return "REPAIRABLE_INVALID_PROOF"
    if "PARTIAL_PROOF" in repairable:
        return "REPAIRABLE_PARTIAL_PROOF"
    if "RECOVERY_PENDING" in repairable:
        return "REPAIRABLE_RECOVERY_PENDING"
    return "REPAIRABLE_OTHER"


def recommended_repair_order(active_pressures: list[str], family: str) -> list[str]:
    if family == "NOT_RESUMABLE_FRESH_ORCHESTRATION":
        return ["continue_forward_orchestration"]
    if family == "NOT_RESUMABLE_SELECTION_BLOCKED":
        return ["switch_to_lighter_mode"]
    if family in {"NOT_RESUMABLE_TERMINAL_ACCEPTED", "NOT_RESUMABLE_TERMINAL_REJECTED", "NOT_RESUMABLE_TERMINAL"}:
        return ["start_new_run"]
    if family == "NOT_RESUMABLE_UNKNOWN":
        return ["inspect_runtime_state"]

    steps: list[str] = []
    if "DOCTOR_BLOCKED" in active_pressures:
        add_unique(steps, "restore_readiness_truth")
    if "INVALID_PROOF" in active_pressures:
        add_unique(steps, "repair_final_result_artifact")
    if "PARTIAL_PROOF" in active_pressures:
        add_unique(steps, "complete_missing_proof_sections")
    if "INVALID_PROOF" in active_pressures or "PARTIAL_PROOF" in active_pressures:
        add_unique(steps, "rebuild_proof_bundle")
    if "RECOVERY_PENDING" in active_pressures:
        add_unique(steps, "complete_recovery_reverification")
        add_unique(steps, "run_refresh_reconciliation")
    add_unique(steps, "rerun_closure")
    return steps


def build_artifact_quality_hints(state: dict) -> list[dict]:
    hints: list[dict] = []

    readiness_parts: list[str] = []
    readiness_inputs: list[str] = []
    readiness_why: list[str] = []
    readiness_subsurfaces: list[dict] = []
    for failure_class in state.get("doctor", {}).get("blocking_failure_classes", []):
        mapped_inputs = DOCTOR_FAILURE_INPUTS.get(failure_class, [])
        for input_id in mapped_inputs:
            add_unique(readiness_inputs, input_id)
        if failure_class == "baseline-identity ambiguous":
            add_unique(readiness_parts, "target_identity_record")
            readiness_subsurfaces.append(
                make_subsurface(
                    "target_identity_record",
                    status="STALE",
                    mapped_inputs=["target_identity_file"],
                    why="target identity evidence is missing or does not match the expected target surface",
                )
            )
        elif failure_class == "dirty-surface unsafe":
            add_unique(readiness_parts, "clean_execution_surface_record")
            readiness_subsurfaces.append(
                make_subsurface(
                    "clean_execution_surface_record",
                    status="STALE",
                    mapped_inputs=["clean_surface_confirmation"],
                    why="the execution surface still looks dirty or not explicitly safe for continuation",
                )
            )
        elif failure_class == "helper-integrity unknown":
            add_unique(readiness_parts, "helper_entrypoint_record")
            readiness_subsurfaces.append(
                make_subsurface(
                    "helper_entrypoint_record",
                    status="STALE",
                    mapped_inputs=["helper_path"],
                    why="the helper entrypoint required for readiness is still unresolved",
                )
            )
        elif failure_class == "credential-surface missing":
            add_unique(readiness_parts, "credential_surface_record")
            readiness_subsurfaces.append(
                make_subsurface(
                    "credential_surface_record",
                    status="STALE",
                    mapped_inputs=["credential_surface"],
                    why="the credential surface is still missing or points at an invalid path",
                )
            )
        elif failure_class == "artifact-viability missing":
            add_unique(readiness_parts, "artifact_path_record")
            readiness_subsurfaces.append(
                make_subsurface(
                    "artifact_path_record",
                    status="STALE",
                    mapped_inputs=["artifact_path"],
                    why="the artifact viability surface still lacks a trusted machine-readable path",
                )
            )
        elif failure_class == "exact-prompt-artifact-missing":
            add_unique(readiness_parts, "prompt_identity_record")
            add_unique(readiness_parts, "task_identity_record")
            readiness_subsurfaces.append(
                make_subsurface(
                    "prompt_identity_record",
                    status="STALE",
                    mapped_inputs=["prompt_identity"],
                    why="the continuation prompt identity is still missing or unresolved",
                )
            )
            readiness_subsurfaces.append(
                make_subsurface(
                    "task_identity_record",
                    status="STALE",
                    mapped_inputs=["task_identity"],
                    why="the continuation task identity is still missing or unresolved",
                )
            )
        add_unique(readiness_why, failure_class)
    if readiness_parts:
        hints.append(
            make_hint(
                "readiness_surface",
                quality="STALE",
                still_stale_parts=readiness_parts,
                mapped_inputs=readiness_inputs,
                repair_step="restore_readiness_truth",
                why="doctor still sees stale readiness evidence: " + ", ".join(readiness_why),
                stale_subsurfaces=readiness_subsurfaces,
            )
        )

    missing_sections = merged_missing_sections(state)
    final_result_parts = [part for part in ["final_result_payload", "diff_provenance_record", "cleanup_status_record"] if False]
    final_result_subsurfaces: list[dict] = []
    if "final_result" in missing_sections or state.get("closure", {}).get("blocking_reason") in {"ARTIFACT_BUNDLE_MISSING", "INVALID_PROOF_BUNDLE"}:
        add_unique(final_result_parts, "final_result_payload")
        final_result_subsurfaces.append(
            make_subsurface(
                "final_result_payload",
                status="STALE",
                mapped_inputs=["final_result"],
                why="the final result artifact is missing, empty, or not yet trusted for bundle repair",
            )
        )
    if "diff_provenance" in missing_sections:
        add_unique(final_result_parts, "diff_provenance_record")
        final_result_subsurfaces.append(
            make_subsurface(
                "diff_provenance_record",
                status="STALE",
                mapped_inputs=["final_result"],
                why="diff provenance still cannot be reconstructed from the current final result artifact",
            )
        )
    if "cleanup_status" in missing_sections:
        add_unique(final_result_parts, "cleanup_status_record")
        final_result_subsurfaces.append(
            make_subsurface(
                "cleanup_status_record",
                status="STALE",
                mapped_inputs=["final_result"],
                why="cleanup status still cannot be trusted from the current final result artifact",
            )
        )
    if final_result_parts:
        hints.append(
            make_hint(
                "final_result_artifact",
                quality="STALE",
                still_stale_parts=final_result_parts,
                mapped_inputs=["final_result"],
                repair_step="repair_final_result_artifact",
                why="the final-result truth surface is still stale or incomplete",
                stale_subsurfaces=final_result_subsurfaces,
            )
        )

    supporting_parts: list[str] = []
    supporting_subsurfaces: list[dict] = []
    if "readback" in missing_sections:
        add_unique(supporting_parts, "readback_record")
        supporting_subsurfaces.append(
            make_subsurface(
                "readback_record",
                status="STALE",
                mapped_inputs=["readback"],
                why="the readback surface from changed sections is still missing",
            )
        )
    if "scenario_proof" in missing_sections:
        add_unique(supporting_parts, "scenario_proof_record")
        supporting_subsurfaces.append(
            make_subsurface(
                "scenario_proof_record",
                status="STALE",
                mapped_inputs=["scenario_proof"],
                why="the scenario proof artifact is still missing",
            )
        )
    supporting_inputs = []
    if "readback_record" in supporting_parts:
        supporting_inputs.append("readback")
    if "scenario_proof_record" in supporting_parts:
        supporting_inputs.append("scenario_proof")
    if supporting_parts:
        hints.append(
            make_hint(
                "supporting_proof_artifacts",
                quality="STALE",
                still_stale_parts=supporting_parts,
                mapped_inputs=supporting_inputs,
                repair_step="complete_missing_proof_sections",
                why="supporting proof sections are still missing from the current bundle",
                stale_subsurfaces=supporting_subsurfaces,
            )
        )

    recovery = state.get("recovery", {})
    if recovery.get("status") == "PENDING":
        hints.append(
            make_hint(
                "recovery_reverification_surface",
                quality="STALE",
                still_stale_parts=[
                    "recovery_status_record",
                    "reverification_completion_record",
                ],
                mapped_inputs=["refresh_recovery_complete", "refresh_reverification_complete"],
                repair_step="complete_recovery_reverification",
                why="recovery was started but reverification has not been completed yet",
                stale_subsurfaces=[
                    make_subsurface(
                        "recovery_status_record",
                        status="STALE",
                        mapped_inputs=["refresh_recovery_complete"],
                        why="the recovery status is still pending rather than complete",
                    ),
                    make_subsurface(
                        "reverification_completion_record",
                        status="STALE",
                        mapped_inputs=["refresh_reverification_complete"],
                        why="the recovery reverification completion flag is still missing",
                    ),
                ],
            )
        )

    if state.get("closure", {}).get("blocking_reason") == "MODE_SELECTION_NOT_GOVERNED":
        hints.append(
            make_hint(
                "mode_selection_receipt",
                quality="NON_RESUMABLE",
                still_stale_parts=["selected_mode_policy_gate"],
                mapped_inputs=[],
                repair_step="switch_to_lighter_mode",
                why="the current selected mode explicitly keeps this run out of the governed continuation contour",
                stale_subsurfaces=[
                    make_subsurface(
                        "selected_mode_policy_gate",
                        status="NON_RESUMABLE",
                        mapped_inputs=[],
                        why="the recorded selection receipt routes this scenario away from governed continuation",
                    )
                ],
            )
        )

    if state.get("state") in {"INITIALIZED", "TARGET_SURFACE_ATTESTED", "READY"}:
        hints.append(
            make_hint(
                "runtime_entrypoint_state",
                quality="NON_RESUMABLE",
                still_stale_parts=["forward_orchestration_entrypoint"],
                mapped_inputs=[],
                repair_step="continue_forward_orchestration",
                why="this state still belongs to forward governed orchestration rather than named continuation",
                stale_subsurfaces=[
                    make_subsurface(
                        "forward_orchestration_entrypoint",
                        status="NON_RESUMABLE",
                        mapped_inputs=[],
                        why="the run has not yet entered a repairable continuation family, so `orchestrate` is the correct entrypoint rather than `resume`",
                    )
                ],
            )
        )

    if state.get("state") == "CLOSURE_ACCEPTED" or state.get("closure", {}).get("status") == "ACCEPTED":
        hints.append(
            make_hint(
                "terminal_run_state",
                quality="NON_RESUMABLE",
                still_stale_parts=["accepted_terminal_state"],
                mapped_inputs=[],
                repair_step="start_new_run",
                why="the current run is already accepted and continuation should yield to a new run",
                stale_subsurfaces=[
                    make_subsurface(
                        "accepted_terminal_state",
                        status="NON_RESUMABLE",
                        mapped_inputs=[],
                        why="the accepted closure state is terminal and should not be resumed",
                    )
                ],
            )
        )
    elif state.get("state") == "CLOSURE_REJECTED" or state.get("closure", {}).get("status") == "REJECTED":
        hints.append(
            make_hint(
                "terminal_run_state",
                quality="NON_RESUMABLE",
                still_stale_parts=["rejected_terminal_state"],
                mapped_inputs=[],
                repair_step="start_new_run",
                why="the current run is already rejected and continuation should yield to a new run",
                stale_subsurfaces=[
                    make_subsurface(
                        "rejected_terminal_state",
                        status="NON_RESUMABLE",
                        mapped_inputs=[],
                        why="the rejected closure state is terminal and should not be resumed",
                    )
                ],
            )
        )

    if not hints:
        hints.append(
            make_hint(
                "runtime_state",
                quality="STALE",
                still_stale_parts=["runtime_state_surface"],
                mapped_inputs=[],
                repair_step="inspect_runtime_state",
                why="the bounded runtime sees a resumable contour but does not have a narrower artifact-quality hint yet",
                stale_subsurfaces=[
                    make_subsurface(
                        "runtime_state_surface",
                        status="STALE",
                        mapped_inputs=[],
                        why="the runtime contour still needs inspection before a narrower stale artifact surface can be named",
                    )
                ],
            )
        )
    return hints


def build_repair_policy(resumability: dict, artifact_quality_hints: list[dict]) -> dict:
    steps: list[dict] = []
    ready_now_step_ids: list[str] = []
    step_to_inputs = {
        step_id: [] for step_id in resumability["recommended_repair_order"]
    }
    for hint in artifact_quality_hints:
        step_inputs = step_to_inputs.setdefault(hint["repair_step"], [])
        for input_id in hint.get("mapped_inputs", []):
            add_unique(step_inputs, input_id)

    ordered_ids = list(resumability["recommended_repair_order"])
    policy_type = "MULTI_STEP_REPAIR" if resumability["status"] == "REPAIRABLE" else "NON_RESUMABLE_NEXT_STEP"
    for index, step_id in enumerate(ordered_ids):
        if resumability["status"] == "REPAIRABLE":
            status = "READY_NOW" if index == 0 else "WAITING_ON_PREVIOUS_STEP"
        else:
            status = "TERMINAL_NEXT_STEP" if index == 0 else "NOT_AVAILABLE"
        if status == "READY_NOW":
            ready_now_step_ids.append(step_id)
        steps.append(
            {
                "step_id": step_id,
                "status": status,
                "required_inputs": list(step_to_inputs.get(step_id, [])),
                "repairs_artifacts": list(STEP_ARTIFACTS.get(step_id, [])),
                "resolves_pressures": [pressure for pressure in STEP_PRESSURES.get(step_id, []) if pressure in resumability["active_pressures"]],
                "why": {
                    "restore_readiness_truth": "doctor-blocked truth must be repaired before governed continuation can restart honestly",
                    "repair_final_result_artifact": "invalid final-result truth should be repaired before later proof or recovery steps run",
                    "complete_missing_proof_sections": "missing proof sections should be completed before bundle rebuild and closure recheck",
                    "rebuild_proof_bundle": "the bundle should be rebuilt only after the stale proof artifacts above are repaired",
                    "complete_recovery_reverification": "recovery should be completed before refresh reconciliation can restore closure acceptance",
                "run_refresh_reconciliation": "refresh reconciliation should only run once recovery reverification is complete",
                "rerun_closure": "closure should be rechecked only after earlier repair steps finish",
                "switch_to_lighter_mode": "this contour should follow the lighter selected mode instead of resuming governed execution",
                "continue_forward_orchestration": "this contour should continue through the forward governed path rather than the named continuation entrypoint",
                "start_new_run": "terminal state should yield to a new run rather than another resume attempt",
                "inspect_runtime_state": "runtime state should be inspected before the next continuation decision is made",
            }.get(step_id, "follow the bounded repair order before resuming"),
            }
        )
    return {
        "policy_type": policy_type,
        "next_step_id": ordered_ids[0] if ordered_ids else "",
        "ready_now_step_ids": ready_now_step_ids,
        "ordered_steps": steps,
    }


def resumability_explanation(family: str) -> str:
    return {
        "REPAIRABLE_DOCTOR_BLOCKED": "readiness failed early, but the contour can resume once the doctor inputs are repaired",
        "REPAIRABLE_INVALID_PROOF": "the proof surface is invalid, but continuation can resume once final-result truth is repaired",
        "REPAIRABLE_PARTIAL_PROOF": "the proof surface is partial, but continuation can resume once the missing proof sections are supplied",
        "REPAIRABLE_RECOVERY_PENDING": "recovery reverification is still pending, but continuation can resume once recovery is completed and refresh can reconcile closure",
        "REPAIRABLE_COMPOUND": "more than one repairable pressure is active, so continuation should follow the ordered repair sequence before closure is rechecked",
        "REPAIRABLE_OTHER": "the bounded runtime still treats this contour as repairable through the named resume path",
        "NOT_RESUMABLE_FRESH_ORCHESTRATION": "the run is still on the forward governed path, so continuation should use orchestrate rather than resume",
        "NOT_RESUMABLE_SELECTION_BLOCKED": "the governed contour should not resume because the current policy choice points to a lighter mode instead",
        "NOT_RESUMABLE_TERMINAL_ACCEPTED": "the run is already accepted, so continuation should stop and a new run should start instead",
        "NOT_RESUMABLE_TERMINAL_REJECTED": "the run is already rejected, so continuation should stop and a new run should start instead",
        "NOT_RESUMABLE_TERMINAL": "accepted or rejected terminal state should start a new run instead of resuming",
        "NOT_RESUMABLE_UNKNOWN": "the bounded runtime does not currently classify this state as resumable",
    }[family]


def build_resumability(state: dict) -> dict:
    allowed = continuation_allowed(state)
    active_pressures = collect_active_pressures(state)
    family = resumability_family(state, active_pressures, allowed)
    return {
        "status": "REPAIRABLE" if allowed else "NOT_RESUMABLE",
        "family": family,
        "active_pressures": active_pressures,
        "recommended_repair_order": recommended_repair_order(active_pressures, family),
        "requires_new_run": family in {"NOT_RESUMABLE_TERMINAL_ACCEPTED", "NOT_RESUMABLE_TERMINAL_REJECTED", "NOT_RESUMABLE_TERMINAL"},
        "explanation": resumability_explanation(family),
    }


def build_required_inputs(required_input_ids: list[str]) -> list[dict]:
    required_inputs = []
    for input_id in required_input_ids:
        spec = INPUT_SPECS[input_id]
        required_inputs.append(
            {
                "input_id": input_id,
                "kind": spec["kind"],
                "cli_flag": spec["cli_flag"],
                "description": spec["description"],
                "required_value": spec["required_value"],
            }
        )
    return required_inputs


def build_repair_handoff(state: dict) -> dict:
    allowed = continuation_allowed(state)
    resumability = build_resumability(state)
    artifact_quality_hints = build_artifact_quality_hints(state)
    repair_policy = build_repair_policy(resumability, artifact_quality_hints)
    required_input_ids = build_required_input_ids(repair_policy, artifact_quality_hints)
    return {
        "schema_version": "repair_handoff_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "from_state": state["state"],
        "closure_status": state["closure"]["status"],
        "blocking_reason": state["closure"]["blocking_reason"],
        "continuation_allowed": allowed,
        "continuation_entrypoint": "resume" if allowed else "",
        "resumability": resumability,
        "repair_policy": repair_policy,
        "artifact_quality_hints": artifact_quality_hints,
        "required_inputs": build_required_inputs(required_input_ids),
        "runtime_defaults": build_runtime_defaults(state, required_input_ids),
        "next_safe_step": state["next_safe_step"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-repair-handoff-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    handoff = build_repair_handoff(load_json(Path(args.state_file)))
    save_json(Path(args.output), handoff)
    print(
        json.dumps(
            {
                "result": "OK",
                "continuation_allowed": handoff["continuation_allowed"],
                "resumability_status": handoff["resumability"]["status"],
                "resumability_family": handoff["resumability"]["family"],
                "required_inputs": [item["input_id"] for item in handoff["required_inputs"]],
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
