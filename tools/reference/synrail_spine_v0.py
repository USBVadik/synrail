#!/usr/bin/env python3
"""Minimal executable Synrail spine prototype."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


TERMINAL_STATES = {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}
HERE = Path(__file__).resolve().parent
DOCTOR = HERE / "synrail_doctor_v1.py"
BUNDLE = HERE / "synrail_bundle_v0.py"
CLOSURE = HERE / "synrail_closure_v0.py"
REFRESH = HERE / "synrail_refresh_v0.py"
HARNESS_V0 = HERE / "synrail_baseline_harness_v0.py"
HARNESS_V1 = HERE / "synrail_baseline_harness_v1.py"

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
        )
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


def build_canonical_run_artifact(*, state: dict, report: dict, worked: dict) -> dict:
    return {
        "schema_version": "canonical_run_artifact_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "report": {
            "result": report["result"],
            "stopping_stage": report["stopping_stage"],
            "reason": report["reason"],
            "doctor_verdict": report["doctor_verdict"],
            "bundle_status": report["bundle_status"],
            "closure_status": report["closure_status"],
            "refresh_applied": report["refresh_applied"],
            "comparison_applied": report["comparison_applied"],
            "blockers": list(report["blockers"]),
            "dominant_blocker": report["dominant_blocker"],
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
    }


def emit_requested_artifacts(
    args: argparse.Namespace,
    *,
    state: dict,
    report: dict,
    doctor_record: dict | None = None,
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
        bundle=bundle,
        closure=closure,
        refresh_report=refresh_report,
        comparison=comparison,
    )
    if args.worked_artifact_output:
        save_json(Path(args.worked_artifact_output), worked)
    if args.run_artifact_output:
        canonical = build_canonical_run_artifact(state=state, report=report, worked=worked)
        save_json(Path(args.run_artifact_output), canonical)


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
            block_report=block_report,
        )
        save_state(state_path, state)
        save_json(Path(args.report_output), report)
        emit_requested_artifacts(args, state=state, report=report)
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
    ]:
        if value:
            doctor_args.extend([flag, value])
    for env_name in args.credential_env:
        doctor_args.extend(["--credential-env", env_name])

    code, _ = run_python_capture(DOCTOR, doctor_args)
    if code != 0:
        save_json(Path(args.report_output), build_error_report(state, reason="DOCTOR_EXECUTION_FAILED"))
        return code

    doctor_record = load_json(Path(args.doctor_output))
    code, state, block_report = apply_doctor(load_state(state_path), doctor_record)
    if code != 0:
        save_state(state_path, state)
        report = build_error_report(state, reason=block_report["dominant_blocker"], stopping_stage="doctor_apply")
        save_json(Path(args.report_output), report)
        emit_requested_artifacts(args, state=state, report=report, doctor_record=doctor_record)
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
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        emit_requested_artifacts(args, state=state, report=report, doctor_record=doctor_record)
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "ready_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(state_path, state)
    if state["doctor"]["status"] != "PASS":
        report = build_blocked_report(state, doctor_record)
        save_json(Path(args.report_output), report)
        emit_requested_artifacts(args, state=state, report=report, doctor_record=doctor_record)
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "doctor"}, ensure_ascii=True))
        return 0

    code, state, block_report = maybe_advance_to_execution_completed(load_state(state_path))
    if code != 0:
        save_state(state_path, state)
        report = build_transition_blocked_report(
            state,
            stopping_stage="execution_transition",
            doctor_verdict=doctor_record["final_verdict"],
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        emit_requested_artifacts(args, state=state, report=report, doctor_record=doctor_record)
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "execution_transition", "reason": block_report["dominant_blocker"]}, ensure_ascii=True))
        return 0
    save_state(state_path, state)

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
    code, state, block_report = apply_bundle(load_state(state_path), bundle)
    if code != 0:
        save_state(state_path, state)
        report = build_transition_blocked_report(
            state,
            stopping_stage="proof_bundle_transition",
            doctor_verdict=doctor_record["final_verdict"],
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        emit_requested_artifacts(args, state=state, report=report, doctor_record=doctor_record, bundle=bundle)
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
            block_report=block_report,
        )
        save_json(Path(args.report_output), report)
        emit_requested_artifacts(args, state=state, report=report, doctor_record=doctor_record, bundle=bundle, closure=closure)
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
    emit_requested_artifacts(
        args,
        state=state,
        report=report,
        doctor_record=doctor_record,
        bundle=bundle,
        closure=closure,
        refresh_report=refresh_report,
        comparison=comparison,
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
    p_orchestrate.set_defaults(func=cmd_orchestrate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
