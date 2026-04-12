#!/usr/bin/env python3
"""Minimal executable Synrail spine prototype."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


TERMINAL_STATES = {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}


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


def save_state(path: Path, state: dict) -> None:
    path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")


def deny(message: str) -> int:
    print(json.dumps({"result": "DENY", "reason": message}, ensure_ascii=True))
    return 2


def allow(state: dict, target: str, next_safe_step: str) -> dict:
    state["state"] = target
    state["next_safe_step"] = next_safe_step
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
    if state["proof_bundle"]["status"] != "COMPLETE":
        return False, "PROOF_BUNDLE_INCOMPLETE"
    return True, ""


def gate_recovery(state: dict) -> tuple[bool, str]:
    if state["recovery"]["status"] == "PENDING" and not state["recovery"]["reverification_complete"]:
        return False, "RECOVERY_REVERIFICATION_INCOMPLETE"
    return True, ""


def transition(state: dict, target: str) -> tuple[int, dict | None]:
    current = state["state"]
    if current in TERMINAL_STATES:
        return deny("TERMINAL_STATE"), None

    if target == "TARGET_SURFACE_ATTESTED":
        ok, reason = gate_target_surface(state)
        if not ok:
            return deny(reason), None
        return 0, allow(state, target, "run doctor readiness")

    if target == "READY":
        for gate in (gate_target_surface, gate_doctor, gate_integrity):
            ok, reason = gate(state)
            if not ok:
                return deny(reason), None
        return 0, allow(state, target, "run execution")

    if target == "EXECUTION_COMPLETED":
        for gate in (gate_target_surface, gate_doctor, gate_integrity):
            ok, reason = gate(state)
            if not ok:
                return deny(reason), None
        if state["execution"]["status"] != "COMPLETED":
            return deny("EXECUTION_NOT_COMPLETED"), None
        return 0, allow(state, target, "assemble proof bundle")

    if target == "PROOF_BUNDLE_COMPLETE":
        ok, reason = gate_artifacts(state)
        if not ok:
            return deny(reason), None
        ok, reason = gate_proof_bundle(state)
        if not ok:
            return deny(reason), None
        return 0, allow(state, target, "decide closure")

    if target == "CLOSURE_ACCEPTED":
        for gate in (gate_artifacts, gate_proof_bundle, gate_recovery):
            ok, reason = gate(state)
            if not ok:
                return deny(reason), None
        state["closure"]["status"] = "ACCEPTED"
        state["closure"]["blocking_reason"] = ""
        state["closure"]["next_allowed_transition"] = "NONE"
        state["closure"]["narrow_next_safe_step"] = "NONE"
        state["closure"]["missing_sections"] = []
        return 0, allow(state, target, "NONE")

    if target == "CLOSURE_REJECTED":
        state["closure"]["status"] = "REJECTED"
        state["closure"]["next_allowed_transition"] = "emit narrow next safe step"
        state["closure"]["narrow_next_safe_step"] = "emit narrow next safe step"
        return 0, allow(state, target, "emit narrow next safe step")

    return deny(f"UNKNOWN_TARGET_STATE:{target}"), None


def apply_bundle(state: dict, bundle: dict) -> tuple[int, dict | None]:
    state["execution"]["artifact_bundle_present"] = bool(bundle.get("final_result", {}).get("present", False))
    state["proof_bundle"]["status"] = bundle.get("status", "INVALID")
    state["proof_bundle"]["missing_sections"] = list(bundle.get("missing_sections", []))

    if bundle.get("status") == "COMPLETE":
        return transition(state, "PROOF_BUNDLE_COMPLETE")

    state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
    if bundle.get("status") == "INVALID":
        state["closure"]["blocking_reason"] = "INVALID_PROOF_BUNDLE"
        state["closure"]["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        state["closure"]["narrow_next_safe_step"] = "repair the final result artifact and rebuild the proof bundle"
    else:
        state["closure"]["blocking_reason"] = "MISSING_PROOF_SECTIONS"
        state["closure"]["next_allowed_transition"] = "PROOF_BUNDLE_COMPLETION"
        state["closure"]["narrow_next_safe_step"] = "complete the missing proof sections"
    state["closure"]["missing_sections"] = list(bundle.get("missing_sections", []))
    state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
    state["state"] = "EXECUTION_COMPLETED"
    return 0, state


def apply_doctor(state: dict, record: dict) -> tuple[int, dict | None]:
    acceptable = record.get("final_verdict", "").startswith("ACCEPTABLE_")
    state["doctor"]["status"] = "PASS" if acceptable else "FAIL"
    state["doctor"]["blocking_failure_classes"] = list(record.get("blocking_failure_classes", []))

    if acceptable:
        state["closure"]["status"] = "OPEN"
        state["closure"]["blocking_reason"] = ""
        state["closure"]["next_allowed_transition"] = "READY"
        state["closure"]["narrow_next_safe_step"] = "confirm exact task identity"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = "confirm exact task identity"
        return 0, state

    state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
    state["closure"]["blocking_reason"] = "DOCTOR_NOT_GREEN"
    state["closure"]["next_allowed_transition"] = "DOCTOR_READINESS"
    state["closure"]["narrow_next_safe_step"] = record.get("recommended_next_safe_step", "run doctor readiness")
    state["closure"]["missing_sections"] = []
    state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
    return 0, state


def apply_closure(state: dict, verdict: dict) -> tuple[int, dict | None]:
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

    if state["proof_bundle"]["status"] == "COMPLETE":
        state["state"] = "PROOF_BUNDLE_COMPLETE"
    else:
        state["state"] = "EXECUTION_COMPLETED"
    return 0, state


def cmd_init(args: argparse.Namespace) -> int:
    state = default_state(args.run_id, args.task_class)
    save_state(Path(args.output), state)
    print(json.dumps({"result": "OK", "state": state["state"]}, ensure_ascii=True))
    return 0


def cmd_transition(args: argparse.Namespace) -> int:
    path = Path(args.state_file)
    state = load_state(path)
    code, next_state = transition(state, args.target)
    if code != 0:
        return code
    save_state(path, next_state)
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
    code, next_state = apply_bundle(state, bundle)
    if code != 0:
        return code
    save_state(state_path, next_state)
    print(json.dumps({"result": "OK", "state": next_state["state"], "proof_bundle": next_state["proof_bundle"]["status"]}, ensure_ascii=True))
    return 0


def cmd_apply_doctor(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    record = load_json(Path(args.doctor_file))
    code, next_state = apply_doctor(state, record)
    if code != 0:
        return code
    save_state(state_path, next_state)
    print(json.dumps({"result": "OK", "doctor": next_state["doctor"]["status"], "next_safe_step": next_state["next_safe_step"]}, ensure_ascii=True))
    return 0


def cmd_apply_closure(args: argparse.Namespace) -> int:
    state_path = Path(args.state_file)
    state = load_state(state_path)
    verdict = load_json(Path(args.closure_file))
    code, next_state = apply_closure(state, verdict)
    if code != 0:
        return code
    save_state(state_path, next_state)
    print(json.dumps({"result": "OK", "state": next_state["state"], "closure": next_state["closure"]["status"]}, ensure_ascii=True))
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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
