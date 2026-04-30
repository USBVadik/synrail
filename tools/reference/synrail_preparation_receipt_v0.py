#!/usr/bin/env python3
"""Emit one machine-readable governed-path preparation receipt."""

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


PREPARATION_RECEIPT_PATH_SCOPES = {
    "plan_file": ARTIFACT_SCOPE,
    "bundle_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_preparation_receipt_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=PREPARATION_RECEIPT_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def build_receipt(plan_path: Path, bundle_path: Path) -> dict:
    plan = load_json(plan_path)
    bundle = load_json(bundle_path)

    if plan.get("schema_version") != "proof_bundle_plan_v0":
        raise ValueError("plan must use proof_bundle_plan_v0")
    if bundle.get("schema_version") != "proof_bundle_v0":
        raise ValueError("bundle must use proof_bundle_v0")

    required_sections = plan["required_sections"]
    missing_required_sections = [section for section in required_sections if section in bundle["missing_sections"]]
    present_count = len(required_sections) - len(missing_required_sections)
    run_matches_plan = bundle["run_id"] == plan["run_id"]
    task_matches_plan = bundle["task_class"] == plan["task_class"]
    complete_on_first_bundle_pass = (
        bundle["status"] == "COMPLETE"
        and run_matches_plan
        and task_matches_plan
        and not missing_required_sections
    )

    next_safe_step = "run closure on the complete planned bundle"
    if not complete_on_first_bundle_pass:
        next_safe_step = bundle.get("semantic_next_safe_step", "") or "collect the missing planned proof sections and rebuild the bundle"

    return {
        "schema_version": "governed_path_preparation_receipt_v0",
        "plan_file": str(plan_path),
        "bundle_file": str(bundle_path),
        "run_id": plan["run_id"],
        "task_class": plan["task_class"],
        "bundle_run_matches_plan": run_matches_plan,
        "bundle_task_class_matches_plan": task_matches_plan,
        "planned_required_sections_count": len(required_sections),
        "planned_required_sections_present_count": present_count,
        "bundle_status": bundle["status"],
        "missing_required_sections": missing_required_sections,
        "complete_on_first_bundle_pass": complete_on_first_bundle_pass,
        "ready_for_closure": complete_on_first_bundle_pass,
        "next_safe_step": next_safe_step,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-preparation-receipt-v0")
    parser.add_argument("--plan-file", required=True)
    parser.add_argument("--bundle-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        artifact_root = Path(args.plan_file).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "plan_file",
            args.plan_file,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_preparation_receipt_paths(args, artifact_root=artifact_root, project_root=project_root)
        receipt = build_receipt(Path(args.plan_file), Path(args.bundle_file))
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), receipt)
    print(json.dumps({"result": "OK", "ready_for_closure": receipt["ready_for_closure"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
