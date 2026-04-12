#!/usr/bin/env python3
"""Minimal terminal-first CLI facade for Synrail v0."""

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
VALIDATE = HERE / "synrail_validate_v0.py"
DOCTOR = HERE / "synrail_doctor_v1.py"
HARNESS = HERE / "synrail_baseline_harness_v0.py"


def run_python(script: Path, args: list[str]) -> int:
    cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, check=False).returncode


def run_python_capture(script: Path, args: list[str], *, passthrough: bool = True) -> tuple[int, str]:
    cmd = [sys.executable, str(script), *args]
    completed = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if passthrough and completed.stdout:
        print(completed.stdout, end="")
    if passthrough and completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
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


def cmd_status(args: argparse.Namespace) -> int:
    state = load_json(Path(args.state_file))
    summary = {
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "state": state["state"],
        "target_surface": state["target_surface"]["status"],
        "doctor": state["doctor"]["status"],
        "proof_bundle": state["proof_bundle"]["status"],
        "closure": state["closure"]["status"],
        "next_safe_step": state["next_safe_step"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    forwarded = [
        "init",
        "--run-id", args.run_id,
        "--task-class", args.task_class,
        "--output", args.output,
    ]
    return run_python(SPINE, forwarded)


def cmd_bundle_check(args: argparse.Namespace) -> int:
    forwarded = [
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--output", args.output,
    ]
    optional_pairs = [
        ("--run-id", args.run_id),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--baseline-identity", args.baseline_identity),
        ("--execution-surface-identity", args.execution_surface_identity),
        ("--prompt-identity", args.prompt_identity),
        ("--task-identity", args.task_identity),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    return run_python(BUNDLE, forwarded)


def cmd_apply_bundle(args: argparse.Namespace) -> int:
    return run_python(SPINE, ["apply-bundle", args.state_file, args.bundle_file])


def cmd_closure(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--bundle-file", args.bundle_file,
        "--output", args.output,
    ]
    if args.update_state:
        forwarded.append("--update-state")
    return run_python(CLOSURE, forwarded)


def cmd_apply_closure(args: argparse.Namespace) -> int:
    return run_python(SPINE, ["apply-closure", args.state_file, args.closure_file])


def cmd_refresh(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--event-type", args.event_type,
        "--output", args.output,
    ]
    optional_pairs = [
        ("--doctor-status", args.doctor_status),
        ("--bundle-file", args.bundle_file),
        ("--closure-file", args.closure_file),
        ("--recovery-status", args.recovery_status),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    if args.reverification_complete:
        forwarded.append("--reverification-complete")
    if args.update_state:
        forwarded.append("--update-state")
    return run_python(REFRESH, forwarded)


def cmd_validate(args: argparse.Namespace) -> int:
    forwarded = [
        "--schema", args.schema,
        "--document", args.document,
    ]
    return run_python(VALIDATE, forwarded)


def cmd_doctor(args: argparse.Namespace) -> int:
    forwarded = [
        "--doctor-run-id", args.doctor_run_id,
        "--doctor-level", args.doctor_level,
        "--target-path", args.target_path,
        "--target-classification", args.target_classification,
        "--baseline-identity", args.baseline_identity,
        "--intended-run-class", args.intended_run_class,
        "--output", args.output,
    ]
    if args.state_file:
        forwarded.extend(["--state-file", args.state_file])
    if args.update_state:
        forwarded.append("--update-state")
    if args.clean_surface:
        forwarded.append("--clean-surface")
    if args.artifact_viable:
        forwarded.append("--artifact-viable")
    if args.helper_ok:
        forwarded.append("--helper-ok")
    if args.credentials_ok:
        forwarded.append("--credentials-ok")
    if args.prompt_identity_ok:
        forwarded.append("--prompt-identity-ok")
    optional_pairs = [
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--prompt-identity-file", args.prompt_identity_file),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    return run_python(DOCTOR, forwarded)


def cmd_compare(args: argparse.Namespace) -> int:
    forwarded = [
        "--baseline-file", args.baseline_file,
        "--synrail-file", args.synrail_file,
        "--output", args.output,
    ]
    return run_python(HARNESS, forwarded)


def cmd_orchestrate(args: argparse.Namespace) -> int:
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
    optional_doctor_pairs = [
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--prompt-identity-file", args.prompt_identity_file),
    ]
    for flag, value in optional_doctor_pairs:
        if value:
            doctor_args.extend([flag, value])
    for env_name in args.credential_env:
        doctor_args.extend(["--credential-env", env_name])

    code, _ = run_python_capture(DOCTOR, doctor_args, passthrough=False)
    if code != 0:
        report = {
            "schema_version": "orchestration_report_v0",
            "run_id": load_json(Path(args.state_file))["run_id"],
            "task_class": load_json(Path(args.state_file))["task_class"],
            "result": "ERROR",
            "stopping_stage": "doctor",
            "reason": "DOCTOR_EXECUTION_FAILED",
            "doctor_verdict": "",
            "bundle_status": "",
            "closure_status": "",
            "refresh_applied": False,
            "refresh_resulting_closure_status": "",
            "comparison_applied": False,
            "comparison_verdict": "",
            "resulting_state": load_json(Path(args.state_file))["state"],
            "next_safe_step": load_json(Path(args.state_file))["next_safe_step"],
        }
        save_json(Path(args.report_output), report)
        return code

    code, _ = run_python_capture(SPINE, ["apply-doctor", args.state_file, args.doctor_output], passthrough=False)
    if code != 0:
        return code

    doctor_record = load_json(Path(args.doctor_output))
    state_after_doctor = load_json(Path(args.state_file))
    if state_after_doctor["doctor"]["status"] != "PASS":
        report = {
            "schema_version": "orchestration_report_v0",
            "run_id": state_after_doctor["run_id"],
            "task_class": state_after_doctor["task_class"],
            "result": "BLOCKED",
            "stopping_stage": "doctor",
            "reason": "DOCTOR_NOT_GREEN",
            "doctor_verdict": doctor_record["final_verdict"],
            "bundle_status": "",
            "closure_status": state_after_doctor["closure"]["status"],
            "refresh_applied": False,
            "refresh_resulting_closure_status": "",
            "comparison_applied": False,
            "comparison_verdict": "",
            "resulting_state": state_after_doctor["state"],
            "next_safe_step": state_after_doctor["next_safe_step"],
        }
        save_json(Path(args.report_output), report)
        print(json.dumps({"result": "BLOCKED", "stopping_stage": "doctor"}, ensure_ascii=True))
        return 0

    bundle_args = [
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--output", args.bundle_output,
        "--run-id", state_after_doctor["run_id"],
        "--baseline-identity", args.baseline_identity,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
    ]
    if args.readback:
        bundle_args.extend(["--readback", args.readback])
    if args.scenario_proof:
        bundle_args.extend(["--scenario-proof", args.scenario_proof])
    code, _ = run_python_capture(BUNDLE, bundle_args, passthrough=False)
    if code != 0:
        return code

    code, _ = run_python_capture(SPINE, ["apply-bundle", args.state_file, args.bundle_output], passthrough=False)
    if code != 0:
        return code

    code, _ = run_python_capture(CLOSURE, ["--state-file", args.state_file, "--bundle-file", args.bundle_output, "--output", args.closure_output], passthrough=False)
    if code != 0:
        return code

    code, _ = run_python_capture(SPINE, ["apply-closure", args.state_file, args.closure_output], passthrough=False)
    if code != 0:
        return code

    final_state = load_json(Path(args.state_file))
    bundle = load_json(Path(args.bundle_output))
    closure = load_json(Path(args.closure_output))
    refresh_applied = False
    refresh_resulting_closure_status = ""
    comparison_applied = False
    comparison_verdict = ""
    refresh_report = None
    comparison = None
    stopping_stage = "closure" if closure["closure_status"] != "ACCEPTED" else "accepted"
    reason = closure["blocking_reason"] or "NONE"

    if args.refresh_output and args.refresh_event_type:
        refresh_args = [
            "--state-file", args.state_file,
            "--event-type", args.refresh_event_type,
            "--output", args.refresh_output,
            "--update-state",
        ]
        optional_refresh_pairs = [
            ("--doctor-status", args.refresh_doctor_status),
            ("--bundle-file", args.bundle_output if args.refresh_use_bundle else ""),
            ("--closure-file", args.closure_output if args.refresh_use_closure else ""),
            ("--recovery-status", args.refresh_recovery_status),
        ]
        for flag, value in optional_refresh_pairs:
            if value:
                refresh_args.extend([flag, value])
        if args.refresh_reverification_complete:
            refresh_args.append("--reverification-complete")
        code, _ = run_python_capture(REFRESH, refresh_args, passthrough=False)
        if code != 0:
            return code
        final_state = load_json(Path(args.state_file))
        refresh_report = load_json(Path(args.refresh_output))
        refresh_applied = True
        refresh_resulting_closure_status = refresh_report["resulting_closure_status"]
        stopping_stage = "refresh"
        reason = final_state["closure"]["blocking_reason"] or "NONE"

    if args.comparison_output and args.baseline_file and args.synrail_file:
        code, _ = run_python_capture(
            HARNESS,
            [
                "--baseline-file", args.baseline_file,
                "--synrail-file", args.synrail_file,
                "--output", args.comparison_output,
            ],
            passthrough=False,
        )
        if code != 0:
            return code
        comparison = load_json(Path(args.comparison_output))
        comparison_applied = True
        comparison_verdict = comparison["verdict"]
        stopping_stage = "comparison"

    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": final_state["run_id"],
        "task_class": final_state["task_class"],
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
        "resulting_state": final_state["state"],
        "next_safe_step": final_state["next_safe_step"],
    }
    save_json(Path(args.report_output), report)

    if args.worked_artifact_output:
        worked = build_worked_orchestration_artifact(
            state=final_state,
            doctor_record=doctor_record,
            bundle=bundle,
            closure=closure,
            refresh_report=refresh_report,
            comparison=comparison,
        )
        save_json(Path(args.worked_artifact_output), worked)

    print(json.dumps({"result": "OK", "closure_status": closure["closure_status"]}, ensure_ascii=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--run-id", required=True)
    p_init.add_argument("--task-class", required=True)
    p_init.add_argument("--output", required=True)
    p_init.set_defaults(func=cmd_init)

    p_status = sub.add_parser("status")
    p_status.add_argument("state_file")
    p_status.set_defaults(func=cmd_status)

    p_bundle = sub.add_parser("bundle-check")
    p_bundle.add_argument("--final-result", required=True)
    p_bundle.add_argument("--task-class", required=True)
    p_bundle.add_argument("--output", required=True)
    p_bundle.add_argument("--run-id")
    p_bundle.add_argument("--readback")
    p_bundle.add_argument("--scenario-proof")
    p_bundle.add_argument("--baseline-identity")
    p_bundle.add_argument("--execution-surface-identity")
    p_bundle.add_argument("--prompt-identity")
    p_bundle.add_argument("--task-identity")
    p_bundle.set_defaults(func=cmd_bundle_check)

    p_apply_bundle = sub.add_parser("apply-bundle")
    p_apply_bundle.add_argument("state_file")
    p_apply_bundle.add_argument("bundle_file")
    p_apply_bundle.set_defaults(func=cmd_apply_bundle)

    p_closure = sub.add_parser("closure")
    p_closure.add_argument("--state-file", required=True)
    p_closure.add_argument("--bundle-file", required=True)
    p_closure.add_argument("--output", required=True)
    p_closure.add_argument("--update-state", action="store_true")
    p_closure.set_defaults(func=cmd_closure)

    p_apply_closure = sub.add_parser("apply-closure")
    p_apply_closure.add_argument("state_file")
    p_apply_closure.add_argument("closure_file")
    p_apply_closure.set_defaults(func=cmd_apply_closure)

    p_refresh = sub.add_parser("refresh")
    p_refresh.add_argument("--state-file", required=True)
    p_refresh.add_argument("--event-type", required=True)
    p_refresh.add_argument("--output", required=True)
    p_refresh.add_argument("--doctor-status", choices=["PASS", "FAIL"])
    p_refresh.add_argument("--bundle-file")
    p_refresh.add_argument("--closure-file")
    p_refresh.add_argument("--recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    p_refresh.add_argument("--reverification-complete", action="store_true")
    p_refresh.add_argument("--update-state", action="store_true")
    p_refresh.set_defaults(func=cmd_refresh)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--schema", required=True)
    p_validate.add_argument("--document", required=True)
    p_validate.set_defaults(func=cmd_validate)

    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--doctor-run-id", required=True)
    p_doctor.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_doctor.add_argument("--target-path", required=True)
    p_doctor.add_argument("--target-classification", required=True)
    p_doctor.add_argument("--baseline-identity", required=True)
    p_doctor.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    p_doctor.add_argument("--output", required=True)
    p_doctor.add_argument("--state-file")
    p_doctor.add_argument("--update-state", action="store_true")
    p_doctor.add_argument("--clean-surface", action="store_true")
    p_doctor.add_argument("--artifact-viable", action="store_true")
    p_doctor.add_argument("--helper-ok", action="store_true")
    p_doctor.add_argument("--credentials-ok", action="store_true")
    p_doctor.add_argument("--prompt-identity-ok", action="store_true")
    p_doctor.add_argument("--artifact-path")
    p_doctor.add_argument("--helper-path")
    p_doctor.add_argument("--credential-env", action="append", default=[])
    p_doctor.add_argument("--prompt-identity-file")
    p_doctor.set_defaults(func=cmd_doctor)

    p_compare = sub.add_parser("compare")
    p_compare.add_argument("--baseline-file", required=True)
    p_compare.add_argument("--synrail-file", required=True)
    p_compare.add_argument("--output", required=True)
    p_compare.set_defaults(func=cmd_compare)

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
