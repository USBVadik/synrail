#!/usr/bin/env python3
"""Minimal executable doctor for Synrail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json


VERDICTS = {
    "baseline_identity": "NOT_ACCEPTABLE_BASELINE_IDENTITY",
    "clean_execution_surface": "NOT_ACCEPTABLE_DIRTY_SURFACE",
    "helper_integrity": "NOT_ACCEPTABLE_HELPER_INTEGRITY",
    "credential_surface": "NOT_ACCEPTABLE_CREDENTIAL_SURFACE",
    "artifact_viability": "NOT_ACCEPTABLE_ARTIFACT_PATH",
    "prompt_task_identity": "NOT_ACCEPTABLE_EXACT_PROMPT_MISSING",
}

PASS_VERDICT = {
    "CORE_DOCTOR": "ACCEPTABLE_FOR_CORE_RUN",
    "SUPPORT_DOCTOR": "ACCEPTABLE_FOR_SUPPORT_RUN",
    "EXACT_RETRY_DOCTOR": "ACCEPTABLE_FOR_EXACT_RETRY",
}

FAILURE_CLASSES = {
    "baseline_identity": "baseline-identity ambiguous",
    "clean_execution_surface": "dirty-surface unsafe",
    "helper_integrity": "helper-integrity unknown",
    "credential_surface": "credential-surface missing",
    "artifact_viability": "artifact-viability missing",
    "prompt_task_identity": "exact-prompt-artifact-missing",
}






def gate(status: str, note: str) -> dict:
    return {"status": status, "note": note}


def build_record(args: argparse.Namespace) -> dict:
    gates = {
        "baseline_identity": gate("PASS" if args.baseline_identity else "FAIL", "trusted baseline identity is present" if args.baseline_identity else "trusted baseline identity is missing"),
        "clean_execution_surface": gate("PASS" if args.clean_surface else "FAIL", "execution surface is acceptable" if args.clean_surface else "execution surface is unsafe for this run"),
        "artifact_viability": gate("PASS" if args.artifact_viable else "FAIL", "machine-readable artifact path is viable" if args.artifact_viable else "artifact path is not viable"),
        "helper_integrity": gate("NOT_APPLICABLE", "helper integrity not required for this level"),
        "credential_surface": gate("NOT_APPLICABLE", "credential surface not required for this level"),
        "prompt_task_identity": gate("NOT_APPLICABLE", "prompt/task identity not required for this level"),
    }

    if args.doctor_level in {"SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"}:
        gates["helper_integrity"] = gate("PASS" if args.helper_ok else "FAIL", "helper surface is trusted or safely bypassed" if args.helper_ok else "helper surface is not trusted")
        gates["credential_surface"] = gate("PASS" if args.credentials_ok else "FAIL", "credential surface is present" if args.credentials_ok else "credential surface is missing")

    if args.doctor_level == "EXACT_RETRY_DOCTOR":
        gates["prompt_task_identity"] = gate("PASS" if args.prompt_identity_ok else "FAIL", "exact prompt and task identity are present" if args.prompt_identity_ok else "exact prompt or task identity is missing")

    blocking_failure_classes = []
    final_verdict = PASS_VERDICT[args.doctor_level]
    next_safe_step = "run execution"

    for key, result in gates.items():
        if result["status"] == "FAIL":
            blocking_failure_classes.append(FAILURE_CLASSES[key])
            final_verdict = VERDICTS[key]
            next_safe_step = {
                "baseline_identity": "name the trusted baseline identity",
                "clean_execution_surface": "move to a clean or explicitly observed-safe execution surface",
                "helper_integrity": "trust or safely bypass the helper entrypoint",
                "credential_surface": "restore required provider credentials",
                "artifact_viability": "restore a reliable machine-readable artifact path",
                "prompt_task_identity": "restore the exact prompt and task identity artifacts",
            }[key]
            break

    return {
        "schema_version": "doctor_record_v0",
        "doctor_run_id": args.doctor_run_id,
        "doctor_level": args.doctor_level,
        "target_execution_surface": {
            "path": args.target_path,
            "classification": args.target_classification,
        },
        "trusted_baseline": {
            "identity": args.baseline_identity,
        },
        "intended_run_class": args.intended_run_class,
        "gate_results": gates,
        "blocking_failure_classes": blocking_failure_classes,
        "final_verdict": final_verdict,
        "recommended_next_safe_step": next_safe_step,
    }


def apply_record_to_state(state: dict, record: dict) -> dict:
    acceptable = record["final_verdict"].startswith("ACCEPTABLE_")
    state["doctor"]["status"] = "PASS" if acceptable else "FAIL"
    state["doctor"]["blocking_failure_classes"] = list(record["blocking_failure_classes"])
    if not acceptable:
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "DOCTOR_NOT_GREEN"
        state["closure"]["next_allowed_transition"] = "DOCTOR_READINESS"
        state["closure"]["narrow_next_safe_step"] = record["recommended_next_safe_step"]
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = record["recommended_next_safe_step"]
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-doctor-v0")
    parser.add_argument("--doctor-run-id", required=True)
    parser.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    parser.add_argument("--target-path", required=True)
    parser.add_argument("--target-classification", required=True)
    parser.add_argument("--baseline-identity", required=True)
    parser.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--state-file")
    parser.add_argument("--update-state", action="store_true")
    parser.add_argument("--clean-surface", action="store_true")
    parser.add_argument("--artifact-viable", action="store_true")
    parser.add_argument("--helper-ok", action="store_true")
    parser.add_argument("--credentials-ok", action="store_true")
    parser.add_argument("--prompt-identity-ok", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(args)
    save_json(Path(args.output), record)

    if args.update_state:
      if not args.state_file:
        print(json.dumps({"result": "ERROR", "reason": "STATE_FILE_REQUIRED_FOR_UPDATE"}, ensure_ascii=True))
        return 2
      state_path = Path(args.state_file)
      state = load_json(state_path)
      save_json(state_path, apply_record_to_state(state, record))

    print(json.dumps({"result": "OK", "final_verdict": record["final_verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
