#!/usr/bin/env python3
"""Minimal executable Synrail spine prototype."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from synrail_artifact_repair_receipt_v0 import build_receipt as build_artifact_repair_receipt
from synrail_repair_handoff_v0 import build_repair_handoff, build_resumability
from synrail_repair_packet_v0 import build_packet_from_runtime_truth


TERMINAL_STATES = {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}
HERE = Path(__file__).resolve().parent
DOCTOR = HERE / "synrail_doctor_v1.py"
BUNDLE = HERE / "synrail_bundle_v0.py"
CLOSURE = HERE / "synrail_closure_v0.py"
REFRESH = HERE / "synrail_refresh_v0.py"
HARNESS_V0 = HERE / "synrail_baseline_harness_v0.py"
HARNESS_V1 = HERE / "synrail_baseline_harness_v1.py"
PROOF_PLAN = HERE / "synrail_proof_plan_v0.py"
PREPARATION_RECEIPT = HERE / "synrail_preparation_receipt_v0.py"

TRANSITION_PRECEDENCE = {
    "TARGET_SURFACE_ATTESTED": [
        "TARGET_SURFACE_NOT_ATTESTED",
    ],
    "READY": [
        "TARGET_SURFACE_NOT_ATTESTED",
        "DOCTOR_NOT_GREEN",
        "EXACT_TASK_IDENTITY_NOT_CONFIRMED",
    ],
    "EXECUTION_COMPLETED": [
        "TARGET_SURFACE_NOT_ATTESTED",
        "DOCTOR_NOT_GREEN",
        "EXACT_TASK_IDENTITY_NOT_CONFIRMED",
        "EXECUTION_NOT_COMPLETED",
    ],
    "PROOF_BUNDLE_COMPLETE": [
        "ARTIFACT_BUNDLE_MISSING",
        "INVALID_PROOF_BUNDLE",
        "MISSING_PROOF_SECTIONS",
    ],
    "CLOSURE_ACCEPTED": [
        "ARTIFACT_BUNDLE_MISSING",
        "INVALID_PROOF_BUNDLE",
        "MISSING_PROOF_SECTIONS",
        "RECOVERY_REVERIFICATION_INCOMPLETE",
    ],
}


def default_state(run_id: str, task_class: str) -> dict:
    return {
        "schema_version": "run_state_v0",
        "run_id": run_id,
        "task_class": task_class,
        "state": "INITIALIZED",
        "target_surface": {
            "status": "UNKNOWN",
            "identity": "",
            "baseline_relation": "",
        },
        "doctor": {
            "status": "UNKNOWN",
            "blocking_failure_classes": [],
        },
        "integrity": {
            "status": "UNKNOWN",
            "exact_task_identity_ok": False,
        },
        "execution": {
            "status": "NOT_RUN",
            "artifact_bundle_present": False,
        },
        "proof_bundle": {
            "status": "MISSING",
            "missing_sections": [],
        },
        "closure": {
            "status": "OPEN",
            "blocking_reason": "",
            "next_allowed_transition": "TARGET_SURFACE_ATTESTED",
            "narrow_next_safe_step": "attest target surface",
            "missing_sections": [],
        },
        "recovery": {
            "status": "NOT_REQUIRED",
            "reverification_complete": False,
        },
        "next_safe_step": "attest target surface",
    }


def load_state(path: Path) -> dict:
    return json.loads(path.read_text())


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_mode_selection_receipt(path: Path) -> dict:
    receipt = load_json(path)
    if receipt.get("schema_version") != "mode_selection_receipt_v0":
        raise ValueError("mode selection receipt must use mode_selection_receipt_v0")
    return receipt


def load_repair_handoff(path: Path) -> dict:
    handoff = load_json(path)
    if handoff.get("schema_version") != "repair_handoff_v0":
        raise ValueError("repair handoff must use repair_handoff_v0")
    return handoff


def load_repair_packet(path: Path) -> dict:
    packet = load_json(path)
    if packet.get("schema_version") != "repair_packet_v0":
        raise ValueError("repair packet must use repair_packet_v0")
    return packet


def load_repair_receipt(path: Path) -> dict:
    receipt = load_json(path)
    if receipt.get("schema_version") != "artifact_repair_receipt_v0":
        raise ValueError("repair receipt must use artifact_repair_receipt_v0")
    return receipt


def report_resumability_fields(state: dict, handoff: dict | None = None) -> dict:
    current_handoff = handoff if handoff and handoff.get("from_state") == state.get("state") else build_repair_handoff(state)
    resumability = current_handoff.get("resumability", build_resumability(state))
    repair_policy = current_handoff.get("repair_policy", {})
    artifact_quality_hints = current_handoff.get("artifact_quality_hints", [])
    stale_subsurface_ids: list[str] = []
    for hint in artifact_quality_hints:
        if hint.get("quality") != "STALE":
            continue
        for subsurface in hint.get("stale_subsurfaces", []):
            subsurface_id = subsurface.get("subsurface_id", "")
            if subsurface_id and subsurface_id not in stale_subsurface_ids:
                stale_subsurface_ids.append(subsurface_id)
    return {
        "resumability_status": resumability["status"],
        "resumability_family": resumability["family"],
        "resumability_active_pressures": list(resumability["active_pressures"]),
        "resumability_repair_order": list(resumability["recommended_repair_order"]),
        "resumability_requires_new_run": resumability["requires_new_run"],
        "resumability_policy_type": repair_policy.get("policy_type", ""),
        "resumability_policy_next_step": repair_policy.get("next_step_id", ""),
        "resumability_ready_now_steps": list(repair_policy.get("ready_now_step_ids", [])),
        "resumability_stale_artifact_ids": [
            hint["artifact_id"] for hint in artifact_quality_hints if hint.get("quality") == "STALE"
        ],
        "resumability_stale_subsurface_ids": stale_subsurface_ids,
    }


def repair_packet_summary(packet: dict | None, state: dict) -> dict:
    handoff = packet["repair_handoff"] if packet else build_repair_handoff(state)
    resumability = packet["resumability"] if packet else handoff.get("resumability", build_resumability(state))
    repair_policy = packet["repair_policy"] if packet else handoff.get("repair_policy", {})
    repair_history = packet.get("repair_history", {}) if packet else {
        "applied": False,
        "last_receipt_result": "",
        "last_completed_step_id": "",
        "completed_step_ids": [],
        "current_step_id": repair_policy.get("next_step_id", ""),
        "waiting_step_ids": [
            step.get("step_id", "")
            for step in repair_policy.get("ordered_steps", [])
            if step.get("step_id", "") and step.get("step_id", "") != repair_policy.get("next_step_id", "")
        ],
        "history_chain_length": 0,
        "history_chain_results": [],
        "history_chain_step_ids": [],
    }
    artifact_quality_summary = packet.get("artifact_quality_summary", {}) if packet else {
        "stale_artifact_ids": [hint["artifact_id"] for hint in handoff.get("artifact_quality_hints", []) if hint.get("quality") == "STALE"],
        "non_resumable_artifact_ids": [hint["artifact_id"] for hint in handoff.get("artifact_quality_hints", []) if hint.get("quality") == "NON_RESUMABLE"],
        "stale_subsurface_ids": [
            subsurface.get("subsurface_id", "")
            for hint in handoff.get("artifact_quality_hints", [])
            if hint.get("quality") == "STALE"
            for subsurface in hint.get("stale_subsurfaces", [])
            if subsurface.get("subsurface_id", "")
        ],
        "non_resumable_subsurface_ids": [
            subsurface.get("subsurface_id", "")
            for hint in handoff.get("artifact_quality_hints", [])
            if hint.get("quality") == "NON_RESUMABLE"
            for subsurface in hint.get("stale_subsurfaces", [])
            if subsurface.get("subsurface_id", "")
        ],
    }
    receipt_context = packet.get("repair_receipt_context", {}) if packet else {}
    operator_evidence = receipt_context.get("operator_evidence", {}) if receipt_context else {}
    return {
        "emitted": packet is not None,
        "from_state": packet["from_state"] if packet else "",
        "ready_for_resume": packet["ready_for_resume"] if packet else False,
        "missing_inputs": list(packet["missing_inputs"]) if packet else [],
        "selected_with_preparation": packet["selection_context"]["selected_with_preparation"] if packet else False,
        "resumability_status": resumability["status"],
        "resumability_family": resumability["family"],
        "active_pressures": list(resumability["active_pressures"]),
        "repair_order": list(resumability["recommended_repair_order"]),
        "policy_type": repair_policy.get("policy_type", ""),
        "policy_next_step": repair_policy.get("next_step_id", ""),
        "policy_ready_steps": list(repair_policy.get("ready_now_step_ids", [])),
        "repair_history_applied": repair_history.get("applied", False),
        "repair_history_last_result": repair_history.get("last_receipt_result", ""),
        "repair_history_last_completed_step_id": repair_history.get("last_completed_step_id", ""),
        "repair_history_completed_step_ids": list(repair_history.get("completed_step_ids", [])),
        "repair_history_current_step_id": repair_history.get("current_step_id", ""),
        "repair_history_waiting_step_ids": list(repair_history.get("waiting_step_ids", [])),
        "repair_history_chain_length": repair_history.get("history_chain_length", 0),
        "repair_history_chain_results": list(repair_history.get("history_chain_results", [])),
        "repair_history_chain_step_ids": list(repair_history.get("history_chain_step_ids", [])),
        "repair_receipt_last_operator_focus": operator_evidence.get("operator_focus", ""),
        "repair_receipt_next_step_required_inputs": list(operator_evidence.get("next_step_required_inputs", [])),
        "repair_receipt_next_step_subsurface_ids": list(operator_evidence.get("next_step_subsurface_ids", [])),
        "stale_artifact_ids": list(artifact_quality_summary.get("stale_artifact_ids", [])),
        "non_resumable_artifact_ids": list(artifact_quality_summary.get("non_resumable_artifact_ids", [])),
        "stale_subsurface_ids": list(artifact_quality_summary.get("stale_subsurface_ids", [])),
        "non_resumable_subsurface_ids": list(artifact_quality_summary.get("non_resumable_subsurface_ids", [])),
    }

def repair_history_summary(packet: dict | None, state: dict) -> dict:
    packet_summary = repair_packet_summary(packet, state)
    return {
        "available": packet_summary["emitted"],
        "from_state": packet_summary["from_state"],
        "last_result": packet_summary["repair_history_last_result"],
        "last_completed_step_id": packet_summary["repair_history_last_completed_step_id"],
        "current_step_id": packet_summary["repair_history_current_step_id"],
        "waiting_step_ids": list(packet_summary["repair_history_waiting_step_ids"]),
        "completed_step_ids": list(packet_summary["repair_history_completed_step_ids"]),
        "chain_length": packet_summary["repair_history_chain_length"],
        "chain_results": list(packet_summary["repair_history_chain_results"]),
        "chain_step_ids": list(packet_summary["repair_history_chain_step_ids"]),
        "last_operator_focus": packet_summary["repair_receipt_last_operator_focus"],
        "next_step_required_inputs": list(packet_summary["repair_receipt_next_step_required_inputs"]),
        "next_step_subsurface_ids": list(packet_summary["repair_receipt_next_step_subsurface_ids"]),
    }



def comparison_harness_for_inputs(baseline_file: str, synrail_file: str) -> Path:
    baseline = load_json(Path(baseline_file))
    synrail = load_json(Path(synrail_file))
    baseline_version = baseline.get("schema_version", "")
    synrail_version = synrail.get("schema_version", "")

    if baseline_version != synrail_version:
        raise ValueError("comparison input schema versions do not match")

    if baseline_version == "comparison_input_v1":
        return HARNESS_V1

    return HARNESS_V0


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def repair_handoff_required_input_ids(handoff: dict | None) -> list[str]:
    if not handoff:
        return []
    return [item["input_id"] for item in handoff.get("required_inputs", [])]


def apply_repair_handoff_defaults(args: argparse.Namespace, handoff: dict | None) -> None:
    if not handoff:
        return
    runtime_defaults = handoff.get("runtime_defaults", {})
    if runtime_defaults.get("refresh_event_type") and not args.refresh_event_type:
        args.refresh_event_type = runtime_defaults["refresh_event_type"]
    if runtime_defaults.get("refresh_use_bundle"):
        args.refresh_use_bundle = True
    if runtime_defaults.get("refresh_use_closure"):
        args.refresh_use_closure = True
    if (args.refresh_event_type or args.refresh_use_bundle or args.refresh_use_closure) and not args.refresh_output:
        args.refresh_output = str(Path(args.report_output).with_name("refresh.json"))


def missing_continuation_inputs(args: argparse.Namespace, handoff: dict | None) -> list[str]:
    if not handoff:
        return []

    missing: list[str] = []
    for input_id in repair_handoff_required_input_ids(handoff):
        if input_id == "prompt_identity" and not args.prompt_identity.strip():
            missing.append(input_id)
        elif input_id == "task_identity" and not args.task_identity.strip():
            missing.append(input_id)
        elif input_id == "target_identity_file" and not args.target_identity_file:
            missing.append(input_id)
        elif input_id == "clean_surface_confirmation" and not args.clean_surface:
            missing.append(input_id)
        elif input_id == "artifact_path" and not args.artifact_path:
            missing.append(input_id)
        elif input_id == "helper_path" and not args.helper_path:
            missing.append(input_id)
        elif input_id == "credential_surface" and not (args.credentials_ok or args.credential_env):
            missing.append(input_id)
        elif input_id == "final_result" and not args.final_result:
            missing.append(input_id)
        elif input_id == "readback" and not args.readback:
            missing.append(input_id)
        elif input_id == "scenario_proof" and not args.scenario_proof:
            missing.append(input_id)
        elif input_id == "refresh_recovery_complete" and args.refresh_recovery_status != "COMPLETE":
            missing.append(input_id)
        elif input_id == "refresh_reverification_complete" and not args.refresh_reverification_complete:
            missing.append(input_id)
    return missing


def provided_continuation_inputs(args: argparse.Namespace) -> list[str]:
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


def repair_policy_out_of_order_steps(args: argparse.Namespace, handoff: dict | None, missing_inputs: list[str]) -> list[str]:
    if not handoff or not missing_inputs:
        return []
    repair_policy = handoff.get("repair_policy", {})
    if repair_policy.get("policy_type") != "MULTI_STEP_REPAIR":
        return []
    ordered_steps = list(repair_policy.get("ordered_steps", []))
    if len(ordered_steps) < 2:
        return []
    next_required_inputs = set(ordered_steps[0].get("required_inputs", []))
    if not next_required_inputs.intersection(missing_inputs):
        return []
    provided_inputs = set(provided_continuation_inputs(args))
    out_of_order: list[str] = []
    for step in ordered_steps[1:]:
        step_inputs = set(step.get("required_inputs", []))
        if step_inputs and step_inputs.intersection(provided_inputs):
            out_of_order.append(step["step_id"])
    return out_of_order


def maybe_emit_repair_handoff(args: argparse.Namespace, state: dict) -> dict | None:
    if not getattr(args, "repair_handoff_output", None):
        return None
    handoff = build_repair_handoff(state)
    save_json(Path(args.repair_handoff_output), handoff)
    return handoff


def resolve_repair_packet_output(args: argparse.Namespace) -> Path | None:
    if getattr(args, "repair_packet_output", None):
        return Path(args.repair_packet_output)
    if getattr(args, "report_output", None):
        return Path(args.report_output).with_name("repair_packet.json")
    return None


def resolve_repair_receipt_output(args: argparse.Namespace) -> Path | None:
    if getattr(args, "repair_receipt_output", None):
        return Path(args.repair_receipt_output)
    if getattr(args, "resume_from_state", None) and getattr(args, "repair_packet_output", None):
        return None
    if getattr(args, "report_output", None):
        return Path(args.report_output).with_name("repair_receipt.json")
    return None


def packet_output_defaults(args: argparse.Namespace, packet_output: Path) -> dict:
    return {
        "doctor_output": getattr(args, "doctor_output", ""),
        "bundle_output": getattr(args, "bundle_output", ""),
        "closure_output": getattr(args, "closure_output", ""),
        "refresh_output": getattr(args, "refresh_output", ""),
        "report_output": getattr(args, "report_output", ""),
        "worked_artifact_output": getattr(args, "worked_artifact_output", ""),
        "run_artifact_output": getattr(args, "run_artifact_output", ""),
        "repair_handoff_output": getattr(args, "repair_handoff_output", ""),
        "repair_packet_output": str(packet_output),
        "repair_receipt_output": getattr(args, "repair_receipt_output", ""),
        "plan_output": getattr(args, "plan_output", "") or str(packet_output.with_name("plan.json")),
        "preparation_receipt_output": getattr(args, "preparation_receipt_output", "") or str(packet_output.with_name("preparation_receipt.json")),
    }


def maybe_emit_repair_packet(
    args: argparse.Namespace,
    *,
    state: dict,
    report: dict,
    repair_handoff: dict | None,
    selection_receipt: dict | None = None,
    preparation_receipt: dict | None = None,
    repair_receipt: dict | None = None,
) -> dict | None:
    packet_output = resolve_repair_packet_output(args)
    if not packet_output:
        return None

    state_handoff = build_repair_handoff(state)
    handoff = state_handoff
    if repair_handoff and repair_handoff.get("from_state") == state["state"]:
        handoff = repair_handoff

    packet = build_packet_from_runtime_truth(
        state=state,
        artifact_root=packet_output.parent,
        doctor_run_id=args.doctor_run_id,
        doctor_level=args.doctor_level,
        target_path=args.target_path,
        target_classification=args.target_classification,
        baseline_identity=args.baseline_identity,
        intended_run_class=args.intended_run_class,
        execution_surface_identity=args.execution_surface_identity,
        repair_handoff=handoff,
        final_result=args.final_result or "",
        prompt_identity=args.prompt_identity or "",
        task_identity=args.task_identity or "",
        prompt_identity_ok=getattr(args, "prompt_identity_ok", False),
        readback=args.readback or "",
        scenario_proof=args.scenario_proof or "",
        target_identity_file=args.target_identity_file or "",
        clean_surface=getattr(args, "clean_surface", False),
        artifact_viable=getattr(args, "artifact_viable", False),
        helper_ok=getattr(args, "helper_ok", False),
        credentials_ok=getattr(args, "credentials_ok", False),
        artifact_path=args.artifact_path or "",
        helper_path=args.helper_path or "",
        credential_env=list(getattr(args, "credential_env", [])),
        refresh_output=args.refresh_output or "",
        refresh_event_type=args.refresh_event_type or "",
        refresh_recovery_status=args.refresh_recovery_status or "NOT_REQUIRED",
        refresh_reverification_complete=getattr(args, "refresh_reverification_complete", False),
        refresh_use_bundle=getattr(args, "refresh_use_bundle", False),
        refresh_use_closure=getattr(args, "refresh_use_closure", False),
        output_defaults_overrides=packet_output_defaults(args, packet_output),
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        repair_receipt=repair_receipt,
        report=report,
    )
    save_json(packet_output, packet)
    return packet


def maybe_emit_repair_receipt(
    args: argparse.Namespace,
    *,
    starting_repair_packet: dict | None,
    previous_repair_receipt: dict | None,
    state: dict,
    report: dict,
) -> dict | None:
    if not starting_repair_packet:
        return None
    receipt = build_artifact_repair_receipt(
        starting_packet=starting_repair_packet,
        resulting_state=state,
        report=report,
        previous_receipt=previous_repair_receipt,
    )
    receipt_output = resolve_repair_receipt_output(args)
    if receipt_output:
        save_json(receipt_output, receipt)
    return receipt


def run_python_capture(script: Path, args: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, str(script), *args]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return completed.returncode, completed.stdout


def allow(state: dict, target: str, next_safe_step: str) -> dict:
    state["state"] = target
    state["next_safe_step"] = next_safe_step
    return state


def enter_blocked_state(
    state: dict,
    *,
    target: str,
    closure_status: str,
    blocking_reason: str,
    next_allowed_transition: str,
    narrow_next_safe_step: str,
    missing_sections: list[str] | None = None,
) -> dict:
    state["state"] = target
    state["closure"]["status"] = closure_status
    state["closure"]["blocking_reason"] = blocking_reason
    state["closure"]["next_allowed_transition"] = next_allowed_transition
    state["closure"]["narrow_next_safe_step"] = narrow_next_safe_step
    state["closure"]["missing_sections"] = list(missing_sections or [])
    state["next_safe_step"] = narrow_next_safe_step
    return state


def gate_target_surface(state: dict) -> tuple[bool, str]:
    if state["target_surface"]["status"] != "ATTESTED":
        return False, "TARGET_SURFACE_NOT_ATTESTED"
    return True, ""


def gate_doctor(state: dict) -> tuple[bool, str]:
    if state["doctor"]["status"] != "PASS":
        return False, "DOCTOR_NOT_GREEN"
    return True, ""


def gate_integrity(state: dict) -> tuple[bool, str]:
    if not state["integrity"]["exact_task_identity_ok"]:
        return False, "EXACT_TASK_IDENTITY_NOT_CONFIRMED"
    return True, ""


def gate_artifacts(state: dict) -> tuple[bool, str]:
    if not state["execution"]["artifact_bundle_present"]:
        return False, "ARTIFACT_BUNDLE_MISSING"
    return True, ""


def gate_proof_bundle(state: dict) -> tuple[bool, str]:
    if state["proof_bundle"]["status"] == "COMPLETE":
        return True, ""
    if state["proof_bundle"]["status"] == "INVALID":
        return False, "INVALID_PROOF_BUNDLE"
    return False, "MISSING_PROOF_SECTIONS"


def blockers_for_target(state: dict, target: str) -> list[str]:
    blockers: list[str] = []

    if target == "TARGET_SURFACE_ATTESTED":
        ok, reason = gate_target_surface(state)
        if not ok:
            blockers.append(reason)
        return blockers

    if target == "READY":
        for gate in (gate_target_surface, gate_doctor, gate_integrity):
            ok, reason = gate(state)
            if not ok:
                blockers.append(reason)
        return blockers

    if target == "EXECUTION_COMPLETED":
        for gate in (gate_target_surface, gate_doctor, gate_integrity):
            ok, reason = gate(state)
            if not ok:
                blockers.append(reason)
        if state["execution"]["status"] != "COMPLETED":
            blockers.append("EXECUTION_NOT_COMPLETED")
        return blockers

    if target == "PROOF_BUNDLE_COMPLETE":
        ok, reason = gate_artifacts(state)
        if not ok:
            blockers.append(reason)
        ok, reason = gate_proof_bundle(state)
        if not ok:
            blockers.append(reason)
        return blockers

    if target == "CLOSURE_ACCEPTED":
        for gate in (gate_artifacts, gate_proof_bundle, gate_recovery):
            ok, reason = gate(state)
            if not ok:
                blockers.append(reason)
        return blockers

    return blockers


def dominant_blocker(target: str, blockers: list[str]) -> str:
    for candidate in TRANSITION_PRECEDENCE.get(target, []):
        if candidate in blockers:
            return candidate
    return blockers[0] if blockers else ""


def apply_dominant_blocker_to_state(state: dict, dominant: str) -> dict:
    if dominant == "TARGET_SURFACE_NOT_ATTESTED":
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "TARGET_SURFACE_NOT_ATTESTED"
        state["closure"]["next_allowed_transition"] = "TARGET_SURFACE_ATTESTED"
        state["closure"]["narrow_next_safe_step"] = "attest target surface"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return state

    if dominant == "DOCTOR_NOT_GREEN":
        return enter_blocked_state(
            state,
            target="DOCTOR_BLOCKED",
            closure_status="CLAIMED_NOT_ACCEPTED",
            blocking_reason="DOCTOR_NOT_GREEN",
            next_allowed_transition="DOCTOR_READINESS",
            narrow_next_safe_step="run doctor and clear blocking failure classes",
        )

    if dominant == "EXACT_TASK_IDENTITY_NOT_CONFIRMED":
        state["integrity"]["status"] = "FAIL"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "EXACT_TASK_IDENTITY_NOT_CONFIRMED"
        state["closure"]["next_allowed_transition"] = "READY"
        state["closure"]["narrow_next_safe_step"] = "restore exact prompt and task identity"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return state

    if dominant == "EXECUTION_NOT_COMPLETED":
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "EXECUTION_NOT_COMPLETED"
        state["closure"]["next_allowed_transition"] = "EXECUTION_COMPLETED"
        state["closure"]["narrow_next_safe_step"] = "complete bounded execution on the attested target surface"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return state

    if dominant == "ARTIFACT_BUNDLE_MISSING":
        state["state"] = "EXECUTION_COMPLETED"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "ARTIFACT_BUNDLE_MISSING"
        state["closure"]["next_allowed_transition"] = "PROOF_BUNDLE_COMPLETION"
        state["closure"]["narrow_next_safe_step"] = "capture the final result artifact and rebuild the proof bundle"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return state

    if dominant == "INVALID_PROOF_BUNDLE":
        return enter_blocked_state(
            state,
            target="PROOF_BUNDLE_INVALID",
            closure_status="CLAIMED_NOT_ACCEPTED",
            blocking_reason="INVALID_PROOF_BUNDLE",
            next_allowed_transition="PROOF_BUNDLE_REPAIR",
            narrow_next_safe_step="repair the final result artifact and rebuild the proof bundle",
            missing_sections=list(state["proof_bundle"]["missing_sections"]),
        )

    if dominant == "MISSING_PROOF_SECTIONS":
        return enter_blocked_state(
            state,
            target="PROOF_BUNDLE_PARTIAL",
            closure_status="CLAIMED_NOT_ACCEPTED",
            blocking_reason="MISSING_PROOF_SECTIONS",
            next_allowed_transition="PROOF_BUNDLE_COMPLETION",
            narrow_next_safe_step="complete the missing proof sections",
            missing_sections=list(state["proof_bundle"]["missing_sections"]),
        )

    if dominant == "RECOVERY_REVERIFICATION_INCOMPLETE":
        return enter_blocked_state(
            state,
            target="RECOVERY_PENDING",
            closure_status="CLAIMED_NOT_ACCEPTED",
            blocking_reason="RECOVERY_REVERIFICATION_INCOMPLETE",
            next_allowed_transition="RECOVERY_REVERIFICATION",
            narrow_next_safe_step="run reverification against the attested target surface",
        )

    return state


def build_transition_block_report(state: dict, *, target: str, blockers: list[str], dominant: str) -> dict:
    return {
        "schema_version": "spine_block_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "target_state": target,
        "blockers": blockers,
        "dominant_blocker": dominant,
        "resulting_state": state["state"],
        "closure_status": state["closure"]["status"],
        "blocking_reason": state["closure"]["blocking_reason"],
        "next_allowed_transition": state["closure"]["next_allowed_transition"],
        "next_safe_step": state["next_safe_step"],
    }


def deny_transition(state: dict, *, target: str, blockers: list[str], dominant: str) -> tuple[int, dict, dict]:
    next_state = apply_dominant_blocker_to_state(state, dominant)
    report = build_transition_block_report(next_state, target=target, blockers=blockers, dominant=dominant)
    return 2, next_state, report


def deny_simple(state: dict, *, target: str, reason: str) -> tuple[int, dict, dict]:
    report = {
        "schema_version": "spine_block_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "target_state": target,
        "blockers": [reason],
        "dominant_blocker": reason,
        "resulting_state": state["state"],
        "closure_status": state["closure"]["status"],
        "blocking_reason": state["closure"]["blocking_reason"],
        "next_allowed_transition": state["closure"]["next_allowed_transition"],
        "next_safe_step": state["next_safe_step"],
    }
    return 2, state, report


def gate_recovery(state: dict) -> tuple[bool, str]:
    if state["recovery"]["status"] == "PENDING" and not state["recovery"]["reverification_complete"]:
        return False, "RECOVERY_REVERIFICATION_INCOMPLETE"
    return True, ""


def transition(state: dict, target: str) -> tuple[int, dict, dict | None]:
    current = state["state"]
    if current in TERMINAL_STATES:
        return deny_simple(state, target=target, reason="TERMINAL_STATE")

    blockers = blockers_for_target(state, target)
    if blockers:
        dominant = dominant_blocker(target, blockers)
        return deny_transition(state, target=target, blockers=blockers, dominant=dominant)

    if target == "TARGET_SURFACE_ATTESTED":
        return 0, allow(state, target, "run doctor readiness"), None

    if target == "READY":
        return 0, allow(state, target, "run execution"), None

    if target == "EXECUTION_COMPLETED":
        return 0, allow(state, target, "assemble proof bundle"), None

    if target == "PROOF_BUNDLE_COMPLETE":
        return 0, allow(state, target, "decide closure"), None

    if target == "CLOSURE_ACCEPTED":
        state["closure"]["status"] = "ACCEPTED"
        state["closure"]["blocking_reason"] = ""
        state["closure"]["next_allowed_transition"] = "NONE"
        state["closure"]["narrow_next_safe_step"] = "NONE"
        state["closure"]["missing_sections"] = []
        return 0, allow(state, target, "NONE"), None

    if target == "CLOSURE_REJECTED":
        state["closure"]["status"] = "REJECTED"
        state["closure"]["next_allowed_transition"] = "emit narrow next safe step"
        state["closure"]["narrow_next_safe_step"] = "emit narrow next safe step"
        return 0, allow(state, target, "emit narrow next safe step"), None

    return deny_simple(state, target=target, reason=f"UNKNOWN_TARGET_STATE:{target}")


def apply_bundle(state: dict, bundle: dict) -> tuple[int, dict, dict | None]:
    state["execution"]["artifact_bundle_present"] = bool(bundle.get("final_result", {}).get("present", False))
    state["proof_bundle"]["status"] = bundle.get("status", "INVALID")
    state["proof_bundle"]["missing_sections"] = list(bundle.get("missing_sections", []))

    if bundle.get("status") == "COMPLETE":
        return transition(state, "PROOF_BUNDLE_COMPLETE")

    if bundle.get("status") == "INVALID":
        return 0, enter_blocked_state(
            state,
            target="PROOF_BUNDLE_INVALID",
            closure_status="CLAIMED_NOT_ACCEPTED",
            blocking_reason="INVALID_PROOF_BUNDLE",
            next_allowed_transition="PROOF_BUNDLE_REPAIR",
            narrow_next_safe_step="repair the final result artifact and rebuild the proof bundle",
            missing_sections=list(bundle.get("missing_sections", [])),
        ), None
    return 0, enter_blocked_state(
        state,
        target="PROOF_BUNDLE_PARTIAL",
        closure_status="CLAIMED_NOT_ACCEPTED",
        blocking_reason="MISSING_PROOF_SECTIONS",
        next_allowed_transition="PROOF_BUNDLE_COMPLETION",
        narrow_next_safe_step="complete the missing proof sections",
        missing_sections=list(bundle.get("missing_sections", [])),
    ), None


def apply_doctor(state: dict, record: dict) -> tuple[int, dict, dict | None]:
    acceptable = record.get("final_verdict", "").startswith("ACCEPTABLE_")
    state["doctor"]["status"] = "PASS" if acceptable else "FAIL"
    state["doctor"]["blocking_failure_classes"] = list(record.get("blocking_failure_classes", []))

    if acceptable:
        if state["state"] == "DOCTOR_BLOCKED":
            state["state"] = "TARGET_SURFACE_ATTESTED" if state["target_surface"]["status"] == "ATTESTED" else "INITIALIZED"
        state["closure"]["status"] = "OPEN"
        state["closure"]["blocking_reason"] = ""
        state["closure"]["next_allowed_transition"] = "READY"
        state["closure"]["narrow_next_safe_step"] = "confirm exact task identity"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = "confirm exact task identity"
        return 0, state, None

    return 0, enter_blocked_state(
        state,
        target="DOCTOR_BLOCKED",
        closure_status="CLAIMED_NOT_ACCEPTED",
        blocking_reason="DOCTOR_NOT_GREEN",
        next_allowed_transition="DOCTOR_READINESS",
        narrow_next_safe_step=record.get("recommended_next_safe_step", "run doctor readiness"),
    ), None


def apply_target_surface(state: dict, *, identity: str, baseline_relation: str) -> dict:
    state["target_surface"]["status"] = "ATTESTED"
    state["target_surface"]["identity"] = identity
    state["target_surface"]["baseline_relation"] = baseline_relation
    return state


def apply_integrity(state: dict, *, prompt_identity: str, task_identity: str) -> dict:
    exact_ok = bool(prompt_identity.strip() and task_identity.strip())
    state["integrity"]["status"] = "PASS" if exact_ok else "FAIL"
    state["integrity"]["exact_task_identity_ok"] = exact_ok
    return state


def maybe_advance_to_target_surface_attested(state: dict) -> tuple[int, dict, dict | None]:
    if state["state"] == "INITIALIZED":
        return transition(state, "TARGET_SURFACE_ATTESTED")
    return 0, state, None


def maybe_advance_to_ready(state: dict) -> tuple[int, dict, dict | None]:
    if state["state"] in {"INITIALIZED", "TARGET_SURFACE_ATTESTED"}:
        return transition(state, "READY")
    return 0, state, None


def maybe_advance_to_execution_completed(state: dict) -> tuple[int, dict, dict | None]:
    if state["state"] == "READY":
        state["execution"]["status"] = "COMPLETED"
        return transition(state, "EXECUTION_COMPLETED")
    return 0, state, None


def apply_closure(state: dict, verdict: dict) -> tuple[int, dict, dict | None]:
    state["closure"]["status"] = verdict["closure_status"]
    state["closure"]["blocking_reason"] = verdict["blocking_reason"]
    state["closure"]["next_allowed_transition"] = verdict["next_allowed_transition"]
    state["closure"]["narrow_next_safe_step"] = verdict["narrow_next_safe_step"]
    state["closure"]["missing_sections"] = list(verdict["missing_sections"])
    state["next_safe_step"] = verdict["narrow_next_safe_step"]

    if verdict["closure_status"] == "ACCEPTED":
        return transition(state, "CLOSURE_ACCEPTED")

    if verdict["closure_status"] == "REJECTED":
        return transition(state, "CLOSURE_REJECTED")

    if verdict["blocking_reason"] == "INVALID_PROOF_BUNDLE":
        state["state"] = "PROOF_BUNDLE_INVALID"
        return 0, state, None

    if verdict["blocking_reason"] == "MISSING_PROOF_SECTIONS":
        state["state"] = "PROOF_BUNDLE_PARTIAL"
        return 0, state, None

    if state["proof_bundle"]["status"] == "COMPLETE":
        state["state"] = "PROOF_BUNDLE_COMPLETE"
    else:
        state["state"] = "EXECUTION_COMPLETED"
    return 0, state, None


def build_worked_orchestration_artifact(
    *,
    state: dict,
    doctor_record: dict | None,
    resume_applied: bool,
    resume_from_state: str,
    repair_handoff: dict | None,
    missing_continuation_inputs: list[str],
    selection_receipt: dict | None,
    preparation_receipt: dict | None,
    repair_packet: dict | None,
    bundle: dict | None,
    closure: dict | None,
    refresh_report: dict | None,
    comparison: dict | None,
) -> dict:
    doctor_record = doctor_record or {
        "final_verdict": "NOT_RUN",
        "blocking_failure_classes": [],
    }
    bundle = bundle or {
        "status": state["proof_bundle"]["status"],
        "missing_sections": list(state["proof_bundle"]["missing_sections"]),
    }
    closure = closure or {
        "closure_status": state["closure"]["status"],
        "blocking_reason": state["closure"]["blocking_reason"],
    }
    return {
        "schema_version": "worked_orchestration_artifact_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "doctor": {
            "final_verdict": doctor_record["final_verdict"],
            "blocking_failure_classes": list(doctor_record["blocking_failure_classes"]),
        },
        "resume": {
            "applied": resume_applied,
            "from_state": resume_from_state,
        },
        "repair_handoff": {
            "applied": repair_handoff is not None,
            "from_state": repair_handoff["from_state"] if repair_handoff else "",
            "required_inputs": repair_handoff_required_input_ids(repair_handoff),
            "missing_inputs": list(missing_continuation_inputs),
        },
        "repair_packet": {
            **repair_packet_summary(repair_packet, state),
        },
        "repair_history": repair_history_summary(repair_packet, state),
        "resumability": report_resumability_fields(state, repair_handoff),
        "selection": {
            "applied": selection_receipt is not None,
            "selected_mode": selection_receipt["selected_mode"] if selection_receipt else "",
            "selected_with_preparation": selection_receipt["selected_with_preparation"] if selection_receipt else False,
        },
        "preparation": {
            "applied": preparation_receipt is not None,
            "ready_for_closure": preparation_receipt["ready_for_closure"] if preparation_receipt else False,
        },
        "bundle": {
            "status": bundle["status"],
            "missing_sections": list(bundle["missing_sections"]),
        },
        "closure": {
            "closure_status": closure["closure_status"],
            "blocking_reason": closure["blocking_reason"],
        },
        "refresh": {
            "applied": refresh_report is not None,
            "event_type": refresh_report["event_type"] if refresh_report else "",
            "resulting_closure_status": refresh_report["resulting_closure_status"] if refresh_report else "",
        },
        "comparison": {
            "applied": comparison is not None,
            "verdict": comparison["verdict"] if comparison else "",
            "reasons": list(comparison["reasons"]) if comparison else [],
        },
        "resulting_state": state["state"],
        "current_closure_status": state["closure"]["status"],
        "next_safe_step": state["next_safe_step"],
    }


def build_error_report(state: dict, *, reason: str, stopping_stage: str = "doctor") -> dict:
    return {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "ERROR",
        "stopping_stage": stopping_stage,
        "reason": reason,
        "doctor_verdict": "",
        "resume_applied": False,
        "resume_from_state": "",
        "repair_handoff_applied": False,
        "repair_handoff_from_state": "",
        "repair_handoff_required_inputs": [],
        "missing_continuation_inputs": [],
        "selection_applied": False,
        "selected_mode": "",
        "selected_with_preparation": False,
        "preparation_applied": False,
        "preparation_ready_for_closure": False,
        "bundle_status": "",
        "closure_status": "",
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "blockers": [],
        "dominant_blocker": "",
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }


def build_blocked_report(state: dict, doctor_record: dict) -> dict:
    return {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "BLOCKED",
        "stopping_stage": "doctor",
        "reason": "DOCTOR_NOT_GREEN",
        "doctor_verdict": doctor_record["final_verdict"],
        "resume_applied": False,
        "resume_from_state": "",
        "repair_handoff_applied": False,
        "repair_handoff_from_state": "",
        "repair_handoff_required_inputs": [],
        "missing_continuation_inputs": [],
        "selection_applied": False,
        "selected_mode": "",
        "selected_with_preparation": False,
        "preparation_applied": False,
        "preparation_ready_for_closure": False,
        "bundle_status": "",
        "closure_status": state["closure"]["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "blockers": list(state["doctor"]["blocking_failure_classes"]),
        "dominant_blocker": "DOCTOR_NOT_GREEN",
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }


def build_transition_blocked_report(
    state: dict,
    *,
    stopping_stage: str,
    doctor_verdict: str,
    resume_applied: bool,
    resume_from_state: str,
    repair_handoff: dict | None,
    missing_continuation_inputs: list[str],
    selection_applied: bool,
    selected_mode: str,
    selected_with_preparation: bool,
    preparation_applied: bool,
    preparation_ready_for_closure: bool,
    block_report: dict,
) -> dict:
    return {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "BLOCKED",
        "stopping_stage": stopping_stage,
        "reason": block_report["dominant_blocker"],
        "doctor_verdict": doctor_verdict,
        "resume_applied": resume_applied,
        "resume_from_state": resume_from_state,
        "repair_handoff_applied": repair_handoff is not None,
        "repair_handoff_from_state": repair_handoff["from_state"] if repair_handoff else "",
        "repair_handoff_required_inputs": repair_handoff_required_input_ids(repair_handoff),
        "missing_continuation_inputs": list(missing_continuation_inputs),
        "selection_applied": selection_applied,
        "selected_mode": selected_mode,
        "selected_with_preparation": selected_with_preparation,
        "preparation_applied": preparation_applied,
        "preparation_ready_for_closure": preparation_ready_for_closure,
        "bundle_status": state["proof_bundle"]["status"],
        "closure_status": state["closure"]["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "blockers": list(block_report["blockers"]),
        "dominant_blocker": block_report["dominant_blocker"],
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }


def build_repair_handoff_blocked_report(
    state: dict,
    *,
    doctor_verdict: str,
    resume_applied: bool,
    resume_from_state: str,
    repair_handoff: dict,
    missing_inputs: list[str],
    selection_applied: bool,
    selected_mode: str,
    selected_with_preparation: bool,
    preparation_applied: bool,
    preparation_ready_for_closure: bool,
) -> dict:
    return {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "BLOCKED",
        "stopping_stage": "repair_handoff",
        "reason": "CONTINUATION_INPUTS_MISSING",
        "doctor_verdict": doctor_verdict,
        "resume_applied": resume_applied,
        "resume_from_state": resume_from_state,
        "repair_handoff_applied": True,
        "repair_handoff_from_state": repair_handoff["from_state"],
        "repair_handoff_required_inputs": repair_handoff_required_input_ids(repair_handoff),
        "missing_continuation_inputs": list(missing_inputs),
        "selection_applied": selection_applied,
        "selected_mode": selected_mode,
        "selected_with_preparation": selected_with_preparation,
        "preparation_applied": preparation_applied,
        "preparation_ready_for_closure": preparation_ready_for_closure,
        "bundle_status": state["proof_bundle"]["status"],
        "closure_status": state["closure"]["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "blockers": list(missing_inputs),
        "dominant_blocker": "CONTINUATION_INPUTS_MISSING",
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }


def build_canonical_run_artifact(*, state: dict, report: dict, worked: dict, repair_packet: dict | None) -> dict:
    return {
        "schema_version": "canonical_run_artifact_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "report": {
            "result": report["result"],
            "stopping_stage": report["stopping_stage"],
            "reason": report["reason"],
            "doctor_verdict": report["doctor_verdict"],
            "resume_applied": report["resume_applied"],
            "resume_from_state": report["resume_from_state"],
            "repair_handoff_applied": report.get("repair_handoff_applied", False),
            "repair_handoff_from_state": report.get("repair_handoff_from_state", ""),
            "repair_handoff_required_inputs": list(report.get("repair_handoff_required_inputs", [])),
            "missing_continuation_inputs": list(report.get("missing_continuation_inputs", [])),
            "selection_applied": report["selection_applied"],
            "selected_mode": report["selected_mode"],
            "selected_with_preparation": report["selected_with_preparation"],
            "preparation_applied": report["preparation_applied"],
            "preparation_ready_for_closure": report["preparation_ready_for_closure"],
            "bundle_status": report["bundle_status"],
            "closure_status": report["closure_status"],
            "refresh_applied": report["refresh_applied"],
            "comparison_applied": report["comparison_applied"],
            "blockers": list(report["blockers"]),
            "dominant_blocker": report["dominant_blocker"],
            "resumability_status": report.get("resumability_status", ""),
            "resumability_family": report.get("resumability_family", ""),
            "resumability_active_pressures": list(report.get("resumability_active_pressures", [])),
            "resumability_repair_order": list(report.get("resumability_repair_order", [])),
            "resumability_requires_new_run": report.get("resumability_requires_new_run", False),
            "resumability_policy_type": report.get("resumability_policy_type", ""),
            "resumability_policy_next_step": report.get("resumability_policy_next_step", ""),
            "resumability_ready_now_steps": list(report.get("resumability_ready_now_steps", [])),
            "resumability_stale_artifact_ids": list(report.get("resumability_stale_artifact_ids", [])),
            "resumability_stale_subsurface_ids": list(report.get("resumability_stale_subsurface_ids", [])),
            "resulting_state": report["resulting_state"],
            "next_safe_step": report["next_safe_step"],
        },
        "resulting_state": {
            "state": state["state"],
            "closure_status": state["closure"]["status"],
            "blocking_reason": state["closure"]["blocking_reason"],
            "next_safe_step": state["next_safe_step"],
        },
        "worked_envelope": {
            "resulting_state": worked["resulting_state"],
            "current_closure_status": worked["current_closure_status"],
            "next_safe_step": worked["next_safe_step"],
        },
        "repair_packet": repair_packet_summary(repair_packet, state),
        "repair_history": repair_history_summary(repair_packet, state),
        "resumability": {
            "status": report.get("resumability_status", ""),
            "family": report.get("resumability_family", ""),
            "active_pressures": list(report.get("resumability_active_pressures", [])),
            "repair_order": list(report.get("resumability_repair_order", [])),
            "requires_new_run": report.get("resumability_requires_new_run", False),
            "policy_type": report.get("resumability_policy_type", ""),
            "policy_next_step": report.get("resumability_policy_next_step", ""),
            "ready_now_steps": list(report.get("resumability_ready_now_steps", [])),
            "stale_artifact_ids": list(report.get("resumability_stale_artifact_ids", [])),
            "stale_subsurface_ids": list(report.get("resumability_stale_subsurface_ids", [])),
        },
    }


def emit_requested_artifacts(
    args: argparse.Namespace,
    *,
    state: dict,
    report: dict,
    doctor_record: dict | None = None,
    resume_applied: bool = False,
    resume_from_state: str = "",
    repair_handoff: dict | None = None,
    missing_continuation_inputs: list[str] | None = None,
    selection_receipt: dict | None = None,
    preparation_receipt: dict | None = None,
    repair_packet: dict | None = None,
    bundle: dict | None = None,
    closure: dict | None = None,
    refresh_report: dict | None = None,
    comparison: dict | None = None,
) -> None:
    if not (args.worked_artifact_output or args.run_artifact_output):
        return

    worked = build_worked_orchestration_artifact(
        state=state,
        doctor_record=doctor_record,
        resume_applied=resume_applied,
        resume_from_state=resume_from_state,
        repair_handoff=repair_handoff,
        missing_continuation_inputs=list(missing_continuation_inputs or []),
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        repair_packet=repair_packet,
        bundle=bundle,
        closure=closure,
        refresh_report=refresh_report,
        comparison=comparison,
    )
    if args.worked_artifact_output:
        save_json(Path(args.worked_artifact_output), worked)
    if args.run_artifact_output:
        canonical = build_canonical_run_artifact(state=state, report=report, worked=worked, repair_packet=repair_packet)
        save_json(Path(args.run_artifact_output), canonical)


def finalize_runtime_outputs(
    args: argparse.Namespace,
    *,
    state: dict,
    report: dict,
    doctor_record: dict | None = None,
    resume_applied: bool = False,
    resume_from_state: str = "",
    repair_handoff: dict | None = None,
    missing_continuation_inputs: list[str] | None = None,
    selection_receipt: dict | None = None,
    preparation_receipt: dict | None = None,
    starting_repair_packet: dict | None = None,
    previous_repair_receipt: dict | None = None,
    bundle: dict | None = None,
    closure: dict | None = None,
    refresh_report: dict | None = None,
    comparison: dict | None = None,
) -> None:
    if starting_repair_packet is None and getattr(args, "repair_packet_file", None):
        try:
            starting_repair_packet = load_repair_packet(Path(args.repair_packet_file))
        except ValueError:
            starting_repair_packet = None
    if previous_repair_receipt is None and getattr(args, "repair_receipt_file", None):
        try:
            previous_repair_receipt = load_repair_receipt(Path(args.repair_receipt_file))
        except ValueError:
            previous_repair_receipt = None
    if repair_handoff and repair_handoff.get("from_state") == state["state"]:
        current_handoff = repair_handoff
    else:
        current_handoff = maybe_emit_repair_handoff(args, state)
    if current_handoff and getattr(args, "repair_handoff_output", None):
        save_json(Path(args.repair_handoff_output), current_handoff)
    report.update(report_resumability_fields(state, current_handoff))
    if getattr(args, "report_output", None):
        save_json(Path(args.report_output), report)
    emitted_repair_receipt = maybe_emit_repair_receipt(
        args,
        starting_repair_packet=starting_repair_packet,
        previous_repair_receipt=previous_repair_receipt,
        state=state,
        report=report,
    )
    repair_packet = maybe_emit_repair_packet(
        args,
        state=state,
        report=report,
        repair_handoff=current_handoff,
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        repair_receipt=emitted_repair_receipt,
    )
    emit_requested_artifacts(
        args,
        state=state,
        report=report,
        doctor_record=doctor_record,
        resume_applied=resume_applied,
        resume_from_state=resume_from_state,
        repair_handoff=current_handoff,
        missing_continuation_inputs=missing_continuation_inputs,
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        repair_packet=repair_packet,
        bundle=bundle,
        closure=closure,
        refresh_report=refresh_report,
        comparison=comparison,
    )


def cmd_init(args: argparse.Namespace) -> int:
    state = default_state(args.run_id, args.task_class)
    save_state(Path(args.output), state)
    print(json.dumps({"result": "OK", "state": state["state"]}, ensure_ascii=True))
    return 0


def cmd_transition(args: argparse.Namespace) -> int:
    path = Path(args.state_file)
    state = load_state(path)
    code, next_state, block_report = transition(state, args.target)
    save_state(path, next_state)
    if code != 0:
        print(json.dumps(block_report, ensure_ascii=True))
        return code
    print(json.dumps({"result": "ALLOW", "state": next_state["state"]}, ensure_ascii=True))
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    state = load_state(Path(args.state_file))
    print(json.dumps(state, indent=2, ensure_ascii=True))
    return 0


def cmd_apply_bundle(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    bundle = load_json(Path(args.bundle_file))
    code, next_state, block_report = apply_bundle(state, bundle)
    save_state(state_path, next_state)
    if code != 0:
        print(json.dumps(block_report, ensure_ascii=True))
        return code
    print(json.dumps({"result": "OK", "state": next_state["state"], "proof_bundle": next_state["proof_bundle"]["status"]}, ensure_ascii=True))
    return 0


def cmd_apply_doctor(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    record = load_json(Path(args.doctor_file))
    code, next_state, block_report = apply_doctor(state, record)
    save_state(state_path, next_state)
    if code != 0:
        print(json.dumps(block_report, ensure_ascii=True))
        return code
    print(json.dumps({"result": "OK", "doctor": next_state["doctor"]["status"], "next_safe_step": next_state["next_safe_step"]}, ensure_ascii=True))
    return 0


def cmd_apply_closure(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    verdict = load_json(Path(args.closure_file))
    code, next_state, block_report = apply_closure(state, verdict)
    save_state(state_path, next_state)
    if code != 0:
        print(json.dumps(block_report, ensure_ascii=True))
        return code
    print(json.dumps({"result": "OK", "state": next_state["state"], "closure": next_state["closure"]["status"]}, ensure_ascii=True))
    return 0


def cmd_orchestrate(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    resume_applied = bool(args.resume_from_state)
    resume_from_state = args.resume_from_state or ""
    repair_handoff = None
    repair_handoff_applied = False
    continuation_missing_inputs: list[str] = []
    starting_repair_packet = None
    previous_repair_receipt = None
    selection_receipt = None
    selection_applied = False
    selected_mode = ""
    selected_with_preparation = False
    preparation_receipt = None
    preparation_applied = False
    preparation_ready_for_closure = False

    if args.mode_selection_receipt:
        try:
            selection_receipt = load_mode_selection_receipt(Path(args.mode_selection_receipt))
        except ValueError:
            report = build_error_report(state, reason="INVALID_MODE_SELECTION_RECEIPT", stopping_stage="selection")
            report["resume_applied"] = resume_applied
            report["resume_from_state"] = resume_from_state
            save_json(Path(args.report_output), report)
            finalize_runtime_outputs(
                args,
                state=state,
                report=report,
                resume_applied=resume_applied,
                resume_from_state=resume_from_state,
                repair_handoff=repair_handoff,
                missing_continuation_inputs=continuation_missing_inputs,
            )
            return 2
        selection_applied = True
        selected_mode = selection_receipt["selected_mode"]
        selected_with_preparation = bool(selection_receipt.get("selected_with_preparation", False))

    if getattr(args, "repair_receipt_file", None):
        try:
            previous_repair_receipt = load_repair_receipt(Path(args.repair_receipt_file))
        except ValueError:
            previous_repair_receipt = None

    if resume_applied:
        if getattr(args, "repair_packet_file", None):
            try:
                starting_repair_packet = load_repair_packet(Path(args.repair_packet_file))
            except ValueError:
                report = build_error_report(state, reason="INVALID_REPAIR_PACKET", stopping_stage="repair_packet")
                report["resume_applied"] = True
                report["resume_from_state"] = resume_from_state
                report["selection_applied"] = selection_applied
                report["selected_mode"] = selected_mode
                report["selected_with_preparation"] = selected_with_preparation
                save_json(Path(args.report_output), report)
                finalize_runtime_outputs(
                    args,
                    state=state,
                    report=report,
                    resume_applied=True,
                    resume_from_state=resume_from_state,
                    selection_receipt=selection_receipt,
                    previous_repair_receipt=previous_repair_receipt,
                )
                return 2
            if not selection_receipt and starting_repair_packet.get("selection_receipt"):
                selection_receipt = dict(starting_repair_packet["selection_receipt"])
                selection_applied = True
                selected_mode = selection_receipt.get("selected_mode", "")
                selected_with_preparation = bool(selection_receipt.get("selected_with_preparation", False))
            if previous_repair_receipt is None and starting_repair_packet.get("repair_receipt"):
                previous_repair_receipt = dict(starting_repair_packet["repair_receipt"])
        if state["state"] != resume_from_state:
            report = build_error_report(state, reason="RESUME_STATE_MISMATCH", stopping_stage="resume")
            report["resume_applied"] = True
            report["resume_from_state"] = resume_from_state
            report["selection_applied"] = selection_applied
            report["selected_mode"] = selected_mode
            report["selected_with_preparation"] = selected_with_preparation
            save_json(Path(args.report_output), report)
            finalize_runtime_outputs(
                args,
                state=state,
                report=report,
                resume_applied=True,
                resume_from_state=resume_from_state,
                selection_receipt=selection_receipt,
                starting_repair_packet=starting_repair_packet,
                previous_repair_receipt=previous_repair_receipt,
            )
            return 2
        if state["state"] in TERMINAL_STATES:
            state["closure"]["status"] = state["closure"]["status"] or "CLAIMED_NOT_ACCEPTED"
            state["closure"]["blocking_reason"] = "TERMINAL_STATE_NOT_RESUMABLE"
            state["closure"]["next_allowed_transition"] = "NONE"
            state["closure"]["narrow_next_safe_step"] = "start a new run instead of resuming a terminal state"
            state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
            report = {
                "schema_version": "orchestration_report_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "result": "BLOCKED",
                "stopping_stage": "resume",
                "reason": "TERMINAL_STATE_NOT_RESUMABLE",
                "doctor_verdict": "",
                "resume_applied": True,
                "resume_from_state": resume_from_state,
                "selection_applied": selection_applied,
                "selected_mode": selected_mode,
                "selected_with_preparation": selected_with_preparation,
                "preparation_applied": False,
                "preparation_ready_for_closure": False,
                "bundle_status": state["proof_bundle"]["status"],
                "closure_status": state["closure"]["status"],
                "refresh_applied": False,
                "refresh_resulting_closure_status": "",
                "comparison_applied": False,
                "comparison_verdict": "",
                "blockers": ["TERMINAL_STATE_NOT_RESUMABLE"],
                "dominant_blocker": "TERMINAL_STATE_NOT_RESUMABLE",
                "resulting_state": state["state"],
                "next_safe_step": state["next_safe_step"],
            }
            save_state(state_path, state)
            save_json(Path(args.report_output), report)
            finalize_runtime_outputs(
                args,
                state=state,
                report=report,
                resume_applied=True,
                resume_from_state=resume_from_state,
                selection_receipt=selection_receipt,
                starting_repair_packet=starting_repair_packet,
                previous_repair_receipt=previous_repair_receipt,
            )
            print(json.dumps({"result": "BLOCKED", "stopping_stage": "resume", "reason": "TERMINAL_STATE_NOT_RESUMABLE"}, ensure_ascii=True))
            return 0
        if getattr(args, "repair_handoff_file", None):
            try:
                repair_handoff = load_repair_handoff(Path(args.repair_handoff_file))
            except ValueError:
                report = build_error_report(state, reason="INVALID_REPAIR_HANDOFF", stopping_stage="repair_handoff")
                report["resume_applied"] = True
                report["resume_from_state"] = resume_from_state
                report["repair_handoff_applied"] = True
                report["repair_handoff_from_state"] = state["state"]
                report["repair_handoff_required_inputs"] = []
                report["missing_continuation_inputs"] = []
                report["selection_applied"] = selection_applied
                report["selected_mode"] = selected_mode
                report["selected_with_preparation"] = selected_with_preparation
                save_json(Path(args.report_output), report)
                finalize_runtime_outputs(
                    args,
                    state=state,
                    report=report,
                    resume_applied=True,
                    resume_from_state=resume_from_state,
                    missing_continuation_inputs=continuation_missing_inputs,
                    selection_receipt=selection_receipt,
                    starting_repair_packet=starting_repair_packet,
                    previous_repair_receipt=previous_repair_receipt,
                )
                return 2
            repair_handoff_applied = True
            if repair_handoff["run_id"] != state["run_id"] or repair_handoff["from_state"] != state["state"]:
                report = build_error_report(state, reason="REPAIR_HANDOFF_STATE_MISMATCH", stopping_stage="repair_handoff")
                report["resume_applied"] = True
                report["resume_from_state"] = resume_from_state
                report["repair_handoff_applied"] = True
                report["repair_handoff_from_state"] = repair_handoff["from_state"]
                report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(repair_handoff)
                report["missing_continuation_inputs"] = []
                report["selection_applied"] = selection_applied
                report["selected_mode"] = selected_mode
                report["selected_with_preparation"] = selected_with_preparation
                save_json(Path(args.report_output), report)
                finalize_runtime_outputs(
                    args,
                    state=state,
                    report=report,
                    resume_applied=True,
                    resume_from_state=resume_from_state,
                    repair_handoff=repair_handoff,
                    selection_receipt=selection_receipt,
                    starting_repair_packet=starting_repair_packet,
                    previous_repair_receipt=previous_repair_receipt,
                )
                return 2
        if repair_handoff is None and starting_repair_packet and starting_repair_packet.get("repair_handoff"):
            candidate_handoff = dict(starting_repair_packet["repair_handoff"])
            if candidate_handoff.get("run_id") == state["run_id"] and candidate_handoff.get("from_state") == state["state"]:
                repair_handoff = candidate_handoff
                repair_handoff_applied = True
        current_resume_handoff = repair_handoff or build_repair_handoff(state)
        repair_handoff = current_resume_handoff
        if not current_resume_handoff.get("continuation_allowed", False):
            report = {
                "schema_version": "orchestration_report_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "result": "BLOCKED",
                "stopping_stage": "resume",
                "reason": "STATE_NOT_RESUMABLE",
                "doctor_verdict": "",
                "resume_applied": True,
                "resume_from_state": resume_from_state,
                "repair_handoff_applied": repair_handoff_applied,
                "repair_handoff_from_state": current_resume_handoff["from_state"],
                "repair_handoff_required_inputs": repair_handoff_required_input_ids(current_resume_handoff),
                "missing_continuation_inputs": [],
                "selection_applied": selection_applied,
                "selected_mode": selected_mode,
                "selected_with_preparation": selected_with_preparation,
                "preparation_applied": False,
                "preparation_ready_for_closure": False,
                "bundle_status": state["proof_bundle"]["status"],
                "closure_status": state["closure"]["status"],
                "refresh_applied": False,
                "refresh_resulting_closure_status": "",
                "comparison_applied": False,
                "comparison_verdict": "",
                "blockers": [current_resume_handoff["resumability"]["family"]],
                "dominant_blocker": "STATE_NOT_RESUMABLE",
                "resulting_state": state["state"],
                "next_safe_step": state["next_safe_step"],
            }
            save_state(state_path, state)
            save_json(Path(args.report_output), report)
            finalize_runtime_outputs(
                args,
                state=state,
                report=report,
                resume_applied=True,
                resume_from_state=resume_from_state,
                repair_handoff=current_resume_handoff,
                selection_receipt=selection_receipt,
                starting_repair_packet=starting_repair_packet,
                previous_repair_receipt=previous_repair_receipt,
            )
            print(json.dumps({"result": "BLOCKED", "stopping_stage": "resume", "reason": "STATE_NOT_RESUMABLE"}, ensure_ascii=True))
            return 0
        apply_repair_handoff_defaults(args, current_resume_handoff)
        continuation_missing_inputs = missing_continuation_inputs(args, current_resume_handoff)
        if continuation_missing_inputs:
            out_of_order_steps = repair_policy_out_of_order_steps(args, current_resume_handoff, continuation_missing_inputs)
            if out_of_order_steps:
                report = {
                    "schema_version": "orchestration_report_v0",
                    "run_id": state["run_id"],
                    "task_class": state["task_class"],
                    "result": "BLOCKED",
                    "stopping_stage": "repair_handoff",
                    "reason": "REPAIR_POLICY_STEP_OUT_OF_ORDER",
                    "doctor_verdict": "",
                    "resume_applied": True,
                    "resume_from_state": resume_from_state,
                    "repair_handoff_applied": repair_handoff_applied,
                    "repair_handoff_from_state": current_resume_handoff["from_state"],
                    "repair_handoff_required_inputs": repair_handoff_required_input_ids(current_resume_handoff),
                    "missing_continuation_inputs": list(continuation_missing_inputs),
                    "selection_applied": selection_applied,
                    "selected_mode": selected_mode,
                    "selected_with_preparation": selected_with_preparation,
                    "preparation_applied": False,
                    "preparation_ready_for_closure": False,
                    "bundle_status": state["proof_bundle"]["status"],
                    "closure_status": state["closure"]["status"],
                    "refresh_applied": False,
                    "refresh_resulting_closure_status": "",
                    "comparison_applied": False,
                    "comparison_verdict": "",
                    "blockers": list(out_of_order_steps),
                    "dominant_blocker": "REPAIR_POLICY_STEP_OUT_OF_ORDER",
                    "resulting_state": state["state"],
                    "next_safe_step": state["next_safe_step"],
                }
                save_state(state_path, state)
                save_json(Path(args.report_output), report)
                finalize_runtime_outputs(
                    args,
                    state=state,
                    report=report,
                    resume_applied=True,
                    resume_from_state=resume_from_state,
                    repair_handoff=current_resume_handoff,
                    missing_continuation_inputs=continuation_missing_inputs,
                    selection_receipt=selection_receipt,
                    starting_repair_packet=starting_repair_packet,
                    previous_repair_receipt=previous_repair_receipt,
                )
                print(json.dumps({"result": "BLOCKED", "stopping_stage": "repair_handoff", "reason": "REPAIR_POLICY_STEP_OUT_OF_ORDER"}, ensure_ascii=True))
                return 0
            report = build_repair_handoff_blocked_report(
                state,
                doctor_verdict="",
                resume_applied=True,
                resume_from_state=resume_from_state,
                repair_handoff=current_resume_handoff,
                missing_inputs=continuation_missing_inputs,
                selection_applied=selection_applied,
                selected_mode=selected_mode,
                selected_with_preparation=selected_with_preparation,
                preparation_applied=False,
                preparation_ready_for_closure=False,
            )
            save_state(state_path, state)
            save_json(Path(args.report_output), report)
            finalize_runtime_outputs(
                args,
                state=state,
                report=report,
                resume_applied=True,
                resume_from_state=resume_from_state,
                repair_handoff=current_resume_handoff,
                missing_continuation_inputs=continuation_missing_inputs,
                selection_receipt=selection_receipt,
                starting_repair_packet=starting_repair_packet,
                previous_repair_receipt=previous_repair_receipt,
            )
            print(json.dumps({"result": "BLOCKED", "stopping_stage": "repair_handoff", "reason": "CONTINUATION_INPUTS_MISSING"}, ensure_ascii=True))
            return 0

    if selection_applied and selected_mode != "FULL_GOVERNED_PATH":
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "MODE_SELECTION_NOT_GOVERNED"
        state["closure"]["next_allowed_transition"] = "FOLLOW_SELECTED_MODE"
        state["closure"]["narrow_next_safe_step"] = "follow the selected lighter mode instead of entering governed orchestration"
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        report = {
            "schema_version": "orchestration_report_v0",
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "result": "BLOCKED",
            "stopping_stage": "selection",
            "reason": "MODE_SELECTION_NOT_GOVERNED",
            "doctor_verdict": "",
            "resume_applied": resume_applied,
            "resume_from_state": resume_from_state,
            "repair_handoff_applied": repair_handoff_applied,
            "repair_handoff_from_state": repair_handoff["from_state"] if repair_handoff else "",
            "repair_handoff_required_inputs": repair_handoff_required_input_ids(repair_handoff),
            "missing_continuation_inputs": list(continuation_missing_inputs),
            "selection_applied": True,
            "selected_mode": selected_mode,
            "selected_with_preparation": selected_with_preparation,
            "preparation_applied": False,
            "preparation_ready_for_closure": False,
            "bundle_status": "",
            "closure_status": state["closure"]["status"],
            "refresh_applied": False,
            "refresh_resulting_closure_status": "",
            "comparison_applied": False,
            "comparison_verdict": "",
            "blockers": ["MODE_SELECTION_NOT_GOVERNED"],
            "dominant_blocker": "MODE_SELECTION_NOT_GOVERNED",
            "resulting_state": state["state"],
            "next_safe_step": state["next_safe_step"],
        }
        save_state(state_path, state)
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
            starting_repair_packet=starting_repair_packet,
            previous_repair_receipt=previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "selection", "reason": "MODE_SELECTION_NOT_GOVERNED"}, ensure_ascii=True))
        return 0
    if selected_with_preparation:
        if not args.plan_output:
            args.plan_output = str(Path(args.report_output).with_name("plan.json"))
        if not args.preparation_receipt_output:
            args.preparation_receipt_output = str(Path(args.report_output).with_name("preparation_receipt.json"))
        if not args.preparation_artifact_root:
            args.preparation_artifact_root = str(Path(args.report_output).parent)

    state = apply_target_surface(
        state,
        identity=args.execution_surface_identity,
        baseline_relation=args.baseline_identity,
    )
    code, state, block_report = maybe_advance_to_target_surface_attested(state)
    if code != 0:
        report = build_transition_blocked_report(
            state,
            stopping_stage="target_surface_transition",
            doctor_verdict="",
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_applied=selection_applied,
            selected_mode=selected_mode,
            selected_with_preparation=selected_with_preparation,
            preparation_applied=preparation_applied,
            preparation_ready_for_closure=preparation_ready_for_closure,
            block_report=block_report,
        )
        save_state(state_path, state)
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
            starting_repair_packet=starting_repair_packet,
            previous_repair_receipt=previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "target_surface_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(state_path, state)

    doctor_args = [
        "--doctor-run-id", args.doctor_run_id,
        "--doctor-level", args.doctor_level,
        "--target-path", args.target_path,
        "--target-classification", args.target_classification,
        "--baseline-identity", args.baseline_identity,
        "--intended-run-class", args.intended_run_class,
        "--output", args.doctor_output,
    ]
    for enabled, flag in [
        (args.clean_surface, "--clean-surface"),
        (args.artifact_viable, "--artifact-viable"),
        (args.helper_ok, "--helper-ok"),
        (args.credentials_ok, "--credentials-ok"),
        (args.prompt_identity_ok, "--prompt-identity-ok"),
    ]:
        if enabled:
            doctor_args.append(flag)
    for flag, value in [
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--prompt-identity-file", args.prompt_identity_file),
        ("--expected-task-identity", args.task_identity),
        ("--target-identity-file", args.target_identity_file),
        ("--expected-target-identity", args.execution_surface_identity),
    ]:
        if value:
            doctor_args.extend([flag, value])
    for env_name in args.credential_env:
        doctor_args.extend(["--credential-env", env_name])

    code, _ = run_python_capture(DOCTOR, doctor_args)
    if code != 0:
        report = build_error_report(state, reason="DOCTOR_EXECUTION_FAILED")
        report["resume_applied"] = resume_applied
        report["resume_from_state"] = resume_from_state
        report["repair_handoff_applied"] = repair_handoff_applied
        report["repair_handoff_from_state"] = repair_handoff["from_state"] if repair_handoff else ""
        report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(repair_handoff)
        report["missing_continuation_inputs"] = list(continuation_missing_inputs)
        report["selection_applied"] = selection_applied
        report["selected_mode"] = selected_mode
        report["selected_with_preparation"] = selected_with_preparation
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
            starting_repair_packet=starting_repair_packet,
            previous_repair_receipt=previous_repair_receipt,
        )
        return code

    doctor_record = load_json(Path(args.doctor_output))
    code, state, block_report = apply_doctor(load_state(state_path), doctor_record)
    if code != 0:
        save_state(state_path, state)
        report = build_error_report(state, reason=block_report["dominant_blocker"], stopping_stage="doctor_apply")
        report["resume_applied"] = resume_applied
        report["resume_from_state"] = resume_from_state
        report["repair_handoff_applied"] = repair_handoff_applied
        report["repair_handoff_from_state"] = repair_handoff["from_state"] if repair_handoff else ""
        report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(repair_handoff)
        report["missing_continuation_inputs"] = list(continuation_missing_inputs)
        report["selection_applied"] = selection_applied
        report["selected_mode"] = selected_mode
        report["selected_with_preparation"] = selected_with_preparation
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            doctor_record=doctor_record,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
            starting_repair_packet=starting_repair_packet,
            previous_repair_receipt=previous_repair_receipt,
        )
        print(json.dumps({"result": "ERROR", "stopping_stage": "doctor_apply", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    state = apply_integrity(
        state,
        prompt_identity=args.prompt_identity,
        task_identity=args.task_identity,
    )
    code, state, block_report = maybe_advance_to_ready(state)
    if code != 0:
        save_state(state_path, state)
        report = build_transition_blocked_report(
            state,
            stopping_stage="ready_transition",
            doctor_verdict=doctor_record["final_verdict"],
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_applied=selection_applied,
            selected_mode=selected_mode,
            selected_with_preparation=selected_with_preparation,
            preparation_applied=preparation_applied,
            preparation_ready_for_closure=preparation_ready_for_closure,
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            doctor_record=doctor_record,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
            starting_repair_packet=starting_repair_packet,
            previous_repair_receipt=previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "ready_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(state_path, state)
    if state["doctor"]["status"] != "PASS":
        report = build_blocked_report(state, doctor_record)
        report["resume_applied"] = resume_applied
        report["resume_from_state"] = resume_from_state
        report["repair_handoff_applied"] = repair_handoff_applied
        report["repair_handoff_from_state"] = repair_handoff["from_state"] if repair_handoff else ""
        report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(repair_handoff)
        report["missing_continuation_inputs"] = list(continuation_missing_inputs)
        report["selection_applied"] = selection_applied
        report["selected_mode"] = selected_mode
        report["selected_with_preparation"] = selected_with_preparation
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            doctor_record=doctor_record,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
            starting_repair_packet=starting_repair_packet,
            previous_repair_receipt=previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "doctor"}, ensure_ascii=True))
        return 0

    code, state, block_report = maybe_advance_to_execution_completed(load_state(state_path))
    if code != 0:
        save_state(state_path, state)
        report = build_transition_blocked_report(
            state,
            stopping_stage="execution_transition",
            doctor_verdict=doctor_record["final_verdict"],
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_applied=selection_applied,
            selected_mode=selected_mode,
            selected_with_preparation=selected_with_preparation,
            preparation_applied=preparation_applied,
            preparation_ready_for_closure=preparation_ready_for_closure,
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            doctor_record=doctor_record,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "execution_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(state_path, state)

    if args.plan_output:
        artifact_root = args.preparation_artifact_root or str(Path(args.plan_output).parent)
        plan_args = [
            "--run-id", state["run_id"],
            "--task-class", args.task_class,
            "--artifact-root", artifact_root,
            "--baseline-identity", args.baseline_identity,
            "--execution-surface-identity", args.execution_surface_identity,
            "--prompt-identity", args.prompt_identity,
            "--task-identity", args.task_identity,
            "--output", args.plan_output,
        ]
        code, _ = run_python_capture(PROOF_PLAN, plan_args)
        if code != 0:
            report = build_error_report(state, reason="PROOF_PLAN_EXECUTION_FAILED", stopping_stage="preparation")
            report["resume_applied"] = resume_applied
            report["resume_from_state"] = resume_from_state
            report["repair_handoff_applied"] = repair_handoff_applied
            report["repair_handoff_from_state"] = repair_handoff["from_state"] if repair_handoff else ""
            report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(repair_handoff)
            report["missing_continuation_inputs"] = list(continuation_missing_inputs)
            report["selection_applied"] = selection_applied
            report["selected_mode"] = selected_mode
            report["selected_with_preparation"] = selected_with_preparation
            save_json(Path(args.report_output), report)
            return code
        preparation_applied = True

    bundle_args = [
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--output", args.bundle_output,
        "--run-id", state["run_id"],
        "--baseline-identity", args.baseline_identity,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
    ]
    if args.readback:
        bundle_args.extend(["--readback", args.readback])
    if args.scenario_proof:
        bundle_args.extend(["--scenario-proof", args.scenario_proof])
    code, _ = run_python_capture(BUNDLE, bundle_args)
    if code != 0:
        return code

    bundle = load_json(Path(args.bundle_output))
    if args.plan_output and args.preparation_receipt_output:
        code, _ = run_python_capture(
            PREPARATION_RECEIPT,
            [
                "--plan-file", args.plan_output,
                "--bundle-file", args.bundle_output,
                "--output", args.preparation_receipt_output,
            ],
        )
        if code != 0:
            report = build_error_report(state, reason="PREPARATION_RECEIPT_EXECUTION_FAILED", stopping_stage="preparation")
            report["resume_applied"] = resume_applied
            report["resume_from_state"] = resume_from_state
            report["repair_handoff_applied"] = repair_handoff_applied
            report["repair_handoff_from_state"] = repair_handoff["from_state"] if repair_handoff else ""
            report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(repair_handoff)
            report["missing_continuation_inputs"] = list(continuation_missing_inputs)
            report["selection_applied"] = selection_applied
            report["selected_mode"] = selected_mode
            report["selected_with_preparation"] = selected_with_preparation
            save_json(Path(args.report_output), report)
            return code
        preparation_receipt = load_json(Path(args.preparation_receipt_output))
        preparation_ready_for_closure = preparation_receipt["ready_for_closure"]

    code, state, block_report = apply_bundle(load_state(state_path), bundle)
    if code != 0:
        save_state(state_path, state)
        report = build_transition_blocked_report(
            state,
            stopping_stage="proof_bundle_transition",
            doctor_verdict=doctor_record["final_verdict"],
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_applied=selection_applied,
            selected_mode=selected_mode,
            selected_with_preparation=selected_with_preparation,
            preparation_applied=preparation_applied,
            preparation_ready_for_closure=preparation_ready_for_closure,
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            doctor_record=doctor_record,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
            preparation_receipt=preparation_receipt,
            bundle=bundle,
            starting_repair_packet=starting_repair_packet,
            previous_repair_receipt=previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "proof_bundle_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(state_path, state)

    code, _ = run_python_capture(CLOSURE, ["--state-file", args.state_file, "--bundle-file", args.bundle_output, "--output", args.closure_output])
    if code != 0:
        return code

    closure = load_json(Path(args.closure_output))
    code, state, block_report = apply_closure(load_state(state_path), closure)
    if code != 0:
        save_state(state_path, state)
        report = build_transition_blocked_report(
            state,
            stopping_stage="closure_transition",
            doctor_verdict=doctor_record["final_verdict"],
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_applied=selection_applied,
            selected_mode=selected_mode,
            selected_with_preparation=selected_with_preparation,
            preparation_applied=preparation_applied,
            preparation_ready_for_closure=preparation_ready_for_closure,
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=state,
            report=report,
            doctor_record=doctor_record,
            resume_applied=resume_applied,
            resume_from_state=resume_from_state,
            repair_handoff=repair_handoff,
            missing_continuation_inputs=continuation_missing_inputs,
            selection_receipt=selection_receipt,
            preparation_receipt=preparation_receipt,
            bundle=bundle,
            closure=closure,
            starting_repair_packet=starting_repair_packet,
            previous_repair_receipt=previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "closure_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(state_path, state)

    state = load_state(state_path)
    refresh_report = None
    comparison = None
    refresh_applied = False
    refresh_resulting_closure_status = ""
    comparison_applied = False
    comparison_verdict = ""
    stopping_stage = "closure" if closure["closure_status"] != "ACCEPTED" else "accepted"
    reason = closure["blocking_reason"] or "NONE"

    if args.refresh_output and args.refresh_event_type:
        refresh_args = [
            "--state-file", args.state_file,
            "--event-type", args.refresh_event_type,
            "--output", args.refresh_output,
            "--update-state",
        ]
        for flag, value in [
            ("--doctor-status", args.refresh_doctor_status),
            ("--bundle-file", args.bundle_output if args.refresh_use_bundle else ""),
            ("--closure-file", args.closure_output if args.refresh_use_closure else ""),
            ("--recovery-status", args.refresh_recovery_status),
        ]:
            if value:
                refresh_args.extend([flag, value])
        if args.refresh_reverification_complete:
            refresh_args.append("--reverification-complete")
        code, _ = run_python_capture(REFRESH, refresh_args)
        if code != 0:
            return code
        state = load_state(state_path)
        refresh_report = load_json(Path(args.refresh_output))
        refresh_applied = True
        refresh_resulting_closure_status = refresh_report["resulting_closure_status"]
        stopping_stage = "refresh"
        reason = state["closure"]["blocking_reason"] or "NONE"

    if args.comparison_output and args.baseline_file and args.synrail_file:
        try:
            harness = comparison_harness_for_inputs(args.baseline_file, args.synrail_file)
        except ValueError:
            return 2
        code, _ = run_python_capture(harness, ["--baseline-file", args.baseline_file, "--synrail-file", args.synrail_file, "--output", args.comparison_output])
        if code != 0:
            return code
        comparison = load_json(Path(args.comparison_output))
        comparison_applied = True
        comparison_verdict = comparison["verdict"]
        stopping_stage = "comparison"

    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "OK",
        "stopping_stage": stopping_stage,
        "reason": reason,
        "doctor_verdict": doctor_record["final_verdict"],
        "resume_applied": resume_applied,
        "resume_from_state": resume_from_state,
        "repair_handoff_applied": repair_handoff_applied,
        "repair_handoff_from_state": repair_handoff["from_state"] if repair_handoff else "",
        "repair_handoff_required_inputs": repair_handoff_required_input_ids(repair_handoff),
        "missing_continuation_inputs": list(continuation_missing_inputs),
        "selection_applied": selection_applied,
        "selected_mode": selected_mode,
        "selected_with_preparation": selected_with_preparation,
        "preparation_applied": preparation_applied,
        "preparation_ready_for_closure": preparation_ready_for_closure,
        "bundle_status": bundle["status"],
        "closure_status": state["closure"]["status"],
        "refresh_applied": refresh_applied,
        "refresh_resulting_closure_status": refresh_resulting_closure_status,
        "comparison_applied": comparison_applied,
        "comparison_verdict": comparison_verdict,
        "blockers": [],
        "dominant_blocker": "",
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }
    save_json(Path(args.report_output), report)
    finalize_runtime_outputs(
        args,
        state=state,
        report=report,
        doctor_record=doctor_record,
        resume_applied=resume_applied,
        resume_from_state=resume_from_state,
        repair_handoff=repair_handoff,
        missing_continuation_inputs=continuation_missing_inputs,
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        bundle=bundle,
        closure=closure,
        refresh_report=refresh_report,
        comparison=comparison,
        starting_repair_packet=starting_repair_packet,
        previous_repair_receipt=previous_repair_receipt,
    )

    print(json.dumps({"result": "OK", "closure_status": state["closure"]["status"]}, ensure_ascii=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-spine-v0")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--run-id", required=True)
    p_init.add_argument("--task-class", required=True)
    p_init.add_argument("--output", required=True)
    p_init.set_defaults(func=cmd_init)

    p_transition = sub.add_parser("transition")
    p_transition.add_argument("state_file")
    p_transition.add_argument("target")
    p_transition.set_defaults(func=cmd_transition)

    p_show = sub.add_parser("show")
    p_show.add_argument("state_file")
    p_show.set_defaults(func=cmd_show)

    p_apply_bundle = sub.add_parser("apply-bundle")
    p_apply_bundle.add_argument("state_file")
    p_apply_bundle.add_argument("bundle_file")
    p_apply_bundle.set_defaults(func=cmd_apply_bundle)

    p_apply_doctor = sub.add_parser("apply-doctor")
    p_apply_doctor.add_argument("state_file")
    p_apply_doctor.add_argument("doctor_file")
    p_apply_doctor.set_defaults(func=cmd_apply_doctor)

    p_apply_closure = sub.add_parser("apply-closure")
    p_apply_closure.add_argument("state_file")
    p_apply_closure.add_argument("closure_file")
    p_apply_closure.set_defaults(func=cmd_apply_closure)

    p_orchestrate = sub.add_parser("orchestrate")
    p_orchestrate.add_argument("--state-file", required=True)
    p_orchestrate.add_argument("--resume-from-state")
    p_orchestrate.add_argument("--repair-handoff-file")
    p_orchestrate.add_argument("--repair-handoff-output")
    p_orchestrate.add_argument("--repair-packet-file")
    p_orchestrate.add_argument("--repair-packet-output")
    p_orchestrate.add_argument("--repair-receipt-file")
    p_orchestrate.add_argument("--repair-receipt-output")
    p_orchestrate.add_argument("--mode-selection-receipt")
    p_orchestrate.add_argument("--doctor-run-id", required=True)
    p_orchestrate.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_orchestrate.add_argument("--target-path", required=True)
    p_orchestrate.add_argument("--target-classification", required=True)
    p_orchestrate.add_argument("--baseline-identity", required=True)
    p_orchestrate.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    p_orchestrate.add_argument("--doctor-output", required=True)
    p_orchestrate.add_argument("--final-result", required=True)
    p_orchestrate.add_argument("--task-class", required=True)
    p_orchestrate.add_argument("--bundle-output", required=True)
    p_orchestrate.add_argument("--closure-output", required=True)
    p_orchestrate.add_argument("--report-output", required=True)
    p_orchestrate.add_argument("--execution-surface-identity", required=True)
    p_orchestrate.add_argument("--prompt-identity", required=True)
    p_orchestrate.add_argument("--task-identity", required=True)
    p_orchestrate.add_argument("--readback")
    p_orchestrate.add_argument("--scenario-proof")
    p_orchestrate.add_argument("--plan-output")
    p_orchestrate.add_argument("--preparation-receipt-output")
    p_orchestrate.add_argument("--preparation-artifact-root")
    p_orchestrate.add_argument("--refresh-output")
    p_orchestrate.add_argument("--refresh-event-type")
    p_orchestrate.add_argument("--refresh-doctor-status", choices=["PASS", "FAIL"])
    p_orchestrate.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    p_orchestrate.add_argument("--refresh-reverification-complete", action="store_true")
    p_orchestrate.add_argument("--refresh-use-bundle", action="store_true")
    p_orchestrate.add_argument("--refresh-use-closure", action="store_true")
    p_orchestrate.add_argument("--baseline-file")
    p_orchestrate.add_argument("--synrail-file")
    p_orchestrate.add_argument("--comparison-output")
    p_orchestrate.add_argument("--worked-artifact-output")
    p_orchestrate.add_argument("--run-artifact-output")
    p_orchestrate.add_argument("--clean-surface", action="store_true")
    p_orchestrate.add_argument("--artifact-viable", action="store_true")
    p_orchestrate.add_argument("--helper-ok", action="store_true")
    p_orchestrate.add_argument("--credentials-ok", action="store_true")
    p_orchestrate.add_argument("--prompt-identity-ok", action="store_true")
    p_orchestrate.add_argument("--artifact-path")
    p_orchestrate.add_argument("--helper-path")
    p_orchestrate.add_argument("--credential-env", action="append", default=[])
    p_orchestrate.add_argument("--prompt-identity-file")
    p_orchestrate.add_argument("--target-identity-file")
    p_orchestrate.add_argument("--expected-target-identity")
    p_orchestrate.set_defaults(func=cmd_orchestrate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
