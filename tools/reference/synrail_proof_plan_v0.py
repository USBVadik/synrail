#!/usr/bin/env python3
"""Emit one governed-path proof preparation plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import save_json
except ImportError:
    from synrail_io_v0 import save_json

try:
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


PROOF_PLAN_PATH_SCOPES = {
    "artifact_root": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
}


REQUIRED_SECTION_NAMES = [
    "final_result",
    "modified_files",
    "diff_provenance",
    "artifact_identity",
    "cleanup_status",
]


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_proof_plan_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=PROOF_PLAN_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )




def build_plan(args: argparse.Namespace) -> dict:
    artifact_root = args.artifact_root.rstrip("/")
    return {
        "schema_version": "proof_bundle_plan_v0",
        "run_id": args.run_id,
        "task_class": args.task_class,
        "governed_mode": "FULL_GOVERNED_PATH",
        "required_sections": REQUIRED_SECTION_NAMES,
        "recommended_artifacts": {
            "final_result": f"{artifact_root}/final_result.json",
            "readback": f"{artifact_root}/readback.txt",
            "scenario_proof": f"{artifact_root}/scenario.txt",
            "bundle_output": f"{artifact_root}/bundle.json",
            "closure_output": f"{artifact_root}/closure.json",
            "preparation_receipt_output": f"{artifact_root}/preparation_receipt.json",
        },
        "artifact_identity": {
            "baseline_identity": args.baseline_identity,
            "execution_surface_identity": args.execution_surface_identity,
            "prompt_identity": args.prompt_identity,
            "task_identity": args.task_identity,
        },
        "planning_status": "READY",
        "next_safe_step": "collect the planned proof artifacts and assemble the bundle before closure",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-proof-plan-v0")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--baseline-identity", required=True)
    parser.add_argument("--execution-surface-identity", required=True)
    parser.add_argument("--prompt-identity", required=True)
    parser.add_argument("--task-identity", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        artifact_root = Path(args.artifact_root).expanduser().resolve()
        project_root = current_project_root()
        validate_root_within_project(
            "artifact_root",
            args.artifact_root,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_proof_plan_paths(args, artifact_root=artifact_root, project_root=project_root)
        plan = build_plan(args)
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(Path(args.output), plan)
    print(json.dumps({"result": "OK", "planning_status": plan["planning_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
