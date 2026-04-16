#!/usr/bin/env python3
"""Machine-readable repair packet builder for Synrail continuation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_repair_handoff_v0 import (
        DOCTOR_FAILURE_INPUTS,
        build_repair_handoff,
        build_resumability,
        collect_active_pressures,
        load_json as load_state_json,
    )
    from .synrail_continuation_arbiter_v0 import build_record as build_continuation_arbiter
    from .synrail_repair_focus_v0 import focused_repair_surface, focused_repair_summary
except ImportError:
    from synrail_repair_handoff_v0 import (
        DOCTOR_FAILURE_INPUTS,
        build_repair_handoff,
        build_resumability,
        collect_active_pressures,
        load_json as load_state_json,
    )
    from synrail_continuation_arbiter_v0 import build_record as build_continuation_arbiter
    from synrail_repair_focus_v0 import focused_repair_surface, focused_repair_summary

MAX_REPAIR_ATTEMPTS = 3
NO_PROGRESS_WINDOW = 2
SOURCE_OF_TRUTH_PRECEDENCE = [
    "state_file",
    "repair_packet",
    "repair_receipt",
    "repair_history_chain",
]


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def scalar_arg(current: str | None, fallback: str) -> str:
    return current if current not in {None, ""} else fallback


def bool_arg(current: bool | None, fallback: bool) -> bool:
    """Merge a boolean flag with a fallback from a previous packet.

    When *current* is ``None`` (flag not passed on the CLI), inherit *fallback*.
    When *current* is ``True`` or ``False`` (explicitly provided), use it.
    This prevents previously-True values from being irrevocable.
    """
    if current is None:
        return fallback
    return current


def merge_previous_packet_context(args: argparse.Namespace, previous_packet: dict) -> argparse.Namespace:
    resume_context = dict(previous_packet.get("resume_context", {}))
    repair_inputs = dict(previous_packet.get("repair_inputs", {}))
    continuation_plan = dict(previous_packet.get("continuation_plan", {}))
    output_defaults = dict(previous_packet.get("output_defaults", {}))

    args.doctor_run_id = scalar_arg(args.doctor_run_id, resume_context.get("doctor_run_id", ""))
    args.doctor_level = scalar_arg(args.doctor_level, resume_context.get("doctor_level", ""))
    args.target_path = scalar_arg(args.target_path, resume_context.get("target_path", ""))
    args.target_classification = scalar_arg(args.target_classification, resume_context.get("target_classification", ""))
    args.baseline_identity = scalar_arg(args.baseline_identity, resume_context.get("baseline_identity", ""))
    args.intended_run_class = scalar_arg(args.intended_run_class, resume_context.get("intended_run_class", ""))
    args.execution_surface_identity = scalar_arg(
        args.execution_surface_identity,
        resume_context.get("execution_surface_identity", ""),
    )

    args.final_result = scalar_arg(args.final_result, repair_inputs.get("final_result", ""))
    args.prompt_identity = scalar_arg(args.prompt_identity, repair_inputs.get("prompt_identity", ""))
    args.task_identity = scalar_arg(args.task_identity, repair_inputs.get("task_identity", ""))
    args.readback = scalar_arg(args.readback, repair_inputs.get("readback", ""))
    args.scenario_proof = scalar_arg(args.scenario_proof, repair_inputs.get("scenario_proof", ""))
    args.target_identity_file = scalar_arg(args.target_identity_file, repair_inputs.get("target_identity_file", ""))
    args.artifact_path = scalar_arg(args.artifact_path, repair_inputs.get("artifact_path", ""))
    args.helper_path = scalar_arg(args.helper_path, repair_inputs.get("helper_path", ""))
    args.prompt_identity_ok = bool_arg(args.prompt_identity_ok, repair_inputs.get("prompt_identity_ok", False))
    args.clean_surface = bool_arg(args.clean_surface, repair_inputs.get("clean_surface", False))
    args.artifact_viable = bool_arg(args.artifact_viable, repair_inputs.get("artifact_viable", False))
    args.helper_ok = bool_arg(args.helper_ok, repair_inputs.get("helper_ok", False))
    args.credentials_ok = bool_arg(args.credentials_ok, repair_inputs.get("credentials_ok", False))

    if not args.credential_env:
        args.credential_env = list(repair_inputs.get("credential_env", []))

    args.refresh_event_type = scalar_arg(args.refresh_event_type, continuation_plan.get("refresh_event_type", ""))
    args.refresh_recovery_status = scalar_arg(
        args.refresh_recovery_status,
        repair_inputs.get("refresh_recovery_status", continuation_plan.get("refresh_recovery_status", "NOT_REQUIRED")),
    )
    args.refresh_reverification_complete = bool_arg(
        args.refresh_reverification_complete,
        repair_inputs.get(
            "refresh_reverification_complete",
            continuation_plan.get("refresh_reverification_complete", False),
        ),
    )
    args.refresh_use_bundle = bool_arg(args.refresh_use_bundle, continuation_plan.get("refresh_use_bundle", False))
    args.refresh_use_closure = bool_arg(args.refresh_use_closure, continuation_plan.get("refresh_use_closure", False))

    if not getattr(args, "refresh_output", None):
        args.refresh_output = output_defaults.get("refresh_output", "")

    return args


def provided_input_ids(args: argparse.Namespace) -> list[str]:
    provided: list[str] = []
    checks = [
        ("prompt_identity", bool(args.prompt_identity.strip())),
        ("task_identity", bool(args.task_identity.strip())),
        ("target_identity_file", bool(args.target_identity_file)),
        ("clean_surface_confirmation", args.clean_surface),
        ("artifact_path", bool(args.artifact_path)),
        ("helper_path", bool(args.helper_path)),
        ("credential_surface", bool(args.credentials_ok or args.credential_env)),
        ("final_result", bool(args.final_result)),
        ("readback", bool(args.readback)),
        ("scenario_proof", bool(args.scenario_proof)),
        ("refresh_recovery_complete", args.refresh_recovery_status == "COMPLETE"),
        ("refresh_reverification_complete", args.refresh_reverification_complete),
    ]
    for input_id, present in checks:
        if present:
            provided.append(input_id)
    return provided


def unresolved_doctor_input_ids(state: dict) -> list[str]:
    unresolved: list[str] = []
    for failure_class in state.get("doctor", {}).get("blocking_failure_classes", []):
        for input_id in DOCTOR_FAILURE_INPUTS.get(failure_class, []):
            if input_id not in unresolved:
                unresolved.append(input_id)
    return unresolved


def missing_input_ids(handoff: dict, provided_ids: list[str]) -> list[str]:
    required_ids = [item["input_id"] for item in handoff.get("required_inputs", [])]
    return [input_id for input_id in required_ids if input_id not in provided_ids]


def default_output_paths(root: Path) -> dict:
    return {
        "artifact_root": str(root),
        "doctor_output": str(root / "doctor.json"),
        "bundle_output": str(root / "bundle.json"),
        "closure_output": str(root / "closure.json"),
        "refresh_output": str(root / "refresh.json"),
        "report_output": str(root / "report.json"),
        "worked_artifact_output": str(root / "orchestration.json"),
        "run_artifact_output": str(root / "run.json"),
        "repair_handoff_output": "",
        "repair_packet_output": str(root / "repair_packet.json"),
        "repair_receipt_output": "",
        "plan_output": str(root / "plan.json"),
        "preparation_receipt_output": str(root / "preparation_receipt.json"),
    }


def infer_refresh_event_type(args: argparse.Namespace, handoff: dict) -> str:
    if args.refresh_event_type:
        return args.refresh_event_type
    handoff_defaults = handoff.get("runtime_defaults", {})
    if handoff_defaults.get("refresh_event_type"):
        return handoff_defaults["refresh_event_type"]
    if args.refresh_recovery_status != "NOT_REQUIRED" or args.refresh_reverification_complete:
        return "RECOVERY_EVENT"
    return ""


def build_continuation_plan(args: argparse.Namespace, handoff: dict) -> dict:
    refresh_event_type = infer_refresh_event_type(args, handoff)
    refresh_required = bool(refresh_event_type)
    handoff_defaults = handoff.get("runtime_defaults", {})
    refresh_use_bundle = bool(
        args.refresh_use_bundle
        or handoff_defaults.get("refresh_use_bundle", False)
        or (refresh_required and refresh_event_type == "RECOVERY_EVENT")
    )
    refresh_use_closure = bool(
        args.refresh_use_closure
        or handoff_defaults.get("refresh_use_closure", False)
        or (refresh_required and refresh_event_type == "RECOVERY_EVENT")
    )
    return {
        "doctor_required": True,
        "bundle_required": True,
        "closure_required": True,
        "refresh_required": refresh_required,
        "refresh_event_type": refresh_event_type,
        "refresh_use_bundle": refresh_use_bundle,
        "refresh_use_closure": refresh_use_closure,
        "refresh_recovery_status": args.refresh_recovery_status,
        "refresh_reverification_complete": args.refresh_reverification_complete,
    }


def build_selection_context(selection_receipt: dict | None) -> dict:
    if not selection_receipt:
        return {
            "applied": False,
            "scenario_class": "",
            "recommended_mode": "",
            "selected_mode": "",
            "followed_recommendation": False,
            "governed_preparation_recommended": False,
            "selected_with_preparation": False,
            "heavier_contour_entered": False,
            "estimated_avoided_operator_minutes": 0,
            "estimated_avoided_interventions": 0,
            "estimated_avoided_closure_latency_minutes": 0,
        }
    return {
        "applied": True,
        "scenario_class": selection_receipt.get("scenario_class", ""),
        "recommended_mode": selection_receipt["recommended_mode"],
        "selected_mode": selection_receipt["selected_mode"],
        "followed_recommendation": selection_receipt.get("followed_recommendation", False),
        "governed_preparation_recommended": selection_receipt.get("governed_preparation_recommended", False),
        "selected_with_preparation": selection_receipt.get("selected_with_preparation", False),
        "heavier_contour_entered": selection_receipt.get("heavier_contour_entered", False),
        "estimated_avoided_operator_minutes": selection_receipt.get("estimated_avoided_operator_minutes", 0),
        "estimated_avoided_interventions": selection_receipt.get("estimated_avoided_interventions", 0),
        "estimated_avoided_closure_latency_minutes": selection_receipt.get("estimated_avoided_closure_latency_minutes", 0),
    }


def build_preparation_context(preparation_receipt: dict | None) -> dict:
    if not preparation_receipt:
        return {
            "applied": False,
            "ready_for_closure": False,
            "complete_on_first_bundle_pass": False,
            "bundle_status": "",
            "planned_required_sections_count": 0,
            "planned_required_sections_present_count": 0,
        }
    return {
        "applied": True,
        "ready_for_closure": preparation_receipt.get("ready_for_closure", False),
        "complete_on_first_bundle_pass": preparation_receipt.get("complete_on_first_bundle_pass", False),
        "bundle_status": preparation_receipt.get("bundle_status", ""),
        "planned_required_sections_count": preparation_receipt.get("planned_required_sections_count", 0),
        "planned_required_sections_present_count": preparation_receipt.get("planned_required_sections_present_count", 0),
    }


def build_runtime_truth(state: dict, report: dict | None) -> dict:
    report = report or {}
    active_pressures = collect_active_pressures(state)
    return {
        "report_result": report.get("result", ""),
        "stopping_stage": report.get("stopping_stage", ""),
        "report_reason": report.get("reason", ""),
        "doctor_verdict": report.get("doctor_verdict", ""),
        "bundle_status": report.get("bundle_status", state.get("proof_bundle", {}).get("status", "")),
        "closure_status": report.get("closure_status", state.get("closure", {}).get("status", "")),
        "refresh_applied": report.get("refresh_applied", False),
        "refresh_resulting_closure_status": report.get("refresh_resulting_closure_status", ""),
        "resulting_state": report.get("resulting_state", state.get("state", "")),
        "next_safe_step": report.get("next_safe_step", state.get("next_safe_step", "")),
        "active_pressures": active_pressures,
        "state_snapshot": {
            "state": state.get("state", ""),
            "target_surface_status": state.get("target_surface", {}).get("status", ""),
            "doctor_status": state.get("doctor", {}).get("status", ""),
            "doctor_failure_classes": list(state.get("doctor", {}).get("blocking_failure_classes", [])),
            "integrity_status": state.get("integrity", {}).get("status", ""),
            "execution_status": state.get("execution", {}).get("status", ""),
            "proof_bundle_status": state.get("proof_bundle", {}).get("status", ""),
            "proof_missing_sections": list(state.get("proof_bundle", {}).get("missing_sections", [])),
            "closure_status": state.get("closure", {}).get("status", ""),
            "closure_blocking_reason": state.get("closure", {}).get("blocking_reason", ""),
            "recovery_status": state.get("recovery", {}).get("status", ""),
            "recovery_reverification_complete": state.get("recovery", {}).get("reverification_complete", False),
        },
    }


def build_artifact_quality_summary(handoff: dict) -> dict:
    hints = handoff.get("artifact_quality_hints", [])
    stale_subsurface_ids: list[str] = []
    non_resumable_subsurface_ids: list[str] = []
    for hint in hints:
        quality = hint.get("quality")
        for subsurface in hint.get("stale_subsurfaces", []):
            subsurface_id = subsurface.get("subsurface_id", "")
            if not subsurface_id:
                continue
            if quality == "STALE" and subsurface_id not in stale_subsurface_ids:
                stale_subsurface_ids.append(subsurface_id)
            if quality == "NON_RESUMABLE" and subsurface_id not in non_resumable_subsurface_ids:
                non_resumable_subsurface_ids.append(subsurface_id)
    return {
        "artifact_ids": [hint["artifact_id"] for hint in hints],
        "stale_artifact_ids": [hint["artifact_id"] for hint in hints if hint.get("quality") == "STALE"],
        "non_resumable_artifact_ids": [hint["artifact_id"] for hint in hints if hint.get("quality") == "NON_RESUMABLE"],
        "stale_subsurface_ids": stale_subsurface_ids,
        "non_resumable_subsurface_ids": non_resumable_subsurface_ids,
    }


def build_source_of_truth(repair_receipt: dict | None) -> dict:
    history_chain = list(repair_receipt.get("repair_history_chain", [])) if repair_receipt else []
    latest_receipt_available = bool(repair_receipt)
    return {
        "authoritative_entry_artifacts": ["state_file", "repair_packet"],
        "precedence_order": list(SOURCE_OF_TRUTH_PRECEDENCE),
        "artifact_roles": {
            "state_file": "authoritative current run state",
            "repair_packet": "authoritative continuation contract, required inputs, and output defaults",
            "repair_receipt": "authoritative latest repair-step progress only when it matches the same contour",
            "repair_history_chain": "supporting chronology embedded for replay, not a stronger state source than the packet or state file",
        },
        "freshness_rule": "prefer the fresher stricter lower-level artifact when derived continuation surfaces disagree",
        "contradiction_rule": "state_file anchors current state; repair_packet anchors continuation contract; repair_receipt can refine latest step progress but must not soften stricter state truth",
        "latest_repair_receipt_available": latest_receipt_available,
        "embedded_history_chain_length": len(history_chain),
        "packet_replay_ready": True,
        "packet_replay_why": (
            "state_file and repair_packet are enough for packet-first continuation, with any latest repair receipt and history embedded for replay"
        ),
    }


def build_repair_history(handoff: dict, repair_receipt: dict | None) -> dict:
    completed_step_ids = list(repair_receipt.get("repair_history", {}).get("completed_step_ids", [])) if repair_receipt else []
    history_chain = list(repair_receipt.get("repair_history_chain", [])) if repair_receipt else []
    current_step_id = handoff.get("repair_policy", {}).get("next_step_id", "")
    ordered = [step.get("step_id", "") for step in handoff.get("repair_policy", {}).get("ordered_steps", []) if step.get("step_id", "")]
    waiting = [step_id for step_id in ordered if step_id and step_id not in completed_step_ids and step_id != current_step_id]
    return {
        "applied": bool(repair_receipt),
        "last_receipt_result": repair_receipt.get("result", "") if repair_receipt else "",
        "last_completed_step_id": repair_receipt.get("completed_step_id", "") if repair_receipt else "",
        "completed_step_ids": completed_step_ids,
        "current_step_id": current_step_id,
        "waiting_step_ids": waiting,
        "history_chain_length": len(history_chain),
        "history_chain_results": [entry.get("result", "") for entry in history_chain[-3:]],
        "history_chain_step_ids": [
            entry.get("completed_step_id", "") or entry.get("active_step_id", "")
            for entry in history_chain[-3:]
            if entry.get("completed_step_id", "") or entry.get("active_step_id", "")
        ],
    }


def build_repair_termination(*, resumability: dict, repair_history: dict, repair_receipt: dict | None) -> dict:
    history_chain = list(repair_receipt.get("repair_history_chain", [])) if repair_receipt else []
    attempt_count = len(history_chain)
    if resumability.get("status") == "NOT_RESUMABLE":
        return {
            "status": "TERMINATE",
            "reason": "NON_RESUMABLE",
            "attempt_count": attempt_count,
            "max_attempts": MAX_REPAIR_ATTEMPTS,
            "no_progress_window": NO_PROGRESS_WINDOW,
            "stalled_step_id": repair_history.get("current_step_id", ""),
            "next_action": "stop resuming this contour and follow the named non-resumable boundary",
        }

    if len(history_chain) >= NO_PROGRESS_WINDOW:
        window = history_chain[-NO_PROGRESS_WINDOW:]
        if all(entry.get("result", "") in {"STEP_NOT_COMPLETED", "STEP_PROGRESS_RECORDED"} for entry in window):
            active_step_ids = {entry.get("active_step_id", "") for entry in window}
            completed_step_ids = {entry.get("completed_step_id", "") for entry in window if entry.get("completed_step_id", "")}
            next_step_ids = {entry.get("next_step_id", "") for entry in window}
            if len(active_step_ids) == 1 and not completed_step_ids and len(next_step_ids) == 1:
                stalled_step_id = next(iter(active_step_ids))
                return {
                    "status": "TERMINATE",
                    "reason": "NO_PROGRESS_DETECTED",
                    "attempt_count": attempt_count,
                    "max_attempts": MAX_REPAIR_ATTEMPTS,
                    "no_progress_window": NO_PROGRESS_WINDOW,
                    "stalled_step_id": stalled_step_id,
                    "next_action": "stop retrying the same repair step without new evidence or inputs",
                }

    if attempt_count >= MAX_REPAIR_ATTEMPTS:
        return {
            "status": "TERMINATE",
            "reason": "MAX_REPAIR_ATTEMPTS",
            "attempt_count": attempt_count,
            "max_attempts": MAX_REPAIR_ATTEMPTS,
            "no_progress_window": NO_PROGRESS_WINDOW,
            "stalled_step_id": repair_history.get("current_step_id", ""),
            "next_action": "stop this repair loop and start a new run or manual recovery path",
        }

    return {
        "status": "CONTINUE",
        "reason": "",
        "attempt_count": attempt_count,
        "max_attempts": MAX_REPAIR_ATTEMPTS,
        "no_progress_window": NO_PROGRESS_WINDOW,
        "stalled_step_id": "",
        "next_action": "continue with the current repair policy order",
    }


def build_receipt_context(repair_receipt: dict | None) -> dict:
    if not repair_receipt:
        return {
            "applied": False,
            "result": "",
            "completed_step_id": "",
            "remaining_stale_artifact_ids": [],
            "remaining_stale_subsurface_ids": [],
            "remaining_non_resumable_artifact_ids": [],
            "remaining_non_resumable_subsurface_ids": [],
            "remaining_stale_hints": [],
            "remaining_non_resumable_hints": [],
            "completed_hints": [],
            "next_step_required_inputs": [],
            "next_step_hints": [],
            "history_chain": [],
            "operator_evidence": {
                "completed_step_id": "",
                "completed_artifact_hints": [],
                "completed_subsurface_ids": [],
                "next_step_id": "",
                "next_step_required_inputs": [],
                "next_step_artifact_hints": [],
                "next_step_subsurface_ids": [],
                "operator_focus": "",
            },
        }
    return {
        "applied": True,
        "result": repair_receipt.get("result", ""),
        "completed_step_id": repair_receipt.get("completed_step_id", ""),
        "remaining_stale_artifact_ids": list(repair_receipt.get("remaining_stale_artifact_ids", [])),
        "remaining_stale_subsurface_ids": list(repair_receipt.get("remaining_stale_subsurface_ids", [])),
        "remaining_non_resumable_artifact_ids": list(repair_receipt.get("remaining_non_resumable_artifact_ids", [])),
        "remaining_non_resumable_subsurface_ids": list(repair_receipt.get("remaining_non_resumable_subsurface_ids", [])),
        "remaining_stale_hints": list(repair_receipt.get("remaining_stale_hints", [])),
        "remaining_non_resumable_hints": list(repair_receipt.get("remaining_non_resumable_hints", [])),
        "completed_hints": list(repair_receipt.get("completed_hints", [])),
        "next_step_required_inputs": list(repair_receipt.get("next_step_required_inputs", [])),
        "next_step_hints": list(repair_receipt.get("next_step_hints", [])),
        "history_chain": list(repair_receipt.get("repair_history_chain", [])),
        "operator_evidence": dict(repair_receipt.get("operator_evidence", {})),
    }


def build_continuation_core(
    *,
    handoff: dict,
    resumability: dict,
    artifact_quality_summary: dict,
    repair_history: dict,
    receipt_context: dict,
    selection_context: dict,
    missing_ids: list[str],
    repair_termination: dict,
    source_of_truth: dict,
    output_defaults: dict,
    resume_context: dict,
) -> dict:
    operator_evidence = dict(receipt_context.get("operator_evidence", {}))
    required_inputs = [item.get("input_id", "") for item in handoff.get("required_inputs", []) if item.get("input_id", "")]
    next_step_required_inputs = list(operator_evidence.get("next_step_required_inputs", [])) or required_inputs
    next_step_subsurface_ids = list(operator_evidence.get("next_step_subsurface_ids", [])) or list(
        artifact_quality_summary.get("stale_subsurface_ids", [])
    )
    focused_surface = focused_repair_surface(
        current_step_id=handoff.get("repair_policy", {}).get("next_step_id", ""),
        stale_subsurfaces=next_step_subsurface_ids,
        artifact_root=output_defaults.get("artifact_root", ""),
        target_path=resume_context.get("target_path", ""),
    )
    current_step_subsurface_id = focused_surface.get("current_step_subsurface_id", "")
    current_step_target_path = focused_surface.get("current_step_target_path", "")
    operator_focus = operator_evidence.get("operator_focus", "") or handoff.get("next_safe_step", "")
    if current_step_target_path:
        operator_focus = focused_repair_summary(
            current_step_id=handoff.get("repair_policy", {}).get("next_step_id", ""),
            current_step_subsurface_id=current_step_subsurface_id,
            current_step_target_path=current_step_target_path,
        )
    ready_for_resume = handoff.get("continuation_allowed", False) and not missing_ids and repair_termination.get("status") != "TERMINATE"
    return {
        "contract_version": "continuation_core_v0",
        "entrypoint": "resume",
        "ready_for_resume": ready_for_resume,
        "resumability_status": resumability.get("status", ""),
        "resumability_family": resumability.get("family", ""),
        "current_step_id": handoff.get("repair_policy", {}).get("next_step_id", ""),
        "current_step_subsurface_id": current_step_subsurface_id,
        "current_step_target_path": current_step_target_path,
        "required_inputs": required_inputs,
        "missing_inputs": list(missing_ids),
        "next_step_required_inputs": next_step_required_inputs,
        "next_step_subsurface_ids": next_step_subsurface_ids,
        "operator_focus": operator_focus,
        "next_safe_step": handoff.get("next_safe_step", ""),
        "history_chain_length": repair_history.get("history_chain_length", 0),
        "selection_applied": selection_context.get("applied", False),
        "selected_with_preparation": selection_context.get("selected_with_preparation", False),
        "packet_supplies_resume_context": True,
        "packet_supplies_repair_inputs": True,
        "packet_supplies_output_defaults": True,
        "requires_sibling_discovery": False,
        "authoritative_entry_artifacts": list(source_of_truth.get("authoritative_entry_artifacts", [])),
        "source_of_truth_precedence": list(source_of_truth.get("precedence_order", [])),
        "packet_replay_ready": source_of_truth.get("packet_replay_ready", False),
    }


def apply_arbiter_to_continuation_core(core: dict, arbiter: dict) -> dict:
    resolved = dict(arbiter.get("resolved_decision", {}))
    patched = dict(core)
    patched["ready_for_resume"] = resolved.get("ready_for_resume", patched.get("ready_for_resume", False))
    patched["resumability_status"] = resolved.get("resumability_status", patched.get("resumability_status", ""))
    patched["resumability_family"] = resolved.get("resumability_family", patched.get("resumability_family", ""))
    patched["current_step_id"] = resolved.get("current_step_id", patched.get("current_step_id", ""))
    patched["missing_inputs"] = list(resolved.get("missing_inputs", patched.get("missing_inputs", [])))
    patched["next_step_required_inputs"] = list(
        resolved.get("next_step_required_inputs", patched.get("next_step_required_inputs", []))
    )
    patched["operator_focus"] = resolved.get("operator_focus", patched.get("operator_focus", ""))
    patched["next_safe_step"] = resolved.get("next_safe_step", patched.get("next_safe_step", ""))
    patched["packet_replay_ready"] = resolved.get("packet_replay_ready", patched.get("packet_replay_ready", False))
    return patched


def build_packet_from_runtime_truth(
    *,
    state: dict,
    artifact_root: Path,
    doctor_run_id: str,
    doctor_level: str,
    target_path: str,
    target_classification: str,
    baseline_identity: str,
    intended_run_class: str,
    execution_surface_identity: str,
    repair_handoff: dict | None = None,
    final_result: str = "",
    prompt_identity: str = "",
    task_identity: str = "",
    prompt_identity_ok: bool = False,
    readback: str = "",
    scenario_proof: str = "",
    target_identity_file: str = "",
    clean_surface: bool = False,
    artifact_viable: bool = False,
    helper_ok: bool = False,
    credentials_ok: bool = False,
    artifact_path: str = "",
    helper_path: str = "",
    credential_env: list[str] | None = None,
    refresh_output: str = "",
    refresh_event_type: str = "",
    refresh_recovery_status: str = "NOT_REQUIRED",
    refresh_reverification_complete: bool = False,
    refresh_use_bundle: bool = False,
    refresh_use_closure: bool = False,
    output_defaults_overrides: dict | None = None,
    selection_receipt: dict | None = None,
    preparation_receipt: dict | None = None,
    repair_receipt: dict | None = None,
    report: dict | None = None,
) -> dict:
    handoff = repair_handoff or build_repair_handoff(state)
    resumability = build_resumability(state)
    packet_args = argparse.Namespace(
        refresh_event_type=refresh_event_type,
        refresh_recovery_status=refresh_recovery_status,
        refresh_reverification_complete=refresh_reverification_complete,
        refresh_use_bundle=refresh_use_bundle,
        refresh_use_closure=refresh_use_closure,
        prompt_identity=prompt_identity,
        task_identity=task_identity,
        target_identity_file=target_identity_file,
        clean_surface=clean_surface,
        artifact_path=artifact_path,
        helper_path=helper_path,
        credentials_ok=credentials_ok,
        credential_env=list(credential_env or []),
        final_result=final_result,
        readback=readback,
        scenario_proof=scenario_proof,
    )

    prompt_identity_ok = prompt_identity_ok or bool(prompt_identity.strip() and task_identity.strip())
    provided_ids = provided_input_ids(packet_args)
    for input_id in unresolved_doctor_input_ids(state):
        if input_id in provided_ids:
            provided_ids.remove(input_id)
    missing_ids = missing_input_ids(handoff, provided_ids)

    output_defaults = default_output_paths(artifact_root)
    for key, value in (output_defaults_overrides or {}).items():
        if value:
            output_defaults[key] = value
    if refresh_output:
        output_defaults["refresh_output"] = refresh_output

    artifact_quality_summary = build_artifact_quality_summary(handoff)
    repair_history = build_repair_history(handoff, repair_receipt)
    receipt_context = build_receipt_context(repair_receipt)
    source_of_truth = build_source_of_truth(repair_receipt)
    repair_termination = build_repair_termination(
        resumability=resumability,
        repair_history=repair_history,
        repair_receipt=repair_receipt,
    )
    selection_context = build_selection_context(selection_receipt)
    ready_for_resume = (
        handoff.get("continuation_allowed", False)
        and not missing_ids
        and repair_termination.get("status") != "TERMINATE"
    )

    packet = {
        "schema_version": "repair_packet_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "from_state": state["state"],
        "continuation_entrypoint": "resume",
        "repair_handoff": handoff,
        "resumability": resumability,
        "repair_policy": handoff.get("repair_policy", {}),
        "artifact_quality_hints": list(handoff.get("artifact_quality_hints", [])),
        "artifact_quality_summary": artifact_quality_summary,
        "repair_history": repair_history,
        "repair_history_chain": list(repair_receipt.get("repair_history_chain", [])) if repair_receipt else [],
        "repair_termination": repair_termination,
        "repair_receipt_context": receipt_context,
        "continuation_plan": build_continuation_plan(packet_args, handoff),
        "resume_context": {
            "doctor_run_id": doctor_run_id,
            "doctor_level": doctor_level,
            "target_path": target_path,
            "target_classification": target_classification,
            "baseline_identity": baseline_identity,
            "intended_run_class": intended_run_class,
            "execution_surface_identity": execution_surface_identity,
        },
        "repair_inputs": {
            "prompt_identity": prompt_identity,
            "task_identity": task_identity,
            "prompt_identity_ok": prompt_identity_ok,
            "target_identity_file": target_identity_file,
            "clean_surface": clean_surface,
            "artifact_viable": artifact_viable,
            "helper_ok": helper_ok,
            "credentials_ok": credentials_ok,
            "artifact_path": artifact_path,
            "helper_path": helper_path,
            "credential_env": list(credential_env or []),
            "final_result": final_result,
            "readback": readback,
            "scenario_proof": scenario_proof,
            "refresh_recovery_status": refresh_recovery_status,
            "refresh_reverification_complete": refresh_reverification_complete,
        },
        "selection_context": selection_context,
        "preparation_context": build_preparation_context(preparation_receipt),
        "source_of_truth": source_of_truth,
        "runtime_truth": build_runtime_truth(state, report),
        "output_defaults": output_defaults,
        "provided_inputs": provided_ids,
        "missing_inputs": missing_ids,
        "ready_for_resume": ready_for_resume,
        "next_safe_step": handoff["next_safe_step"],
    }
    packet["continuation_core"] = build_continuation_core(
        handoff=handoff,
        resumability=resumability,
        artifact_quality_summary=artifact_quality_summary,
        repair_history=repair_history,
        receipt_context=receipt_context,
        selection_context=selection_context,
        missing_ids=missing_ids,
        repair_termination=repair_termination,
        source_of_truth=source_of_truth,
        output_defaults=output_defaults,
        resume_context=packet["resume_context"],
    )
    if selection_receipt:
        packet["selection_receipt"] = selection_receipt
    if repair_receipt:
        packet["repair_receipt"] = repair_receipt
    packet["continuation_arbiter"] = build_continuation_arbiter(
        state=state,
        packet=packet,
        repair_receipt=repair_receipt,
    )
    packet["continuation_core"] = apply_arbiter_to_continuation_core(
        packet["continuation_core"],
        packet["continuation_arbiter"],
    )
    resolved = packet["continuation_arbiter"].get("resolved_decision", {})
    packet["ready_for_resume"] = resolved.get("ready_for_resume", packet["ready_for_resume"])
    packet["missing_inputs"] = list(resolved.get("missing_inputs", packet["missing_inputs"]))
    packet["next_safe_step"] = resolved.get("next_safe_step", packet["next_safe_step"])
    return packet


def build_packet(args: argparse.Namespace) -> dict:
    state = load_state_json(Path(args.state_file))
    previous_packet = load_json(Path(args.previous_packet_file)) if getattr(args, "previous_packet_file", None) else None
    if previous_packet:
        args = merge_previous_packet_context(args, previous_packet)
    missing_context = [
        field
        for field in [
            "doctor_run_id",
            "doctor_level",
            "target_path",
            "target_classification",
            "baseline_identity",
            "intended_run_class",
            "execution_surface_identity",
        ]
        if getattr(args, field, None) in {None, ""}
    ]
    if missing_context:
        raise ValueError(f"repair packet context incomplete: {', '.join(missing_context)}")
    if args.repair_handoff_file:
        handoff = load_json(Path(args.repair_handoff_file))
    else:
        handoff = build_repair_handoff(state)

    selection_receipt = load_json(Path(args.mode_selection_receipt)) if getattr(args, "mode_selection_receipt", None) else None
    if selection_receipt is None and previous_packet and previous_packet.get("selection_receipt"):
        selection_receipt = dict(previous_packet["selection_receipt"])
    preparation_receipt = load_json(Path(args.preparation_receipt_file)) if getattr(args, "preparation_receipt_file", None) else None
    repair_receipt = load_json(Path(args.repair_receipt_file)) if getattr(args, "repair_receipt_file", None) else None
    if repair_receipt is None and previous_packet and previous_packet.get("repair_receipt"):
        repair_receipt = dict(previous_packet["repair_receipt"])
    report = load_json(Path(args.report_file)) if getattr(args, "report_file", None) else None

    return build_packet_from_runtime_truth(
        state=state,
        artifact_root=Path(args.artifact_root),
        doctor_run_id=args.doctor_run_id,
        doctor_level=args.doctor_level,
        target_path=args.target_path,
        target_classification=args.target_classification,
        baseline_identity=args.baseline_identity,
        intended_run_class=args.intended_run_class,
        execution_surface_identity=args.execution_surface_identity,
        repair_handoff=handoff,
        final_result=args.final_result,
        prompt_identity=args.prompt_identity,
        task_identity=args.task_identity,
        prompt_identity_ok=args.prompt_identity_ok,
        readback=args.readback or "",
        scenario_proof=args.scenario_proof or "",
        target_identity_file=args.target_identity_file or "",
        clean_surface=args.clean_surface,
        artifact_viable=args.artifact_viable,
        helper_ok=args.helper_ok,
        credentials_ok=args.credentials_ok,
        artifact_path=args.artifact_path or "",
        helper_path=args.helper_path or "",
        credential_env=list(args.credential_env),
        refresh_output=args.refresh_output or "",
        refresh_event_type=args.refresh_event_type or "",
        refresh_recovery_status=args.refresh_recovery_status,
        refresh_reverification_complete=args.refresh_reverification_complete,
        refresh_use_bundle=args.refresh_use_bundle,
        refresh_use_closure=args.refresh_use_closure,
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        repair_receipt=repair_receipt,
        report=report,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-repair-packet-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous-packet-file")
    parser.add_argument("--repair-handoff-file")
    parser.add_argument("--mode-selection-receipt")
    parser.add_argument("--preparation-receipt-file")
    parser.add_argument("--repair-receipt-file")
    parser.add_argument("--report-file")
    parser.add_argument("--doctor-run-id")
    parser.add_argument("--doctor-level", choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    parser.add_argument("--target-path")
    parser.add_argument("--target-classification")
    parser.add_argument("--baseline-identity")
    parser.add_argument("--intended-run-class", choices=["core_probe", "support_run", "exact_retry"])
    parser.add_argument("--execution-surface-identity")
    parser.add_argument("--final-result", default="")
    parser.add_argument("--prompt-identity", default="")
    parser.add_argument("--task-identity", default="")
    parser.add_argument("--prompt-identity-ok", action="store_true", default=None)
    parser.add_argument("--readback")
    parser.add_argument("--scenario-proof")
    parser.add_argument("--target-identity-file")
    parser.add_argument("--clean-surface", action="store_true", default=None)
    parser.add_argument("--artifact-viable", action="store_true", default=None)
    parser.add_argument("--helper-ok", action="store_true", default=None)
    parser.add_argument("--credentials-ok", action="store_true", default=None)
    parser.add_argument("--artifact-path")
    parser.add_argument("--helper-path")
    parser.add_argument("--credential-env", action="append", default=[])
    parser.add_argument("--refresh-output")
    parser.add_argument("--refresh-event-type")
    parser.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"], default="NOT_REQUIRED")
    parser.add_argument("--refresh-reverification-complete", action="store_true", default=None)
    parser.add_argument("--refresh-use-bundle", action="store_true", default=None)
    parser.add_argument("--refresh-use-closure", action="store_true", default=None)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        packet = build_packet(args)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": "INVALID_REPAIR_PACKET_CONTEXT", "detail": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), packet)
    print(
        json.dumps(
            {
                "result": "OK",
                "ready_for_resume": packet["ready_for_resume"],
                "missing_inputs": packet["missing_inputs"],
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
