#!/usr/bin/env python3
"""Minimal refresh-chain automation for Synrail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json

try:
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


REFRESH_PATH_SCOPES = {
    "state_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
    "bundle_file": ARTIFACT_SCOPE,
    "closure_file": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_refresh_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=REFRESH_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )






PRECEDENCE = [
    "closure_invalidated_by_doctor",
    "closure_invalidated_by_invalid_bundle",
    "closure_invalidated_by_semantic_bundle",
    "closure_invalidated_by_partial_bundle",
    "closure_invalidated_by_recovery",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-refresh-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--doctor-status", choices=["PASS", "FAIL"])
    parser.add_argument("--bundle-file")
    parser.add_argument("--closure-file")
    parser.add_argument("--recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    parser.add_argument("--reverification-complete", action="store_true")
    parser.add_argument("--update-state", action="store_true")
    return parser


def applicable_invalidations(state: dict) -> list[str]:
    invalidations: list[str] = []
    if state["doctor"]["status"] == "FAIL":
        invalidations.append("closure_invalidated_by_doctor")
    if state["proof_bundle"]["status"] == "INVALID":
        invalidations.append("closure_invalidated_by_invalid_bundle")
    elif state["proof_bundle"]["status"] == "STRUCTURALLY_COMPLETE":
        invalidations.append("closure_invalidated_by_semantic_bundle")
    elif state["proof_bundle"]["status"] != "COMPLETE":
        invalidations.append("closure_invalidated_by_partial_bundle")
    if state["recovery"]["status"] == "PENDING" and not state["recovery"]["reverification_complete"]:
        invalidations.append("closure_invalidated_by_recovery")
    return invalidations


def dominant_invalidation(invalidations: list[str]) -> str:
    for candidate in PRECEDENCE:
        if candidate in invalidations:
            return candidate
    return ""


def apply_dominant_invalidation(state: dict, dominant: str) -> None:
    if dominant == "closure_invalidated_by_doctor":
        state["state"] = "DOCTOR_BLOCKED"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "DOCTOR_NOT_GREEN"
        state["closure"]["next_allowed_transition"] = "DOCTOR_READINESS"
        state["closure"]["narrow_next_safe_step"] = "run doctor and clear blocking failure classes"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return

    if dominant == "closure_invalidated_by_invalid_bundle":
        state["state"] = "PROOF_BUNDLE_INVALID"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "INVALID_PROOF_BUNDLE"
        state["closure"]["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        state["closure"]["narrow_next_safe_step"] = "repair the final result artifact and rebuild the proof bundle"
        state["closure"]["missing_sections"] = list(state["proof_bundle"]["missing_sections"])
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return

    if dominant == "closure_invalidated_by_semantic_bundle":
        state["state"] = "PROOF_BUNDLE_STRUCTURALLY_COMPLETE"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "SEMANTIC_PROOF_INSUFFICIENT"
        state["closure"]["next_allowed_transition"] = "PROOF_BUNDLE_STRENGTHENING"
        state["closure"]["narrow_next_safe_step"] = state["proof_bundle"].get("semantic_next_safe_step", "") or "strengthen the semantic proof evidence before trusting closure"
        state["closure"]["missing_sections"] = list(state["proof_bundle"].get("semantically_insufficient_sections", []))
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return

    if dominant == "closure_invalidated_by_partial_bundle":
        state["state"] = "PROOF_BUNDLE_PARTIAL"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "MISSING_PROOF_SECTIONS"
        state["closure"]["next_allowed_transition"] = "PROOF_BUNDLE_COMPLETION"
        state["closure"]["narrow_next_safe_step"] = "complete the missing proof sections"
        state["closure"]["missing_sections"] = list(state["proof_bundle"]["missing_sections"])
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return

    if dominant == "closure_invalidated_by_recovery":
        state["state"] = "RECOVERY_PENDING"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "RECOVERY_REVERIFICATION_INCOMPLETE"
        state["closure"]["next_allowed_transition"] = "RECOVERY_REVERIFICATION"
        state["closure"]["narrow_next_safe_step"] = "run reverification against the attested target surface"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        return


def apply_event(args: argparse.Namespace, state: dict) -> tuple[dict, dict]:
    steps_applied: list[str] = []

    if args.doctor_status:
        state["doctor"]["status"] = args.doctor_status
        steps_applied.append("doctor_status_refreshed")

    if args.bundle_file:
        bundle = load_json(Path(args.bundle_file))
        state["execution"]["artifact_bundle_present"] = bool(bundle.get("final_result", {}).get("present", False))
        state["proof_bundle"]["status"] = bundle.get("status", "INVALID")
        state["proof_bundle"]["structural_status"] = bundle.get("structural_status", bundle.get("status", "INVALID"))
        state["proof_bundle"]["semantic_status"] = bundle.get("semantic_status", "NOT_EVALUATED")
        state["proof_bundle"]["missing_sections"] = list(bundle.get("missing_sections", []))
        state["proof_bundle"]["semantically_insufficient_sections"] = list(bundle.get("semantically_insufficient_sections", []))
        state["proof_bundle"]["semantic_next_safe_step"] = bundle.get("semantic_next_safe_step", "")
        steps_applied.append("proof_bundle_refreshed")

    if args.closure_file:
        closure = load_json(Path(args.closure_file))
        state["closure"]["status"] = closure["closure_status"]
        state["closure"]["blocking_reason"] = closure["blocking_reason"]
        state["closure"]["next_allowed_transition"] = closure["next_allowed_transition"]
        state["closure"]["narrow_next_safe_step"] = closure["narrow_next_safe_step"]
        state["closure"]["missing_sections"] = list(closure["missing_sections"])
        state["next_safe_step"] = closure["narrow_next_safe_step"]
        steps_applied.append("closure_verdict_refreshed")

    if args.recovery_status:
        state["recovery"]["status"] = args.recovery_status
        state["recovery"]["reverification_complete"] = bool(args.reverification_complete)
        steps_applied.append("recovery_status_refreshed")

    invalidations = applicable_invalidations(state)
    dominant = dominant_invalidation(invalidations)
    if dominant:
        apply_dominant_invalidation(state, dominant)

    if (
        not invalidations
        and state["closure"]["status"] == "CLAIMED_NOT_ACCEPTED"
        and state["closure"]["blocking_reason"] == "RECOVERY_REVERIFICATION_INCOMPLETE"
        and state["proof_bundle"]["status"] == "COMPLETE"
        and state["doctor"]["status"] != "FAIL"
        and state["recovery"]["status"] == "COMPLETE"
        and state["recovery"]["reverification_complete"]
    ):
        state["closure"]["status"] = "ACCEPTED"
        state["closure"]["blocking_reason"] = ""
        state["closure"]["next_allowed_transition"] = "NONE"
        state["closure"]["narrow_next_safe_step"] = "NONE"
        state["closure"]["missing_sections"] = []
        state["state"] = "CLOSURE_ACCEPTED"
        state["next_safe_step"] = "NONE"
    elif state["closure"]["status"] == "ACCEPTED":
        state["state"] = "CLOSURE_ACCEPTED"
        state["next_safe_step"] = "NONE"
    elif state["proof_bundle"]["status"] == "COMPLETE" and state["recovery"]["status"] != "PENDING" and state["doctor"]["status"] != "FAIL":
        state["state"] = "PROOF_BUNDLE_COMPLETE"

    report = {
        "schema_version": "refresh_report_v0",
        "run_id": state["run_id"],
        "event_type": args.event_type,
        "steps_applied": steps_applied,
        "invalidations": invalidations,
        "dominant_invalidation": dominant,
        "resulting_state": state["state"],
        "resulting_closure_status": state["closure"]["status"],
        "next_safe_step": state["next_safe_step"],
    }
    return state, report


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        artifact_root = Path(args.state_file).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "state_file",
            args.state_file,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_refresh_paths(args, artifact_root=artifact_root, project_root=project_root)
        state_path = Path(args.state_file)
        output_path = Path(args.output)
        state = load_json(state_path)
        updated_state, report = apply_event(args, state)
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(output_path, report)
    if args.update_state:
        save_json(state_path, updated_state)
    print(json.dumps({"result": "OK", "resulting_closure_status": report["resulting_closure_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
