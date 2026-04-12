#!/usr/bin/env python3
"""Bounded runtime contour for Synrail v0."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPINE = HERE / "synrail_spine_v0.py"
BUNDLE = HERE / "synrail_bundle_v0.py"
CLOSURE = HERE / "synrail_closure_v0.py"
REFRESH = HERE / "synrail_refresh_v0.py"
DOCTOR = HERE / "synrail_doctor_v1.py"
HARNESS = HERE / "synrail_baseline_harness_v0.py"


def run_python_capture(script: Path, args: list[str]) -> tuple[int, str]:
    cmd = [sys.executable, str(script), *args]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    return completed.returncode, completed.stdout


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_worked_orchestration_artifact(
    *,
    state: dict,
    doctor_record: dict,
    bundle: dict,
    closure: dict,
    refresh_report: dict | None,
    comparison: dict | None,
) -> dict:
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


def build_error_report(state: dict, *, reason: str) -> dict:
    return {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "ERROR",
        "stopping_stage": "doctor",
        "reason": reason,
        "doctor_verdict": "",
        "bundle_status": "",
        "closure_status": "",
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
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
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-runtime-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--doctor-run-id", required=True)
    parser.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    parser.add_argument("--target-path", required=True)
    parser.add_argument("--target-classification", required=True)
    parser.add_argument("--baseline-identity", required=True)
    parser.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    parser.add_argument("--doctor-output", required=True)
    parser.add_argument("--final-result", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--bundle-output", required=True)
    parser.add_argument("--closure-output", required=True)
    parser.add_argument("--report-output", required=True)
    parser.add_argument("--execution-surface-identity", required=True)
    parser.add_argument("--prompt-identity", required=True)
    parser.add_argument("--task-identity", required=True)
    parser.add_argument("--readback")
    parser.add_argument("--scenario-proof")
    parser.add_argument("--refresh-output")
    parser.add_argument("--refresh-event-type")
    parser.add_argument("--refresh-doctor-status", choices=["PASS", "FAIL"])
    parser.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    parser.add_argument("--refresh-reverification-complete", action="store_true")
    parser.add_argument("--refresh-use-bundle", action="store_true")
    parser.add_argument("--refresh-use-closure", action="store_true")
    parser.add_argument("--baseline-file")
    parser.add_argument("--synrail-file")
    parser.add_argument("--comparison-output")
    parser.add_argument("--worked-artifact-output")
    parser.add_argument("--clean-surface", action="store_true")
    parser.add_argument("--artifact-viable", action="store_true")
    parser.add_argument("--helper-ok", action="store_true")
    parser.add_argument("--credentials-ok", action="store_true")
    parser.add_argument("--prompt-identity-ok", action="store_true")
    parser.add_argument("--artifact-path")
    parser.add_argument("--helper-path")
    parser.add_argument("--credential-env", action="append", default=[])
    parser.add_argument("--prompt-identity-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    state_path = Path(args.state_file)
    state = load_json(state_path)

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

    code, _ = run_python_capture(SPINE, ["apply-doctor", args.state_file, args.doctor_output])
    if code != 0:
        return code

    doctor_record = load_json(Path(args.doctor_output))
    state = load_json(state_path)
    if state["doctor"]["status"] != "PASS":
        save_json(Path(args.report_output), build_blocked_report(state, doctor_record))
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "doctor"}, ensure_ascii=True))
        return 0

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

    code, _ = run_python_capture(SPINE, ["apply-bundle", args.state_file, args.bundle_output])
    if code != 0:
        return code

    code, _ = run_python_capture(CLOSURE, ["--state-file", args.state_file, "--bundle-file", args.bundle_output, "--output", args.closure_output])
    if code != 0:
        return code

    code, _ = run_python_capture(SPINE, ["apply-closure", args.state_file, args.closure_output])
    if code != 0:
        return code

    state = load_json(state_path)
    bundle = load_json(Path(args.bundle_output))
    closure = load_json(Path(args.closure_output))
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
        state = load_json(state_path)
        refresh_report = load_json(Path(args.refresh_output))
        refresh_applied = True
        refresh_resulting_closure_status = refresh_report["resulting_closure_status"]
        stopping_stage = "refresh"
        reason = state["closure"]["blocking_reason"] or "NONE"

    if args.comparison_output and args.baseline_file and args.synrail_file:
        code, _ = run_python_capture(HARNESS, ["--baseline-file", args.baseline_file, "--synrail-file", args.synrail_file, "--output", args.comparison_output])
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
        "closure_status": closure["closure_status"],
        "refresh_applied": refresh_applied,
        "refresh_resulting_closure_status": refresh_resulting_closure_status,
        "comparison_applied": comparison_applied,
        "comparison_verdict": comparison_verdict,
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }
    save_json(Path(args.report_output), report)

    if args.worked_artifact_output:
        worked = build_worked_orchestration_artifact(
            state=state,
            doctor_record=doctor_record,
            bundle=bundle,
            closure=closure,
            refresh_report=refresh_report,
            comparison=comparison,
        )
        save_json(Path(args.worked_artifact_output), worked)

    print(json.dumps({"result": "OK", "closure_status": closure["closure_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
