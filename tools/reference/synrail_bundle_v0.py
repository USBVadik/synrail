#!/usr/bin/env python3
"""Minimal proof bundle assembler for Synrail."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import stat as stat_module
import subprocess
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, load_json_if_valid
except ImportError:
    from synrail_io_v0 import load_json, load_json_if_valid

try:
    from .synrail_path_scope_v0 import (
        ARTIFACT_SCOPE,
        DUAL_SCOPE,
        PathScopeValidationError,
        path_surface_violation,
        path_within_scope,
        validate_namespace_paths,
        validate_root_within_project,
    )
except ImportError:
    from synrail_path_scope_v0 import (
        ARTIFACT_SCOPE,
        DUAL_SCOPE,
        PathScopeValidationError,
        path_surface_violation,
        path_within_scope,
        validate_namespace_paths,
        validate_root_within_project,
    )


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
    "final_result_status": "state a trust-bearing final_result.status: use PROVEN for an evidenced modification run, or ALREADY_SATISFIED for a truthful no-op attestation",
    "readback": "record substantive readback from the changed sections on the attested surface",
    "scenario_proof": "record an explicit scenario-proof result for the attested target surface",
    "artifact_identity": "restore baseline, execution surface, prompt, and task identity values for this run",
    "cleanup_status": "record a successful cleanup status for the execution surface",
}

GENERIC_EXECUTION_STATUSES = {"SUCCESS", "COMPLETED", "DONE", "OK", "PASSED"}
VERIFICATION_RECHECK_ALLOWED_BINARIES = {"grep", "cat", "head", "tail", "git"}
VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10
VERIFICATION_RECHECK_STDOUT_LIMIT = 4096
PROJECT_ROOT = Path(__file__).resolve().parents[2]

BUNDLE_PATH_SCOPES = {
    "output": ARTIFACT_SCOPE,
    "state_file": ARTIFACT_SCOPE,
    "doctor_file": ARTIFACT_SCOPE,
    "final_result": DUAL_SCOPE,
    "readback": DUAL_SCOPE,
    "scenario_proof": DUAL_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_bundle_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=BUNDLE_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def direct_file_fingerprint(path: Path) -> tuple[int, int, int, int] | None:
    try:
        stat_result = path.stat(follow_symlinks=False)
    except OSError:
        return None
    if not stat_module.S_ISREG(stat_result.st_mode):
        return None
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def artifact_binding_entry(*, artifact_id: str, path: Path | None, required: bool) -> dict:
    present = bool(path and path.is_file())
    resolved_path = str(path.resolve()) if present else ""
    return {
        "artifact_id": artifact_id,
        "path": resolved_path,
        "required": required,
        "present": present,
        "sha256": file_sha256(path) if present else "",
    }


def build_closure_freshness_binding(
    *,
    final_path: Path | None,
    readback_path: Path | None,
    scenario_path: Path | None,
    doctor_path: Path | None,
) -> dict:
    return {
        "schema_version": "closure_freshness_binding_v0",
        "bound_at_utc": now_iso(),
        "artifacts": [
            artifact_binding_entry(artifact_id="final_result", path=final_path, required=True),
            artifact_binding_entry(artifact_id="readback", path=readback_path, required=False),
            artifact_binding_entry(artifact_id="scenario_proof", path=scenario_path, required=False),
            artifact_binding_entry(artifact_id="doctor", path=doctor_path, required=False),
        ],
    }


def starter_final_result_replacement_is_sanctioned(
    *,
    last_known_final_result_hash: str,
    starter_final_result_hash: str,
    current_final_result_hash: str,
) -> bool:
    return bool(
        last_known_final_result_hash
        and starter_final_result_hash
        and current_final_result_hash
        and last_known_final_result_hash == starter_final_result_hash
        and current_final_result_hash != starter_final_result_hash
    )


def normalize_verification_recheck_text(value: str, *, executable: str) -> str:
    normalized = value.rstrip("\n")
    if executable != "grep":
        return normalized
    lines: list[str] = []
    for line in normalized.splitlines():
        prefix, sep, rest = line.partition(":")
        lines.append(rest if sep and prefix.isdigit() else line)
    return "\n".join(lines)


def verification_recheck_result(record: object, *, project_root: Path | None = None) -> dict:
    recheck_root = (project_root or PROJECT_ROOT).resolve()
    result = {
        "required": False,
        "executed": False,
        "command_allowed": False,
        "matched": False,
        "stdout_snippet": "",
        "skip_reason": "",
    }
    if not isinstance(record, dict):
        result["skip_reason"] = "verification_missing"
        return result

    verification_command = non_empty_string(record.get("verification_command", ""))
    verification_result_raw = record.get("verification_result", "")
    verification_result = verification_result_raw if isinstance(verification_result_raw, str) else ""
    if not (verification_command and verification_result.strip()):
        result["skip_reason"] = "verification_missing"
        return result

    try:
        argv = shlex.split(verification_command)
    except ValueError:
        result["skip_reason"] = "command_parse_error"
        return result

    if not argv:
        result["skip_reason"] = "command_parse_error"
        return result

    executable = argv[0]
    if executable not in VERIFICATION_RECHECK_ALLOWED_BINARIES:
        result["skip_reason"] = "command_not_in_allowlist"
        return result

    result["command_allowed"] = True
    changed_file = non_empty_string(record.get("changed_file", ""))
    verified_changed_path: Path | None = None
    initial_changed_binding: tuple[int, int, int, int] | None = None
    if changed_file:
        changed_path = Path(changed_file)
        if not changed_path.is_absolute():
            changed_path = recheck_root / changed_path
        if not path_within_scope(str(changed_path), scope=DUAL_SCOPE, project_root=recheck_root, artifact_root=recheck_root / ".synrail"):
            result["skip_reason"] = "changed_file_out_of_scope"
            return result
        violation = path_surface_violation(
            str(changed_path),
            field="final_result",
            scope=DUAL_SCOPE,
            surface_label="verification recheck changed file",
            expected_surface="a direct in-scope verification surface",
            stop_at=recheck_root,
            project_root=recheck_root,
            artifact_root=recheck_root / ".synrail",
        )
        if violation is not None:
            result["skip_reason"] = "changed_file_symlink_surface"
            return result
        initial_changed_binding = direct_file_fingerprint(changed_path)
        if initial_changed_binding is None:
            result["skip_reason"] = "changed_file_missing"
            return result
        verified_changed_path = changed_path.resolve(strict=True)

    result["executed"] = True

    try:
        completed = subprocess.run(
            argv,
            check=False,
            capture_output=True,
            text=True,
            cwd=recheck_root,
            timeout=VERIFICATION_RECHECK_TIMEOUT_SECONDS,
        )
    except FileNotFoundError:
        result["skip_reason"] = "command_missing"
        return result
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        result["stdout_snippet"] = stdout[:VERIFICATION_RECHECK_STDOUT_LIMIT]
        result["skip_reason"] = "timeout"
        return result

    stdout = completed.stdout or ""
    normalized_stdout = normalize_verification_recheck_text(stdout, executable=executable)
    result["stdout_snippet"] = normalized_stdout[:VERIFICATION_RECHECK_STDOUT_LIMIT]

    normalized_expected = normalize_verification_recheck_text(verification_result, executable=executable)
    if verified_changed_path is not None and initial_changed_binding is not None:
        if not verified_changed_path.exists() or verified_changed_path.is_symlink():
            result["matched"] = False
            result["stdout_snippet"] = f"{normalized_expected}\n"[:VERIFICATION_RECHECK_STDOUT_LIMIT] if normalized_expected else ""
            result["skip_reason"] = "changed_file_changed_during_recheck"
            return result
        violation = path_surface_violation(
            str(verified_changed_path),
            field="final_result",
            scope=DUAL_SCOPE,
            surface_label="verification recheck changed file",
            expected_surface="a direct in-scope verification surface",
            stop_at=recheck_root,
            project_root=recheck_root,
            artifact_root=recheck_root / ".synrail",
        )
        if violation is not None or direct_file_fingerprint(verified_changed_path) != initial_changed_binding:
            result["matched"] = False
            result["stdout_snippet"] = f"{normalized_expected}\n"[:VERIFICATION_RECHECK_STDOUT_LIMIT] if normalized_expected else ""
            result["skip_reason"] = "changed_file_changed_during_recheck"
            return result
    result["matched"] = normalized_stdout == normalized_expected
    if not result["matched"] and completed.returncode != 0:
        result["skip_reason"] = f"exit_code_{completed.returncode}"
    return result


def aggregate_verification_recheck_results(results: list[dict]) -> dict:
    if not results:
        return {
            "required": False,
            "executed": False,
            "command_allowed": False,
            "matched": False,
            "stdout_snippet": "",
            "skip_reason": "verification_missing",
        }

    skip_reasons = [
        reason
        for result in results
        for reason in [non_empty_string(result.get("skip_reason", ""))]
        if reason
    ]
    first_stdout_snippet = next(
        (result.get("stdout_snippet", "") for result in results if result.get("stdout_snippet", "")),
        "",
    )
    return {
        "required": any(bool(result.get("required")) for result in results),
        "executed": all(bool(result.get("executed")) for result in results),
        "command_allowed": all(bool(result.get("command_allowed")) for result in results),
        "matched": all(bool(result.get("matched")) for result in results),
        "stdout_snippet": first_stdout_snippet,
        "skip_reason": skip_reasons[0] if skip_reasons else "",
        "record_count": len(results),
    }


def diff_provenance_records_from_final_result(final: dict) -> list[dict]:
    records: list[dict] = []
    diff_provenance = final.get("diff_provenance", {})
    if isinstance(diff_provenance, dict):
        if any(bool(non_empty_string(diff_provenance.get(key, ""))) for key in [
            "changed_file",
            "added_line",
            "removed_line",
            "observed_line",
            "verification_command",
            "verification_result",
        ]):
            records.append(diff_provenance)
    elif isinstance(diff_provenance, list):
        records.extend(value for value in diff_provenance if isinstance(value, dict))

    for key in ("diff_provenance_records", "per_file_diff_provenance", "per_file_diff_provenance_records"):
        value = final.get(key, [])
        if isinstance(value, list):
            records.extend(item for item in value if isinstance(item, dict))
    return records


def any_diff_provenance_verification_command_present(records: list[dict]) -> bool:
    return any(bool(non_empty_string(record.get("verification_command", ""))) for record in records)


def inferred_diff_provenance_method(records: list[dict], *, change_disposition: str) -> str:
    for record in records:
        method = normalized_diff_provenance_method(record, change_disposition=change_disposition)
        if method:
            return method
    return ""


def inferred_diff_provenance_method_inferred(records: list[dict], *, change_disposition: str) -> bool:
    for record in records:
        method = normalized_diff_provenance_method(record, change_disposition=change_disposition)
        if not method:
            continue
        return not bool(non_empty_string(record.get("method", "")))
    return False


def has_structured_diff_provenance_records(records: list[dict]) -> bool:
    return bool(records)


def primary_diff_provenance_record(records: list[dict]) -> dict:
    return records[0] if records else {}


def structured_diff_provenance_records_are_semantically_sufficient(
    records: list[dict],
    modified_files: list[str],
    *,
    change_disposition: str,
) -> bool:
    if change_disposition == "already_satisfied":
        return any(
            structured_diff_provenance_is_semantically_sufficient(
                record,
                modified_files,
                change_disposition=change_disposition,
            )
            for record in records
        )
    if not modified_files:
        return False
    for modified_file in modified_files:
        if not any(
            structured_diff_provenance_is_semantically_sufficient(
                record,
                [modified_file],
                change_disposition=change_disposition,
            )
            for record in records
        ):
            return False
    return True


def attested_surfaces_from_records(modified_files: object, records: list[dict]) -> list[str]:
    surfaces: list[str] = []
    if isinstance(modified_files, list):
        for item in modified_files:
            if isinstance(item, str) and item.strip():
                surfaces.append(item.strip())
    for record in records:
        changed_file = non_empty_string(record.get("changed_file", ""))
        if changed_file and changed_file not in surfaces:
            surfaces.append(changed_file)
    return surfaces


def verification_recheck_results(records: list[dict], *, project_root: Path | None = None) -> dict:
    return aggregate_verification_recheck_results(
        [verification_recheck_result(record, project_root=project_root) for record in records]
    )


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


def normalize_diff_path(value: str) -> str:
    path = value.strip().strip('"')
    if path in {"", "/dev/null"}:
        return ""
    if path.startswith(("a/", "b/")):
        path = path[2:]
    if path.startswith("./"):
        path = path[2:]
    return path


def normalized_modified_file_path(value: str) -> str:
    return normalize_diff_path(value)


def git_diff_patch_paths(value: str) -> list[str]:
    paths: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        candidates: list[str] = []
        if line.startswith("diff --git "):
            try:
                parts = shlex.split(line)
            except ValueError:
                parts = line.split()
            candidates.extend(parts[2:4])
        elif line.startswith("--- ") or line.startswith("+++ "):
            candidates.append(line[4:].strip())
        for candidate in candidates:
            normalized = normalize_diff_path(candidate)
            if normalized and normalized not in paths:
                paths.append(normalized)
    return paths


def git_diff_covers_modified_files(value: str, modified_files: list[str]) -> bool:
    expected_paths = [
        normalized_modified_file_path(path)
        for path in modified_files
        if isinstance(path, str) and normalized_modified_file_path(path)
    ]
    if not expected_paths:
        return False
    patch_paths = set(git_diff_patch_paths(value))
    if not patch_paths:
        return False
    return all(path in patch_paths for path in expected_paths)


def attested_surfaces(modified_files: object, record: object) -> list[str]:
    return attested_surfaces_from_records(modified_files, [record] if isinstance(record, dict) else [])


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


def load_json_object_if_present(path: Path) -> dict:
    if not path.exists():
        return {}
    ok, payload = load_json_if_valid(path)
    if not ok or not isinstance(payload, dict):
        return {}
    return payload


def state_bound_final_result_hashes(state_file: object) -> tuple[str, str]:
    state_file_text = non_empty_string(state_file)
    if not state_file_text:
        return "", ""
    state_path = Path(state_file_text)
    state_payload = load_json_object_if_present(state_path)
    last_known_hash = non_empty_string(state_payload.get("last_known_final_result_hash", ""))
    proof_request_payload = load_json_object_if_present(state_path.with_name("proof_request.json"))
    starter_hashes = proof_request_payload.get("starter_hashes", {})
    starter_hash = ""
    if isinstance(starter_hashes, dict):
        starter_hash = non_empty_string(starter_hashes.get("final_result", ""))
    return last_known_hash, starter_hash


def state_bound_project_root(state_file: object) -> Path:
    state_file_text = non_empty_string(state_file)
    if not state_file_text:
        return PROJECT_ROOT
    state_path = Path(state_file_text)
    project_profile = load_json_object_if_present(state_path.with_name("project_profile.json"))
    project_root = non_empty_string(project_profile.get("project_root", ""))
    if not project_root:
        return PROJECT_ROOT
    return Path(project_root).expanduser().resolve()


def first_non_empty(*values: object) -> str:
    for value in values:
        text = non_empty_string(value)
        if text:
            return text
    return ""


def normalized_final_result_status(value: object) -> str:
    text = non_empty_string(value)
    if not text:
        return ""
    return text.replace("-", "_").replace(" ", "_").upper()


def expected_final_result_status(change_disposition: str) -> str:
    if change_disposition == "already_satisfied":
        return "ALREADY_SATISFIED"
    return "PROVEN"


def final_result_status_is_semantically_sufficient(*, status: str, change_disposition: str) -> bool:
    return bool(status and status == expected_final_result_status(change_disposition))


def final_result_status_reason(*, status: str, change_disposition: str, semantically_sufficient: bool) -> str:
    expected = expected_final_result_status(change_disposition)
    if semantically_sufficient:
        if expected == "ALREADY_SATISFIED":
            return "final_result.status truthfully marks this run as ALREADY_SATISFIED for a no-op attestation"
        return "final_result.status truthfully marks this run as PROVEN for an evidenced modification run"
    if not status:
        return f"final_result.status is empty; use {expected} instead of a blank or decorative execution label"
    if status in GENERIC_EXECUTION_STATUSES:
        return f"final_result.status uses generic execution language ({status}) instead of the trust-bearing closure claim {expected}"
    if change_disposition == "already_satisfied":
        return f"final_result.status ({status}) does not match the trust-bearing closure claim {expected} for a truthful no-op attestation"
    return f"final_result.status ({status}) does not match the trust-bearing closure claim {expected} for an evidenced modification run"


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
    method = normalized_diff_provenance_method(record, change_disposition=change_disposition)
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
        has_observation = bool(observed_line)
        return bool(method and changed_file and changed_file_matches and has_verification and has_observation and provenance_note)
    has_patch_context = any([added_line, removed_line, context_before, context_after])
    return bool(method and changed_file and changed_file_matches and has_patch_context and has_verification)


def patch_plus_verification_is_semantically_sufficient(
    *,
    git_diff: str,
    record: object,
    modified_files: list[str],
    change_disposition: str,
) -> bool:
    if change_disposition == "already_satisfied":
        return False
    if not isinstance(record, dict):
        return False
    if not (
        bool(git_diff)
        and "diff --git" in git_diff
        and "@@" in git_diff
        and contains_patch_lines(git_diff)
        and git_diff_covers_modified_files(git_diff, modified_files)
    ):
        return False
    changed_file = non_empty_string(record.get("changed_file", ""))
    verification_command = non_empty_string(record.get("verification_command", ""))
    verification_result = non_empty_string(record.get("verification_result", ""))
    changed_file_matches = references_modified_file(changed_file, modified_files) if modified_files else bool(changed_file)
    return bool(changed_file and changed_file_matches and verification_command and verification_result)


def normalized_diff_provenance_method(record: object, *, change_disposition: str) -> str:
    if not isinstance(record, dict):
        return ""
    explicit_method = non_empty_string(record.get("method", ""))
    if explicit_method:
        return explicit_method
    changed_file = non_empty_string(record.get("changed_file", ""))
    verification_command = non_empty_string(record.get("verification_command", ""))
    verification_result = non_empty_string(record.get("verification_result", ""))
    if not (changed_file and verification_command and verification_result):
        return ""
    if change_disposition == "already_satisfied":
        observed_line = non_empty_string(record.get("observed_line", ""))
        provenance_note = non_empty_string(record.get("provenance_note", ""))
        if observed_line and provenance_note:
            return "direct_file_observation"
        return ""
    added_line = non_empty_string(record.get("added_line", ""))
    removed_line = non_empty_string(record.get("removed_line", ""))
    context_before = non_empty_string(record.get("context_before", ""))
    context_after = non_empty_string(record.get("context_after", ""))
    if any([added_line, removed_line, context_before, context_after]):
        return "direct_file_observation"
    return ""


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
    if not proof_meaningful or not task_meaningful:
        return False
    shared_words = proof_meaningful & task_meaningful
    overlap = len(shared_words) / len(proof_meaningful)
    task_coverage = len(shared_words) / len(task_meaningful)
    if overlap > 0.70:
        return True
    return task_coverage > 0.85 and not _has_concrete_identifier(proof_text)


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

_OBSERVATION_LABELS = ["observed", "confirmed", "verified"]
_SCENARIO_COMMAND_LABELS = ["command:", "cmd:"]
_SCENARIO_OBSERVED_LABELS = ["observed:", "result:", "output:"]
_STRICT_OBSERVATION_GUARD_TASK_CLASS_KEYWORDS = (
    "bounded_change",
    "proof_sensitive",
    "router_trigger_fix",
    "medium_risk",
    "restoration_guard",
)


_VACUOUS_OBSERVATION_PHRASES = [
    "looks good",
    "everything looks",
    "works correctly",
    "works as expected",
    "functioning properly",
    "processes correctly",
    "is now present",
    "is present",
    "present and correct",
    "available and correct",
    "verified successfully",
    "looks correct",
    "ready for use",
    "working as designed",
    "present and valid",
    "present and available",
    "exists as expected",
    "successfully updated",
    "successfully applied",
    "appears correct",
    "appears to be correct",
    "looks right",
    "is available now",
    "is ready",
    "has been verified",
    "confirmed ready",
    "confirmed available",
    "ready now",
    "verified and ready",
    "now available",
    "now ready",
    "verification passed",
    "available to use",
    "looks available",
    "ready for verification",
    "verified as ready",
    "ready and available",
    "is verified",
    "ready to use",
    "available and ready",
    "verified and available",
    "looks ready",
    "ready to proceed",
    "safe to proceed",
    "good to go",
    "appears ready",
    "verified in place",
    "verified on disk",
    "present on disk",
    "verified on the filesystem",
    "verified in file",
    "present in file",
    "verified in the file",
    "present in the file",
    "verified in the source",
    "present in the source",
    "verified in code",
    "present in code",
    "verified in the code",
    "present in the code",
    "verified in source",
    "present in source",
    "is in place",
    "change applied",
    "change is applied",
    "change completed",
    "has been applied",
    "has been made",
    "has been completed",
    "has been updated",
    "has been implemented",
    "was successful",
    "was completed",
    "is correct",
    "is working",
    "follows the expected",
    "as described",
    "as requested",
    "as intended",
    "done correctly",
    "done successfully",
]

_DIRECT_OBSERVATION_ANCHORS = (
    " contains ",
    " returns ",
    " imports ",
    " reads ",
    " shows ",
    " line ",
    " lines ",
    " function ",
    " class ",
    " appears ",
)

_THIN_SELF_DESCRIPTION_ANCHORS = (
    " contains ",
)

_NUMERIC_THIN_SELF_DESCRIPTION_CODE_MARKERS = (
    " import ",
    " function ",
    " class ",
    " handler ",
    " route ",
    " router ",
    " module ",
    " branch ",
    " endpoint ",
    " query ",
    " schema ",
    " table ",
    " column ",
    " hook ",
    " config ",
    " setting ",
)

_THIN_LOCATION_CLAIM_MARKERS = (
    " is ",
    " are ",
    " under ",
    " below ",
    " above ",
    " inside ",
    " within ",
    " near ",
)

_UNANCHORED_SEMANTIC_CLAIM_MARKERS = (
    " before ",
    " after ",
    " unless ",
    " when ",
    " while ",
    " applies ",
    " apply ",
    " enforces ",
    " enforce ",
    " routes ",
    " route ",
    " dispatches ",
    " dispatch ",
    " clamps ",
    " clamp ",
    " evaluates ",
    " evaluate ",
)


def _observation_line_is_unanchored_semantic_claim(line: str) -> bool:
    lowered = line.lower()
    for label in _OBSERVATION_LABELS:
        pos = lowered.find(label)
        if pos == -1:
            continue
        after = line[pos + len(label):].lstrip(":- \t")
        if not after:
            return False
        lowered_after = after.lower()
        has_line_number = any(ch.isdigit() for ch in lowered_after) and contains_any_keyword(lowered_after, ["line", ":"])
        has_quoted = "'" in after or '"' in after or "`" in after
        has_command_output_token = any(tok in after for tok in ["=>", "->", ">>>", "...", "\\n"])
        has_code_token = "(" in after or ")" in after
        if has_line_number or has_quoted or has_command_output_token or has_code_token:
            return False
        padded = f" {lowered_after} "
        if any(marker in padded for marker in _DIRECT_OBSERVATION_ANCHORS):
            return False
        return any(marker in padded for marker in _UNANCHORED_SEMANTIC_CLAIM_MARKERS)
    return False


def _observation_line_is_structured_but_thin_self_description(line: str, task_identity: str) -> bool:
    if not task_identity:
        return False
    lowered = line.lower()
    for label in _OBSERVATION_LABELS:
        pos = lowered.find(label)
        if pos == -1:
            continue
        after = line[pos + len(label):].lstrip(":- \t")
        if not after:
            return False
        lowered_after = after.lower()
        has_line_number = any(ch.isdigit() for ch in lowered_after) and contains_any_keyword(lowered_after, ["line", ":"])
        has_quoted = "'" in after or '"' in after or "`" in after
        has_command_output_token = any(tok in after for tok in ["=>", "->", ">>>", "...", "\\n"])
        has_code_token = "(" in after or ")" in after
        has_numeric = any(ch.isdigit() for ch in after)
        if has_line_number or has_quoted or has_command_output_token or has_code_token or has_numeric:
            return False
        padded = f" {lowered_after} "
        if not any(marker in padded for marker in _THIN_SELF_DESCRIPTION_ANCHORS):
            return False
        return _is_parroting_task(after, task_identity)
    return False


def _observation_line_is_numeric_thin_self_description(line: str, labels: tuple[str, ...]) -> bool:
    lowered = line.lower()
    for label in labels:
        pos = lowered.find(label)
        if pos == -1:
            continue
        after = line[pos + len(label):].lstrip(":- \t")
        if not after:
            return False
        lowered_after = after.lower()
        has_numeric = any(ch.isdigit() for ch in after)
        has_quoted = "'" in after or '"' in after or "`" in after
        has_command_output_token = any(tok in after for tok in ["=>", "->", ">>>", "...", "\\n"])
        has_code_token = any(tok in after for tok in ["(", ")", "<", ">", "{", "}", "[", "]", "="])
        if not has_numeric or has_quoted or has_command_output_token or has_code_token:
            return False
        padded = f" {lowered_after} "
        if " contains " not in padded:
            return False
        if not any(marker in padded for marker in _NUMERIC_THIN_SELF_DESCRIPTION_CODE_MARKERS):
            return False
        return True
    return False


def _observation_line_is_thin_line_or_location_claim(line: str, labels: tuple[str, ...]) -> bool:
    lowered = line.lower()

    def tail_has_literal_evidence(text: str) -> bool:
        stripped_tail = text.strip()
        if not stripped_tail:
            return False
        return (
            "'" in stripped_tail
            or '"' in stripped_tail
            or "`" in stripped_tail
            or any(tok in stripped_tail for tok in ["=>", "->", ">>>", "...", "\\n", "(", ")", "<", ">", "{", "}", "[", "]", "="])
        )

    for label in labels:
        pos = lowered.find(label)
        if pos == -1:
            continue
        after = line[pos + len(label):].lstrip(":- \t")
        if not after:
            return False
        lowered_after = after.lower()
        has_quoted = "'" in after or '"' in after or "`" in after
        has_command_output_token = any(tok in after for tok in ["=>", "->", ">>>", "...", "\\n"])
        has_code_token = any(tok in after for tok in ["(", ")", "<", ">", "{", "}", "[", "]", "="])
        if has_quoted or has_command_output_token or has_code_token:
            return False
        stripped = after.strip()
        if ":" in stripped:
            prefix, suffix = stripped.split(":", 1)
            if prefix.strip().isdigit() and suffix.strip():
                return False

        prefix = ""
        suffix = ""
        if lowered_after.startswith("line "):
            suffix = lowered_after[len("line "):]
        else:
            location_token = next((token for token in (" at line ", " on line ", " line ") if token in lowered_after), None)
            if location_token is None:
                return False
            prefix, suffix = lowered_after.split(location_token, 1)

        digit_prefix = ""
        for char in suffix:
            if char.isdigit():
                digit_prefix += char
                continue
            break
        if not digit_prefix:
            return False

        remainder = suffix[len(digit_prefix):].lstrip()
        if remainder.startswith(":") and remainder[1:].strip():
            colon_tail = remainder[1:].lstrip()
            if tail_has_literal_evidence(colon_tail):
                return False
            remainder = colon_tail

        padded_prefix = f" {prefix.strip()} "
        padded_remainder = f" {remainder.strip()} "

        line_numbered_reporting_verbs = (
            "show", "shows", "showed", "showing",
            "say", "says", "said", "saying",
            "mention", "mentions", "mentioned", "mentioning",
            "indicate", "indicates", "indicated", "indicating",
            "confirm", "confirms", "confirmed", "confirming",
            "note", "notes", "noted", "noting",
            "report", "reports", "reported", "reporting",
            "record", "records", "recorded", "recording",
            "document", "documents", "documented", "documenting",
            "describe", "describes", "described", "describing",
            "reflect", "reflects", "reflected", "reflecting",
            "capture", "captures", "captured", "capturing",
            "list", "lists", "listed", "listing",
            "present", "presents", "presented", "presenting",
            "carry", "carries", "carried", "carrying",
            "mark", "marks", "marked", "marking",
            "preserve", "preserves", "preserved", "preserving",
            "maintain", "maintains", "maintained", "maintaining",
            "keep", "keeps", "kept", "keeping",
            "set", "sets", "setting",
            "include", "includes", "included", "including",
            "display", "displays", "displayed", "displaying",
            "render", "renders", "rendered", "rendering",
            "hold", "holds", "holding",
            "store", "stores", "stored", "storing",
            "move", "moves", "moved", "moving",
            "place", "places", "placed", "placing",
            "put", "puts", "putting",
            "leave", "leaves", "leaving",
            "state", "states", "stated", "stating",
            "spell", "spells", "spelled", "spelling",
            "feature", "features", "featured", "featuring",
            "offer", "offers", "offered", "offering",
            "deliver", "delivers", "delivered", "delivering",
            "serve", "serves", "served", "serving",
            "surface", "surfaces", "surfaced", "surfacing",
            "expose", "exposes", "exposed", "exposing",
            "host", "hosts", "hosted", "hosting",
            "announce", "announces", "announced", "announcing",
            "signal", "signals", "signaled", "signaling",
            "convey", "conveys", "conveyed", "conveying",
            "relay", "relays", "relayed", "relaying",
            "reveal", "reveals", "revealed", "revealing",
            "highlight", "highlights", "highlighted", "highlighting",
            "spotlight", "spotlights", "spotlighted", "spotlighting",
            "showcase", "showcases", "showcased", "showcasing",
            "underline", "underlines", "underlined", "underlining",
            "read", "reads", "reading",
            "contain", "contains", "contained", "containing",
            "return", "returns", "returned", "returning",
            "import", "imports", "imported", "importing",
        )
        reporting_tail = next(
            (remainder[len(f"{verb} "):].lstrip() for verb in line_numbered_reporting_verbs if remainder.startswith(f"{verb} ")),
            "",
        )
        has_reporting_paraphrase = bool(reporting_tail) and not tail_has_literal_evidence(reporting_tail)

        line_numbered_paraphrase_verbs = (
            "add", "adds", "added", "adding",
            "update", "updates", "updated", "updating",
            "change", "changes", "changed", "changing",
            "fix", "fixes", "fixed", "fixing",
            "remove", "removes", "removed", "removing",
            "replace", "replaces", "replaced", "replacing",
            "modify", "modifies", "modified", "modifying",
        )
        has_action_paraphrase = any(
            remainder.startswith(f"{verb} ") or f" {verb} " in padded_remainder
            for verb in line_numbered_paraphrase_verbs
        )
        return (
            any(marker in padded_prefix for marker in _THIN_LOCATION_CLAIM_MARKERS)
            or any(marker in padded_remainder for marker in _THIN_LOCATION_CLAIM_MARKERS)
            or any(marker in padded_prefix for marker in _UNANCHORED_SEMANTIC_CLAIM_MARKERS)
            or any(marker in padded_remainder for marker in _UNANCHORED_SEMANTIC_CLAIM_MARKERS)
            or has_reporting_paraphrase
            or has_action_paraphrase
        )
    return False


def proof_sensitive_unseen_guard_enabled(task_class: str) -> bool:
    normalized = (task_class or "").strip().lower().replace("-", "_")
    return normalized in {
        "proof_sensitive_style_tweak",
        "proof_sensitive_copy_update",
        "proof_sensitive_router_adjustment",
        "proof_sensitive_billing_adjustment",
    }


def _strip_subject_prefix(text: str) -> str:
    """Strip common subject prefixes so action-verb detection works on passive/first-person forms.

    'i implemented ...'       → 'implemented ...'
    'the file was updated ...' → 'updated ...'
    'change was applied ...'   → 'applied ...'
    """
    # First person: "i ..."
    if text.startswith("i ") and len(text) > 2:
        return text[2:]
    # Passive with article: "the X was ..."
    if text.startswith("the "):
        was_pos = text.find(" was ")
        if was_pos != -1 and was_pos < 40:
            return text[was_pos + 5:]
        were_pos = text.find(" were ")
        if were_pos != -1 and were_pos < 40:
            return text[were_pos + 6:]
    # Passive without article: "X was ..."
    was_pos = text.find(" was ")
    if was_pos != -1 and was_pos < 30:
        return text[was_pos + 5:]
    return text


def _observation_line_is_vacuous(line: str) -> bool:
    """Return True if an observation-labeled line contains no substantive observation.

    Vacuous observations are generic success claims with no specific content.
    Example vacuous: "Observed: the change is now present in the source code."
    Example vacuous: "Confirmed: change applied."
    Example substantive: "Observed: line 2 now imports logging"
    Example substantive: "Observed: the template now contains a subtitle under the heading"
    """
    lowered = line.lower()
    for label in _OBSERVATION_LABELS:
        pos = lowered.find(label)
        if pos == -1:
            continue
        after = lowered[pos + len(label):].lstrip(":- \t")
        if not after:
            return True
        has_line_number = any(ch.isdigit() for ch in after) and contains_any_keyword(after, ["line", ":"])
        has_quoted = "'" in after or '"' in after or "`" in after
        has_command_output_token = any(tok in after for tok in ["=>", "->", ">>>", "...", "\\n"])
        if has_line_number or has_quoted or has_command_output_token:
            return False
        normalized_after = after.strip(" .,!?:;\t")
        if normalized_after in {"operational"}:
            return True
        # Vacuous if it matches known generic phrases
        for phrase in _VACUOUS_OBSERVATION_PHRASES:
            if phrase in after:
                return True
    return False


def _scenario_observation_lacks_evidence(line: str) -> bool:
    """Return True if a scenario Observed:/Result: line restates action without command-output evidence.

    A genuine scenario observation contains evidence from running a command: line numbers,
    quoted output, code tokens from stdout. A restatement just says what was done using
    action verbs, or makes a claim without any numeric or quoted evidence.

    Example lacking: "Observed: logging import added to src/app.py"
    Example lacking: "Result: logging import is in src/app.py"
    Example genuine: "Observed: line 2 shows 'import logging'"
    Example genuine: "Result: 2:import logging"
    """
    lowered = line.lower()
    for label in _SCENARIO_OBSERVED_LABELS:
        if not lowered.lstrip().startswith(label):
            continue
        # Result:/Output: lines should contain literal command output, not prose assertions
        # Trust them only if they don't look like prose assertions
        if label in ("result:", "output:"):
            after = lowered[lowered.index(label) + len(label):].lstrip()
            if not after:
                return True
            if after in {"ok", "okay", "pass", "passed", "success", "succeeded", "true"}:
                return True
            has_line_number = any(ch.isdigit() for ch in after) and contains_any_keyword(after, ["line", ":"])
            has_quoted = "'" in after or '"' in after or "`" in after
            has_command_output_token = any(tok in after for tok in ["=>", "->", ">>>", "...", "\\n"])
            has_code_token = "(" in after or ")" in after
            if has_line_number or has_quoted or has_command_output_token or has_code_token:
                return False
            # Prose assertions about what "is in" or "was found" are not command output
            if contains_any_keyword(after, ["is in ", "is present", "is there", "exists", "was found", "found in ", "found at ", "confirm", "confirmed"]):
                return True
            if " contains " in f" {after} ":
                return True
            if any(marker in f" {after} " for marker in _UNANCHORED_SEMANTIC_CLAIM_MARKERS):
                return True
            has_action = any(f" {verb} " in f" {after} " or after.startswith(verb) for verb in _ACTION_VERBS)
            if has_action:
                return True
            return False
        # Observed: lines describe what the agent saw — check for substance
        after = lowered[lowered.index(label) + len(label):].lstrip()
        if not after:
            return True
        has_line_number = any(ch.isdigit() for ch in after) and contains_any_keyword(after, ["line", ":"])
        has_quoted = "'" in after or '"' in after or "`" in after
        has_command_output_token = any(tok in after for tok in ["=>", "->", ">>>", "...", "\\n"])
        has_evidence = has_line_number or has_quoted or has_command_output_token
        # If there's concrete evidence (line numbers, quotes, output), it's a real observation
        if has_evidence:
            return False
        if contains_any_keyword(after, ["confirm", "confirmed", "exit code", "return code", "status code"]):
            return True
        if " contains " in f" {after} ":
            return True
        if any(marker in f" {after} " for marker in _UNANCHORED_SEMANTIC_CLAIM_MARKERS):
            return True
        # If action verbs present without evidence → restatement
        has_action = any(f" {verb} " in f" {after} " or after.startswith(verb) for verb in _ACTION_VERBS)
        if has_action:
            return True
        # If no action verbs and no evidence, check if it's just a plain assertion
        # (e.g. "logging import is in src/app.py") — lacks evidence of command output
        label_pos = lowered.index(label)
        after_text = line[label_pos + len(label):].lstrip()
        if after_text and not _has_concrete_identifier(after_text):
            return True
        # Has a concrete identifier but no evidence — check for known assertion patterns
        if contains_any_keyword(after, ["is in ", "is present", "is there", "exists", "was found"]):
            return True
        return False
    return False


def observation_guard_profile(task_class: str) -> str:
    """Return which observation heuristic profile applies to this task class.

    The stricter anti-narrative guard is intentionally limited to the proof-sensitive
    local change families we have already pressure-tested. New or unmeasured task
    classes should not inherit these hostile checks automatically.
    """
    normalized = (task_class or "").strip().lower().replace("-", "_")
    if any(keyword in normalized for keyword in _STRICT_OBSERVATION_GUARD_TASK_CLASS_KEYWORDS):
        return "STRICT_RUNTIME_EVIDENCE"
    return "BASELINE_OBSERVATION"


def strict_observation_guard_enabled(task_class: str) -> bool:
    return observation_guard_profile(task_class) == "STRICT_RUNTIME_EVIDENCE"


def broad_observation_guard_would_fire(task_class: str, line: str, task_identity: str = "") -> bool:
    if line_starts_with_any_label(line, _SCENARIO_OBSERVED_LABELS):
        return (
            _readback_line_is_action_narrative(line)
            or _observation_line_is_vacuous(line)
            or _observation_line_is_unanchored_semantic_claim(line)
            or _scenario_observation_lacks_evidence(line)
            or _observation_line_is_structured_but_thin_self_description(line, task_identity)
            or (
                proof_sensitive_unseen_guard_enabled(task_class)
                and _observation_line_is_thin_line_or_location_claim(line, tuple(_SCENARIO_OBSERVED_LABELS))
            )
        )
    if contains_any_keyword(line, _OBSERVATION_LABELS):
        return (
            _readback_line_is_action_narrative(line)
            or _observation_line_is_vacuous(line)
            or _observation_line_is_unanchored_semantic_claim(line)
            or _observation_line_is_structured_but_thin_self_description(line, task_identity)
            or _observation_line_is_numeric_thin_self_description(line, tuple(_OBSERVATION_LABELS))
            or (
                proof_sensitive_unseen_guard_enabled(task_class)
                and _observation_line_is_thin_line_or_location_claim(line, tuple(_OBSERVATION_LABELS))
            )
        )
    return False


def shadow_observation_guard_results(*, task_class: str, task_identity: str, readback_text: str, scenario_text: str) -> dict:
    readback_lines = [
        line for line in non_empty_lines(readback_text)
        if contains_any_keyword(line, _OBSERVATION_LABELS)
    ]
    scenario_lines = [
        line for line in non_empty_lines(scenario_text)
        if line_starts_with_any_label(line, _SCENARIO_OBSERVED_LABELS)
    ]
    flagged_readback = [
        line for line in readback_lines
        if broad_observation_guard_would_fire(task_class, line, task_identity)
    ]
    flagged_scenario = [
        line for line in scenario_lines
        if broad_observation_guard_would_fire(task_class, line, task_identity)
    ]
    return {
        "would_block": (
            (bool(readback_lines) and len(flagged_readback) == len(readback_lines))
            or (bool(scenario_lines) and len(flagged_scenario) == len(scenario_lines))
        ),
        "lines_flagged": len(flagged_readback) + len(flagged_scenario),
    }


def _readback_line_is_action_narrative(line: str) -> bool:
    """Return True if a line uses an observation label but contains action verbs.

    Example bad line: "Observed: Implemented compute_retry_delay with backoff"
    Example bad line: "Observed: I added the import to line 2"
    Example bad line: "Observed: the file was updated correctly"
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
        # Normalize subject prefixes for passive/first-person detection
        normalized = _strip_subject_prefix(after)
        # Check if the (possibly normalized) content starts with an action verb
        for verb in _ACTION_VERBS:
            if normalized.startswith(verb) and (
                len(normalized) == len(verb) or not normalized[len(verb)].isalpha()
            ):
                return True
    return False


def readback_is_semantically_sufficient(
    value: str,
    modified_files: list[str],
    task_identity: str = "",
    task_class: str = "bounded_change",
) -> bool:
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
    # Reject if every line with an observation label is action-narrative or vacuous
    observation_label_lines = [
        line for line in matching_lines
        if contains_any_keyword(line, _OBSERVATION_LABELS)
    ]
    if strict_observation_guard_enabled(task_class) and observation_label_lines and all(
        _readback_line_is_action_narrative(line)
        or _observation_line_is_vacuous(line)
        or _observation_line_is_unanchored_semantic_claim(line)
        or _observation_line_is_structured_but_thin_self_description(line, task_identity)
        or _observation_line_is_numeric_thin_self_description(line, tuple(_OBSERVATION_LABELS))
        or (
            proof_sensitive_unseen_guard_enabled(task_class)
            and _observation_line_is_thin_line_or_location_claim(line, tuple(_OBSERVATION_LABELS))
        )
        for line in observation_label_lines
    ):
        return False
    return True


def scenario_has_explicit_command(value: str) -> bool:
    return any(line_starts_with_any_label(line, _SCENARIO_COMMAND_LABELS) for line in non_empty_lines(value))


def scenario_has_explicit_observation(value: str) -> bool:
    return any(line_starts_with_any_label(line, _SCENARIO_OBSERVED_LABELS) for line in non_empty_lines(value))


def scenario_is_semantically_sufficient(
    value: str,
    task_identity: str = "",
    task_class: str = "bounded_change",
) -> bool:
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
    if not (has_context and has_outcome and has_specifics and has_explicit_command and has_explicit_observation):
        return False
    # Reject if every observation line is action-narrative, vacuous, or restates without evidence
    scenario_obs_lines = [
        line for line in lines
        if line_starts_with_any_label(line, _SCENARIO_OBSERVED_LABELS)
    ]
    if strict_observation_guard_enabled(task_class) and scenario_obs_lines and all(
        _readback_line_is_action_narrative(line)
        or _observation_line_is_vacuous(line)
        or _scenario_observation_lacks_evidence(line)
        or (
            proof_sensitive_unseen_guard_enabled(task_class)
            and _observation_line_is_thin_line_or_location_claim(line, tuple(_SCENARIO_OBSERVED_LABELS))
        )
        for line in scenario_obs_lines
    ):
        return False
    return True


def verification_corroboration_is_semantically_sufficient(
    *,
    runtime_verification_sufficient: bool,
    scenario_text: str,
    task_identity: str = "",
    task_class: str = "bounded_change",
) -> bool:
    if runtime_verification_sufficient:
        return True
    return scenario_is_semantically_sufficient(
        scenario_text,
        task_identity=task_identity,
        task_class=task_class,
    )


def readback_requirement_is_semantically_sufficient(
    *,
    readback_sufficient: bool,
    runtime_verification_sufficient: bool,
    final_result_status_sufficient: bool,
) -> tuple[bool, bool]:
    waived_by_runtime_corroboration = runtime_verification_sufficient and final_result_status_sufficient
    return readback_sufficient or waived_by_runtime_corroboration, waived_by_runtime_corroboration


def scenario_requirement_is_semantically_sufficient(
    *,
    scenario_sufficient: bool,
    runtime_verification_sufficient: bool,
    final_result_status_sufficient: bool,
) -> tuple[bool, bool]:
    waived_by_runtime_corroboration = runtime_verification_sufficient and final_result_status_sufficient
    return scenario_sufficient or waived_by_runtime_corroboration, waived_by_runtime_corroboration


def cleanup_requirement_is_semantically_sufficient(
    *,
    cleanup_sufficient: bool,
    runtime_verification_sufficient: bool,
    final_result_status_sufficient: bool,
    doctor_fallback_present: bool,
) -> tuple[bool, bool]:
    """Cleanup is waivable when runtime corroboration + doctor fallback already close trust."""
    waived_by_runtime_corroboration = (
        runtime_verification_sufficient
        and final_result_status_sufficient
        and doctor_fallback_present
    )
    return cleanup_sufficient or waived_by_runtime_corroboration, waived_by_runtime_corroboration


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


def cleanup_fallback_from_doctor(doctor_record: dict | None) -> dict:
    if not isinstance(doctor_record, dict):
        return {}
    final_verdict = non_empty_string(doctor_record.get("final_verdict", ""))
    gate_map = doctor_record.get("gates", {})
    if not isinstance(gate_map, dict) or not gate_map:
        gate_map = doctor_record.get("gate_results", {})
    clean_surface_gate = gate_map.get("clean_execution_surface", {}) if isinstance(gate_map, dict) else {}
    clean_surface_note = non_empty_string(clean_surface_gate.get("note", ""))
    if not final_verdict.startswith("ACCEPTABLE_"):
        return {}
    if clean_surface_gate.get("status", "") != "PASS":
        return {}
    summary = "workspace clean and execution surface acceptable for this run"
    if clean_surface_note and "clean" in clean_surface_note.lower():
        summary = clean_surface_note
    return {
        "success": True,
        "summary": summary,
        "source": "doctor",
    }


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
    doctor_present, doctor_path_str = file_present(getattr(args, "doctor_file", ""))
    doctor_path = Path(doctor_path_str) if doctor_path_str else None
    doctor_parseable, doctor = load_json_if_valid(doctor_path) if doctor_present else (False, {})

    modified_files = final.get("modified_files", [])
    git_diff = final.get("git_diff", "")
    diff_provenance_record = final.get("diff_provenance", {})
    diff_provenance_records = diff_provenance_records_from_final_result(final)
    cleanup_record = final.get("cleanup_status", {})
    cleanup_fallback = cleanup_fallback_from_doctor(doctor if doctor_parseable else {})
    explicit_cleanup_present = isinstance(cleanup_record, dict) and bool(cleanup_record)
    explicit_cleanup_semantically_sufficient = explicit_cleanup_present and cleanup_is_semantically_sufficient(cleanup_record)
    if explicit_cleanup_semantically_sufficient:
        cleanup = cleanup_record
    elif cleanup_fallback:
        cleanup = cleanup_fallback
    else:
        cleanup = cleanup_record if explicit_cleanup_present else {}
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
    normalized_status = normalized_final_result_status(final.get("status", ""))
    expected_status = expected_final_result_status(change_disposition)

    readback_present, readback_path = file_present(args.readback)
    scenario_present, scenario_path = file_present(args.scenario_proof)
    closure_freshness_binding = build_closure_freshness_binding(
        final_path=final_path,
        readback_path=Path(readback_path) if readback_present and readback_path else None,
        scenario_path=Path(scenario_path) if scenario_present and scenario_path else None,
        doctor_path=doctor_path if doctor_present and doctor_parseable else None,
    )

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
    git_diff_patch_paths_list = git_diff_patch_paths(git_diff)
    git_diff_covers_all_modified_files = git_diff_covers_modified_files(
        git_diff,
        modified_files if isinstance(modified_files, list) else [],
    )
    diff_record_semantically_sufficient = structured_diff_provenance_records_are_semantically_sufficient(
        diff_provenance_records,
        modified_files if isinstance(modified_files, list) else [],
        change_disposition=change_disposition,
    )
    primary_diff_record = primary_diff_provenance_record(diff_provenance_records)
    patch_plus_verification_semantically_sufficient = patch_plus_verification_is_semantically_sufficient(
        git_diff=git_diff,
        record=primary_diff_record,
        modified_files=modified_files if isinstance(modified_files, list) else [],
        change_disposition=change_disposition,
    )
    runtime_verification_semantically_sufficient = (
        diff_record_semantically_sufficient or patch_plus_verification_semantically_sufficient
    )
    normalized_diff_method = inferred_diff_provenance_method(
        diff_provenance_records,
        change_disposition=change_disposition,
    )
    diff_provenance_present = "git_diff" in final or bool(diff_provenance_records)
    diff_provenance_verification_command_present = any_diff_provenance_verification_command_present(diff_provenance_records)
    diff_provenance_structurally_complete = diff_provenance_present and (
        "diff_provenance" not in final
        or not isinstance(diff_provenance_record, dict)
        or diff_provenance_verification_command_present
        or bool(diff_provenance_records[1:])
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
                and git_diff_covers_all_modified_files
            )
            or diff_record_semantically_sufficient
        )
    surfaces = attested_surfaces_from_records(modified_files, diff_provenance_records)
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
        task_class=args.task_class,
    )
    scenario_semantically_sufficient = scenario_is_semantically_sufficient(
        scenario_text,
        task_identity=scope_task_text,
        task_class=args.task_class,
    )
    verification_corroboration_semantically_sufficient = verification_corroboration_is_semantically_sufficient(
        runtime_verification_sufficient=runtime_verification_semantically_sufficient,
        scenario_text=scenario_text,
        task_identity=scope_task_text,
        task_class=args.task_class,
    )
    shadow_observation_guard = shadow_observation_guard_results(
        task_class=args.task_class,
        task_identity=scope_task_text,
        readback_text=readback_text,
        scenario_text=scenario_text,
    )
    verification_recheck = verification_recheck_results(
        diff_provenance_records,
        project_root=state_bound_project_root(getattr(args, "state_file", "")),
    )
    verification_recheck["required"] = bool(runtime_verification_semantically_sufficient)
    final_result_status_semantically_sufficient = final_result_status_is_semantically_sufficient(
        status=normalized_status,
        change_disposition=change_disposition,
    )
    readback_requirement_semantically_sufficient, readback_waived_by_runtime_corroboration = (
        readback_requirement_is_semantically_sufficient(
            readback_sufficient=readback_semantically_sufficient,
            runtime_verification_sufficient=runtime_verification_semantically_sufficient,
            final_result_status_sufficient=final_result_status_semantically_sufficient,
        )
    )
    scenario_requirement_semantically_sufficient, scenario_waived_by_runtime_corroboration = (
        scenario_requirement_is_semantically_sufficient(
            scenario_sufficient=scenario_semantically_sufficient,
            runtime_verification_sufficient=runtime_verification_semantically_sufficient,
            final_result_status_sufficient=final_result_status_semantically_sufficient,
        )
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
    cleanup_present = ("cleanup_status" in final) or bool(cleanup_fallback)
    cleanup_content_semantically_sufficient = cleanup_present and cleanup_is_semantically_sufficient(cleanup)
    cleanup_requirement_sufficient, cleanup_waived_by_runtime_corroboration = (
        cleanup_requirement_is_semantically_sufficient(
            cleanup_sufficient=cleanup_content_semantically_sufficient,
            runtime_verification_sufficient=runtime_verification_semantically_sufficient,
            final_result_status_sufficient=final_result_status_semantically_sufficient,
            doctor_fallback_present=bool(cleanup_fallback),
        )
    )
    cleanup_semantically_sufficient = cleanup_requirement_sufficient
    final_request_id = (final.get("request_id", "") or "").strip()
    current_final_result_hash = file_sha256(final_path) if final_path and final_path.exists() else ""
    last_known_final_result_hash, starter_final_result_hash = state_bound_final_result_hashes(
        getattr(args, "state_file", "")
    )
    artifact_integrity_warning = bool(
        last_known_final_result_hash
        and current_final_result_hash
        and current_final_result_hash != last_known_final_result_hash
        and not starter_final_result_replacement_is_sanctioned(
            last_known_final_result_hash=last_known_final_result_hash,
            starter_final_result_hash=starter_final_result_hash,
            current_final_result_hash=current_final_result_hash,
        )
    )

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
            "normalized_status": normalized_status,
            "expected_status": expected_status,
            "semantically_sufficient": final_result_status_semantically_sufficient,
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
            "present": diff_provenance_present,
            "non_empty": bool(git_diff),
            "has_diff_markers": diff_has_markers,
            "has_structured_record": has_structured_diff_provenance_records(diff_provenance_records),
            "record_count": len(diff_provenance_records),
            "patch_paths": git_diff_patch_paths_list,
            "patch_covers_modified_files": git_diff_covers_all_modified_files,
            "normalized_method": normalized_diff_method,
            "method_inferred": inferred_diff_provenance_method_inferred(
                diff_provenance_records,
                change_disposition=change_disposition,
            ),
            "verification_command_present": diff_provenance_verification_command_present,
            "structurally_complete": diff_provenance_structurally_complete,
            "structured_record_sufficient": diff_record_semantically_sufficient,
            "semantically_sufficient": diff_semantically_sufficient,
        },
        "verification_corroboration": {
            "semantically_sufficient": verification_corroboration_semantically_sufficient,
            "has_structured_runtime_verification": diff_record_semantically_sufficient,
            "has_patch_runtime_verification": patch_plus_verification_semantically_sufficient,
            "runtime_verification_sufficient": runtime_verification_semantically_sufficient,
            "scenario_has_explicit_command": scenario_has_explicit_command(scenario_text),
            "scenario_has_explicit_observation": scenario_has_explicit_observation(scenario_text),
        },
        "shadow_observation_guard_results": shadow_observation_guard,
        "verification_recheck": verification_recheck,
        "artifact_integrity_warning": artifact_integrity_warning,
        "closure_freshness_binding": closure_freshness_binding,
        "readback": {
            "present": readback_present,
            "path": readback_path,
            "non_empty": bool(readback_text),
            "content_semantically_sufficient": readback_semantically_sufficient,
            "waived_by_runtime_corroboration": readback_waived_by_runtime_corroboration,
            "structurally_complete": readback_present or readback_waived_by_runtime_corroboration,
            "semantically_sufficient": readback_requirement_semantically_sufficient,
        },
        "scenario_proof": {
            "present": scenario_present,
            "path": scenario_path,
            "non_empty": bool(scenario_text),
            "content_semantically_sufficient": scenario_semantically_sufficient,
            "waived_by_runtime_corroboration": scenario_waived_by_runtime_corroboration,
            "structurally_complete": scenario_present or scenario_waived_by_runtime_corroboration,
            "semantically_sufficient": scenario_requirement_semantically_sufficient,
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
            "present": cleanup_present,
            "success": bool(cleanup.get("success", False)),
            "from_doctor": bool(cleanup_fallback) and not explicit_cleanup_semantically_sufficient,
            "content_semantically_sufficient": cleanup_content_semantically_sufficient,
            "waived_by_runtime_corroboration": cleanup_waived_by_runtime_corroboration,
            "structurally_complete": cleanup_present or cleanup_waived_by_runtime_corroboration,
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
    if not bundle["diff_provenance"]["structurally_complete"]:
        missing.append("diff_provenance")
    if not bundle["readback"]["present"] and not readback_waived_by_runtime_corroboration:
        missing.append("readback")
    if not bundle["scenario_proof"]["present"] and not scenario_waived_by_runtime_corroboration:
        missing.append("scenario_proof")

    if not identity_fields_present:
        missing.append("artifact_identity")
    if not bundle["cleanup_status"]["present"] and not cleanup_waived_by_runtime_corroboration:
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
            structurally_complete=bundle["diff_provenance"]["structurally_complete"],
            why=(
                "git_diff or structured diff_provenance evidence is present in the final result artifact"
                if bundle["diff_provenance"]["structurally_complete"]
                else (
                    "structured diff_provenance is present but verification_command is missing from the final result artifact"
                    if bundle["diff_provenance"]["present"]
                    else "git_diff or structured diff_provenance evidence is missing from the final result artifact"
                )
            ),
        ),
        structural_trace_entry(
            section="readback",
            present=bundle["readback"]["present"],
            structurally_complete=bundle["readback"]["structurally_complete"],
            why=(
                (
                    "readback evidence file is present"
                    if bundle["readback"]["present"]
                    else "readback evidence file is missing, but structured runtime corroboration already covers the trust-bearing contour so readback is optional on this run"
                )
                if bundle["readback"]["structurally_complete"]
                else "readback evidence file is missing"
            ),
        ),
        structural_trace_entry(
            section="scenario_proof",
            present=bundle["scenario_proof"]["present"],
            structurally_complete=bundle["scenario_proof"]["structurally_complete"],
            why=(
                (
                    "scenario-proof evidence file is present"
                    if bundle["scenario_proof"]["present"]
                    else "scenario-proof evidence file is missing, but structured runtime corroboration already covers the trust-bearing contour so scenario proof is optional on this run"
                )
                if bundle["scenario_proof"]["structurally_complete"]
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
            structurally_complete=bundle["cleanup_status"]["structurally_complete"],
            why=(
                (
                    "cleanup status is present in the final result artifact"
                    if explicit_cleanup_semantically_sufficient
                    else (
                        "cleanup status is satisfied by the current doctor-ready workspace"
                        if bundle["cleanup_status"]["from_doctor"]
                        else "cleanup status is waived because structured runtime corroboration and doctor context already close the trust decision"
                    )
                )
                if bundle["cleanup_status"]["structurally_complete"]
                else "cleanup status is missing from the final result artifact and current doctor context"
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
        if not readback_requirement_semantically_sufficient:
            semantically_insufficient_sections.append("readback")
        if not scenario_requirement_semantically_sufficient:
            semantically_insufficient_sections.append("scenario_proof")
        if not identity_semantically_sufficient:
            semantically_insufficient_sections.append("artifact_identity")
        if not cleanup_semantically_sufficient:
            semantically_insufficient_sections.append("cleanup_status")
        if not final_result_status_semantically_sufficient:
            semantically_insufficient_sections.append("final_result_status")

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
            section="final_result_status",
            evaluated=not missing,
            semantically_sufficient=final_result_status_semantically_sufficient,
            why=final_result_status_reason(
                status=normalized_status,
                change_disposition=change_disposition,
                semantically_sufficient=final_result_status_semantically_sufficient,
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["final_result_status"],
        ),
        semantic_trace_entry(
            section="readback",
            evaluated=not missing,
            semantically_sufficient=readback_requirement_semantically_sufficient,
            why=(
                (
                    "readback evidence names the changed surface and records an observed property of it"
                    if readback_semantically_sufficient
                    else "structured runtime corroboration already closes the trust decision, so readback stays fallback-only instead of blocking acceptance on this run"
                )
                if readback_requirement_semantically_sufficient
                else "readback evidence does not yet name the changed surface with a concrete observed property, and the bundle still needs that blocker-specific fallback evidence because runtime corroboration is not yet strong enough to waive it"
            ),
            recommended_action=SEMANTIC_SECTION_STEPS["readback"],
        ),
        semantic_trace_entry(
            section="scenario_proof",
            evaluated=not missing,
            semantically_sufficient=scenario_requirement_semantically_sufficient,
            why=(
                (
                    "scenario-proof evidence records a concrete scenario context and outcome"
                    if scenario_semantically_sufficient
                    else "structured runtime corroboration already closes the trust decision, so scenario proof stays fallback-only instead of blocking acceptance on this run"
                )
                if scenario_requirement_semantically_sufficient
                else "scenario-proof evidence does not yet record a concrete scenario context and outcome, and the bundle still needs that blocker-specific fallback verification because runtime corroboration is not yet strong enough to waive it"
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
                (
                    "cleanup status reports success with an explicit clean-surface summary"
                    if explicit_cleanup_semantically_sufficient
                    else (
                        "waived: runtime verification and doctor fallback already close trust on cleanup"
                        if cleanup_waived_by_runtime_corroboration
                        else "doctor already reports an acceptable clean execution surface for this run"
                    )
                )
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
    parser.add_argument("--doctor-file")
    parser.add_argument("--state-file")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        artifact_root = Path(args.output).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "output",
            args.output,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_bundle_paths(args, artifact_root=artifact_root, project_root=project_root)
        bundle = build_bundle(args)
        out = Path(args.output)
        out.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
        print(json.dumps({"result": "OK", "status": bundle["status"]}, ensure_ascii=True))
        return 0
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
