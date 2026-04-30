#!/usr/bin/env python3
"""Check that a consistency recovery prompt stays bounded to the restore-or-reemit plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_io_v0 import load_json, save_json
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


CONSISTENCY_RECOVERY_PROMPT_READING_PATH_SCOPES = {
    "consistency_recovery_file": ARTIFACT_SCOPE,
    "prompt_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_consistency_recovery_prompt_reading_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=CONSISTENCY_RECOVERY_PROMPT_READING_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def build_record(*, recovery: dict, prompt: dict) -> dict:
    expected_scope = list(recovery.get("restore_artifact_ids", [])) + list(recovery.get("reemit_artifact_ids", []))
    missing_markers: list[str] = []

    if prompt.get("allowed_scope", []) != expected_scope:
        missing_markers.append("allowed_scope")
    for instruction in recovery.get("operator_instructions", []):
        if instruction not in prompt.get("must_pass", []):
            missing_markers.append(f"must_pass:{instruction}")
        if instruction not in prompt.get("prompt", ""):
            missing_markers.append(f"prompt:{instruction}")
    if "Do not modify state_file." not in prompt.get("forbidden_scope", []):
        missing_markers.append("forbidden_scope_state_file")

    verdict = "RECOVERY_PROMPT_BOUNDED" if not missing_markers else "RECOVERY_PROMPT_DRIFT"
    return {
        "schema_version": "consistency_recovery_prompt_reading_record_v0",
        "run_id": recovery["run_id"],
        "task_class": recovery["task_class"],
        "primary_action": recovery.get("primary_action", ""),
        "allowed_scope": prompt.get("allowed_scope", []),
        "missing_markers": missing_markers,
        "verdict": verdict,
        "why": (
            "the restore-or-reemit path can be handed to the next agent call without broadening beyond the listed artifact actions"
            if verdict == "RECOVERY_PROMPT_BOUNDED"
            else "the generated recovery prompt drifted away from the concrete restore-or-reemit action set"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-consistency-recovery-prompt-reading-v0")
    parser.add_argument("--consistency-recovery-file", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
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
        validate_consistency_recovery_prompt_reading_paths(args, artifact_root=artifact_root, project_root=project_root)
        record = build_record(
            recovery=load_json(Path(args.consistency_recovery_file)),
            prompt=load_json(Path(args.prompt_file)),
        )
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0 if record["verdict"] == "RECOVERY_PROMPT_BOUNDED" else 2


if __name__ == "__main__":
    sys.exit(main())
