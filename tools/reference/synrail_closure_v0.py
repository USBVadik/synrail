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

SEMANTIC_SECTION_STEPS = {
    "modified_files": "record the actual changed files in the final result artifact",
    "diff_provenance": "capture non-empty diff or provenance evidence for the changed files",
    "readback": "record substantive readback from the changed sections on the attested surface",
    "scenario_proof": "record an explicit scenario-proof result for the attested target surface",
    "artifact_identity": "repair baseline, surface, prompt, and task identity fields",
    "cleanup_status": "record a successful cleanup status for the execution surface",
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


def first_semantic_step(semantically_insufficient_sections: list[str]) -> str:
    for section in semantically_insufficient_sections:
        if section in SEMANTIC_SECTION_STEPS:
            return SEMANTIC_SECTION_STEPS[section]
    return "strengthen the semantic proof evidence before trusting closure"


def build_verdict(state: dict, bundle: dict, criteria_validation: dict | None = None) -> dict:
    missing_sections = list(bundle.get("missing_sections", []))
    semantically_insufficient_sections = list(bundle.get("semantically_insufficient_sections", []))
    state_run_id = state.get("run_id", "")
    bundle_run_id = bundle.get("run_id", "")
    artifact_request_id = (bundle.get("final_result", {}).get("request_id", "") or "").strip()
    run_id = state_run_id or bundle_run_id
    task_class = state.get("task_class", bundle.get("task_class", ""))
    criteria_validation = criteria_validation or {}

    # Cross-artifact identity binding: if state, bundle, or final-result
    # request_id disagree, the proof was assembled from mixed run surfaces.
    run_id_mismatch = bool(
        (state_run_id and artifact_request_id and state_run_id != artifact_request_id)
        or (state_run_id and bundle_run_id and state_run_id != bundle_run_id)
    )

    verdict = {
        "schema_version": "closure_verdict_v0",
        "run_id": run_id,
        "task_class": task_class,
        "closure_status": "CLAIMED_NOT_ACCEPTED",
        "blocking_reason": "",
        "next_allowed_transition": "",
        "narrow_next_safe_step": "",
        "missing_sections": missing_sections,
        "semantically_insufficient_sections": semantically_insufficient_sections,
        "acceptance_criteria_revision_id": criteria_validation.get("criteria_revision_id", ""),
        "acceptance_criteria_status": criteria_validation.get("status", ""),
        "acceptance_criteria_reason": criteria_validation.get("reason", ""),
    }

    if run_id_mismatch:
        verdict["blocking_reason"] = "RUN_ID_MISMATCH"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "rebuild the proof bundle for the current run"
        return verdict

    criteria_status = criteria_validation.get("status", "")
    if criteria_status == "STALE":
        verdict["blocking_reason"] = "ACCEPTANCE_CRITERIA_STALE"
        verdict["next_allowed_transition"] = "ACCEPTANCE_CRITERIA_REFRESH"
        verdict["narrow_next_safe_step"] = "refresh the acceptance criteria for the current project state"
        return verdict
    if criteria_status == "INVALID":
        verdict["blocking_reason"] = "ACCEPTANCE_CRITERIA_INVALID"
        verdict["next_allowed_transition"] = "ACCEPTANCE_CRITERIA_REPAIR"
        verdict["narrow_next_safe_step"] = "repair or rebuild the acceptance criteria before trusting closure"
        return verdict

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

    if not state["integrity"].get("bootstrap_provenance_ok", False):
        verdict["blocking_reason"] = "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"
        verdict["next_allowed_transition"] = "CONTROLLED_START"
        verdict["narrow_next_safe_step"] = "start the run in controlled mode before trusting any proof or acceptance"
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

    if bundle.get("status") == "STRUCTURALLY_COMPLETE":
        verdict["blocking_reason"] = "SEMANTIC_PROOF_INSUFFICIENT"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_STRENGTHENING"
        verdict["narrow_next_safe_step"] = bundle.get("semantic_next_safe_step", "") or first_semantic_step(semantically_insufficient_sections)
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
    state["proof_bundle"]["structural_status"] = bundle.get("structural_status", bundle.get("status", "INVALID"))
    state["proof_bundle"]["semantic_status"] = bundle.get("semantic_status", "NOT_EVALUATED")
    state["proof_bundle"]["missing_sections"] = list(bundle.get("missing_sections", []))
    state["proof_bundle"]["semantically_insufficient_sections"] = list(bundle.get("semantically_insufficient_sections", []))
    state["proof_bundle"]["semantic_next_safe_step"] = bundle.get("semantic_next_safe_step", "")
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
    elif state["proof_bundle"]["status"] == "STRUCTURALLY_COMPLETE":
        state["state"] = "PROOF_BUNDLE_STRUCTURALLY_COMPLETE"

    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-closure-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--bundle-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--acceptance-validation-file")
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
    verdict = build_verdict(
        state,
        bundle,
        load_json(Path(args.acceptance_validation_file)) if args.acceptance_validation_file else None,
    )
    save_json(output_path, verdict)

    if args.update_state:
        updated_state = apply_verdict_to_state(state, bundle, verdict)
        save_json(state_path, updated_state)

    print(json.dumps({"result": "OK", "closure_status": verdict["closure_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
