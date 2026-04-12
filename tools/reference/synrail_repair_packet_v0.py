#!/usr/bin/env python3
"""Machine-readable repair packet builder for Synrail continuation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from synrail_repair_handoff_v0 import build_repair_handoff, load_json as load_state_json


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


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


def build_packet(args: argparse.Namespace) -> dict:
    state = load_state_json(Path(args.state_file))
    if args.repair_handoff_file:
        handoff = load_json(Path(args.repair_handoff_file))
    else:
        handoff = build_repair_handoff(state)

    prompt_identity_ok = args.prompt_identity_ok or bool(args.prompt_identity.strip() and args.task_identity.strip())

    provided_ids = provided_input_ids(args)
    missing_ids = missing_input_ids(handoff, provided_ids)

    output_defaults = default_output_paths(Path(args.artifact_root))
    if args.refresh_output:
        output_defaults["refresh_output"] = args.refresh_output
    continuation_plan = build_continuation_plan(args, handoff)

    return {
        "schema_version": "repair_packet_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "from_state": state["state"],
        "continuation_entrypoint": "resume",
        "repair_handoff": handoff,
        "continuation_plan": continuation_plan,
        "resume_context": {
            "doctor_run_id": args.doctor_run_id,
            "doctor_level": args.doctor_level,
            "target_path": args.target_path,
            "target_classification": args.target_classification,
            "baseline_identity": args.baseline_identity,
            "intended_run_class": args.intended_run_class,
            "execution_surface_identity": args.execution_surface_identity,
        },
        "repair_inputs": {
            "prompt_identity": args.prompt_identity,
            "task_identity": args.task_identity,
            "prompt_identity_ok": prompt_identity_ok,
            "target_identity_file": args.target_identity_file or "",
            "clean_surface": args.clean_surface,
            "artifact_viable": args.artifact_viable,
            "helper_ok": args.helper_ok,
            "credentials_ok": args.credentials_ok,
            "artifact_path": args.artifact_path or "",
            "helper_path": args.helper_path or "",
            "credential_env": list(args.credential_env),
            "final_result": args.final_result,
            "readback": args.readback or "",
            "scenario_proof": args.scenario_proof or "",
            "refresh_recovery_status": args.refresh_recovery_status,
            "refresh_reverification_complete": args.refresh_reverification_complete,
        },
        "output_defaults": output_defaults,
        "provided_inputs": provided_ids,
        "missing_inputs": missing_ids,
        "ready_for_resume": handoff.get("continuation_allowed", False) and not missing_ids,
        "next_safe_step": handoff["next_safe_step"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-repair-packet-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repair-handoff-file")
    parser.add_argument("--doctor-run-id", required=True)
    parser.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    parser.add_argument("--target-path", required=True)
    parser.add_argument("--target-classification", required=True)
    parser.add_argument("--baseline-identity", required=True)
    parser.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    parser.add_argument("--execution-surface-identity", required=True)
    parser.add_argument("--final-result", default="")
    parser.add_argument("--prompt-identity", default="")
    parser.add_argument("--task-identity", default="")
    parser.add_argument("--prompt-identity-ok", action="store_true")
    parser.add_argument("--readback")
    parser.add_argument("--scenario-proof")
    parser.add_argument("--target-identity-file")
    parser.add_argument("--clean-surface", action="store_true")
    parser.add_argument("--artifact-viable", action="store_true")
    parser.add_argument("--helper-ok", action="store_true")
    parser.add_argument("--credentials-ok", action="store_true")
    parser.add_argument("--artifact-path")
    parser.add_argument("--helper-path")
    parser.add_argument("--credential-env", action="append", default=[])
    parser.add_argument("--refresh-output")
    parser.add_argument("--refresh-event-type")
    parser.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"], default="NOT_REQUIRED")
    parser.add_argument("--refresh-reverification-complete", action="store_true")
    parser.add_argument("--refresh-use-bundle", action="store_true")
    parser.add_argument("--refresh-use-closure", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    packet = build_packet(args)
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
