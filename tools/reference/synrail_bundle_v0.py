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
    "modified_files": "record the actual changed files in the final result artifact, or mark the run as already_satisfied only when the requested state was already present before edits",
    "scope_alignment": "keep the implementation inside the requested additive scope and remove unrelated adjacent rewrites or spacing tweaks",
    "presentation_alignment": "keep the newly added surface visually plain and close to the requested text-only intent; remove extra emphasis styling unless the task asked for it",
    "diff_provenance": "prove the patch on the changed files with a patch-shaped git_diff or a structured diff_provenance record, or use a truthful already_satisfied observation record when no edit was required",
    "verification_corroboration": "tie acceptance to explicit local verification evidence inside the current proof surfaces instead of prose-only readback and scenario text",
    "readback": "record substantive readback from the changed sections on the attested surface",
    "scenario_proof": "record an explicit scenario-proof result for the attested target surface",
    "artifact_identity": "restore baseline, execution surface, prompt, and task identity values for this run",
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


def line_starts_with_any_label(value: str, labels: list[str]) -> bool:
    lowered = value.strip().lower()
    return any(lowered.startswith(label) for label in labels)


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


def attested_surfaces(modified_files: object, record: object) -> list[str]:
    surfaces: list[str] = []
    if isinstance(modified_files, list):
        for item in modified_files:
            if isinstance(item, str) and item.strip():
                surfaces.append(item.strip())
    if isinstance(record, dict):
        changed_file = non_empty_string(record.get("changed_file", ""))
        if changed_file and changed_file not in surfaces:
            surfaces.append(changed_file)
    return surfaces


def contains_patch_lines(value: str) -> bool:
    return any(
        line.startswith("+") or line.startswith("-")
        for line in non_empty_lines(value)
        if not line.startswith("+++") and not line.startswith("---")
    )


def removed_patch_lines(value: str) -> list[str]:
    removed: list[str] = []
    for raw_line in value.splitlines():
        if raw_line.startswith(("diff --git", "@@", "---", "+++")):
            continue
        if raw_line.startswith("-"):
            removed.append(raw_line[1:].strip())
    return removed


def added_patch_lines(value: str) -> list[str]:
    added: list[str] = []
    for raw_line in value.splitlines():
        if raw_line.startswith(("diff --git", "@@", "---", "+++")):
            continue
        if raw_line.startswith("+"):
            added.append(raw_line[1:].strip())
    return added


def non_empty_string(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def first_non_empty(*values: object) -> str:
    for value in values:
        text = non_empty_string(value)
        if text:
            return text
    return ""


def diff_mentions_modified_files(value: str, modified_files: list[str]) -> bool:
    if not modified_files:
        return False
    return references_modified_file(value, modified_files)


def additive_only_scope_requested(*values: object) -> bool:
    text = " ".join(non_empty_string(value).lower() for value in values if non_empty_string(value))
    if not text:
        return False
    additive_verbs = ["add", "insert", "append"]
    small_target = [
        "subtitle",
        "caption",
        "label",
        "helper text",
        "tagline",
        "badge",
        "note",
        "copy",
        "text",
    ]
    broader_change_markers = [
        "margin",
        "padding",
        "spacing",
        "class",
        "style",
        "layout",
        "css",
        "refactor",
        "rename",
        "remove",
        "replace",
        "rewrite",
        "restyle",
        "cleanup",
        "format",
    ]
    asks_for_addition = any(marker in text for marker in additive_verbs)
    names_small_target = any(marker in text for marker in small_target)
    broadens_scope = any(marker in text for marker in broader_change_markers)
    return asks_for_addition and names_small_target and not broadens_scope


def scope_alignment_is_semantically_sufficient(
    *,
    change_disposition: str,
    git_diff: str,
    diff_provenance_record: object,
    task_identity_text: str,
) -> tuple[bool, bool]:
    evaluated = additive_only_scope_requested(task_identity_text)
    if not evaluated or change_disposition == "already_satisfied":
        return evaluated, True
    if removed_patch_lines(git_diff):
        return True, False
    if isinstance(diff_provenance_record, dict) and non_empty_string(diff_provenance_record.get("removed_line", "")):
        return True, False
    return True, True


def style_intent_requested(task_text: str) -> bool:
    lowered = task_text.lower()
    return any(
        marker in lowered
        for marker in [
            "italic",
            "bold",
            "uppercase",
            "tracking",
            "opacity",
            "faded",
            "muted",
            "accent",
            "emphasis",
            "style",
            "styled",
            "css",
            "class",
            "blue",
            "gray",
            "grey",
            "caps",
        ]
    )


def suspicious_emphasis_classes(line: str) -> list[str]:
    text = non_empty_string(line)
    if not text or 'class="' not in text:
        return []
    class_blob = text.split('class="', 1)[1].split('"', 1)[0]
    classes = [item.strip() for item in class_blob.split() if item.strip()]
    suspicious_prefixes = [
        "italic",
        "underline",
        "line-through",
        "uppercase",
        "capitalize",
        "tracking-",
        "opacity-",
        "font-bold",
        "font-extrabold",
        "font-black",
        "shadow",
        "animate-",
        "rotate-",
        "skew-",
        "scale-",
        "blur",
    ]
    return [
        item
        for item in classes
        if any(item == prefix or item.startswith(prefix) for prefix in suspicious_prefixes)
    ]


def presentation_alignment_is_semantically_sufficient(
    *,
    change_disposition: str,
    git_diff: str,
    diff_provenance_record: object,
    task_identity_text: str,
) -> tuple[bool, bool, list[str]]:
    if change_disposition == "already_satisfied":
        return False, True, []
    if not additive_only_scope_requested(task_identity_text) or style_intent_requested(task_identity_text):
        return False, True, []
    candidate_lines: list[str] = []
    if isinstance(diff_provenance_record, dict):
        for key in ["added_line", "observed_line"]:
            line = non_empty_string(diff_provenance_record.get(key, ""))
            if line:
                candidate_lines.append(line)
    candidate_lines.extend(added_patch_lines(git_diff))
    suspicious: list[str] = []
    for line in candidate_lines:
        suspicious.extend(suspicious_emphasis_classes(line))
    unique = sorted(set(suspicious))
    if not candidate_lines:
        return False, True, []
    return True, not bool(unique), unique


def structured_diff_provenance_is_semantically_sufficient(
    record: object,
    modified_files: list[str],
    *,
    change_disposition: str,
) -> bool:
    if not isinstance(record, dict):
        return False
    method = non_empty_string(record.get("method", ""))
    changed_file = non_empty_string(record.get("changed_file", ""))
    added_line = non_empty_string(record.get("added_line", ""))
    removed_line = non_empty_string(record.get("removed_line", ""))
    observed_line = non_empty_string(record.get("observed_line", ""))
    context_before = non_empty_string(record.get("context_before", ""))
    context_after = non_empty_string(record.get("context_after", ""))
    verification_command = non_empty_string(record.get("verification_command", ""))
    verification_result = non_empty_string(record.get("verification_result", ""))
    provenance_note = non_empty_string(record.get("provenance_note", ""))
    changed_file_matches = references_modified_file(changed_file, modified_files) if modified_files else bool(changed_file)
    has_verification = bool(verification_command and verification_result)
    if change_disposition == "already_satisfied":
        has_observation = bool(observed_line or verification_result)
        return bool(method and changed_file and changed_file_matches and has_verification and has_observation and provenance_note)
    has_patch_context = any([added_line, removed_line, context_before, context_after])
    return bool(method and changed_file and changed_file_matches and has_patch_context and has_verification)


def _word_set(text: str) -> set[str]:
    """Extract lowercase alphabetic tokens of 3+ chars for overlap comparison."""
    return {w for w in text.lower().split() if len(w) >= 3 and w.isalpha()}


def _is_parroting_task(proof_text: str, task_text: str) -> bool:
    """Return True if proof is suspiciously similar to the task description.

    A proof that merely restates the task in different words is worthless.
    We check word-level overlap: if >70% of the proof's content words also
    appear in the task description, it's likely parroting.
    """
    if not task_text or not proof_text:
        return False
    proof_words = _word_set(proof_text)
    task_words = _word_set(task_text)
    if len(proof_words) < 4:
        return False
    # Exclude very common words that inflate overlap
    filler = {"the", "and", "for", "this", "that", "with", "from", "was", "were", "has", "have", "not", "are", "but"}
    proof_meaningful = proof_words - filler
    task_meaningful = task_words - filler
    if not proof_meaningful:
        return False
    overlap = len(proof_meaningful & task_meaningful) / len(proof_meaningful)
    return overlap > 0.70


def _has_concrete_identifier(value: str) -> bool:
    """Return True if the text contains at least one concrete identifier.

    Concrete identifiers are file paths, function/class names, line numbers,
    code tokens, or command fragments — anything more specific than prose.
    """
    for line in non_empty_lines(value):
        stripped = line.strip()
        # File path patterns: contains / or . with extension-like suffix
        if "/" in stripped or "\\" in stripped:
            return True
        # Dotted identifiers like module.function or file.ext
        if "." in stripped and any(
            part.strip() for part in stripped.split(".") if len(part.strip()) >= 2
        ):
            tokens = stripped.split()
            if any("." in tok and not tok.endswith(".") and not tok.startswith(".") for tok in tokens):
                return True
        # Line number references
        if contains_any_keyword(stripped, ["line ", "line:", "L", ":"]) and any(ch.isdigit() for ch in stripped):
            return True
        # Code-like tokens: camelCase, snake_case, or ALL_CAPS identifiers
        for token in stripped.split():
            clean = token.strip(".,;:\"'`()[]{}#")
            if not clean:
                continue
            if "_" in clean and len(clean) >= 4 and any(ch.isalpha() for ch in clean):
                return True
            if any(ch.isupper() for ch in clean[1:]) and any(ch.islower() for ch in clean):
                return True
    return False


_ACTION_VERBS = [
    "implemented", "added", "created", "wrote", "built", "made",
    "refactored", "updated", "modified", "changed", "fixed", "removed",
    "deleted", "replaced", "introduced", "set up", "configured",
    "applied", "integrated", "migrated", "converted", "moved",
]

_OBSERVATION_LABELS = ["observed", "confirmed"]
_SCENARIO_COMMAND_LABELS = ["command:", "cmd:"]
_SCENARIO_OBSERVED_LABELS = ["observed:", "result:", "output:"]


def _readback_line_is_action_narrative(line: str) -> bool:
    """Return True if a line uses an observation label but contains action verbs.

    Example bad line: "Observed: Implemented compute_retry_delay with backoff"
    Example good line: "Observed: compute_retry_delay returns 2.0 for attempt=1"
    """
    lowered = line.lower()
    for label in _OBSERVATION_LABELS:
        pos = lowered.find(label)
        if pos == -1:
            continue
        # Extract the content after the label
        after = lowered[pos + len(label):]
        # Strip colon, dash, whitespace
        after = after.lstrip(":- \t")
        if not after:
            continue
        # Check if the content starts with an action verb
        for verb in _ACTION_VERBS:
            if after.startswith(verb) and (
                len(after) == len(verb) or not after[len(verb)].isalpha()
            ):
                return True
    return False


def readback_is_semantically_sufficient(value: str, modified_files: list[str], task_identity: str = "") -> bool:
    if not value:
        return False
    lines = non_empty_lines(value)
    if not lines or len(value.strip()) < 48:
        return False
    if len(lines) < 2:
        return False
    if not references_modified_file(value, modified_files):
        return False
    if not _has_concrete_identifier(value):
        return False
    if _is_parroting_task(value, task_identity):
        return False
    observation_keywords = [
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
    ]
    matching_lines = [
        line for line in lines
        if contains_any_keyword(line, observation_keywords)
    ]
    if not matching_lines:
        return False
    # Reject if every line with an observation label is action-narrative
    observation_label_lines = [
        line for line in matching_lines
        if contains_any_keyword(line, _OBSERVATION_LABELS)
    ]
    if observation_label_lines and all(
        _readback_line_is_action_narrative(line) for line in observation_label_lines
    ):
        return False
    return True


def scenario_has_explicit_command(value: str) -> bool:
    return any(line_starts_with_any_label(line, _SCENARIO_COMMAND_LABELS) for line in non_empty_lines(value))


def scenario_has_explicit_observation(value: str) -> bool:
    return any(line_starts_with_any_label(line, _SCENARIO_OBSERVED_LABELS) for line in non_empty_lines(value))


def scenario_is_semantically_sufficient(value: str, task_identity: str = "") -> bool:
    if not value:
        return False
    lines = non_empty_lines(value)
    if not lines or len(value.strip()) < 48:
        return False
    if len(lines) < 3:
        return False
    if _is_parroting_task(value, task_identity):
        return False
    has_context = any(
        contains_any_keyword(line, ["scenario:", "status:", "result:", "observed", "returned", "response", "output"])
        for line in lines
    )
    has_outcome = any(
        contains_any_keyword(line, ["pass", "passed", "fail", "failed", "success", "succeeded", "blocked"])
        for line in lines
    )
    has_explicit_command = scenario_has_explicit_command(value)
    has_explicit_observation = scenario_has_explicit_observation(value)
    has_specifics = _has_concrete_identifier(value) or any(
        contains_any_keyword(line, ["command:", "curl", "python", "node", "npm", "bash", "http", "localhost", "grep", "cat", "run "])
        for line in lines
    )
    return has_context and has_outcome and has_specifics and has_explicit_command and has_explicit_observation


def verification_corroboration_is_semantically_sufficient(
    *,
    structured_diff_sufficient: bool,
    scenario_text: str,
) -> bool:
    if structured_diff_sufficient:
        return True
    return scenario_has_explicit_command(scenario_text) and scenario_has_explicit_observation(scenario_text)


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
    diff_provenance_record = final.get("diff_provenance", {})
    cleanup = final.get("cleanup_status", {})
    readback_text = file_text(args.readback)
    scenario_text = file_text(args.scenario_proof)
    raw_change_disposition = non_empty_string(final.get("change_disposition", ""))
    inferred_already_satisfied = (
        isinstance(modified_files, list)
        and len(modified_files) == 0
        and not non_empty_string(git_diff)
        and isinstance(diff_provenance_record, dict)
        and bool(non_empty_string(diff_provenance_record.get("changed_file", "")))
    )
    change_disposition = raw_change_disposition or ("already_satisfied" if inferred_already_satisfied else "modified")

    readback_present, readback_path = file_present(args.readback)
    scenario_present, scenario_path = file_present(args.scenario_proof)

    modified_files_semantically_sufficient = False
    if isinstance(modified_files, list) and all(isinstance(item, str) for item in modified_files):
        if change_disposition == "already_satisfied":
            modified_files_semantically_sufficient = (
                len(modified_files) == 0
                and bool(non_empty_string(diff_provenance_record.get("changed_file", "")))
            )
        else:
            modified_files_semantically_sufficient = len(modified_files) > 0 and all(bool(item.strip()) for item in modified_files)
    diff_has_markers = contains_diff_markers(git_diff)
    diff_record_semantically_sufficient = structured_diff_provenance_is_semantically_sufficient(
        diff_provenance_record,
        modified_files if isinstance(modified_files, list) else [],
        change_disposition=change_disposition,
    )
    if change_disposition == "already_satisfied":
        diff_semantically_sufficient = not bool(non_empty_string(git_diff)) and diff_record_semantically_sufficient
    else:
        diff_semantically_sufficient = (
            (
                bool(git_diff)
                and "diff --git" in git_diff
                and "@@" in git_diff
                and contains_patch_lines(git_diff)
                and diff_mentions_modified_files(git_diff, modified_files if isinstance(modified_files, list) else [])
            )
            or diff_record_semantically_sufficient
        )
    surfaces = attested_surfaces(modified_files, diff_provenance_record)
    artifact_identity_record = final.get("artifact_identity", {})
    baseline_identity = first_non_empty(args.baseline_identity, artifact_identity_record.get("baseline_identity", ""))
    execution_surface_identity = first_non_empty(
        args.execution_surface_identity,
        artifact_identity_record.get("execution_surface_identity", ""),
    )
    prompt_identity = first_non_empty(args.prompt_identity, artifact_identity_record.get("prompt_identity", ""))
    task_identity = first_non_empty(args.task_identity, artifact_identity_record.get("task_identity", ""))
    scope_task_text = first_non_empty(task_identity, prompt_identity)
    readback_semantically_sufficient = readback_is_semantically_sufficient(
        readback_text,
        surfaces,
        task_identity=scope_task_text,
    )
    scenario_semantically_sufficient = scenario_is_semantically_sufficient(scenario_text, task_identity=scope_task_text)
    verification_corroboration_semantically_sufficient = verification_corroboration_is_semantically_sufficient(
        structured_diff_sufficient=diff_record_semantically_sufficient,
        scenario_text=scenario_text,
    )
    scope_alignment_evaluated, scope_alignment_semantically_sufficient = scope_alignment_is_semantically_sufficient(
        change_disposition=change_disposition,
        git_diff=git_diff,
        diff_provenance_record=diff_provenance_record,
        task_identity_text=scope_task_text,
    )
    (
        presentation_alignment_evaluated,
        presentation_alignment_semantically_sufficient,
        suspicious_presentation_classes,
    ) = presentation_alignment_is_semantically_sufficient(
        change_disposition=change_disposition,
        git_diff=git_diff,
        diff_provenance_record=diff_provenance_record,
        task_identity_text=scope_task_text,
    )
    identity_values = [
        baseline_identity,
        execution_surface_identity,
        prompt_identity,
        task_identity,
    ]
    identity_fields_present = all(bool(value.strip()) for value in identity_values)
    identity_semantically_sufficient = identity_fields_present
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
            "change_disposition": change_disposition,
        },
        "modified_files": {
            "present": isinstance(modified_files, list),
            "count": len(modified_files) if isinstance(modified_files, list) else 0,
            "semantically_sufficient": modified_files_semantically_sufficient,
        },
        "scope_alignment": {
            "evaluated": scope_alignment_evaluated,
            "semantically_sufficient": scope_alignment_semantically_sufficient,
        },
        "presentation_alignment": {
            "evaluated": presentation_alignment_evaluated,
            "semantically_sufficient": presentation_alignment_semantically_sufficient,
            "suspicious_classes": suspicious_presentation_classes,
        },
        "diff_provenance": {
            "present": "git_diff" in final or "diff_provenance" in final,
            "non_empty": bool(git_diff),
            "has_diff_markers": diff_has_markers,
            "has_structured_record": isinstance(diff_provenance_record, dict),
            "structured_record_sufficient": diff_record_semantically_sufficient,
            "semantically_sufficient": diff_semantically_sufficient,
        },
        "verification_corroboration": {
            "semantically_sufficient": verification_corroboration_semantically_sufficient,
            "has_structured_runtime_verification": diff_record_semantically_sufficient,
            "scenario_has_explicit_command": scenario_has_explicit_command(scenario_text),
            "scenario_has_explicit_observation": scenario_has_explicit_observation(scenario_text),
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
            "baseline_identity": baseline_identity,
            "execution_surface_identity": execution_surface_identity,
            "prompt_identity": prompt_identity,
            "task_identity": task_identity,
            "from_final_result": isinstance(artifact_identity_record, dict) and any(
                bool(non_empty_string(artifact_identity_record.get(key, "")))
                for key in [
                    "baseline_identity",
                    "execution_surface_identity",
                    "prompt_identity",
                    "task_identity",
                ]
            ),
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

    if not identity_fields_present:
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
                "git_diff or structured diff_provenance evidence is present in the final result artifact"
                if bundle["diff_provenance"]["present"]
                else "git_diff or structured diff_provenance evidence is missing from the final result artifact"
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
            present=identity_fields_present,
            structurally_complete=identity_fields_present,
            why=(
                "baseline, surface, prompt, and task identity fields are all present from the current run or final result artifact"
                if identity_fields_present
                else "one or more identity fields are missing from the current run context and final result artifact"
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
        if scope_alignment_evaluated and not scope_alignment_semantically_sufficient:
            semantically_insufficient_sections.append("scope_alignment")
        if presentation_alignment_evaluated and not presentation_alignment_semantically_sufficient:
            semantically_insufficient_sections.append("presentation_alignment")
        if not diff_semantically_sufficient:
            semantically_insufficient_sections.append("diff_provenance")
        if not verification_corroboration_semantically_sufficient:
            semantically_insufficient_sections.append("verification_corroboration")
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
                (
                    "the run is truthfully marked already_satisfied, the modified-files list stays empty, and the attested surface is named through diff_provenance.changed_file"
                    if change_disposition == "already_satisfied" and modified_files_semantically_sufficient
                    else "the modified-files list names at least one concrete changed file"
                )
                if modified_files_semantically_sufficient
                else (
                    "already_satisfied runs must keep modified_files empty and still name the attested surface through diff_provenance.changed_file"
                    if change_disposition == "already_satisfied"
                    else "the modified-files list is empty, malformed, or does not name concrete changed files"
                )
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["modified_files"],
        ),
        semantic_trace_entry(
            section="scope_alignment",
            evaluated=not missing and scope_alignment_evaluated,
            semantically_sufficient=scope_alignment_semantically_sufficient,
            why=(
                "the task reads like an add-only request and the proof stays additive without rewriting adjacent existing lines"
                if scope_alignment_semantically_sufficient
                else "the task reads like an add-only request, but the proof shows adjacent rewrites or removals beyond the requested insertion"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["scope_alignment"],
        ),
        semantic_trace_entry(
            section="presentation_alignment",
            evaluated=not missing and presentation_alignment_evaluated,
            semantically_sufficient=presentation_alignment_semantically_sufficient,
            why=(
                "the task reads like a plain add-only request and the newly added surface stays visually plain without extra emphasis styling"
                if presentation_alignment_semantically_sufficient
                else (
                    "the task reads like a plain add-only request, but the newly added surface adds extra emphasis styling: "
                    + ", ".join(suspicious_presentation_classes)
                )
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["presentation_alignment"],
        ),
        semantic_trace_entry(
            section="diff_provenance",
            evaluated=not missing,
            semantically_sufficient=diff_semantically_sufficient,
            why=(
                (
                    "already_satisfied proof keeps git_diff empty and uses structured direct observation on the attested surface instead of inventing a patch"
                    if change_disposition == "already_satisfied"
                    else "git_diff or structured diff_provenance proves a concrete patch for the named modified files"
                )
                if diff_semantically_sufficient
                else (
                    "already_satisfied proof must keep git_diff empty and use structured observation with changed_file, observed_line, verification command, verification result, and provenance_note"
                    if change_disposition == "already_satisfied"
                    else "diff or provenance evidence is present but does not yet prove a concrete patch on the named files with patch markers or structured verification"
                )
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["diff_provenance"],
        ),
        semantic_trace_entry(
            section="verification_corroboration",
            evaluated=not missing,
            semantically_sufficient=verification_corroboration_semantically_sufficient,
            why=(
                "the proof includes explicit local verification evidence through structured provenance or a labeled scenario command and observed result"
                if verification_corroboration_semantically_sufficient
                else "the proof still leans on authored text without an explicit structured verification record or a labeled scenario command/result pair"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["verification_corroboration"],
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
                "baseline, surface, prompt, and task identity fields are all non-empty from the current run or final result artifact"
                if identity_semantically_sufficient
                else "identity fields are incomplete or empty in the current run context and final result artifact"
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
