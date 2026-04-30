#!/usr/bin/env python3
"""Inspect whether a packet-first continuation path is followable by a second operator without author memory."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_continuation_arbiter_v0 import build_record as build_continuation_arbiter
    from .synrail_io_v0 import load_json, save_json
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_continuation_arbiter_v0 import build_record as build_continuation_arbiter
    from synrail_io_v0 import load_json, save_json
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


SECOND_OPERATOR_PATH_SCOPES = {
    "state_file": ARTIFACT_SCOPE,
    "repair_packet_file": ARTIFACT_SCOPE,
    "run_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_second_operator_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=SECOND_OPERATOR_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def build_record(*, state: dict, packet: dict, run_artifact: dict) -> dict:
    core = packet.get("continuation_core", {})
    report = run_artifact.get("report", {})
    repair_packet = run_artifact.get("repair_packet", {})
    embedded_arbiter = packet.get("continuation_arbiter", {})
    if isinstance(embedded_arbiter, dict) and embedded_arbiter.get("schema_version") == "continuation_arbiter_record_v0":
        arbiter = embedded_arbiter
    else:
        arbiter = build_continuation_arbiter(
            state=state,
            packet=packet,
            repair_receipt=packet.get("repair_receipt"),
        )
    resolved = arbiter.get("resolved_decision", {})
    visible_entry_artifacts = ["state_file", "repair_packet"]
    resumability_status = resolved.get("resumability_status", repair_packet.get("resumability_status", core.get("resumability_status", "")))
    has_explicit_next_step = bool(resolved.get("next_safe_step", ""))
    has_explicit_required_inputs = bool(resolved.get("next_step_required_inputs", []))
    no_input_boundary = resumability_status == "NOT_RESUMABLE" and not resolved.get("next_step_required_inputs", [])
    has_explicit_focus = bool(resolved.get("operator_focus", ""))
    current_step_subsurface_id = core.get("current_step_subsurface_id", "")
    current_step_target_path = core.get("current_step_target_path", "")
    has_explicit_target_path = bool(current_step_target_path) if current_step_subsurface_id else True
    has_explicit_precedence = bool(arbiter.get("precedence_order", []))
    packet_replay_ready = bool(resolved.get("packet_replay_ready", False))
    packet_only_entry = visible_entry_artifacts == ["state_file", "repair_packet"]
    requires_author_intuition = not (
        arbiter.get("resolution_status", "") == "RESOLVED"
        and has_explicit_next_step
        and has_explicit_focus
        and has_explicit_target_path
        and (has_explicit_required_inputs or no_input_boundary)
        and has_explicit_precedence
        and packet_replay_ready
    )
    verdict = "FOLLOWABLE_BY_SECOND_OPERATOR" if packet_only_entry and not requires_author_intuition else "AUTHOR_INTUITION_STILL_REQUIRED"
    return {
        "schema_version": "second_operator_record_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "entrypoint": "resume",
        "entry_state": state["state"],
        "visible_entry_artifacts": visible_entry_artifacts,
        "packet_only_entry": packet_only_entry,
        "has_explicit_next_step": has_explicit_next_step,
        "has_explicit_required_inputs": has_explicit_required_inputs,
        "has_explicit_operator_focus": has_explicit_focus,
        "has_explicit_target_path": has_explicit_target_path,
        "has_explicit_precedence": has_explicit_precedence,
        "packet_replay_ready": packet_replay_ready,
        "arbiter_resolution_status": arbiter.get("resolution_status", ""),
        "arbiter_conflict_count": arbiter.get("conflict_count", 0),
        "arbiter_ignored_sources": list(arbiter.get("ignored_sources", [])),
        "requires_author_intuition": requires_author_intuition,
        "expected_result": report.get("result", ""),
        "expected_reason": report.get("reason", ""),
        "expected_next_safe_step": report.get("next_safe_step", ""),
        "repair_family": resolved.get("resumability_family", repair_packet.get("resumability_family", core.get("resumability_family", ""))),
        "current_step_id": core.get("current_step_id", ""),
        "current_step_subsurface_id": current_step_subsurface_id,
        "current_step_target_path": current_step_target_path,
        "verdict": verdict,
        "why": (
            "the packet-first continuation path now resolves conflicts through the arbiter, so a second operator can follow the same next step without author memory"
            if verdict == "FOLLOWABLE_BY_SECOND_OPERATOR"
            else "the continuation path still leaves too much continuation conflict unresolved after explicit arbitration"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-second-operator-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--run-file", required=True)
    parser.add_argument("--output", required=True)
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
        validate_second_operator_paths(args, artifact_root=artifact_root, project_root=project_root)
        record = build_record(
            state=load_json(Path(args.state_file)),
            packet=load_json(Path(args.repair_packet_file)),
            run_artifact=load_json(Path(args.run_file)),
        )
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
