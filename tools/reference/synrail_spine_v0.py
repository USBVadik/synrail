#!/usr/bin/env python3
"""Minimal executable Synrail spine prototype."""

from __future__ import annotations

import argparse
import dataclasses
import datetime as dt
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from .synrail_io_v0 import load_json
except ImportError:
    from synrail_io_v0 import load_json

try:
    from .synrail_artifact_consistency_v0 import build_record as build_artifact_consistency_record
    from .synrail_artifact_repair_receipt_v0 import build_receipt as build_artifact_repair_receipt
    from .synrail_bundle_v0 import build_bundle, state_bound_project_root
    from .synrail_closure_v0 import apply_verdict_to_state, build_closure_certificate, build_verdict, persist_closure_certificate
    from .synrail_observability_v0 import build_record as build_observability_record
    from .synrail_repair_handoff_v0 import build_repair_handoff, build_resumability
    from .synrail_repair_packet_v0 import build_packet_from_runtime_truth
except ImportError:
    from synrail_artifact_consistency_v0 import build_record as build_artifact_consistency_record
    from synrail_artifact_repair_receipt_v0 import build_receipt as build_artifact_repair_receipt
    from synrail_bundle_v0 import build_bundle, state_bound_project_root
    from synrail_closure_v0 import apply_verdict_to_state, build_closure_certificate, build_verdict, persist_closure_certificate
    from synrail_observability_v0 import build_record as build_observability_record
    from synrail_repair_handoff_v0 import build_repair_handoff, build_resumability
    from synrail_repair_packet_v0 import build_packet_from_runtime_truth

try:
    from .synrail_path_scope_v0 import (
        ARTIFACT_SCOPE,
        DUAL_SCOPE,
        PROJECT_SCOPE,
        PathScopeValidationError,
        validate_namespace_paths,
        validate_root_within_project,
    )
except ImportError:
    from synrail_path_scope_v0 import (
        ARTIFACT_SCOPE,
        DUAL_SCOPE,
        PROJECT_SCOPE,
        PathScopeValidationError,
        validate_namespace_paths,
        validate_root_within_project,
    )


SPINE_PATH_SCOPES = {
    "output": ARTIFACT_SCOPE,
    "state_file": ARTIFACT_SCOPE,
    "bundle_file": ARTIFACT_SCOPE,
    "doctor_file": ARTIFACT_SCOPE,
    "closure_file": ARTIFACT_SCOPE,
    "closure_certificate_output": ARTIFACT_SCOPE,
    "repair_handoff_file": ARTIFACT_SCOPE,
    "repair_handoff_output": ARTIFACT_SCOPE,
    "repair_packet_file": ARTIFACT_SCOPE,
    "repair_packet_output": ARTIFACT_SCOPE,
    "repair_receipt_file": ARTIFACT_SCOPE,
    "repair_receipt_output": ARTIFACT_SCOPE,
    "mode_selection_receipt": ARTIFACT_SCOPE,
    "doctor_output": ARTIFACT_SCOPE,
    "final_result": DUAL_SCOPE,
    "readback": DUAL_SCOPE,
    "scenario_proof": DUAL_SCOPE,
    "plan_output": ARTIFACT_SCOPE,
    "preparation_receipt_output": ARTIFACT_SCOPE,
    "preparation_artifact_root": ARTIFACT_SCOPE,
    "refresh_output": ARTIFACT_SCOPE,
    "observability_output": ARTIFACT_SCOPE,
    "artifact_consistency_output": ARTIFACT_SCOPE,
    "baseline_file": ARTIFACT_SCOPE,
    "synrail_file": ARTIFACT_SCOPE,
    "comparison_output": ARTIFACT_SCOPE,
    "worked_artifact_output": ARTIFACT_SCOPE,
    "run_artifact_output": ARTIFACT_SCOPE,
    "artifact_path": DUAL_SCOPE,
    "helper_path": PROJECT_SCOPE,
    "prompt_identity_file": ARTIFACT_SCOPE,
    "target_identity_file": DUAL_SCOPE,
    "coverage_profile_file": PROJECT_SCOPE,
    "coverage_corpus_file": PROJECT_SCOPE,
    "acceptance_criteria_file": ARTIFACT_SCOPE,
    "acceptance_validation_output": ARTIFACT_SCOPE,
    "project_profile_file": ARTIFACT_SCOPE,
    "report_output": ARTIFACT_SCOPE,
    "target_path": PROJECT_SCOPE,
}


TERMINAL_STATES = {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}
HERE = Path(__file__).resolve().parent
DOCTOR = HERE / "synrail_doctor_v1.py"
BUNDLE = HERE / "synrail_bundle_v0.py"
CLOSURE = HERE / "synrail_closure_v0.py"
ACCEPTANCE_CRITERIA = HERE / "synrail_acceptance_criteria_v0.py"
REFRESH = HERE / "synrail_refresh_v0.py"
HARNESS_V0 = HERE / "synrail_baseline_harness_v0.py"
HARNESS_V1 = HERE / "synrail_baseline_harness_v1.py"
HARNESS_V2 = HERE / "synrail_substitute_harness_v0.py"
PROOF_PLAN = HERE / "synrail_proof_plan_v0.py"
PREPARATION_RECEIPT = HERE / "synrail_preparation_receipt_v0.py"

TRANSITION_PRECEDENCE = {
    "TARGET_SURFACE_ATTESTED": [
        "TARGET_SURFACE_NOT_ATTESTED",
    ],
    "READY": [
        "TARGET_SURFACE_NOT_ATTESTED",
        "DOCTOR_NOT_GREEN",
        "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED",
        "EXACT_TASK_IDENTITY_NOT_CONFIRMED",
    ],
    "EXECUTION_COMPLETED": [
        "TARGET_SURFACE_NOT_ATTESTED",
        "DOCTOR_NOT_GREEN",
        "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED",
        "EXACT_TASK_IDENTITY_NOT_CONFIRMED",
        "EXECUTION_NOT_COMPLETED",
    ],
    "PROOF_BUNDLE_COMPLETE": [
        "ARTIFACT_BUNDLE_MISSING",
        "INVALID_PROOF_BUNDLE",
        "SEMANTIC_PROOF_INSUFFICIENT",
        "MISSING_PROOF_SECTIONS",
    ],
    "CLOSURE_ACCEPTED": [
        "ARTIFACT_BUNDLE_MISSING",
        "INVALID_PROOF_BUNDLE",
        "SEMANTIC_PROOF_INSUFFICIENT",
        "MISSING_PROOF_SECTIONS",
        "RECOVERY_REVERIFICATION_INCOMPLETE",
    ],
}


@dataclasses.dataclass
class OrchestrationContext:
    """Shared mutable state for orchestration phases."""
    state: dict
    state_path: Path
    resume_applied: bool = False
    resume_from_state: str = ""
    repair_handoff: dict | None = None
    repair_handoff_applied: bool = False
    continuation_missing_inputs: list = dataclasses.field(default_factory=list)
    starting_repair_packet: dict | None = None
    previous_repair_receipt: dict | None = None
    selection_receipt: dict | None = None
    selection_applied: bool = False
    selected_mode: str = ""
    selected_with_preparation: bool = False
    preparation_receipt: dict | None = None
    preparation_applied: bool = False
    preparation_ready_for_closure: bool = False
    doctor_record: dict | None = None
    bundle: dict | None = None
    closure: dict | None = None
    refresh_report: dict | None = None
    comparison: dict | None = None
    refresh_applied: bool = False
    comparison_applied: bool = False
    refresh_resulting_closure_status: str = ""
    comparison_verdict: str = ""
    stopping_stage: str = ""
    reason: str = ""


def _finalize_and_exit(ctx: OrchestrationContext, args: argparse.Namespace, report: dict, result_json: dict, *, save: bool = True, exit_code: int = 0) -> int:
    if save:
        save_state(ctx.state_path, ctx.state)
    save_json(Path(args.report_output), report)
    finalize_runtime_outputs(
        args,
        state=ctx.state,
        report=report,
        doctor_record=ctx.doctor_record,
        resume_applied=ctx.resume_applied,
        resume_from_state=ctx.resume_from_state,
        repair_handoff=ctx.repair_handoff,
        missing_continuation_inputs=ctx.continuation_missing_inputs,
        selection_receipt=ctx.selection_receipt,
        preparation_receipt=ctx.preparation_receipt,
        starting_repair_packet=ctx.starting_repair_packet,
        previous_repair_receipt=ctx.previous_repair_receipt,
        bundle=ctx.bundle,
        closure=ctx.closure,
        refresh_report=ctx.refresh_report,
        comparison=ctx.comparison,
    )
    print(json.dumps(result_json, ensure_ascii=True))
    return exit_code


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


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
            "override_gates": [],
        },
        "integrity": {
            "status": "UNKNOWN",
            "exact_task_identity_ok": False,
            "bootstrap_provenance_ok": False,
            "bootstrap_provenance_reason": "CONTROLLED_BOOTSTRAP_MISSING",
        },
        "execution": {
            "status": "NOT_RUN",
            "artifact_bundle_present": False,
        },
        "proof_bundle": {
            "status": "MISSING",
            "missing_sections": [],
            "structural_status": "MISSING",
            "semantic_status": "MISSING",
            "semantically_insufficient_sections": [],
            "semantic_next_safe_step": "",
            "artifact_integrity_warning": False,
        },
        "closure": {
            "status": "OPEN",
            "blocking_reason": "",
            "next_allowed_transition": "TARGET_SURFACE_ATTESTED",
            "narrow_next_safe_step": "attest target surface",
            "missing_sections": [],
            "warnings": [],
        },
        "recovery": {
            "status": "NOT_REQUIRED",
            "reverification_complete": False,
        },
        "next_safe_step": "attest target surface",
        "start_timestamp_utc": now_iso(),
        "closure_timestamp_utc": "",
        "check_count": 0,
        "last_known_final_result_hash": "",
    }


def load_state(path: Path) -> dict:
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


def normalize_repair_packet(packet: dict) -> dict:
    normalized = dict(packet)
    if normalized.get("schema_version") != "repair_packet_v0":
        raise ValueError("repair packet must use repair_packet_v0")
    handoff = dict(normalized.get("repair_handoff", {})) if isinstance(normalized.get("repair_handoff", {}), dict) else {}
    repair_policy = dict(normalized.get("repair_policy", {})) if isinstance(normalized.get("repair_policy", {}), dict) else {}
    continuation_core = dict(normalized.get("continuation_core", {})) if isinstance(normalized.get("continuation_core", {}), dict) else {}
    artifact_quality_summary = dict(normalized.get("artifact_quality_summary", {})) if isinstance(normalized.get("artifact_quality_summary", {}), dict) else {}
    resumability = dict(normalized.get("resumability", {})) if isinstance(normalized.get("resumability", {}), dict) else {}
    missing_inputs = list(normalized.get("missing_inputs", [])) if isinstance(normalized.get("missing_inputs", []), list) else []

    if not continuation_core:
        next_step_id = continuation_core.get("current_step_id", "") or repair_policy.get("next_step_id", "")
        continuation_core = {
            "contract_version": "continuation_core_v0",
            "entrypoint": normalized.get("continuation_entrypoint", "resume"),
            "ready_for_resume": bool(normalized.get("ready_for_resume", False)),
            "resumability_status": resumability.get("status", ""),
            "resumability_family": resumability.get("family", ""),
            "current_step_id": next_step_id,
            "current_step_subsurface_id": "",
            "current_step_target_path": "",
            "required_inputs": [
                item.get("input_id", "")
                for item in handoff.get("required_inputs", [])
                if isinstance(item, dict) and item.get("input_id", "")
            ],
            "missing_inputs": missing_inputs,
            "next_step_required_inputs": list(missing_inputs),
            "next_step_subsurface_ids": list(artifact_quality_summary.get("stale_subsurface_ids", [])),
            "operator_focus": normalized.get("next_safe_step", ""),
            "next_safe_step": normalized.get("next_safe_step", ""),
            "history_chain_length": 0,
            "selection_applied": bool((normalized.get("selection_context", {}) or {}).get("applied", False)),
            "selected_with_preparation": bool((normalized.get("selection_context", {}) or {}).get("selected_with_preparation", False)),
            "packet_supplies_resume_context": bool(normalized.get("resume_context", {})),
            "packet_supplies_repair_inputs": bool(normalized.get("repair_inputs", {})),
            "packet_supplies_output_defaults": bool(normalized.get("output_defaults", {})),
            "requires_sibling_discovery": False,
            "authoritative_entry_artifacts": ["repair_packet"],
            "source_of_truth_precedence": ["repair_packet", "repair_handoff", "state"],
            "packet_replay_ready": True,
        }
    normalized["continuation_core"] = continuation_core
    return normalized


def load_repair_packet(path: Path) -> dict:
    packet = load_json(path)
    return normalize_repair_packet(packet)


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
    repair_termination = (packet.get("repair_termination") or {}) if packet else {
        "status": "CONTINUE",
        "reason": "",
        "attempt_count": 0,
        "max_attempts": 0,
        "no_progress_window": 0,
        "stalled_step_id": "",
        "next_action": "",
    }
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
        "repair_termination_status": repair_termination.get("status", ""),
        "repair_termination_reason": repair_termination.get("reason", ""),
        "repair_attempt_count": repair_termination.get("attempt_count", 0),
        "repair_max_attempts": repair_termination.get("max_attempts", 0),
        "repair_no_progress_window": repair_termination.get("no_progress_window", 0),
        "repair_stalled_step_id": repair_termination.get("stalled_step_id", ""),
        "repair_termination_next_action": repair_termination.get("next_action", ""),
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
        "termination_status": packet_summary["repair_termination_status"],
        "termination_reason": packet_summary["repair_termination_reason"],
        "attempt_count": packet_summary["repair_attempt_count"],
        "max_attempts": packet_summary["repair_max_attempts"],
        "no_progress_window": packet_summary["repair_no_progress_window"],
        "stalled_step_id": packet_summary["repair_stalled_step_id"],
        "termination_next_action": packet_summary["repair_termination_next_action"],
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
    if baseline_version == "comparison_input_v2":
        return HARNESS_V2

    return HARNESS_V0


def save_state(path: Path, state: dict) -> None:
    state.setdefault("start_timestamp_utc", "")
    state.setdefault("closure_timestamp_utc", "")
    state.setdefault("check_count", 0)
    state.setdefault("last_known_final_result_hash", "")
    state.setdefault("doctor", {}).setdefault("override_gates", [])
    state.setdefault("proof_bundle", {}).setdefault("artifact_integrity_warning", False)
    state.setdefault("closure", {}).setdefault("warnings", [])
    save_json(path, state)


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        handle.write(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")
        temp_name = handle.name
    os.replace(temp_name, path)


def missing_acceptance_validation_record(reason: str) -> dict:
    return {
        "schema_version": "acceptance_criteria_validation_record_v0",
        "criteria_revision_id": "",
        "status": "INVALID",
        "reason": reason,
        "task_class_matches": False,
        "project_type_matches": False,
        "target_classification_matches": False,
        "intended_run_class_matches": False,
        "required_gate_ids_match": False,
        "required_bundle_sections_match": False,
        "criteria_standard_matches": False,
        "criteria_owner_matches": False,
        "project_profile_fingerprint_matches": False,
        "criteria_revision_matches": False,
        "provenance_complete": False,
        "provenance_profile_fingerprint_matches": False,
    }


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
        "closure_certificate_output": getattr(args, "closure_certificate_output", ""),
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
    if report.get("stopping_stage") == "resume" and report.get("repair_termination_status") == "TERMINATE":
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
    state["closure"]["warnings"] = []
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
    if not state["integrity"].get("bootstrap_provenance_ok", False):
        return False, "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"
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
    if state["proof_bundle"]["status"] == "STRUCTURALLY_COMPLETE":
        return False, "SEMANTIC_PROOF_INSUFFICIENT"
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

    if dominant == "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED":
        state["integrity"]["status"] = "FAIL"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"
        state["closure"]["next_allowed_transition"] = "CONTROLLED_START"
        state["closure"]["narrow_next_safe_step"] = "start the run in controlled mode before trusting any proof or acceptance"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return state

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

    if dominant == "SEMANTIC_PROOF_INSUFFICIENT":
        return enter_blocked_state(
            state,
            target="PROOF_BUNDLE_STRUCTURALLY_COMPLETE",
            closure_status="CLAIMED_NOT_ACCEPTED",
            blocking_reason="SEMANTIC_PROOF_INSUFFICIENT",
            next_allowed_transition="PROOF_BUNDLE_STRENGTHENING",
            narrow_next_safe_step=state["proof_bundle"].get("semantic_next_safe_step", "") or "strengthen the semantic proof evidence before trusting closure",
            missing_sections=list(state["proof_bundle"].get("semantically_insufficient_sections", [])),
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
        state["closure_timestamp_utc"] = now_iso()
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
    state["proof_bundle"]["structural_status"] = bundle.get("structural_status", "")
    state["proof_bundle"]["semantic_status"] = bundle.get("semantic_status", "")
    state["proof_bundle"]["semantically_insufficient_sections"] = list(bundle.get("semantically_insufficient_sections", []))
    state["proof_bundle"]["semantic_next_safe_step"] = bundle.get("semantic_next_safe_step", "")
    state["proof_bundle"]["final_result"] = dict(bundle.get("final_result", {}))
    state["proof_bundle"]["verification_corroboration"] = dict(bundle.get("verification_corroboration", {}))
    state["proof_bundle"]["artifact_identity"] = dict(bundle.get("artifact_identity", {}))
    state["proof_bundle"]["cleanup_status"] = dict(bundle.get("cleanup_status", {}))
    state["proof_bundle"]["artifact_integrity_warning"] = bool(bundle.get("artifact_integrity_warning", False))

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
    if bundle.get("status") == "STRUCTURALLY_COMPLETE":
        return 0, enter_blocked_state(
            state,
            target="PROOF_BUNDLE_STRUCTURALLY_COMPLETE",
            closure_status="CLAIMED_NOT_ACCEPTED",
            blocking_reason="SEMANTIC_PROOF_INSUFFICIENT",
            next_allowed_transition="PROOF_BUNDLE_STRENGTHENING",
            narrow_next_safe_step=bundle.get("semantic_next_safe_step", "") or "strengthen the semantic proof evidence before trusting closure",
            missing_sections=list(bundle.get("semantically_insufficient_sections", [])),
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
    state["doctor"]["override_gates"] = list(record.get("override_gates", []))

    if acceptable:
        if state["state"] == "DOCTOR_BLOCKED":
            state["state"] = "TARGET_SURFACE_ATTESTED" if state["target_surface"]["status"] == "ATTESTED" else "INITIALIZED"
        state["closure"]["status"] = "OPEN"
        state["closure"]["blocking_reason"] = ""
        state["closure"]["next_allowed_transition"] = "READY"
        state["closure"]["narrow_next_safe_step"] = "confirm exact task identity"
        state["closure"]["missing_sections"] = []
        state["closure"]["warnings"] = []
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


def apply_integrity(
    state: dict,
    *,
    prompt_identity: str,
    task_identity: str,
    bootstrap_provenance_ok: bool,
    bootstrap_provenance_reason: str,
) -> dict:
    exact_ok = bool(prompt_identity.strip() and task_identity.strip())
    state["integrity"]["status"] = "PASS" if exact_ok and bootstrap_provenance_ok else "FAIL"
    state["integrity"]["exact_task_identity_ok"] = exact_ok
    state["integrity"]["bootstrap_provenance_ok"] = bool(bootstrap_provenance_ok)
    state["integrity"]["bootstrap_provenance_reason"] = bootstrap_provenance_reason or (
        "CONTROLLED_BOOTSTRAP_CONFIRMED" if bootstrap_provenance_ok else "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"
    )
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
    state["closure"]["warnings"] = list(verdict.get("closure_warnings", []))
    state["next_safe_step"] = verdict["narrow_next_safe_step"]

    if verdict["closure_status"] == "ACCEPTED":
        return transition(state, "CLOSURE_ACCEPTED")

    if verdict["closure_status"] == "REJECTED":
        return transition(state, "CLOSURE_REJECTED")

    if verdict["blocking_reason"] == "INVALID_PROOF_BUNDLE":
        state["state"] = "PROOF_BUNDLE_INVALID"
        return 0, state, None

    if verdict["blocking_reason"] == "SEMANTIC_PROOF_INSUFFICIENT":
        state["state"] = "PROOF_BUNDLE_STRUCTURALLY_COMPLETE"
        return 0, state, None

    if verdict["blocking_reason"] == "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED":
        state["integrity"]["status"] = "FAIL"
        state["state"] = "INITIALIZED"
        return 0, state, None

    if verdict["blocking_reason"] == "MISSING_PROOF_SECTIONS":
        if state["proof_bundle"].get("semantic_status") == "INSUFFICIENT" or state["proof_bundle"].get("semantically_insufficient_sections"):
            state["state"] = "PROOF_BUNDLE_STRUCTURALLY_COMPLETE"
        else:
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
        "repair_termination_status": "",
        "repair_termination_reason": "",
        "repair_attempt_count": 0,
        "repair_max_attempts": 0,
        "repair_no_progress_window": 0,
        "repair_stalled_step_id": "",
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


def enforce_atomic_closure_freshness(
    *,
    state: dict,
    state_path: Path,
    bundle: dict,
    bundle_path: Path,
    verdict: dict,
    criteria_validation: dict | None,
) -> tuple[dict, dict, dict | None]:
    bound_state = dict(state)
    bound_state["_state_file"] = str(state_path)
    bound_bundle = dict(bundle)
    bound_bundle["_bundle_file"] = str(bundle_path)
    certificate = build_closure_certificate(
        state=bound_state,
        bundle=bound_bundle,
        verdict=verdict,
        criteria_validation=criteria_validation,
    )
    freshness = certificate.get("closure_freshness_binding", {})
    if verdict.get("closure_status") != "ACCEPTED":
        return verdict, certificate, None
    if freshness.get("all_required_present", False) and freshness.get("all_hashes_match", False):
        return verdict, certificate, None

    rejected_verdict = dict(verdict)
    warnings = list(rejected_verdict.get("closure_warnings", []))
    if "closure_freshness_binding_mismatch" not in warnings:
        warnings.append("closure_freshness_binding_mismatch")
    rejected_verdict.update({
        "closure_status": "REJECTED",
        "blocking_reason": "CLOSURE_FRESHNESS_FAILED",
        "next_allowed_transition": "PROOF_BUNDLE_REPAIR",
        "narrow_next_safe_step": "rebuild the final result artifact and proof bundle on the current surface",
        "closure_warnings": warnings,
    })
    block_report = {
        "target": "CLOSURE_ACCEPTED",
        "allowed": False,
        "dominant_blocker": "CLOSURE_FRESHNESS_FAILED",
        "blocking_reasons": ["CLOSURE_FRESHNESS_FAILED"],
        "blockers": ["CLOSURE_FRESHNESS_FAILED"],
        "narrow_next_safe_step": rejected_verdict["narrow_next_safe_step"],
    }
    rebound_certificate = build_closure_certificate(
        state=bound_state,
        bundle=bound_bundle,
        verdict=rejected_verdict,
        criteria_validation=criteria_validation,
    )
    return rejected_verdict, rebound_certificate, block_report


def bound_final_result_sha256(bundle: dict) -> str:
    binding = bundle.get("closure_freshness_binding", {})
    artifacts = binding.get("artifacts", []) if isinstance(binding, dict) else []
    for artifact in artifacts:
        if not isinstance(artifact, dict) or artifact.get("artifact_id") != "final_result":
            continue
        value = artifact.get("sha256", "")
        if (
            artifact.get("required") is True
            and artifact.get("present") is True
            and isinstance(value, str)
            and len(value) == 64
            and all(character in "0123456789abcdefABCDEF" for character in value)
        ):
            return value
    return ""


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


def build_canonical_run_artifact(
    *,
    state: dict,
    report: dict,
    worked: dict,
    repair_packet: dict | None,
    closure_certificate: dict | None,
) -> dict:
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
        "closure_certificate": dict(closure_certificate or {}),
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
    closure_certificate: dict | None = None,
) -> None:
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
    canonical = build_canonical_run_artifact(
        state=state,
        report=report,
        worked=worked,
        repair_packet=repair_packet,
        closure_certificate=closure_certificate,
    )
    if args.worked_artifact_output:
        save_json(Path(args.worked_artifact_output), worked)
    if args.run_artifact_output:
        save_json(Path(args.run_artifact_output), canonical)
    if getattr(args, "artifact_consistency_output", None):
        consistency = build_artifact_consistency_record(
            state=state,
            state_file=Path(args.state_file),
            bundle_file=Path(args.bundle_output) if getattr(args, "bundle_output", None) else None,
            bundle=bundle,
            report=report,
            orchestration=worked,
            run_artifact=canonical,
            closure_certificate=closure_certificate,
            repair_packet=repair_packet,
            repair_handoff=repair_handoff,
        )
        save_json(Path(args.artifact_consistency_output), consistency)


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
    closure_certificate: dict | None = None,
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
    if closure_certificate is None and getattr(args, "closure_certificate_output", None):
        certificate_path = Path(args.closure_certificate_output)
        if certificate_path.exists():
            closure_certificate = load_json(certificate_path)
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
    effective_repair_receipt = emitted_repair_receipt or previous_repair_receipt
    repair_packet = maybe_emit_repair_packet(
        args,
        state=state,
        report=report,
        repair_handoff=current_handoff,
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        repair_receipt=effective_repair_receipt,
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
        closure_certificate=closure_certificate,
    )
    if getattr(args, "observability_output", None):
        output_files = {
            "state": Path(args.state_file).name,
            "report": Path(args.report_output).name if getattr(args, "report_output", None) else "",
        }
        if getattr(args, "repair_packet_output", None):
            output_files["repair_packet"] = Path(args.repair_packet_output).name
        if getattr(args, "repair_receipt_output", None):
            output_files["repair_receipt"] = Path(args.repair_receipt_output).name
        if getattr(args, "refresh_output", None):
            output_files["refresh"] = Path(args.refresh_output).name
        observability = build_observability_record(
            state=state,
            report=report,
            repair_packet=repair_packet,
            repair_receipt=effective_repair_receipt,
            refresh_report=refresh_report,
            output_files={key: value for key, value in output_files.items() if value},
        )
        save_json(Path(args.observability_output), observability)


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


def _phase_init(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Load mode_selection_receipt and repair_receipt."""
    if args.mode_selection_receipt:
        try:
            ctx.selection_receipt = load_mode_selection_receipt(Path(args.mode_selection_receipt))
        except ValueError:
            report = build_error_report(ctx.state, reason="INVALID_MODE_SELECTION_RECEIPT", stopping_stage="selection")
            report["resume_applied"] = ctx.resume_applied
            report["resume_from_state"] = ctx.resume_from_state
            save_json(Path(args.report_output), report)
            finalize_runtime_outputs(
                args,
                state=ctx.state,
                report=report,
                resume_applied=ctx.resume_applied,
                resume_from_state=ctx.resume_from_state,
                repair_handoff=ctx.repair_handoff,
                missing_continuation_inputs=ctx.continuation_missing_inputs,
            )
            return 2
        ctx.selection_applied = True
        ctx.selected_mode = ctx.selection_receipt["selected_mode"]
        ctx.selected_with_preparation = bool(ctx.selection_receipt.get("selected_with_preparation", False))

    if getattr(args, "repair_receipt_file", None):
        try:
            ctx.previous_repair_receipt = load_repair_receipt(Path(args.repair_receipt_file))
        except ValueError:
            ctx.previous_repair_receipt = None

    return None


def _resume_early_exit(
    ctx: OrchestrationContext,
    args: argparse.Namespace,
    report: dict,
    *,
    save_state_first: bool = False,
    print_summary: dict | None = None,
) -> int:
    """Centralized early-exit helper for resume/handoff phase."""
    if save_state_first:
        save_state(ctx.state_path, ctx.state)
    save_json(Path(args.report_output), report)
    finalize_runtime_outputs(
        args,
        state=ctx.state,
        report=report,
        resume_applied=True,
        resume_from_state=ctx.resume_from_state,
        repair_handoff=ctx.repair_handoff,
        missing_continuation_inputs=ctx.continuation_missing_inputs,
        selection_receipt=ctx.selection_receipt,
        starting_repair_packet=ctx.starting_repair_packet,
        previous_repair_receipt=ctx.previous_repair_receipt,
    )
    if print_summary:
        print(json.dumps(print_summary, ensure_ascii=True))
    return 0 if save_state_first else 2


def _resume_load_packet(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Load repair packet and extract embedded selection/receipt context."""
    if not getattr(args, "repair_packet_file", None):
        return None
    try:
        ctx.starting_repair_packet = load_repair_packet(Path(args.repair_packet_file))
    except ValueError:
        report = build_error_report(ctx.state, reason="INVALID_REPAIR_PACKET", stopping_stage="repair_packet")
        report["resume_applied"] = True
        report["resume_from_state"] = ctx.resume_from_state
        report["selection_applied"] = ctx.selection_applied
        report["selected_mode"] = ctx.selected_mode
        report["selected_with_preparation"] = ctx.selected_with_preparation
        return _resume_early_exit(ctx, args, report)
    if not ctx.selection_receipt and ctx.starting_repair_packet.get("selection_receipt"):
        ctx.selection_receipt = dict(ctx.starting_repair_packet["selection_receipt"])
        ctx.selection_applied = True
        ctx.selected_mode = ctx.selection_receipt.get("selected_mode", "")
        ctx.selected_with_preparation = bool(ctx.selection_receipt.get("selected_with_preparation", False))
    if ctx.previous_repair_receipt is None and ctx.starting_repair_packet.get("repair_receipt"):
        ctx.previous_repair_receipt = dict(ctx.starting_repair_packet["repair_receipt"])
    return None


def _resume_check_termination(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Block if the repair packet says TERMINATE."""
    if not ctx.starting_repair_packet:
        return None
    repair_termination = dict(ctx.starting_repair_packet.get("repair_termination") or {})
    if repair_termination.get("status") != "TERMINATE":
        return None
    if repair_termination.get("reason") not in {"NON_RESUMABLE", "MAX_REPAIR_ATTEMPTS", "NO_PROGRESS_DETECTED"}:
        return None
    ctx.state["closure"]["status"] = ctx.state["closure"]["status"] or "CLAIMED_NOT_ACCEPTED"
    ctx.state["closure"]["blocking_reason"] = repair_termination["reason"]
    ctx.state["closure"]["next_allowed_transition"] = "NONE"
    ctx.state["closure"]["narrow_next_safe_step"] = repair_termination.get(
        "next_action", "stop this repair loop and start a new run instead",
    )
    ctx.state["next_safe_step"] = ctx.state["closure"]["narrow_next_safe_step"]
    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": ctx.state["run_id"],
        "task_class": ctx.state["task_class"],
        "result": "BLOCKED",
        "stopping_stage": "resume",
        "reason": repair_termination["reason"],
        "doctor_verdict": "",
        "resume_applied": True,
        "resume_from_state": ctx.resume_from_state,
        "selection_applied": ctx.selection_applied,
        "selected_mode": ctx.selected_mode,
        "selected_with_preparation": ctx.selected_with_preparation,
        "preparation_applied": False,
        "preparation_ready_for_closure": False,
        "bundle_status": ctx.state["proof_bundle"]["status"],
        "closure_status": ctx.state["closure"]["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "repair_termination_status": repair_termination.get("status", ""),
        "repair_termination_reason": repair_termination.get("reason", ""),
        "repair_attempt_count": repair_termination.get("attempt_count", 0),
        "repair_max_attempts": repair_termination.get("max_attempts", 0),
        "repair_no_progress_window": repair_termination.get("no_progress_window", 0),
        "repair_stalled_step_id": repair_termination.get("stalled_step_id", ""),
        "blockers": [repair_termination["reason"]],
        "dominant_blocker": repair_termination["reason"],
        "resulting_state": ctx.state["state"],
        "next_safe_step": ctx.state["next_safe_step"],
    }
    return _resume_early_exit(
        ctx, args, report, save_state_first=True,
        print_summary={"result": "BLOCKED", "stopping_stage": "resume", "reason": repair_termination["reason"]},
    )


def _resume_validate_state(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Check state mismatch and terminal-state conditions."""
    if ctx.state["state"] != ctx.resume_from_state:
        report = build_error_report(ctx.state, reason="RESUME_STATE_MISMATCH", stopping_stage="resume")
        report["resume_applied"] = True
        report["resume_from_state"] = ctx.resume_from_state
        report["selection_applied"] = ctx.selection_applied
        report["selected_mode"] = ctx.selected_mode
        report["selected_with_preparation"] = ctx.selected_with_preparation
        return _resume_early_exit(ctx, args, report)
    if ctx.state["state"] in TERMINAL_STATES:
        ctx.state["closure"]["status"] = ctx.state["closure"]["status"] or "CLAIMED_NOT_ACCEPTED"
        ctx.state["closure"]["blocking_reason"] = "TERMINAL_STATE_NOT_RESUMABLE"
        ctx.state["closure"]["next_allowed_transition"] = "NONE"
        ctx.state["closure"]["narrow_next_safe_step"] = "start a new run instead of resuming a terminal state"
        ctx.state["next_safe_step"] = ctx.state["closure"]["narrow_next_safe_step"]
        report = {
            "schema_version": "orchestration_report_v0",
            "run_id": ctx.state["run_id"],
            "task_class": ctx.state["task_class"],
            "result": "BLOCKED",
            "stopping_stage": "resume",
            "reason": "TERMINAL_STATE_NOT_RESUMABLE",
            "doctor_verdict": "",
            "resume_applied": True,
            "resume_from_state": ctx.resume_from_state,
            "selection_applied": ctx.selection_applied,
            "selected_mode": ctx.selected_mode,
            "selected_with_preparation": ctx.selected_with_preparation,
            "preparation_applied": False,
            "preparation_ready_for_closure": False,
            "bundle_status": ctx.state["proof_bundle"]["status"],
            "closure_status": ctx.state["closure"]["status"],
            "refresh_applied": False,
            "refresh_resulting_closure_status": "",
            "comparison_applied": False,
            "comparison_verdict": "",
            "blockers": ["TERMINAL_STATE_NOT_RESUMABLE"],
            "dominant_blocker": "TERMINAL_STATE_NOT_RESUMABLE",
            "resulting_state": ctx.state["state"],
            "next_safe_step": ctx.state["next_safe_step"],
        }
        return _resume_early_exit(
            ctx, args, report, save_state_first=True,
            print_summary={"result": "BLOCKED", "stopping_stage": "resume", "reason": "TERMINAL_STATE_NOT_RESUMABLE"},
        )
    return None


def _resume_resolve_handoff(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Load explicit handoff, fall back to packet-embedded or freshly built one."""
    if getattr(args, "repair_handoff_file", None):
        try:
            ctx.repair_handoff = load_repair_handoff(Path(args.repair_handoff_file))
        except ValueError:
            report = build_error_report(ctx.state, reason="INVALID_REPAIR_HANDOFF", stopping_stage="repair_handoff")
            report["resume_applied"] = True
            report["resume_from_state"] = ctx.resume_from_state
            report["repair_handoff_applied"] = True
            report["repair_handoff_from_state"] = ctx.state["state"]
            report["repair_handoff_required_inputs"] = []
            report["missing_continuation_inputs"] = []
            report["selection_applied"] = ctx.selection_applied
            report["selected_mode"] = ctx.selected_mode
            report["selected_with_preparation"] = ctx.selected_with_preparation
            return _resume_early_exit(ctx, args, report)
        ctx.repair_handoff_applied = True
        if ctx.repair_handoff["run_id"] != ctx.state["run_id"] or ctx.repair_handoff["from_state"] != ctx.state["state"]:
            report = build_error_report(ctx.state, reason="REPAIR_HANDOFF_STATE_MISMATCH", stopping_stage="repair_handoff")
            report["resume_applied"] = True
            report["resume_from_state"] = ctx.resume_from_state
            report["repair_handoff_applied"] = True
            report["repair_handoff_from_state"] = ctx.repair_handoff["from_state"]
            report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(ctx.repair_handoff)
            report["missing_continuation_inputs"] = []
            report["selection_applied"] = ctx.selection_applied
            report["selected_mode"] = ctx.selected_mode
            report["selected_with_preparation"] = ctx.selected_with_preparation
            return _resume_early_exit(ctx, args, report)
    if ctx.repair_handoff is None and ctx.starting_repair_packet and ctx.starting_repair_packet.get("repair_handoff"):
        candidate_handoff = dict(ctx.starting_repair_packet["repair_handoff"])
        if candidate_handoff.get("run_id") == ctx.state["run_id"] and candidate_handoff.get("from_state") == ctx.state["state"]:
            ctx.repair_handoff = candidate_handoff
            ctx.repair_handoff_applied = True
    current_resume_handoff = ctx.repair_handoff or build_repair_handoff(ctx.state)
    ctx.repair_handoff = current_resume_handoff
    if not current_resume_handoff.get("continuation_allowed", False):
        report = {
            "schema_version": "orchestration_report_v0",
            "run_id": ctx.state["run_id"],
            "task_class": ctx.state["task_class"],
            "result": "BLOCKED",
            "stopping_stage": "resume",
            "reason": "STATE_NOT_RESUMABLE",
            "doctor_verdict": "",
            "resume_applied": True,
            "resume_from_state": ctx.resume_from_state,
            "repair_handoff_applied": ctx.repair_handoff_applied,
            "repair_handoff_from_state": current_resume_handoff["from_state"],
            "repair_handoff_required_inputs": repair_handoff_required_input_ids(current_resume_handoff),
            "missing_continuation_inputs": [],
            "selection_applied": ctx.selection_applied,
            "selected_mode": ctx.selected_mode,
            "selected_with_preparation": ctx.selected_with_preparation,
            "preparation_applied": False,
            "preparation_ready_for_closure": False,
            "bundle_status": ctx.state["proof_bundle"]["status"],
            "closure_status": ctx.state["closure"]["status"],
            "refresh_applied": False,
            "refresh_resulting_closure_status": "",
            "comparison_applied": False,
            "comparison_verdict": "",
            "blockers": [current_resume_handoff["resumability"]["family"]],
            "dominant_blocker": "STATE_NOT_RESUMABLE",
            "resulting_state": ctx.state["state"],
            "next_safe_step": ctx.state["next_safe_step"],
        }
        return _resume_early_exit(
            ctx, args, report, save_state_first=True,
            print_summary={"result": "BLOCKED", "stopping_stage": "resume", "reason": "STATE_NOT_RESUMABLE"},
        )
    return None


def _resume_validate_inputs(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Check missing continuation inputs and out-of-order repair steps."""
    apply_repair_handoff_defaults(args, ctx.repair_handoff)
    ctx.continuation_missing_inputs = missing_continuation_inputs(args, ctx.repair_handoff)
    if not ctx.continuation_missing_inputs:
        return None
    out_of_order_steps = repair_policy_out_of_order_steps(args, ctx.repair_handoff, ctx.continuation_missing_inputs)
    if out_of_order_steps:
        report = {
            "schema_version": "orchestration_report_v0",
            "run_id": ctx.state["run_id"],
            "task_class": ctx.state["task_class"],
            "result": "BLOCKED",
            "stopping_stage": "repair_handoff",
            "reason": "REPAIR_POLICY_STEP_OUT_OF_ORDER",
            "doctor_verdict": "",
            "resume_applied": True,
            "resume_from_state": ctx.resume_from_state,
            "repair_handoff_applied": ctx.repair_handoff_applied,
            "repair_handoff_from_state": ctx.repair_handoff["from_state"],
            "repair_handoff_required_inputs": repair_handoff_required_input_ids(ctx.repair_handoff),
            "missing_continuation_inputs": list(ctx.continuation_missing_inputs),
            "selection_applied": ctx.selection_applied,
            "selected_mode": ctx.selected_mode,
            "selected_with_preparation": ctx.selected_with_preparation,
            "preparation_applied": False,
            "preparation_ready_for_closure": False,
            "bundle_status": ctx.state["proof_bundle"]["status"],
            "closure_status": ctx.state["closure"]["status"],
            "refresh_applied": False,
            "refresh_resulting_closure_status": "",
            "comparison_applied": False,
            "comparison_verdict": "",
            "blockers": list(out_of_order_steps),
            "dominant_blocker": "REPAIR_POLICY_STEP_OUT_OF_ORDER",
            "resulting_state": ctx.state["state"],
            "next_safe_step": ctx.state["next_safe_step"],
        }
        return _resume_early_exit(
            ctx, args, report, save_state_first=True,
            print_summary={"result": "BLOCKED", "stopping_stage": "repair_handoff", "reason": "REPAIR_POLICY_STEP_OUT_OF_ORDER"},
        )
    report = build_repair_handoff_blocked_report(
        ctx.state,
        doctor_verdict="",
        resume_applied=True,
        resume_from_state=ctx.resume_from_state,
        repair_handoff=ctx.repair_handoff,
        missing_inputs=ctx.continuation_missing_inputs,
        selection_applied=ctx.selection_applied,
        selected_mode=ctx.selected_mode,
        selected_with_preparation=ctx.selected_with_preparation,
        preparation_applied=False,
        preparation_ready_for_closure=False,
    )
    return _resume_early_exit(
        ctx, args, report, save_state_first=True,
        print_summary={"result": "BLOCKED", "stopping_stage": "repair_handoff", "reason": "CONTINUATION_INPUTS_MISSING"},
    )


def _phase_resume_and_handoff(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Resume validation + repair packet + handoff section."""
    if not ctx.resume_applied:
        return None
    for step in [_resume_load_packet, _resume_check_termination, _resume_validate_state, _resume_resolve_handoff, _resume_validate_inputs]:
        code = step(ctx, args)
        if code is not None:
            return code
    return None


def _phase_mode_governance(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Mode selection check + prep output defaults."""
    if ctx.selection_applied and ctx.selected_mode != "FULL_GOVERNED_PATH":
        ctx.state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        ctx.state["closure"]["blocking_reason"] = "MODE_SELECTION_NOT_GOVERNED"
        ctx.state["closure"]["next_allowed_transition"] = "FOLLOW_SELECTED_MODE"
        ctx.state["closure"]["narrow_next_safe_step"] = "follow the selected lighter mode instead of entering governed orchestration"
        ctx.state["next_safe_step"] = ctx.state["closure"]["narrow_next_safe_step"]
        report = {
            "schema_version": "orchestration_report_v0",
            "run_id": ctx.state["run_id"],
            "task_class": ctx.state["task_class"],
            "result": "BLOCKED",
            "stopping_stage": "selection",
            "reason": "MODE_SELECTION_NOT_GOVERNED",
            "doctor_verdict": "",
            "resume_applied": ctx.resume_applied,
            "resume_from_state": ctx.resume_from_state,
            "repair_handoff_applied": ctx.repair_handoff_applied,
            "repair_handoff_from_state": ctx.repair_handoff["from_state"] if ctx.repair_handoff else "",
            "repair_handoff_required_inputs": repair_handoff_required_input_ids(ctx.repair_handoff),
            "missing_continuation_inputs": list(ctx.continuation_missing_inputs),
            "selection_applied": True,
            "selected_mode": ctx.selected_mode,
            "selected_with_preparation": ctx.selected_with_preparation,
            "preparation_applied": False,
            "preparation_ready_for_closure": False,
            "bundle_status": "",
            "closure_status": ctx.state["closure"]["status"],
            "refresh_applied": False,
            "refresh_resulting_closure_status": "",
            "comparison_applied": False,
            "comparison_verdict": "",
            "blockers": ["MODE_SELECTION_NOT_GOVERNED"],
            "dominant_blocker": "MODE_SELECTION_NOT_GOVERNED",
            "resulting_state": ctx.state["state"],
            "next_safe_step": ctx.state["next_safe_step"],
        }
        save_state(ctx.state_path, ctx.state)
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "selection", "reason": "MODE_SELECTION_NOT_GOVERNED"}, ensure_ascii=True))
        return 0
    if ctx.selected_with_preparation:
        if not args.plan_output:
            args.plan_output = str(Path(args.report_output).with_name("plan.json"))
        if not args.preparation_receipt_output:
            args.preparation_receipt_output = str(Path(args.report_output).with_name("preparation_receipt.json"))
        if not args.preparation_artifact_root:
            args.preparation_artifact_root = str(Path(args.report_output).parent)

    return None


def _phase_target_surface(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Target surface attestation transition."""
    ctx.state = apply_target_surface(
        ctx.state,
        identity=args.execution_surface_identity,
        baseline_relation=args.baseline_identity,
    )
    code, ctx.state, block_report = maybe_advance_to_target_surface_attested(ctx.state)
    if code != 0:
        report = build_transition_blocked_report(
            ctx.state,
            stopping_stage="target_surface_transition",
            doctor_verdict="",
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_applied=ctx.selection_applied,
            selected_mode=ctx.selected_mode,
            selected_with_preparation=ctx.selected_with_preparation,
            preparation_applied=ctx.preparation_applied,
            preparation_ready_for_closure=ctx.preparation_ready_for_closure,
            block_report=block_report,
        )
        save_state(ctx.state_path, ctx.state)
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "target_surface_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(ctx.state_path, ctx.state)

    return None


def _phase_doctor(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Doctor execution + application."""
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
        ("--coverage-profile-file", getattr(args, "coverage_profile_file", None)),
        ("--coverage-corpus-file", getattr(args, "coverage_corpus_file", None)),
        ("--expected-target-identity", args.execution_surface_identity),
    ]:
        if value:
            doctor_args.extend([flag, value])
    for changed_file in getattr(args, "changed_file", []):
        doctor_args.extend(["--changed-file", changed_file])
    for allowed_scope_path in getattr(args, "allowed_scope_path", []):
        doctor_args.extend(["--allowed-scope-path", allowed_scope_path])
    for env_name in args.credential_env:
        doctor_args.extend(["--credential-env", env_name])

    code, _ = run_python_capture(DOCTOR, doctor_args)
    if code != 0:
        report = build_error_report(ctx.state, reason="DOCTOR_EXECUTION_FAILED")
        report["resume_applied"] = ctx.resume_applied
        report["resume_from_state"] = ctx.resume_from_state
        report["repair_handoff_applied"] = ctx.repair_handoff_applied
        report["repair_handoff_from_state"] = ctx.repair_handoff["from_state"] if ctx.repair_handoff else ""
        report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(ctx.repair_handoff)
        report["missing_continuation_inputs"] = list(ctx.continuation_missing_inputs)
        report["selection_applied"] = ctx.selection_applied
        report["selected_mode"] = ctx.selected_mode
        report["selected_with_preparation"] = ctx.selected_with_preparation
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        return code

    ctx.doctor_record = load_json(Path(args.doctor_output))
    code, ctx.state, block_report = apply_doctor(load_state(ctx.state_path), ctx.doctor_record)
    if code != 0:
        save_state(ctx.state_path, ctx.state)
        report = build_error_report(ctx.state, reason=block_report["dominant_blocker"], stopping_stage="doctor_apply")
        report["resume_applied"] = ctx.resume_applied
        report["resume_from_state"] = ctx.resume_from_state
        report["repair_handoff_applied"] = ctx.repair_handoff_applied
        report["repair_handoff_from_state"] = ctx.repair_handoff["from_state"] if ctx.repair_handoff else ""
        report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(ctx.repair_handoff)
        report["missing_continuation_inputs"] = list(ctx.continuation_missing_inputs)
        report["selection_applied"] = ctx.selection_applied
        report["selected_mode"] = ctx.selected_mode
        report["selected_with_preparation"] = ctx.selected_with_preparation
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            doctor_record=ctx.doctor_record,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        print(json.dumps({"result": "ERROR", "stopping_stage": "doctor_apply", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0

    return None


def _phase_integrity_and_readiness(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Integrity + advance to ready + doctor block check."""
    ctx.state = apply_integrity(
        ctx.state,
        prompt_identity=args.prompt_identity,
        task_identity=args.task_identity,
        bootstrap_provenance_ok=getattr(args, "bootstrap_provenance_ok", False),
        bootstrap_provenance_reason=getattr(args, "bootstrap_provenance_reason", ""),
    )
    code, ctx.state, block_report = maybe_advance_to_ready(ctx.state)
    if code != 0:
        save_state(ctx.state_path, ctx.state)
        report = build_transition_blocked_report(
            ctx.state,
            stopping_stage="ready_transition",
            doctor_verdict=ctx.doctor_record["final_verdict"],
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_applied=ctx.selection_applied,
            selected_mode=ctx.selected_mode,
            selected_with_preparation=ctx.selected_with_preparation,
            preparation_applied=ctx.preparation_applied,
            preparation_ready_for_closure=ctx.preparation_ready_for_closure,
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            doctor_record=ctx.doctor_record,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "ready_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(ctx.state_path, ctx.state)
    if ctx.state["doctor"]["status"] != "PASS":
        report = build_blocked_report(ctx.state, ctx.doctor_record)
        report["resume_applied"] = ctx.resume_applied
        report["resume_from_state"] = ctx.resume_from_state
        report["repair_handoff_applied"] = ctx.repair_handoff_applied
        report["repair_handoff_from_state"] = ctx.repair_handoff["from_state"] if ctx.repair_handoff else ""
        report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(ctx.repair_handoff)
        report["missing_continuation_inputs"] = list(ctx.continuation_missing_inputs)
        report["selection_applied"] = ctx.selection_applied
        report["selected_mode"] = ctx.selected_mode
        report["selected_with_preparation"] = ctx.selected_with_preparation
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            doctor_record=ctx.doctor_record,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "doctor"}, ensure_ascii=True))
        return 0

    return None


def _phase_execution_and_proof(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Execution transition, planning, bundle, preparation receipt, bundle application."""
    code, ctx.state, block_report = maybe_advance_to_execution_completed(load_state(ctx.state_path))
    if code != 0:
        save_state(ctx.state_path, ctx.state)
        report = build_transition_blocked_report(
            ctx.state,
            stopping_stage="execution_transition",
            doctor_verdict=ctx.doctor_record["final_verdict"],
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_applied=ctx.selection_applied,
            selected_mode=ctx.selected_mode,
            selected_with_preparation=ctx.selected_with_preparation,
            preparation_applied=ctx.preparation_applied,
            preparation_ready_for_closure=ctx.preparation_ready_for_closure,
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            doctor_record=ctx.doctor_record,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "execution_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(ctx.state_path, ctx.state)

    if args.plan_output:
        artifact_root = args.preparation_artifact_root or str(Path(args.plan_output).parent)
        plan_args = [
            "--run-id", ctx.state["run_id"],
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
            report = build_error_report(ctx.state, reason="PROOF_PLAN_EXECUTION_FAILED", stopping_stage="preparation")
            report["resume_applied"] = ctx.resume_applied
            report["resume_from_state"] = ctx.resume_from_state
            report["repair_handoff_applied"] = ctx.repair_handoff_applied
            report["repair_handoff_from_state"] = ctx.repair_handoff["from_state"] if ctx.repair_handoff else ""
            report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(ctx.repair_handoff)
            report["missing_continuation_inputs"] = list(ctx.continuation_missing_inputs)
            report["selection_applied"] = ctx.selection_applied
            report["selected_mode"] = ctx.selected_mode
            report["selected_with_preparation"] = ctx.selected_with_preparation
            save_json(Path(args.report_output), report)
            return code
        ctx.preparation_applied = True

    bundle_args = [
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--output", args.bundle_output,
        "--run-id", ctx.state["run_id"],
        "--baseline-identity", args.baseline_identity,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
        "--state-file", args.state_file,
    ]
    if args.doctor_output:
        bundle_args.extend(["--doctor-file", args.doctor_output])
    if args.readback:
        bundle_args.extend(["--readback", args.readback])
    if args.scenario_proof:
        bundle_args.extend(["--scenario-proof", args.scenario_proof])
    code, _ = run_python_capture(BUNDLE, bundle_args)
    if code != 0:
        return code

    ctx.bundle = load_json(Path(args.bundle_output))
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
            report = build_error_report(ctx.state, reason="PREPARATION_RECEIPT_EXECUTION_FAILED", stopping_stage="preparation")
            report["resume_applied"] = ctx.resume_applied
            report["resume_from_state"] = ctx.resume_from_state
            report["repair_handoff_applied"] = ctx.repair_handoff_applied
            report["repair_handoff_from_state"] = ctx.repair_handoff["from_state"] if ctx.repair_handoff else ""
            report["repair_handoff_required_inputs"] = repair_handoff_required_input_ids(ctx.repair_handoff)
            report["missing_continuation_inputs"] = list(ctx.continuation_missing_inputs)
            report["selection_applied"] = ctx.selection_applied
            report["selected_mode"] = ctx.selected_mode
            report["selected_with_preparation"] = ctx.selected_with_preparation
            save_json(Path(args.report_output), report)
            return code
        ctx.preparation_receipt = load_json(Path(args.preparation_receipt_output))
        ctx.preparation_ready_for_closure = ctx.preparation_receipt["ready_for_closure"]

    code, ctx.state, block_report = apply_bundle(load_state(ctx.state_path), ctx.bundle)
    if code != 0:
        save_state(ctx.state_path, ctx.state)
        report = build_transition_blocked_report(
            ctx.state,
            stopping_stage="proof_bundle_transition",
            doctor_verdict=ctx.doctor_record["final_verdict"],
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_applied=ctx.selection_applied,
            selected_mode=ctx.selected_mode,
            selected_with_preparation=ctx.selected_with_preparation,
            preparation_applied=ctx.preparation_applied,
            preparation_ready_for_closure=ctx.preparation_ready_for_closure,
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            doctor_record=ctx.doctor_record,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            preparation_receipt=ctx.preparation_receipt,
            bundle=ctx.bundle,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "proof_bundle_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(ctx.state_path, ctx.state)

    return None


def _phase_closure(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Acceptance validation + closure application."""
    closure_args = ["--state-file", args.state_file, "--bundle-file", args.bundle_output, "--output", args.closure_output]
    if getattr(args, "closure_certificate_output", None):
        closure_args.extend(["--certificate-output", args.closure_certificate_output])
    if args.acceptance_validation_output and args.project_profile_file:
        if args.acceptance_criteria_file and Path(args.acceptance_criteria_file).exists():
            code, _ = run_python_capture(
                ACCEPTANCE_CRITERIA,
                [
                    "validate",
                    "--criteria-file", args.acceptance_criteria_file,
                    "--state-file", args.state_file,
                    "--project-profile-file", args.project_profile_file,
                    "--output", args.acceptance_validation_output,
                ],
            )
            if code != 0:
                return code
        else:
            save_json(Path(args.acceptance_validation_output), missing_acceptance_validation_record("CRITERIA_FILE_MISSING"))
        closure_args.extend(["--acceptance-validation-file", args.acceptance_validation_output])

    code, _ = run_python_capture(CLOSURE, closure_args)
    if code != 0:
        return code

    criteria_validation = load_json(Path(args.acceptance_validation_output)) if args.acceptance_validation_output and Path(args.acceptance_validation_output).exists() else None
    closure_state = load_state(ctx.state_path)
    live_bundle = build_bundle(
        argparse.Namespace(
            final_result=getattr(args, "final_result", ""),
            task_class=getattr(args, "task_class", closure_state.get("task_class", "")),
            run_id=getattr(args, "run_id", "") or closure_state.get("run_id", ""),
            readback=getattr(args, "readback", ""),
            scenario_proof=getattr(args, "scenario_proof", ""),
            baseline_identity=getattr(args, "baseline_identity", ""),
            execution_surface_identity=getattr(args, "execution_surface_identity", ""),
            prompt_identity=getattr(args, "prompt_identity", ""),
            task_identity=getattr(args, "task_identity", ""),
            doctor_file=getattr(args, "doctor_output", ""),
            state_file=args.state_file,
            output=args.bundle_output,
        )
    )
    live_bundle["_bundle_file"] = str(Path(args.bundle_output))
    closure_state["_state_file"] = str(ctx.state_path)
    closure_state["_project_root"] = str(state_bound_project_root(args.state_file))
    ctx.bundle = live_bundle
    ctx.closure = build_verdict(closure_state, live_bundle, criteria_validation)
    code, ctx.state, block_report = apply_closure(load_state(ctx.state_path), ctx.closure)
    if code != 0:
        save_json(Path(args.bundle_output), live_bundle)
        save_json(Path(args.closure_output), ctx.closure)
        save_state(ctx.state_path, ctx.state)
        if getattr(args, "closure_certificate_output", None):
            persist_closure_certificate(
                Path(args.closure_certificate_output),
                state=ctx.state,
                state_path=ctx.state_path,
                bundle=ctx.bundle,
                bundle_path=Path(args.bundle_output),
                verdict=ctx.closure,
                criteria_validation=criteria_validation,
            )
        report = build_transition_blocked_report(
            ctx.state,
            stopping_stage="closure_transition",
            doctor_verdict=ctx.doctor_record["final_verdict"],
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_applied=ctx.selection_applied,
            selected_mode=ctx.selected_mode,
            selected_with_preparation=ctx.selected_with_preparation,
            preparation_applied=ctx.preparation_applied,
            preparation_ready_for_closure=ctx.preparation_ready_for_closure,
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            doctor_record=ctx.doctor_record,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            preparation_receipt=ctx.preparation_receipt,
            bundle=ctx.bundle,
            closure=ctx.closure,
            closure_certificate=load_json(Path(args.closure_certificate_output)) if getattr(args, "closure_certificate_output", None) and Path(args.closure_certificate_output).exists() else None,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "closure_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0

    save_json(Path(args.bundle_output), live_bundle)
    save_state(ctx.state_path, ctx.state)
    ctx.state = load_state(ctx.state_path)
    rebound_closure, _, rebound_block_report = enforce_atomic_closure_freshness(
        state=ctx.state,
        state_path=ctx.state_path,
        bundle=ctx.bundle,
        bundle_path=Path(args.bundle_output),
        verdict=ctx.closure,
        criteria_validation=criteria_validation,
    )
    if rebound_block_report is not None:
        ctx.closure = rebound_closure
        ctx.state = apply_verdict_to_state(ctx.state, ctx.bundle, ctx.closure)
        ctx.state["closure_timestamp_utc"] = ""
        save_json(Path(args.closure_output), ctx.closure)
        save_state(ctx.state_path, ctx.state)
        if getattr(args, "closure_certificate_output", None):
            persist_closure_certificate(
                Path(args.closure_certificate_output),
                state=ctx.state,
                state_path=ctx.state_path,
                bundle=ctx.bundle,
                bundle_path=Path(args.bundle_output),
                verdict=ctx.closure,
                criteria_validation=criteria_validation,
            )
        report = build_transition_blocked_report(
            ctx.state,
            stopping_stage="closure_transition",
            doctor_verdict=ctx.doctor_record["final_verdict"],
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_applied=ctx.selection_applied,
            selected_mode=ctx.selected_mode,
            selected_with_preparation=ctx.selected_with_preparation,
            preparation_applied=ctx.preparation_applied,
            preparation_ready_for_closure=ctx.preparation_ready_for_closure,
            block_report=rebound_block_report,
        )
        save_json(Path(args.report_output), report)
        finalize_runtime_outputs(
            args,
            state=ctx.state,
            report=report,
            doctor_record=ctx.doctor_record,
            resume_applied=ctx.resume_applied,
            resume_from_state=ctx.resume_from_state,
            repair_handoff=ctx.repair_handoff,
            missing_continuation_inputs=ctx.continuation_missing_inputs,
            selection_receipt=ctx.selection_receipt,
            preparation_receipt=ctx.preparation_receipt,
            bundle=ctx.bundle,
            closure=ctx.closure,
            closure_certificate=load_json(Path(args.closure_certificate_output)) if getattr(args, "closure_certificate_output", None) and Path(args.closure_certificate_output).exists() else None,
            starting_repair_packet=ctx.starting_repair_packet,
            previous_repair_receipt=ctx.previous_repair_receipt,
        )
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "closure_transition", "reason": rebound_block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0

    accepted_final_result_hash = bound_final_result_sha256(ctx.bundle)
    if ctx.closure.get("closure_status") == "ACCEPTED" and accepted_final_result_hash:
        ctx.state["last_known_final_result_hash"] = accepted_final_result_hash
        save_state(ctx.state_path, ctx.state)
    save_json(Path(args.closure_output), ctx.closure)
    if getattr(args, "closure_certificate_output", None):
        persist_closure_certificate(
            Path(args.closure_certificate_output),
            state=ctx.state,
            state_path=ctx.state_path,
            bundle=ctx.bundle,
            bundle_path=Path(args.bundle_output),
            verdict=ctx.closure,
            criteria_validation=criteria_validation,
        )
    return None


def _phase_refresh_and_comparison(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Refresh + comparison."""
    ctx.state = load_state(ctx.state_path)
    ctx.stopping_stage = "closure" if ctx.closure["closure_status"] != "ACCEPTED" else "accepted"
    ctx.reason = ctx.closure["blocking_reason"] or "NONE"

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
        ctx.state = load_state(ctx.state_path)
        ctx.refresh_report = load_json(Path(args.refresh_output))
        ctx.refresh_applied = True
        ctx.refresh_resulting_closure_status = ctx.refresh_report["resulting_closure_status"]
        ctx.stopping_stage = "refresh"
        ctx.reason = ctx.state["closure"]["blocking_reason"] or "NONE"

    if args.comparison_output and args.baseline_file and args.synrail_file:
        try:
            harness = comparison_harness_for_inputs(args.baseline_file, args.synrail_file)
        except ValueError:
            return 2
        code, _ = run_python_capture(harness, ["--baseline-file", args.baseline_file, "--synrail-file", args.synrail_file, "--output", args.comparison_output])
        if code != 0:
            return code
        ctx.comparison = load_json(Path(args.comparison_output))
        ctx.comparison_applied = True
        ctx.comparison_verdict = ctx.comparison["verdict"]
        ctx.stopping_stage = "comparison"

    return None


def _phase_final_report(ctx: OrchestrationContext, args: argparse.Namespace) -> int | None:
    """Final report building."""
    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": ctx.state["run_id"],
        "task_class": ctx.state["task_class"],
        "result": "OK",
        "stopping_stage": ctx.stopping_stage,
        "reason": ctx.reason,
        "doctor_verdict": ctx.doctor_record["final_verdict"],
        "resume_applied": ctx.resume_applied,
        "resume_from_state": ctx.resume_from_state,
        "repair_handoff_applied": ctx.repair_handoff_applied,
        "repair_handoff_from_state": ctx.repair_handoff["from_state"] if ctx.repair_handoff else "",
        "repair_handoff_required_inputs": repair_handoff_required_input_ids(ctx.repair_handoff),
        "missing_continuation_inputs": list(ctx.continuation_missing_inputs),
        "selection_applied": ctx.selection_applied,
        "selected_mode": ctx.selected_mode,
        "selected_with_preparation": ctx.selected_with_preparation,
        "preparation_applied": ctx.preparation_applied,
        "preparation_ready_for_closure": ctx.preparation_ready_for_closure,
        "bundle_status": ctx.bundle["status"],
        "closure_status": ctx.state["closure"]["status"],
        "refresh_applied": ctx.refresh_applied,
        "refresh_resulting_closure_status": ctx.refresh_resulting_closure_status,
        "comparison_applied": ctx.comparison_applied,
        "comparison_verdict": ctx.comparison_verdict,
        "blockers": [],
        "dominant_blocker": "",
        "resulting_state": ctx.state["state"],
        "next_safe_step": ctx.state["next_safe_step"],
    }
    save_json(Path(args.report_output), report)
    finalize_runtime_outputs(
        args,
        state=ctx.state,
        report=report,
        doctor_record=ctx.doctor_record,
        resume_applied=ctx.resume_applied,
        resume_from_state=ctx.resume_from_state,
        repair_handoff=ctx.repair_handoff,
        missing_continuation_inputs=ctx.continuation_missing_inputs,
        selection_receipt=ctx.selection_receipt,
        preparation_receipt=ctx.preparation_receipt,
        bundle=ctx.bundle,
        closure=ctx.closure,
        refresh_report=ctx.refresh_report,
        comparison=ctx.comparison,
        starting_repair_packet=ctx.starting_repair_packet,
        previous_repair_receipt=ctx.previous_repair_receipt,
    )

    print(json.dumps({"result": "OK", "closure_status": ctx.state["closure"]["status"]}, ensure_ascii=True))
    return 0


def current_project_root() -> Path:
    return Path.cwd().resolve()


def inferred_spine_artifact_root(args: argparse.Namespace) -> Path | None:
    for field in [
        "state_file",
        "output",
        "report_output",
        "doctor_output",
        "bundle_output",
        "closure_output",
        "closure_certificate_output",
    ]:
        value = getattr(args, field, None)
        if value:
            return Path(value).expanduser().resolve().parent
    return None


def validate_spine_paths(args: argparse.Namespace) -> None:
    artifact_root = inferred_spine_artifact_root(args)
    target_path = getattr(args, "target_path", None)
    project_root = Path(target_path).expanduser().resolve() if target_path else current_project_root()
    if artifact_root is not None:
        anchor_field = "state_file"
        anchor_value = getattr(args, "state_file", None)
        if not anchor_value:
            for field in ["output", "report_output", "doctor_output", "bundle_output", "closure_output", "closure_certificate_output"]:
                value = getattr(args, field, None)
                if value:
                    anchor_field = field
                    anchor_value = value
                    break
        validate_root_within_project(
            anchor_field,
            str(anchor_value),
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
    validate_namespace_paths(
        args,
        field_scopes=SPINE_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def cmd_orchestrate(args: argparse.Namespace) -> int:
    ctx = OrchestrationContext(
        state=load_state(Path(args.state_file)),
        state_path=Path(args.state_file),
        resume_applied=bool(args.resume_from_state),
        resume_from_state=args.resume_from_state or "",
    )
    for phase in [
        _phase_init,
        _phase_resume_and_handoff,
        _phase_mode_governance,
        _phase_target_surface,
        _phase_doctor,
        _phase_integrity_and_readiness,
        _phase_execution_and_proof,
        _phase_closure,
        _phase_refresh_and_comparison,
        _phase_final_report,
    ]:
        code = phase(ctx, args)
        if code is not None:
            return code
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
    p_orchestrate.add_argument("--closure-certificate-output")
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
    p_orchestrate.add_argument("--observability-output")
    p_orchestrate.add_argument("--artifact-consistency-output")
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
    p_orchestrate.add_argument("--changed-file", action="append", default=[])
    p_orchestrate.add_argument("--allowed-scope-path", action="append", default=[])
    p_orchestrate.add_argument("--prompt-identity-file")
    p_orchestrate.add_argument("--target-identity-file")
    p_orchestrate.add_argument("--coverage-profile-file")
    p_orchestrate.add_argument("--coverage-corpus-file")
    p_orchestrate.add_argument("--bootstrap-provenance-ok", action="store_true")
    p_orchestrate.add_argument("--bootstrap-provenance-reason", default="")
    p_orchestrate.add_argument("--expected-target-identity")
    p_orchestrate.add_argument("--acceptance-criteria-file")
    p_orchestrate.add_argument("--acceptance-validation-output")
    p_orchestrate.add_argument("--project-profile-file")
    p_orchestrate.set_defaults(func=cmd_orchestrate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        if getattr(args, "cmd", "") in {"init", "transition", "show", "apply-bundle", "apply-doctor", "apply-closure", "orchestrate"}:
            validate_spine_paths(args)
        return args.func(args)
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
