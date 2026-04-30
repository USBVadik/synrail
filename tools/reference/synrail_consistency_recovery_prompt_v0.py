#!/usr/bin/env python3
"""Build a bounded next-agent prompt from a consistency recovery plan."""

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


CONSISTENCY_RECOVERY_PROMPT_PATH_SCOPES = {
    "consistency_recovery_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
    "thin_output_file": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_consistency_recovery_prompt_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=CONSISTENCY_RECOVERY_PROMPT_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )






def build_record(*, recovery: dict, thin_output: dict | None = None) -> dict:
    allowed_scope = list(recovery.get("restore_artifact_ids", [])) + list(recovery.get("reemit_artifact_ids", []))
    forbidden_scope = [
        "Do not modify state_file.",
        "Do not broaden scope beyond the listed artifact recovery actions.",
        "Do not claim readiness, closure, or acceptance from artifact recovery alone.",
    ]
    must_pass = list(recovery.get("operator_instructions", []))
    must_pass.append("Preserve the current non-green contour while restoring or re-emitting derived artifacts.")
    prompt_lines = [
        "Repair the derived artifact surface without broadening scope.",
        f"Primary action: {recovery.get('primary_action', '')}",
        f"Allowed scope: {', '.join(allowed_scope) if allowed_scope else 'none'}",
        "Operator instructions:",
    ]
    for instruction in recovery.get("operator_instructions", []):
        prompt_lines.append(f"- {instruction}")
    if thin_output and thin_output.get("diagnosis", ""):
        prompt_lines.append(f"Current diagnosis: {thin_output['diagnosis']}")
    prompt_lines.append("Do not modify state_file or claim the contour is repaired beyond these artifact actions.")
    return {
        "schema_version": "consistency_recovery_prompt_record_v0",
        "run_id": recovery["run_id"],
        "task_class": recovery["task_class"],
        "primary_action": recovery.get("primary_action", ""),
        "allowed_scope": allowed_scope,
        "forbidden_scope": forbidden_scope,
        "must_pass": must_pass,
        "prompt": "\n".join(prompt_lines),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-consistency-recovery-prompt-v0")
    parser.add_argument("--consistency-recovery-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--thin-output-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        artifact_root = Path(args.consistency_recovery_file).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "consistency_recovery_file",
            args.consistency_recovery_file,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_consistency_recovery_prompt_paths(args, artifact_root=artifact_root, project_root=project_root)
        record = build_record(
            recovery=load_json(Path(args.consistency_recovery_file)),
            thin_output=load_json(Path(args.thin_output_file)) if args.thin_output_file else None,
        )
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "primary_action": record["primary_action"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
