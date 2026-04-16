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


def non_empty_lines(value: str) -> list[str]:
    return [line.strip() for line in value.splitlines() if line.strip()]


def references_modified_file(value: str, modified_files: list[str]) -> bool:
    lowered = value.lower()
    for path in modified_files:
        normalized = (path or "").strip().lower()
        if not normalized:
            continue
        basename = Path(normalized).name
        if normalized in lowered or basename in lowered:
            return True
    return False


def contains_patch_lines(value: str) -> bool:
    return any(
        line.startswith("+") or line.startswith("-")
        for line in non_empty_lines(value)
        if not line.startswith("+++") and not line.startswith("---")
    )


def diff_mentions_modified_files(value: str, modified_files: list[str]) -> bool:
    if not modified_files:
        return False
    return references_modified_file(value, modified_files)


def readback_is_semantically_sufficient(value: str, modified_files: list[str]) -> bool:
    if not value:
        return False
    lines = non_empty_lines(value)
    if not lines or len(value.strip()) < 32:
        return False
    if not references_modified_file(value, modified_files):
        return False
    return any(
        contains_any_keyword(
            line,
            [
                "read back",
                "readback",
                "observed",
                "confirmed",
                "contains",
                "returns",
                "imports",
                "branch",
                "handler",
                "route",
                "function",
                "class",
                "line",
            ],
        )
        for line in lines
    )


def scenario_is_semantically_sufficient(value: str) -> bool:
    if not value:
        return False
    lines = non_empty_lines(value)
    if not lines or len(value.strip()) < 32:
        return False
    has_context = any(
        contains_any_keyword(line, ["scenario:", "status:", "result:", "observed", "returned", "response", "output"])
        for line in lines
    )
    has_outcome = any(
        contains_any_keyword(line, ["pass", "passed", "fail", "failed", "success", "succeeded", "blocked"])
        for line in lines
    )
    return has_context and has_outcome


def cleanup_is_semantically_sufficient(cleanup: dict) -> bool:
    if not cleanup.get("success", False):
        return False
    summary = (cleanup.get("summary", "") or "").strip()
    if len(summary) < 24:
        return False
    return contains_any_keyword(
        summary,
        [
            "clean",
            "no extra",
            "no stray",
            "no unintended",
            "unchanged",
            "restored",
            "only intended",
        ],
    )


def first_semantic_step(semantically_insufficient_sections: list[str]) -> str:
    for section in semantically_insufficient_sections:
        if section in SEMANTIC_SECTION_STEPS:
            return SEMANTIC_SECTION_STEPS[section]
    return "strengthen the semantic proof evidence before trusting closure"


def structural_trace_entry(*, section: str, present: bool, structurally_complete: bool, why: str) -> dict:
    return {
        "section": section,
        "present": present,
        "structurally_complete": structurally_complete,
        "why": why,
    }


def semantic_trace_entry(
    *,
    section: str,
    evaluated: bool,
    semantically_sufficient: bool,
    why: str,
    recommended_action: str,
) -> dict:
    return {
        "section": section,
        "evaluated": evaluated,
        "semantically_sufficient": semantically_sufficient,
        "why": why,
        "recommended_action": recommended_action,
    }


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
    diff_semantically_sufficient = (
        bool(git_diff)
        and "diff --git" in git_diff
        and "@@" in git_diff
        and contains_patch_lines(git_diff)
        and diff_mentions_modified_files(git_diff, modified_files if isinstance(modified_files, list) else [])
    )
    readback_semantically_sufficient = readback_is_semantically_sufficient(
        readback_text,
        modified_files if isinstance(modified_files, list) else [],
    )
    scenario_semantically_sufficient = scenario_is_semantically_sufficient(scenario_text)
    identity_values = [
        args.baseline_identity or "",
        args.execution_surface_identity or "",
        args.prompt_identity or "",
        args.task_identity or "",
    ]
    identity_semantically_sufficient = all(bool(value.strip()) for value in identity_values)
    cleanup_semantically_sufficient = "cleanup_status" in final and cleanup_is_semantically_sufficient(cleanup)
    final_request_id = (final.get("request_id", "") or "").strip()

    bundle = {
        "schema_version": "proof_bundle_v0",
        "run_id": args.run_id or final_request_id or "",
        "task_class": args.task_class,
        "status": "COMPLETE",
        "structural_status": "COMPLETE",
        "semantic_status": "SUFFICIENT",
        "final_result": {
            "present": final_present and final_parseable,
            "parseable": final_parseable,
            "status": final.get("status", ""),
            "request_id": final_request_id,
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
        "structural_decision_trace": [],
        "semantic_decision_trace": [],
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
    bundle["structural_decision_trace"] = [
        structural_trace_entry(
            section="final_result",
            present=bundle["final_result"]["present"],
            structurally_complete=bundle["final_result"]["present"],
            why=(
                "the final result artifact is present and parseable"
                if bundle["final_result"]["present"]
                else "the final result artifact is missing or not parseable"
            ),
        ),
        structural_trace_entry(
            section="modified_files",
            present=bundle["modified_files"]["present"],
            structurally_complete=bundle["modified_files"]["present"],
            why=(
                "the modified-files section is present in the final result artifact"
                if bundle["modified_files"]["present"]
                else "the modified-files section is missing from the final result artifact"
            ),
        ),
        structural_trace_entry(
            section="diff_provenance",
            present=bundle["diff_provenance"]["present"],
            structurally_complete=bundle["diff_provenance"]["present"],
            why=(
                "diff or provenance evidence is present in the final result artifact"
                if bundle["diff_provenance"]["present"]
                else "diff or provenance evidence is missing from the final result artifact"
            ),
        ),
        structural_trace_entry(
            section="readback",
            present=bundle["readback"]["present"],
            structurally_complete=bundle["readback"]["present"],
            why=(
                "readback evidence file is present"
                if bundle["readback"]["present"]
                else "readback evidence file is missing"
            ),
        ),
        structural_trace_entry(
            section="scenario_proof",
            present=bundle["scenario_proof"]["present"],
            structurally_complete=bundle["scenario_proof"]["present"],
            why=(
                "scenario-proof evidence file is present"
                if bundle["scenario_proof"]["present"]
                else "scenario-proof evidence file is missing"
            ),
        ),
        structural_trace_entry(
            section="artifact_identity",
            present=all(bool(value) for value in identity.values()),
            structurally_complete=all(bool(value) for value in identity.values()),
            why=(
                "baseline, surface, prompt, and task identity fields are all present"
                if all(bool(value) for value in identity.values())
                else "one or more identity fields are missing"
            ),
        ),
        structural_trace_entry(
            section="cleanup_status",
            present=bundle["cleanup_status"]["present"],
            structurally_complete=bundle["cleanup_status"]["present"],
            why=(
                "cleanup status is present in the final result artifact"
                if bundle["cleanup_status"]["present"]
                else "cleanup status is missing from the final result artifact"
            ),
        ),
    ]

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
    bundle["semantic_decision_trace"] = [
        semantic_trace_entry(
            section="modified_files",
            evaluated=not missing,
            semantically_sufficient=modified_files_semantically_sufficient,
            why=(
                "the modified-files list names at least one concrete changed file"
                if modified_files_semantically_sufficient
                else "the modified-files list is empty, malformed, or does not name concrete changed files"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["modified_files"],
        ),
        semantic_trace_entry(
            section="diff_provenance",
            evaluated=not missing,
            semantically_sufficient=diff_semantically_sufficient,
            why=(
                "diff or provenance evidence contains a concrete patch for the named modified files"
                if diff_semantically_sufficient
                else "diff or provenance evidence is present but does not yet prove a concrete patch on the named files"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["diff_provenance"],
        ),
        semantic_trace_entry(
            section="readback",
            evaluated=not missing,
            semantically_sufficient=readback_semantically_sufficient,
            why=(
                "readback evidence names the changed surface and records an observed property of it"
                if readback_semantically_sufficient
                else "readback evidence does not yet name the changed surface with an observed readback"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["readback"],
        ),
        semantic_trace_entry(
            section="scenario_proof",
            evaluated=not missing,
            semantically_sufficient=scenario_semantically_sufficient,
            why=(
                "scenario-proof evidence records a concrete scenario context and outcome"
                if scenario_semantically_sufficient
                else "scenario-proof evidence does not yet record a concrete scenario context and outcome"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["scenario_proof"],
        ),
        semantic_trace_entry(
            section="artifact_identity",
            evaluated=not missing,
            semantically_sufficient=identity_semantically_sufficient,
            why=(
                "baseline, surface, prompt, and task identity fields are all non-empty"
                if identity_semantically_sufficient
                else "identity fields are incomplete or empty"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["artifact_identity"],
        ),
        semantic_trace_entry(
            section="cleanup_status",
            evaluated=not missing,
            semantically_sufficient=cleanup_semantically_sufficient,
            why=(
                "cleanup status reports success with an explicit clean-surface summary"
                if cleanup_semantically_sufficient
                else "cleanup status is present but does not prove a clean post-change surface"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["cleanup_status"],
        ),
    ]

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
