#!/usr/bin/env python3
"""Minimal closure engine for Synrail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MISSING_SECTION_STEPS = {
    "readback": "collect readback from changed sections on the attested surface",
    "scenario_proof": "rerun the scenario check against the attested target surface",
    "artifact_identity": "repair baseline, surface, prompt, and task identity fields",
    "cleanup_status": "record cleanup status for the execution surface",
    "final_result": "recover the final result artifact and rerun bundle assembly",
    "modified_files": "recover modified-files evidence from the final result artifact",
    "diff_provenance": "recover diff or provenance evidence from the final result artifact",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def first_missing_step(missing_sections: list[str]) -> str:
    for section in missing_sections:
        if section in MISSING_SECTION_STEPS:
            return MISSING_SECTION_STEPS[section]
    return "complete the missing proof sections"


def build_verdict(state: dict, bundle: dict) -> dict:
    missing_sections = list(bundle.get("missing_sections", []))
    run_id = state.get("run_id", bundle.get("run_id", ""))
    task_class = state.get("task_class", bundle.get("task_class", ""))

    verdict = {
        "schema_version": "closure_verdict_v0",
        "run_id": run_id,
        "task_class": task_class,
        "closure_status": "CLAIMED_NOT_ACCEPTED",
        "blocking_reason": "",
        "next_allowed_transition": "",
        "narrow_next_safe_step": "",
        "missing_sections": missing_sections,
    }

    if state["target_surface"]["status"] != "ATTESTED":
        verdict["blocking_reason"] = "TARGET_SURFACE_NOT_ATTESTED"
        verdict["next_allowed_transition"] = "TARGET_SURFACE_ATTESTED"
        verdict["narrow_next_safe_step"] = "attest target surface"
        return verdict

    if state["doctor"]["status"] != "PASS":
        verdict["blocking_reason"] = "DOCTOR_NOT_GREEN"
        verdict["next_allowed_transition"] = "DOCTOR_READINESS"
        verdict["narrow_next_safe_step"] = "run doctor and clear blocking failure classes"
        return verdict

    if not state["integrity"]["exact_task_identity_ok"]:
        verdict["blocking_reason"] = "EXACT_TASK_IDENTITY_NOT_CONFIRMED"
        verdict["next_allowed_transition"] = "INTEGRITY_RECONFIRMATION"
        verdict["narrow_next_safe_step"] = "reconfirm exact task, prompt, and run-class identity"
        return verdict

    if state["execution"]["status"] != "COMPLETED":
        verdict["blocking_reason"] = "EXECUTION_NOT_COMPLETED"
        verdict["next_allowed_transition"] = "EXECUTION_COMPLETION"
        verdict["narrow_next_safe_step"] = "complete execution and capture the final result artifact"
        return verdict

    if bundle.get("status") == "INVALID":
        verdict["blocking_reason"] = "INVALID_PROOF_BUNDLE"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "repair the final result artifact and rebuild the proof bundle"
        return verdict

    if bundle.get("status") != "COMPLETE":
        verdict["blocking_reason"] = "MISSING_PROOF_SECTIONS"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_COMPLETION"
        verdict["narrow_next_safe_step"] = first_missing_step(missing_sections)
        return verdict

    if state["recovery"]["status"] == "PENDING" and not state["recovery"]["reverification_complete"]:
        verdict["blocking_reason"] = "RECOVERY_REVERIFICATION_INCOMPLETE"
        verdict["next_allowed_transition"] = "RECOVERY_REVERIFICATION"
        verdict["narrow_next_safe_step"] = "run reverification against the attested target surface"
        return verdict

    verdict["closure_status"] = "ACCEPTED"
    verdict["blocking_reason"] = ""
    verdict["next_allowed_transition"] = "NONE"
    verdict["narrow_next_safe_step"] = "NONE"
    verdict["missing_sections"] = []
    return verdict


def apply_verdict_to_state(state: dict, bundle: dict, verdict: dict) -> dict:
    state["execution"]["artifact_bundle_present"] = bool(bundle.get("final_result", {}).get("present", False))
    state["proof_bundle"]["status"] = bundle.get("status", "INVALID")
    state["proof_bundle"]["missing_sections"] = list(bundle.get("missing_sections", []))
    state["closure"]["status"] = verdict["closure_status"]
    state["closure"]["blocking_reason"] = verdict["blocking_reason"]
    state["closure"]["next_allowed_transition"] = verdict["next_allowed_transition"]
    state["closure"]["narrow_next_safe_step"] = verdict["narrow_next_safe_step"]
    state["closure"]["missing_sections"] = list(verdict["missing_sections"])
    state["next_safe_step"] = verdict["narrow_next_safe_step"]

    if verdict["closure_status"] == "ACCEPTED":
        state["state"] = "CLOSURE_ACCEPTED"
    elif verdict["closure_status"] == "REJECTED":
        state["state"] = "CLOSURE_REJECTED"
    elif state["proof_bundle"]["status"] == "COMPLETE":
        state["state"] = "PROOF_BUNDLE_COMPLETE"

    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-closure-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--bundle-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--update-state", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    state_path = Path(args.state_file)
    bundle_path = Path(args.bundle_file)
    output_path = Path(args.output)

    state = load_json(state_path)
    bundle = load_json(bundle_path)
    verdict = build_verdict(state, bundle)
    save_json(output_path, verdict)

    if args.update_state:
        updated_state = apply_verdict_to_state(state, bundle, verdict)
        save_json(state_path, updated_state)

    print(json.dumps({"result": "OK", "closure_status": verdict["closure_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
