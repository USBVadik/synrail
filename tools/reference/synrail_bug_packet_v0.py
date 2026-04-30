#!/usr/bin/env python3
"""Compact bug-packet builder for Synrail alpha/runtime debugging."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json_safe
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_io_v0 import load_json, save_json_safe
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


BUG_PACKET_PATH_SCOPES = {
    "state_file": ARTIFACT_SCOPE,
    "report_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
    "doctor_file": ARTIFACT_SCOPE,
    "acceptance_validation_file": ARTIFACT_SCOPE,
    "repair_packet_file": ARTIFACT_SCOPE,
    "observability_file": ARTIFACT_SCOPE,
    "thin_output_file": ARTIFACT_SCOPE,
    "issue_output": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_bug_packet_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=BUG_PACKET_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def load_json_if_exists(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    return load_json(path)


def save_json(path: Path, payload: dict) -> None:
    save_json_safe(path, payload)


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def continuation_summary(repair_packet: dict | None, observability: dict | None) -> dict:
    packet = repair_packet or {}
    export = (observability or {}).get("sanitized_session_export", {})
    core = packet.get("continuation_core", {})
    source_of_truth = packet.get("source_of_truth", {})
    return {
        "entry_artifacts": list(
            export.get("entry_artifacts", [])
            or core.get("authoritative_entry_artifacts", [])
            or source_of_truth.get("authoritative_entry_artifacts", [])
        ),
        "source_of_truth_precedence": list(
            export.get("source_of_truth_precedence", [])
            or core.get("source_of_truth_precedence", [])
            or source_of_truth.get("precedence_order", [])
        ),
        "packet_replay_ready": bool(
            export.get("packet_replay_ready", False)
            or core.get("packet_replay_ready", False)
            or source_of_truth.get("packet_replay_ready", False)
        ),
        "current_step_id": core.get("current_step_id", packet.get("repair_policy", {}).get("next_step_id", "")),
        "current_step_subsurface_id": core.get("current_step_subsurface_id", ""),
        "current_step_target_path": core.get("current_step_target_path", ""),
        "repair_family": packet.get("resumability", {}).get("family", ""),
        "missing_inputs": list(packet.get("missing_inputs", [])),
    }


def doctor_summary(doctor: dict | None) -> dict:
    payload = doctor or {}
    coverage = payload.get("coverage", {})
    return {
        "final_verdict": payload.get("final_verdict", ""),
        "blocking_failure_classes": list(payload.get("blocking_failure_classes", [])),
        "coverage_gate_status": coverage.get("gate_status", ""),
        "coverage_gate_reason": coverage.get("gate_reason", ""),
        "critical_missing_fail_modes": list(coverage.get("critical_missing_fail_modes", [])),
    }


def acceptance_summary(validation: dict | None) -> dict:
    payload = validation or {}
    return {
        "criteria_revision_id": payload.get("criteria_revision_id", ""),
        "status": payload.get("status", ""),
        "reason": payload.get("reason", ""),
    }


def thin_summary(thin_output: dict | None) -> dict:
    payload = thin_output or {}
    return {
        "outcome_class": payload.get("outcome_class", ""),
        "status_label": payload.get("status_label", ""),
        "what_happened": payload.get("what_happened", ""),
        "what_to_do_next": payload.get("what_to_do_next", ""),
        "next_command": payload.get("next_command", ""),
        "restore_command": payload.get("restore_command", ""),
    }


def observability_summary(observability: dict | None) -> dict:
    payload = observability or {}
    counts = payload.get("event_counts", {})
    return {
        "transition_count": counts.get("transition_count", 0),
        "repair_attempt_count": counts.get("repair_attempt_count", 0),
        "rejection_count": counts.get("rejection_count", 0),
        "latest_rejection": (payload.get("rejection_log", []) or [{}])[-1] if payload.get("rejection_log") else {},
    }


def artifact_inventory(files: dict[str, Path | None]) -> dict:
    return {
        "available_artifacts": sorted(name for name, path in files.items() if path is not None and path.exists()),
        "missing_artifacts": sorted(name for name, path in files.items() if path is None or not path.exists()),
    }


def build_issue_title(record: dict) -> str:
    return f"[synrail bug-packet] {record['component_error_class'] or 'ALPHA_SIGNAL'} on {record['run_id']}"


def build_issue_body(record: dict) -> str:
    lines = [
        "# Synrail Bug Packet",
        "",
        "## Summary",
        f"- run id: `{record['run_id']}`",
        f"- task class: `{record['task_class']}`",
        f"- state: `{record['state']}`",
        f"- result: `{record['result']}`",
        f"- reason: `{record['reason']}`",
        f"- component error class: `{record['component_error_class']}`",
        f"- next safe step: `{record['next_safe_step']}`",
        "",
        "## Acceptance",
        f"- criteria revision: `{record['acceptance_summary']['criteria_revision_id']}`",
        f"- validation status: `{record['acceptance_summary']['status']}`",
        f"- validation reason: `{record['acceptance_summary']['reason']}`",
        "",
        "## Doctor",
        f"- final verdict: `{record['doctor_summary']['final_verdict']}`",
        f"- blocking failure classes: `{', '.join(record['doctor_summary']['blocking_failure_classes'])}`",
        f"- coverage gate: `{record['doctor_summary']['coverage_gate_status']}`",
        f"- coverage reason: `{record['doctor_summary']['coverage_gate_reason']}`",
        "",
        "## Continuation",
        f"- repair family: `{record['continuation_summary']['repair_family']}`",
        f"- current step id: `{record['continuation_summary']['current_step_id']}`",
        f"- current step subsurface: `{record['continuation_summary']['current_step_subsurface_id']}`",
        f"- current step target path: `{record['continuation_summary']['current_step_target_path']}`",
        f"- packet replay ready: `{record['continuation_summary']['packet_replay_ready']}`",
        f"- entry artifacts: `{', '.join(record['continuation_summary']['entry_artifacts'])}`",
        f"- precedence: `{', '.join(record['continuation_summary']['source_of_truth_precedence'])}`",
        f"- missing inputs: `{', '.join(record['continuation_summary']['missing_inputs'])}`",
        "",
        "## Observability",
        f"- transition count: `{record['observability_summary']['transition_count']}`",
        f"- repair attempt count: `{record['observability_summary']['repair_attempt_count']}`",
        f"- rejection count: `{record['observability_summary']['rejection_count']}`",
        "",
        "## Available Artifacts",
    ]
    for name in record["artifact_inventory"]["available_artifacts"]:
        lines.append(f"- `{name}`")
    if record["artifact_inventory"]["missing_artifacts"]:
        lines.extend(["", "## Missing Artifacts"])
        for name in record["artifact_inventory"]["missing_artifacts"]:
            lines.append(f"- `{name}`")
    return "\n".join(lines) + "\n"


def build_record(
    *,
    state: dict,
    report: dict,
    doctor: dict | None,
    acceptance_validation: dict | None,
    repair_packet: dict | None,
    observability: dict | None,
    thin_output: dict | None,
    files: dict[str, Path | None],
) -> dict:
    continuation = continuation_summary(repair_packet, observability)
    observability_view = observability_summary(observability)
    record = {
        "schema_version": "bug_packet_record_v0",
        "run_id": state.get("run_id", ""),
        "task_class": state.get("task_class", ""),
        "state": state.get("state", ""),
        "result": report.get("result", ""),
        "reason": report.get("reason", ""),
        "component_error_class": report.get("reason", ""),
        "next_safe_step": report.get("next_safe_step", state.get("next_safe_step", "")),
        "acceptance_summary": acceptance_summary(acceptance_validation),
        "doctor_summary": doctor_summary(doctor),
        "continuation_summary": continuation,
        "thin_output_summary": thin_summary(thin_output),
        "observability_summary": observability_view,
        "artifact_inventory": artifact_inventory(files),
    }
    record["issue_title"] = build_issue_title(record)
    record["issue_body"] = build_issue_body(record)
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-bug-packet-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--doctor-file")
    parser.add_argument("--acceptance-validation-file")
    parser.add_argument("--repair-packet-file")
    parser.add_argument("--observability-file")
    parser.add_argument("--thin-output-file")
    parser.add_argument("--issue-output")
    return parser


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
        validate_bug_packet_paths(args, artifact_root=artifact_root, project_root=project_root)
        files = {
            "state": Path(args.state_file),
            "report": Path(args.report_file),
            "doctor": Path(args.doctor_file) if args.doctor_file else None,
            "acceptance_validation": Path(args.acceptance_validation_file) if args.acceptance_validation_file else None,
            "repair_packet": Path(args.repair_packet_file) if args.repair_packet_file else None,
            "observability": Path(args.observability_file) if args.observability_file else None,
            "thin_output": Path(args.thin_output_file) if args.thin_output_file else None,
        }
        record = build_record(
            state=load_json(files["state"]),
            report=load_json(files["report"]),
            doctor=load_json_if_exists(files["doctor"]),
            acceptance_validation=load_json_if_exists(files["acceptance_validation"]),
            repair_packet=load_json_if_exists(files["repair_packet"]),
            observability=load_json_if_exists(files["observability"]),
            thin_output=load_json_if_exists(files["thin_output"]),
            files=files,
        )
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    if args.issue_output:
        save_text(Path(args.issue_output), record["issue_body"])
    print(json.dumps({"result": "OK", "issue_title": record["issue_title"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
