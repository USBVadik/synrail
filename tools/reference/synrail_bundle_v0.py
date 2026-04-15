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

SEMANTIC_SECTION_STEPS = {
    "modified_files": "record the actual changed files in the final result artifact",
    "diff_provenance": "capture non-empty diff or provenance evidence for the changed files",
    "readback": "record substantive readback from the changed sections on the attested surface",
    "scenario_proof": "record an explicit scenario-proof result for the attested target surface",
    "artifact_identity": "repair baseline, surface, prompt, and task identity fields",
    "cleanup_status": "record a successful cleanup status for the execution surface",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def load_json_if_valid(path: Path | None) -> tuple[bool, dict]:
    if path is None:
        return False, {}
    try:
        return True, load_json(path)
    except json.JSONDecodeError:
        return False, {}


def file_present(path_str: str | None) -> tuple[bool, str]:
    if not path_str:
        return False, ""
    path = Path(path_str)
    return path.is_file(), str(path)


def file_text(path_str: str | None) -> str:
    present, resolved = file_present(path_str)
    if not present:
        return ""
    return Path(resolved).read_text().strip()


def contains_diff_markers(value: str) -> bool:
    return any(marker in value for marker in ["diff --git", "@@", "--- ", "+++ "])


def contains_any_keyword(value: str, keywords: list[str]) -> bool:
    lowered = value.lower()
    return any(keyword in lowered for keyword in keywords)


def first_semantic_step(semantically_insufficient_sections: list[str]) -> str:
    for section in semantically_insufficient_sections:
        if section in SEMANTIC_SECTION_STEPS:
            return SEMANTIC_SECTION_STEPS[section]
    return "strengthen the semantic proof evidence before trusting closure"


def build_bundle(args: argparse.Namespace) -> dict:
    final_present, final_path_str = file_present(args.final_result)
    final_path = Path(final_path_str) if final_path_str else None
    final_parseable, final = load_json_if_valid(final_path) if final_present else (False, {})

    modified_files = final.get("modified_files", [])
    git_diff = final.get("git_diff", "")
    cleanup = final.get("cleanup_status", {})
    readback_text = file_text(args.readback)
    scenario_text = file_text(args.scenario_proof)

    readback_present, readback_path = file_present(args.readback)
    scenario_present, scenario_path = file_present(args.scenario_proof)

    modified_files_semantically_sufficient = (
        isinstance(modified_files, list)
        and len(modified_files) > 0
        and all(isinstance(item, str) and bool(item.strip()) for item in modified_files)
    )
    diff_has_markers = contains_diff_markers(git_diff)
    diff_semantically_sufficient = bool(git_diff) and diff_has_markers
    readback_semantically_sufficient = bool(readback_text) and (
        contains_any_keyword(readback_text, ["readback", "read back", "confirm", "confirmed", "changed", "patch"])
        or len(readback_text) >= 24
    )
    scenario_semantically_sufficient = bool(scenario_text) and (
        contains_any_keyword(scenario_text, ["scenario", "pass", "passed", "success", "ready", "confirm", "confirmed"])
        or len(scenario_text) >= 24
    )
    identity_values = [
        args.baseline_identity or "",
        args.execution_surface_identity or "",
        args.prompt_identity or "",
        args.task_identity or "",
    ]
    identity_semantically_sufficient = all(bool(value.strip()) for value in identity_values)
    cleanup_semantically_sufficient = "cleanup_status" in final and bool(cleanup.get("success", False))

    bundle = {
        "schema_version": "proof_bundle_v0",
        "run_id": final.get("request_id", args.run_id or ""),
        "task_class": args.task_class,
        "status": "COMPLETE",
        "structural_status": "COMPLETE",
        "semantic_status": "SUFFICIENT",
        "final_result": {
            "present": final_present and final_parseable,
            "parseable": final_parseable,
            "status": final.get("status", ""),
        },
        "modified_files": {
            "present": isinstance(modified_files, list),
            "count": len(modified_files) if isinstance(modified_files, list) else 0,
            "semantically_sufficient": modified_files_semantically_sufficient,
        },
        "diff_provenance": {
            "present": "git_diff" in final,
            "non_empty": bool(git_diff),
            "has_diff_markers": diff_has_markers,
            "semantically_sufficient": diff_semantically_sufficient,
        },
        "readback": {
            "present": readback_present,
            "path": readback_path,
            "non_empty": bool(readback_text),
            "semantically_sufficient": readback_semantically_sufficient,
        },
        "scenario_proof": {
            "present": scenario_present,
            "path": scenario_path,
            "non_empty": bool(scenario_text),
            "semantically_sufficient": scenario_semantically_sufficient,
        },
        "artifact_identity": {
            "baseline_identity": args.baseline_identity or "",
            "execution_surface_identity": args.execution_surface_identity or "",
            "prompt_identity": args.prompt_identity or "",
            "task_identity": args.task_identity or "",
            "semantically_sufficient": identity_semantically_sufficient,
        },
        "cleanup_status": {
            "present": "cleanup_status" in final,
            "success": bool(cleanup.get("success", False)),
            "semantically_sufficient": cleanup_semantically_sufficient,
        },
        "missing_sections": [],
        "semantically_insufficient_sections": [],
        "semantic_next_safe_step": "",
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

    semantically_insufficient_sections: list[str] = []
    if not missing and final_present and final_parseable:
        if not modified_files_semantically_sufficient:
            semantically_insufficient_sections.append("modified_files")
        if not diff_semantically_sufficient:
            semantically_insufficient_sections.append("diff_provenance")
        if not readback_semantically_sufficient:
            semantically_insufficient_sections.append("readback")
        if not scenario_semantically_sufficient:
            semantically_insufficient_sections.append("scenario_proof")
        if not identity_semantically_sufficient:
            semantically_insufficient_sections.append("artifact_identity")
        if not cleanup_semantically_sufficient:
            semantically_insufficient_sections.append("cleanup_status")

    bundle["semantically_insufficient_sections"] = semantically_insufficient_sections
    bundle["semantic_next_safe_step"] = (
        first_semantic_step(semantically_insufficient_sections)
        if semantically_insufficient_sections
        else ""
    )

    if not final_present or not final_parseable:
        bundle["status"] = "INVALID"
        bundle["structural_status"] = "INVALID"
        bundle["semantic_status"] = "NOT_EVALUATED"
    elif missing:
        bundle["status"] = "PARTIAL"
        bundle["structural_status"] = "PARTIAL"
        bundle["semantic_status"] = "NOT_EVALUATED"
    elif semantically_insufficient_sections:
        bundle["status"] = "STRUCTURALLY_COMPLETE"
        bundle["structural_status"] = "COMPLETE"
        bundle["semantic_status"] = "INSUFFICIENT"
    else:
        bundle["status"] = "COMPLETE"
        bundle["structural_status"] = "COMPLETE"
        bundle["semantic_status"] = "SUFFICIENT"

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
