#!/usr/bin/env python3
"""Minimal proof bundle assembler for Synrail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REQUIRED_SECTION_NAMES = [
    "final_result",
    "modified_files",
    "diff_provenance",
    "readback",
    "scenario_proof",
    "artifact_identity",
    "cleanup_status",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def file_present(path_str: str | None) -> tuple[bool, str]:
    if not path_str:
        return False, ""
    path = Path(path_str)
    return path.exists(), str(path)


def build_bundle(args: argparse.Namespace) -> dict:
    final_path = Path(args.final_result)
    final_present = final_path.exists()
    final = load_json(final_path) if final_present else {}

    modified_files = final.get("modified_files", [])
    git_diff = final.get("git_diff", "")
    cleanup = final.get("cleanup_status", {})

    readback_present, readback_path = file_present(args.readback)
    scenario_present, scenario_path = file_present(args.scenario_proof)

    bundle = {
        "schema_version": "proof_bundle_v0",
        "run_id": final.get("request_id", args.run_id or ""),
        "task_class": args.task_class,
        "status": "COMPLETE",
        "final_result": {
            "present": final_present,
            "status": final.get("status", ""),
        },
        "modified_files": {
            "present": isinstance(modified_files, list),
            "count": len(modified_files) if isinstance(modified_files, list) else 0,
        },
        "diff_provenance": {
            "present": "git_diff" in final,
            "non_empty": bool(git_diff),
        },
        "readback": {
            "present": readback_present,
            "path": readback_path,
        },
        "scenario_proof": {
            "present": scenario_present,
            "path": scenario_path,
        },
        "artifact_identity": {
            "baseline_identity": args.baseline_identity or "",
            "execution_surface_identity": args.execution_surface_identity or "",
            "prompt_identity": args.prompt_identity or "",
            "task_identity": args.task_identity or "",
        },
        "cleanup_status": {
            "present": "cleanup_status" in final,
            "success": bool(cleanup.get("success", False)),
        },
        "missing_sections": [],
    }

    missing = []
    if not bundle["final_result"]["present"]:
        missing.append("final_result")
    if not bundle["modified_files"]["present"]:
        missing.append("modified_files")
    if not bundle["diff_provenance"]["present"]:
        missing.append("diff_provenance")
    if not bundle["readback"]["present"]:
        missing.append("readback")
    if not bundle["scenario_proof"]["present"]:
        missing.append("scenario_proof")

    identity = bundle["artifact_identity"]
    if not all(identity.values()):
        missing.append("artifact_identity")
    if not bundle["cleanup_status"]["present"]:
        missing.append("cleanup_status")

    bundle["missing_sections"] = missing

    if not final_present:
        bundle["status"] = "INVALID"
    elif missing:
        bundle["status"] = "PARTIAL"
    else:
        bundle["status"] = "COMPLETE"

    return bundle


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-bundle-v0")
    parser.add_argument("--final-result", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--run-id")
    parser.add_argument("--readback")
    parser.add_argument("--scenario-proof")
    parser.add_argument("--baseline-identity")
    parser.add_argument("--execution-surface-identity")
    parser.add_argument("--prompt-identity")
    parser.add_argument("--task-identity")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    bundle = build_bundle(args)
    out = Path(args.output)
    out.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
    print(json.dumps({"result": "OK", "status": bundle["status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
