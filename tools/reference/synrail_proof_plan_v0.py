#!/usr/bin/env python3
"""Emit one governed-path proof preparation plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_SECTION_NAMES = [
    "final_result",
    "modified_files",
    "diff_provenance",
    "artifact_identity",
    "cleanup_status",
]


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


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
    plan = build_plan(args)
    save_json(Path(args.output), plan)
    print(json.dumps({"result": "OK", "planning_status": plan["planning_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
