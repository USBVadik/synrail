#!/usr/bin/env python3
"""Minimal terminal-first CLI facade for Synrail v0."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPINE = HERE / "synrail_spine_v0.py"
BUNDLE = HERE / "synrail_bundle_v0.py"
CLOSURE = HERE / "synrail_closure_v0.py"
REFRESH = HERE / "synrail_refresh_v0.py"
VALIDATE = HERE / "synrail_validate_v0.py"
DOCTOR = HERE / "synrail_doctor_v1.py"
HARNESS_V0 = HERE / "synrail_baseline_harness_v0.py"
HARNESS_V1 = HERE / "synrail_baseline_harness_v1.py"
HYBRID_STATUS = HERE / "synrail_hybrid_status_v0.py"
MODE_SELECTOR = HERE / "synrail_mode_selector_v0.py"
MODE_RECEIPT = HERE / "synrail_mode_receipt_v0.py"
PROOF_PLAN = HERE / "synrail_proof_plan_v0.py"
PREPARATION_RECEIPT = HERE / "synrail_preparation_receipt_v0.py"
GOVERNED_COST = HERE / "synrail_governed_cost_delta_v0.py"
REPAIR_HANDOFF = HERE / "synrail_repair_handoff_v0.py"
REPAIR_PACKET = HERE / "synrail_repair_packet_v0.py"


def run_python(script: Path, args: list[str]) -> int:
    cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, check=False).returncode


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
        ("--expected-task-identity", args.expected_task_identity),
        ("--target-identity-file", args.target_identity_file),
        ("--expected-target-identity", args.expected_target_identity),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    return run_python(DOCTOR, forwarded)


def cmd_compare(args: argparse.Namespace) -> int:
    try:
        harness = comparison_harness_for_inputs(args.baseline_file, args.synrail_file)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": "COMPARISON_INPUT_SCHEMA_MISMATCH", "detail": str(exc)}, ensure_ascii=True))
        return 2
    forwarded = [
        "--baseline-file", args.baseline_file,
        "--synrail-file", args.synrail_file,
        "--output", args.output,
    ]
    return run_python(harness, forwarded)


def cmd_hybrid_status(args: argparse.Namespace) -> int:
    forwarded = [
        "--cost-record", args.cost_record,
        "--output", args.output,
    ]
    for hybrid_record in args.hybrid_record:
        forwarded.extend(["--hybrid-record", hybrid_record])
    return run_python(HYBRID_STATUS, forwarded)


def cmd_recommend_mode(args: argparse.Namespace) -> int:
    forwarded = [
        "--cost-record", args.cost_record,
        "--scenario-class", args.scenario_class,
        "--task-class", args.task_class,
        "--false-success-risk", args.false_success_risk,
        "--recovery-cost", args.recovery_cost,
        "--output", args.output,
    ]
    if args.hybrid_status:
        forwarded.extend(["--hybrid-status", args.hybrid_status])
    if args.governed_cost_delta:
        forwarded.extend(["--governed-cost-delta", args.governed_cost_delta])
    if args.execution_surface_ambiguous:
        forwarded.append("--execution-surface-ambiguous")
    if args.artifact_truth_nontrivial:
        forwarded.append("--artifact-truth-nontrivial")
    if args.explicit_hybrid_ambiguity:
        forwarded.extend(["--explicit-hybrid-ambiguity", args.explicit_hybrid_ambiguity])
    return run_python(MODE_SELECTOR, forwarded)


def cmd_select_mode(args: argparse.Namespace) -> int:
    forwarded = [
        "--recommendation-file", args.recommendation_file,
        "--output", args.output,
    ]
    if args.selected_mode:
        forwarded.extend(["--selected-mode", args.selected_mode])
    if args.selected_with_preparation:
        forwarded.append("--selected-with-preparation")
    return run_python(MODE_RECEIPT, forwarded)


def cmd_plan_proof(args: argparse.Namespace) -> int:
    forwarded = [
        "--run-id", args.run_id,
        "--task-class", args.task_class,
        "--artifact-root", args.artifact_root,
        "--baseline-identity", args.baseline_identity,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
        "--output", args.output,
    ]
    return run_python(PROOF_PLAN, forwarded)


def cmd_preparation_receipt(args: argparse.Namespace) -> int:
    forwarded = [
        "--plan-file", args.plan_file,
        "--bundle-file", args.bundle_file,
        "--output", args.output,
    ]
    return run_python(PREPARATION_RECEIPT, forwarded)


def cmd_governed_cost(args: argparse.Namespace) -> int:
    forwarded = [
        "--unprepared-file", args.unprepared_file,
        "--prepared-file", args.prepared_file,
        "--output", args.output,
    ]
    return run_python(GOVERNED_COST, forwarded)


def cmd_repair_handoff(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    return run_python(REPAIR_HANDOFF, forwarded)


def cmd_repair_packet(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--artifact-root", args.artifact_root,
        "--output", args.output,
        "--doctor-run-id", args.doctor_run_id,
        "--doctor-level", args.doctor_level,
        "--target-path", args.target_path,
        "--target-classification", args.target_classification,
        "--baseline-identity", args.baseline_identity,
        "--intended-run-class", args.intended_run_class,
        "--execution-surface-identity", args.execution_surface_identity,
        "--final-result", args.final_result,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
    ]
    for flag, value in [
        ("--repair-handoff-file", args.repair_handoff_file),
        ("--mode-selection-receipt", args.mode_selection_receipt),
        ("--preparation-receipt-file", args.preparation_receipt_file),
        ("--report-file", args.report_file),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--target-identity-file", args.target_identity_file),
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--refresh-output", args.refresh_output),
        ("--refresh-event-type", args.refresh_event_type),
        ("--refresh-recovery-status", args.refresh_recovery_status),
    ]:
        if value:
            forwarded.extend([flag, value])
    for enabled, flag in [
        (args.prompt_identity_ok, "--prompt-identity-ok"),
        (args.clean_surface, "--clean-surface"),
        (args.artifact_viable, "--artifact-viable"),
        (args.helper_ok, "--helper-ok"),
        (args.credentials_ok, "--credentials-ok"),
        (args.refresh_reverification_complete, "--refresh-reverification-complete"),
        (args.refresh_use_bundle, "--refresh-use-bundle"),
        (args.refresh_use_closure, "--refresh-use-closure"),
    ]:
        if enabled:
            forwarded.append(flag)
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    return run_python(REPAIR_PACKET, forwarded)


def load_repair_packet(path: Path) -> dict:
    packet = load_json(path)
    if packet.get("schema_version") != "repair_packet_v0":
        raise ValueError("repair packet must use repair_packet_v0")
    return packet


def discover_repair_packet_file(args: argparse.Namespace) -> Path | None:
    if getattr(args, "repair_packet_file", None):
        return Path(args.repair_packet_file)
    state_path = Path(args.state_file)
    candidates = [
        state_path.with_name("repair_packet.json"),
    ]
    if getattr(args, "report_output", None):
        candidates.append(Path(args.report_output).with_name("repair_packet.json"))
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def maybe_apply_repair_packet(args: argparse.Namespace, state: dict) -> list[str]:
    packet_path = discover_repair_packet_file(args)
    if not packet_path:
        return []

    args.repair_packet_file = str(packet_path)
    packet = load_repair_packet(packet_path)
    if packet["run_id"] != state["run_id"] or packet["from_state"] != state["state"]:
        raise ValueError("repair packet does not match the requested state")
    if packet.get("resumability", {}).get("status", "REPAIRABLE") != "REPAIRABLE":
        raise ValueError("repair packet does not describe a resumable continuation state")

    context = packet["resume_context"]
    continuation_plan = packet.get("continuation_plan", {})
    repair_inputs = packet["repair_inputs"]
    output_defaults = packet["output_defaults"]
    temp_files: list[str] = []

    for attr, value in [
        ("doctor_run_id", context["doctor_run_id"]),
        ("doctor_level", context["doctor_level"]),
        ("target_path", context["target_path"]),
        ("target_classification", context["target_classification"]),
        ("baseline_identity", context["baseline_identity"]),
        ("intended_run_class", context["intended_run_class"]),
        ("execution_surface_identity", context["execution_surface_identity"]),
        ("task_class", packet["task_class"]),
        ("final_result", repair_inputs["final_result"]),
        ("prompt_identity", repair_inputs["prompt_identity"]),
        ("task_identity", repair_inputs["task_identity"]),
        ("readback", repair_inputs["readback"]),
        ("scenario_proof", repair_inputs["scenario_proof"]),
        ("artifact_path", repair_inputs["artifact_path"]),
        ("helper_path", repair_inputs["helper_path"]),
        ("prompt_identity_file", ""),
        ("target_identity_file", repair_inputs["target_identity_file"]),
        ("doctor_output", output_defaults["doctor_output"]),
        ("bundle_output", output_defaults["bundle_output"]),
        ("closure_output", output_defaults["closure_output"]),
        ("refresh_output", output_defaults["refresh_output"]),
        ("report_output", output_defaults["report_output"]),
        ("worked_artifact_output", output_defaults["worked_artifact_output"]),
        ("run_artifact_output", output_defaults["run_artifact_output"]),
        ("repair_handoff_output", output_defaults["repair_handoff_output"]),
        ("repair_packet_output", output_defaults["repair_packet_output"]),
        ("plan_output", output_defaults["plan_output"]),
        ("preparation_receipt_output", output_defaults["preparation_receipt_output"]),
    ]:
        current = getattr(args, attr, None)
        if current in {None, ""} and value is not None:
            setattr(args, attr, value)

    if not getattr(args, "preparation_artifact_root", None):
        args.preparation_artifact_root = output_defaults["artifact_root"]

    if not getattr(args, "refresh_recovery_status", None):
        args.refresh_recovery_status = repair_inputs["refresh_recovery_status"]
    if not getattr(args, "refresh_event_type", None) and continuation_plan.get("refresh_event_type"):
        args.refresh_event_type = continuation_plan["refresh_event_type"]
    if repair_inputs["refresh_reverification_complete"]:
        args.refresh_reverification_complete = True
    if continuation_plan.get("refresh_use_bundle"):
        args.refresh_use_bundle = True
    if continuation_plan.get("refresh_use_closure"):
        args.refresh_use_closure = True
    if repair_inputs["clean_surface"]:
        args.clean_surface = True
    if repair_inputs["artifact_viable"]:
        args.artifact_viable = True
    if repair_inputs["helper_ok"]:
        args.helper_ok = True
    if repair_inputs["credentials_ok"]:
        args.credentials_ok = True
    if repair_inputs["prompt_identity_ok"]:
        args.prompt_identity_ok = True
    if not args.credential_env:
        args.credential_env = list(repair_inputs["credential_env"])

    selection_receipt = packet.get("selection_receipt")
    if selection_receipt and not getattr(args, "mode_selection_receipt", None):
        temp_selection = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(selection_receipt, temp_selection, indent=2, ensure_ascii=True)
        temp_selection.write("\n")
        temp_selection.close()
        args.mode_selection_receipt = temp_selection.name
        temp_files.append(temp_selection.name)

    temp_handoff = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
    json.dump(packet["repair_handoff"], temp_handoff, indent=2, ensure_ascii=True)
    temp_handoff.write("\n")
    temp_handoff.close()
    args.repair_handoff_file = temp_handoff.name
    temp_files.append(temp_handoff.name)
    return temp_files


def cmd_orchestrate(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--doctor-run-id", args.doctor_run_id,
        "--doctor-level", args.doctor_level,
        "--target-path", args.target_path,
        "--target-classification", args.target_classification,
        "--baseline-identity", args.baseline_identity,
        "--intended-run-class", args.intended_run_class,
        "--doctor-output", args.doctor_output,
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--bundle-output", args.bundle_output,
        "--closure-output", args.closure_output,
        "--report-output", args.report_output,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
    ]
    if getattr(args, "resume_from_state", None):
        forwarded.extend(["--resume-from-state", args.resume_from_state])
    if args.repair_handoff_file:
        forwarded.extend(["--repair-handoff-file", args.repair_handoff_file])
    if args.mode_selection_receipt:
        forwarded.extend(["--mode-selection-receipt", args.mode_selection_receipt])
    for flag, value in [
        ("--repair-handoff-output", args.repair_handoff_output),
        ("--repair-packet-output", args.repair_packet_output),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--plan-output", args.plan_output),
        ("--preparation-receipt-output", args.preparation_receipt_output),
        ("--preparation-artifact-root", args.preparation_artifact_root),
        ("--refresh-output", args.refresh_output),
        ("--refresh-event-type", args.refresh_event_type),
        ("--refresh-doctor-status", args.refresh_doctor_status),
        ("--refresh-recovery-status", args.refresh_recovery_status),
        ("--baseline-file", args.baseline_file),
        ("--synrail-file", args.synrail_file),
        ("--comparison-output", args.comparison_output),
        ("--worked-artifact-output", args.worked_artifact_output),
        ("--run-artifact-output", args.run_artifact_output),
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--prompt-identity-file", args.prompt_identity_file),
        ("--target-identity-file", args.target_identity_file),
        ("--expected-target-identity", args.execution_surface_identity),
    ]:
        if value:
            forwarded.extend([flag, value])
    for enabled, flag in [
        (args.refresh_reverification_complete, "--refresh-reverification-complete"),
        (args.refresh_use_bundle, "--refresh-use-bundle"),
        (args.refresh_use_closure, "--refresh-use-closure"),
        (args.clean_surface, "--clean-surface"),
        (args.artifact_viable, "--artifact-viable"),
        (args.helper_ok, "--helper-ok"),
        (args.credentials_ok, "--credentials-ok"),
        (args.prompt_identity_ok, "--prompt-identity-ok"),
    ]:
        if enabled:
            forwarded.append(flag)
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    return run_python(SPINE, ["orchestrate", *forwarded])


def cmd_resume(args: argparse.Namespace) -> int:
    state = load_json(Path(args.state_file))
    args.resume_from_state = state["state"]
    temp_runtime_files: list[str] = []
    try:
        temp_runtime_files = maybe_apply_repair_packet(args, state)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": "INVALID_REPAIR_PACKET", "detail": str(exc)}, ensure_ascii=True))
        return 2

    for attr in [
        "doctor_run_id",
        "doctor_level",
        "target_path",
        "target_classification",
        "baseline_identity",
        "intended_run_class",
        "doctor_output",
        "task_class",
        "bundle_output",
        "closure_output",
        "report_output",
        "execution_surface_identity",
    ]:
        if not getattr(args, attr, None):
            print(json.dumps({"result": "ERROR", "reason": "RESUME_CONTEXT_INCOMPLETE", "missing_field": attr}, ensure_ascii=True))
            return 2

    if getattr(args, "prompt_identity", None) is None:
        args.prompt_identity = ""
    if getattr(args, "task_identity", None) is None:
        args.task_identity = ""
    if getattr(args, "final_result", None) is None:
        args.final_result = ""

    try:
        return cmd_orchestrate(args)
    finally:
        for temp_path in temp_runtime_files:
            Path(temp_path).unlink(missing_ok=True)


def add_orchestration_args(
    parser: argparse.ArgumentParser,
    *,
    include_resume_from_state: bool,
    relaxed_runtime: bool = False,
) -> None:
    parser.add_argument("--state-file", required=True)
    if include_resume_from_state:
        parser.add_argument("--resume-from-state")
    parser.add_argument("--repair-handoff-file")
    parser.add_argument("--repair-handoff-output")
    parser.add_argument("--repair-packet-file")
    parser.add_argument("--repair-packet-output")
    parser.add_argument("--mode-selection-receipt")
    parser.add_argument("--doctor-run-id", required=not relaxed_runtime)
    parser.add_argument("--doctor-level", required=not relaxed_runtime, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    parser.add_argument("--target-path", required=not relaxed_runtime)
    parser.add_argument("--target-classification", required=not relaxed_runtime)
    parser.add_argument("--baseline-identity", required=not relaxed_runtime)
    parser.add_argument("--intended-run-class", required=not relaxed_runtime, choices=["core_probe", "support_run", "exact_retry"])
    parser.add_argument("--doctor-output", required=not relaxed_runtime)
    parser.add_argument("--final-result", required=not relaxed_runtime)
    parser.add_argument("--task-class", required=not relaxed_runtime)
    parser.add_argument("--bundle-output", required=not relaxed_runtime)
    parser.add_argument("--closure-output", required=not relaxed_runtime)
    parser.add_argument("--report-output", required=not relaxed_runtime)
    parser.add_argument("--execution-surface-identity", required=not relaxed_runtime)
    parser.add_argument("--prompt-identity", required=not relaxed_runtime, default="")
    parser.add_argument("--task-identity", required=not relaxed_runtime, default="")
    parser.add_argument("--readback")
    parser.add_argument("--scenario-proof")
    parser.add_argument("--plan-output")
    parser.add_argument("--preparation-receipt-output")
    parser.add_argument("--preparation-artifact-root")
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
    parser.add_argument("--run-artifact-output")
    parser.add_argument("--clean-surface", action="store_true")
    parser.add_argument("--artifact-viable", action="store_true")
    parser.add_argument("--helper-ok", action="store_true")
    parser.add_argument("--credentials-ok", action="store_true")
    parser.add_argument("--prompt-identity-ok", action="store_true")
    parser.add_argument("--artifact-path")
    parser.add_argument("--helper-path")
    parser.add_argument("--credential-env", action="append", default=[])
    parser.add_argument("--prompt-identity-file")
    parser.add_argument("--target-identity-file")


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
    p_doctor.add_argument("--expected-task-identity")
    p_doctor.add_argument("--target-identity-file")
    p_doctor.add_argument("--expected-target-identity")
    p_doctor.set_defaults(func=cmd_doctor)

    p_compare = sub.add_parser("compare")
    p_compare.add_argument("--baseline-file", required=True)
    p_compare.add_argument("--synrail-file", required=True)
    p_compare.add_argument("--output", required=True)
    p_compare.set_defaults(func=cmd_compare)

    p_hybrid = sub.add_parser("hybrid-status")
    p_hybrid.add_argument("--cost-record", required=True)
    p_hybrid.add_argument("--hybrid-record", action="append", required=True)
    p_hybrid.add_argument("--output", required=True)
    p_hybrid.set_defaults(func=cmd_hybrid_status)

    p_mode = sub.add_parser("recommend-mode")
    p_mode.add_argument("--cost-record", required=True)
    p_mode.add_argument("--hybrid-status")
    p_mode.add_argument("--scenario-class", required=True)
    p_mode.add_argument("--task-class", required=True)
    p_mode.add_argument("--false-success-risk", required=True, choices=["LOW", "MEDIUM", "HIGH"])
    p_mode.add_argument("--recovery-cost", required=True, choices=["LOW", "MEDIUM", "HIGH"])
    p_mode.add_argument("--execution-surface-ambiguous", action="store_true")
    p_mode.add_argument("--artifact-truth-nontrivial", action="store_true")
    p_mode.add_argument("--explicit-hybrid-ambiguity")
    p_mode.add_argument("--governed-cost-delta")
    p_mode.add_argument("--output", required=True)
    p_mode.set_defaults(func=cmd_recommend_mode)

    p_select = sub.add_parser("select-mode")
    p_select.add_argument("--recommendation-file", required=True)
    p_select.add_argument("--selected-mode", choices=["FULL_GOVERNED_PATH", "LIGHTWEIGHT_BASELINE", "HYBRID_EXCEPTION"])
    p_select.add_argument("--selected-with-preparation", action="store_true")
    p_select.add_argument("--output", required=True)
    p_select.set_defaults(func=cmd_select_mode)

    p_plan = sub.add_parser("plan-proof")
    p_plan.add_argument("--run-id", required=True)
    p_plan.add_argument("--task-class", required=True)
    p_plan.add_argument("--artifact-root", required=True)
    p_plan.add_argument("--baseline-identity", required=True)
    p_plan.add_argument("--execution-surface-identity", required=True)
    p_plan.add_argument("--prompt-identity", required=True)
    p_plan.add_argument("--task-identity", required=True)
    p_plan.add_argument("--output", required=True)
    p_plan.set_defaults(func=cmd_plan_proof)

    p_prep = sub.add_parser("preparation-receipt")
    p_prep.add_argument("--plan-file", required=True)
    p_prep.add_argument("--bundle-file", required=True)
    p_prep.add_argument("--output", required=True)
    p_prep.set_defaults(func=cmd_preparation_receipt)

    p_governed_cost = sub.add_parser("governed-cost")
    p_governed_cost.add_argument("--unprepared-file", required=True)
    p_governed_cost.add_argument("--prepared-file", required=True)
    p_governed_cost.add_argument("--output", required=True)
    p_governed_cost.set_defaults(func=cmd_governed_cost)

    p_repair_handoff = sub.add_parser("repair-handoff")
    p_repair_handoff.add_argument("--state-file", required=True)
    p_repair_handoff.add_argument("--output", required=True)
    p_repair_handoff.set_defaults(func=cmd_repair_handoff)

    p_repair_packet = sub.add_parser("repair-packet")
    p_repair_packet.add_argument("--state-file", required=True)
    p_repair_packet.add_argument("--artifact-root", required=True)
    p_repair_packet.add_argument("--output", required=True)
    p_repair_packet.add_argument("--repair-handoff-file")
    p_repair_packet.add_argument("--mode-selection-receipt")
    p_repair_packet.add_argument("--preparation-receipt-file")
    p_repair_packet.add_argument("--report-file")
    p_repair_packet.add_argument("--doctor-run-id", required=True)
    p_repair_packet.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_repair_packet.add_argument("--target-path", required=True)
    p_repair_packet.add_argument("--target-classification", required=True)
    p_repair_packet.add_argument("--baseline-identity", required=True)
    p_repair_packet.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    p_repair_packet.add_argument("--execution-surface-identity", required=True)
    p_repair_packet.add_argument("--final-result", default="")
    p_repair_packet.add_argument("--prompt-identity", default="")
    p_repair_packet.add_argument("--task-identity", default="")
    p_repair_packet.add_argument("--prompt-identity-ok", action="store_true")
    p_repair_packet.add_argument("--readback")
    p_repair_packet.add_argument("--scenario-proof")
    p_repair_packet.add_argument("--target-identity-file")
    p_repair_packet.add_argument("--clean-surface", action="store_true")
    p_repair_packet.add_argument("--artifact-viable", action="store_true")
    p_repair_packet.add_argument("--helper-ok", action="store_true")
    p_repair_packet.add_argument("--credentials-ok", action="store_true")
    p_repair_packet.add_argument("--artifact-path")
    p_repair_packet.add_argument("--helper-path")
    p_repair_packet.add_argument("--credential-env", action="append", default=[])
    p_repair_packet.add_argument("--refresh-output")
    p_repair_packet.add_argument("--refresh-event-type")
    p_repair_packet.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"], default="NOT_REQUIRED")
    p_repair_packet.add_argument("--refresh-reverification-complete", action="store_true")
    p_repair_packet.add_argument("--refresh-use-bundle", action="store_true")
    p_repair_packet.add_argument("--refresh-use-closure", action="store_true")
    p_repair_packet.set_defaults(func=cmd_repair_packet)

    p_orchestrate = sub.add_parser("orchestrate")
    add_orchestration_args(p_orchestrate, include_resume_from_state=True)
    p_orchestrate.set_defaults(func=cmd_orchestrate)

    p_resume = sub.add_parser("resume")
    add_orchestration_args(p_resume, include_resume_from_state=False, relaxed_runtime=True)
    p_resume.set_defaults(func=cmd_resume)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
