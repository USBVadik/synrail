#!/usr/bin/env python3
"""Minimal refresh-chain automation for Synrail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


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


def downgrade_for_doctor(state: dict, invalidations: list[str]) -> None:
    if state["doctor"]["status"] == "FAIL":
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "DOCTOR_NOT_GREEN"
        state["closure"]["next_allowed_transition"] = "DOCTOR_READINESS"
        state["closure"]["narrow_next_safe_step"] = "run doctor and clear blocking failure classes"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        invalidations.append("closure_invalidated_by_doctor")


def downgrade_for_partial_bundle(state: dict, invalidations: list[str]) -> None:
    if state["proof_bundle"]["status"] != "COMPLETE":
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "MISSING_PROOF_SECTIONS"
        state["closure"]["next_allowed_transition"] = "PROOF_BUNDLE_COMPLETION"
        state["closure"]["narrow_next_safe_step"] = "complete the missing proof sections"
        state["closure"]["missing_sections"] = list(state["proof_bundle"]["missing_sections"])
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        invalidations.append("closure_invalidated_by_partial_bundle")


def downgrade_for_recovery(state: dict, invalidations: list[str]) -> None:
    if state["recovery"]["status"] == "PENDING" and not state["recovery"]["reverification_complete"]:
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "RECOVERY_REVERIFICATION_INCOMPLETE"
        state["closure"]["next_allowed_transition"] = "RECOVERY_REVERIFICATION"
        state["closure"]["narrow_next_safe_step"] = "run reverification against the attested target surface"
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
        invalidations.append("closure_invalidated_by_recovery")


def apply_event(args: argparse.Namespace, state: dict) -> tuple[dict, dict]:
    steps_applied: list[str] = []
    invalidations: list[str] = []

    if args.doctor_status:
        state["doctor"]["status"] = args.doctor_status
        steps_applied.append("doctor_status_refreshed")

    if args.bundle_file:
        bundle = load_json(Path(args.bundle_file))
        state["execution"]["artifact_bundle_present"] = bool(bundle.get("final_result", {}).get("present", False))
        state["proof_bundle"]["status"] = bundle.get("status", "INVALID")
        state["proof_bundle"]["missing_sections"] = list(bundle.get("missing_sections", []))
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

    downgrade_for_doctor(state, invalidations)
    downgrade_for_partial_bundle(state, invalidations)
    downgrade_for_recovery(state, invalidations)

    if state["closure"]["status"] == "ACCEPTED":
        state["state"] = "CLOSURE_ACCEPTED"
        state["next_safe_step"] = "NONE"
    elif state["proof_bundle"]["status"] == "COMPLETE":
        state["state"] = "PROOF_BUNDLE_COMPLETE"

    report = {
        "schema_version": "refresh_report_v0",
        "run_id": state["run_id"],
        "event_type": args.event_type,
        "steps_applied": steps_applied,
        "invalidations": invalidations,
        "resulting_state": state["state"],
        "resulting_closure_status": state["closure"]["status"],
        "next_safe_step": state["next_safe_step"],
    }
    return state, report


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    state_path = Path(args.state_file)
    output_path = Path(args.output)
    state = load_json(state_path)
    updated_state, report = apply_event(args, state)
    save_json(output_path, report)
    if args.update_state:
        save_json(state_path, updated_state)
    print(json.dumps({"result": "OK", "resulting_closure_status": report["resulting_closure_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
