#!/usr/bin/env python3
"""Fail-closed proof recording for small tracked change sets."""

from __future__ import annotations

import hashlib
import json
import shlex
from pathlib import Path

try:
    from .synrail_bundle_v0 import (
        VERIFICATION_RECHECK_STDOUT_LIMIT,
        git_diff_patch_paths,
        verification_recheck_result,
    )
    from .synrail_io_v0 import load_json, save_json
    from .synrail_path_scope_v0 import (
        PROJECT_SCOPE,
        path_in_root,
        path_surface_violation,
    )
    from .synrail_safe_git_v0 import SafeGitError, run_safe_git
except ImportError:
    from synrail_bundle_v0 import (
        VERIFICATION_RECHECK_STDOUT_LIMIT,
        git_diff_patch_paths,
        verification_recheck_result,
    )
    from synrail_io_v0 import load_json, save_json
    from synrail_path_scope_v0 import (
        PROJECT_SCOPE,
        path_in_root,
        path_surface_violation,
    )
    from synrail_safe_git_v0 import SafeGitError, run_safe_git


MAX_GIT_DIFF_BYTES = 256_000
MAX_BATCH_FILES = 32
CAPTURE_PROBE_RESULT = "__SYNRAIL_CAPTURE_PROBE_RESULT__"
TERMINAL_RUN_STATES = {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}


class ProofRecordError(ValueError):
    def __init__(self, reason: str, detail: str, next_step: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail
        self.next_step = next_step

    def as_payload(self) -> dict:
        return {
            "result": "ERROR",
            "reason": self.reason,
            "detail": self.detail,
            "next_step": self.next_step,
            "accepted": False,
            "closure_evaluated": False,
        }


def _run_git(project_root: Path, args: list[str]) -> str:
    try:
        completed = run_safe_git(project_root, args)
    except SafeGitError as exc:
        raise ProofRecordError(
            exc.reason,
            exc.detail,
            "Install git or strengthen final_result.json manually with structured provenance.",
        ) from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "git inspection failed").strip()
        raise ProofRecordError(
            "GIT_INSPECTION_FAILED",
            detail,
            "Run git status from the target repository and fix the repository state before retrying.",
        )
    return completed.stdout


def _control_artifact_path(
    path: str,
    *,
    project_root: Path,
    artifact_root: Path | None,
) -> bool:
    normalized = path.replace("\\", "/")
    if artifact_root is None or not path_in_root(artifact_root.resolve(), project_root):
        return False
    relative_artifact_root = artifact_root.resolve().relative_to(project_root).as_posix()
    return normalized == relative_artifact_root or normalized.startswith(relative_artifact_root + "/")


def _changed_git_paths(project_root: Path, *, artifact_root: Path | None = None) -> list[str]:
    tracked = _run_git(
        project_root,
        ["diff", "--no-ext-diff", "--name-only", "-z", "HEAD", "--"],
    ).split("\0")
    untracked = _run_git(
        project_root,
        ["ls-files", "-z", "--others", "--exclude-standard"],
    ).split("\0")
    return sorted(
        {
            value.replace("\\", "/")
            for value in [*tracked, *untracked]
            if value
            and not _control_artifact_path(
                value,
                project_root=project_root,
                artifact_root=artifact_root,
            )
        }
    )


def capture_record_baseline(*, project_root: Path, artifact_root: Path) -> dict:
    try:
        head = _run_git(project_root, ["rev-parse", "HEAD"]).strip()
        dirty_paths = _changed_git_paths(project_root, artifact_root=artifact_root)
    except ProofRecordError as exc:
        return {
            "status": "unavailable",
            "reason": exc.reason,
            "git_head": "",
            "dirty_paths": [],
        }
    return {
        "status": "captured",
        "reason": "",
        "git_head": head,
        "dirty_paths": dirty_paths,
    }


def _validated_changed_file(project_root: Path, changed_file: str) -> tuple[Path, str]:
    raw = Path(changed_file).expanduser()
    if raw.is_absolute():
        raise ProofRecordError(
            "CHANGED_FILE_MUST_BE_RELATIVE",
            "record accepts a repository-relative changed file, not an absolute path.",
            "Pass the path shown by git status relative to the target repository root.",
        )
    candidate = project_root / raw
    violation = path_surface_violation(
        str(candidate),
        field="changed_file",
        scope=PROJECT_SCOPE,
        surface_label="record changed file",
        expected_surface="a direct regular file inside the target repository",
        stop_at=project_root,
        project_root=project_root,
        artifact_root=None,
    )
    if violation is not None:
        raise ProofRecordError(
            "CHANGED_FILE_SYMLINK_SURFACE",
            violation.detail,
            "Use a direct non-symlink file inside the target repository.",
        )
    try:
        resolved = candidate.resolve(strict=True)
    except FileNotFoundError as exc:
        raise ProofRecordError(
            "CHANGED_FILE_MISSING",
            "The named changed file does not exist.",
            "Pass one existing tracked file changed by this bounded run.",
        ) from exc
    if not path_in_root(resolved, project_root) or not resolved.is_file():
        raise ProofRecordError(
            "CHANGED_FILE_OUT_OF_SCOPE",
            "The named surface is not a regular file inside the target repository.",
            "Pass one existing tracked file changed by this bounded run.",
        )
    return resolved, resolved.relative_to(project_root).as_posix()


def _capture_git_patch(project_root: Path, relative_file: str) -> str:
    patch = _run_git(
        project_root,
        ["diff", "HEAD", "--", relative_file],
    )
    if not patch.strip() or "diff --git " not in patch or "@@" not in patch:
        raise ProofRecordError(
            "TRACKED_PATCH_REQUIRED",
            "The thin record path could not find a real HEAD-to-worktree patch for this file.",
            "Use record only for one tracked modified file; use the manual structured-provenance path for untracked, deleted, or no-op work.",
        )
    if len(patch.encode("utf-8")) > MAX_GIT_DIFF_BYTES:
        raise ProofRecordError(
            "PATCH_TOO_LARGE_FOR_THIN_RECORD",
            "The single-file patch exceeds the 256 KB thin-record boundary.",
            "Use the manual proof path so the large change remains explicit and reviewable.",
        )
    return patch


def _capture_worktree_patch(project_root: Path) -> str:
    patch = _run_git(project_root, ["diff", "HEAD", "--"])
    if not patch.strip() or "diff --git " not in patch or "@@" not in patch:
        raise ProofRecordError(
            "TRACKED_PATCH_REQUIRED",
            "The record path could not find a real HEAD-to-worktree patch for the active change set.",
            "Use record only for tracked modified files; use the manual proof path for untracked, deleted, binary, or no-op work.",
        )
    if len(patch.encode("utf-8")) > MAX_GIT_DIFF_BYTES:
        raise ProofRecordError(
            "PATCH_TOO_LARGE_FOR_THIN_RECORD",
            "The active change-set patch exceeds the 256 KB record boundary.",
            "Split the task into smaller bounded runs or use the manual proof path so the large change remains explicit and reviewable.",
        )
    return patch


def _file_fingerprint(path: Path) -> tuple[int, int, int, int, str]:
    stat = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, digest.hexdigest())


def _capture_verification(
    *,
    project_root: Path,
    relative_file: str,
    verification_command: str,
) -> str:
    probe = verification_recheck_result(
        {
            "changed_file": relative_file,
            "verification_command": verification_command,
            "verification_result": CAPTURE_PROBE_RESULT,
        },
        project_root=project_root,
    )
    skip_reason = str(probe.get("skip_reason", "") or "")
    if not probe.get("command_allowed") or not probe.get("executed") or skip_reason:
        raise ProofRecordError(
            "VERIFICATION_COMMAND_NOT_RECHECKABLE",
            f"The existing closure recheck policy rejected the command: {skip_reason or 'command_not_executed'}.",
            "Use one repo-relative grep, cat, head, tail, or supported git diff/show/log command against the changed file.",
        )
    output = str(probe.get("stdout_snippet", "") or "")
    if not output.strip():
        raise ProofRecordError(
            "VERIFICATION_OUTPUT_EMPTY",
            "The verification command completed but produced no observable stdout.",
            "Use a recheckable command that prints concrete evidence for the changed file.",
        )
    if len(output) >= VERIFICATION_RECHECK_STDOUT_LIMIT:
        raise ProofRecordError(
            "VERIFICATION_OUTPUT_TOO_LARGE",
            "The verification output reached the closure recheck capture limit.",
            "Use a narrower grep, head, or tail command that prints only the relevant evidence.",
        )
    return output


def _active_record_context(
    *,
    artifact_root: Path,
    project_root: Path,
    summary: str,
) -> tuple[dict, str]:
    state_path = artifact_root / "state.json"
    profile_path = artifact_root / "project_profile.json"
    if not state_path.is_file() or not profile_path.is_file():
        raise ProofRecordError(
            "CONTROLLED_RUN_REQUIRED",
            "record needs an active Synrail run and its project profile.",
            "Run synrail start first, then make one bounded tracked-file change.",
        )

    try:
        state = load_json(state_path)
        profile = load_json(profile_path)
    except (OSError, json.JSONDecodeError) as exc:
        raise ProofRecordError(
            "ACTIVE_RUN_ARTIFACT_UNREADABLE",
            "The active state or project profile is not readable valid JSON.",
            "Repair or remove the broken artifact root, then start a fresh bounded run.",
        ) from exc
    profile_root_text = str(profile.get("project_root", "") or "").strip()
    if not profile_root_text or Path(profile_root_text).expanduser().resolve() != project_root:
        raise ProofRecordError(
            "PROJECT_ROOT_MISMATCH",
            "The requested project root does not match the active controlled run.",
            "Use the same --project-root and artifact mode used by synrail start.",
        )
    if str(state.get("state", "") or "") in TERMINAL_RUN_STATES:
        raise ProofRecordError(
            "RUN_ALREADY_TERMINAL",
            "The active run has already reached a terminal closure state.",
            "Start a new bounded run before recording proof for another change.",
        )

    baseline = profile.get("thin_record_baseline", {})
    if not isinstance(baseline, dict) or baseline.get("status") != "captured":
        raise ProofRecordError(
            "THIN_RECORD_BASELINE_UNAVAILABLE",
            "The active run does not carry a usable clean-start git baseline.",
            "Start a fresh run in a git repository or use the manual proof path.",
        )
    dirty_at_start = baseline.get("dirty_paths", [])
    if not isinstance(dirty_at_start, list) or dirty_at_start:
        detail = ", ".join(str(path) for path in dirty_at_start) if isinstance(dirty_at_start, list) else "invalid baseline"
        raise ProofRecordError(
            "CLEAN_START_REQUIRED",
            "The record path cannot separate this run from files that were already dirty at start: " + detail,
            "Commit, stash, or otherwise isolate the pre-existing work, then start a fresh run; otherwise use explicit manual proof.",
        )
    current_head = _run_git(project_root, ["rev-parse", "HEAD"]).strip()
    if not current_head or current_head != str(baseline.get("git_head", "") or ""):
        raise ProofRecordError(
            "GIT_HEAD_CHANGED_DURING_RUN",
            "The repository HEAD changed after the controlled run started.",
            "Start a fresh run against the current revision before recording thin proof.",
        )

    cleaned_summary = summary.strip()
    if len(cleaned_summary) < 24:
        raise ProofRecordError(
            "SUMMARY_TOO_THIN",
            "The proof summary must contain at least 24 non-whitespace characters.",
            "Describe the concrete bounded result rather than writing a generic done claim.",
        )
    return state, cleaned_summary


def _batch_verification_command(relative_file: str) -> str:
    return "git diff --numstat HEAD -- " + shlex.quote(relative_file)


def _artifact_root_relative_to_project(*, artifact_root: Path, project_root: Path) -> str:
    try:
        return artifact_root.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return ""


def record_single_file_proof(
    *,
    artifact_root: Path,
    project_root: Path,
    changed_file: str,
    summary: str,
    verification_command: str,
) -> dict:
    artifact_root = artifact_root.resolve()
    project_root = project_root.resolve()
    state, cleaned_summary = _active_record_context(
        artifact_root=artifact_root,
        project_root=project_root,
        summary=summary,
    )

    resolved_file, relative_file = _validated_changed_file(project_root, changed_file)
    initial_fingerprint = _file_fingerprint(resolved_file)
    changed_paths = _changed_git_paths(project_root, artifact_root=artifact_root)
    if changed_paths != [relative_file]:
        raise ProofRecordError(
            "SINGLE_FILE_SCOPE_REQUIRED",
            "The thin record path requires exactly one changed file, but git observed: "
            + (", ".join(changed_paths) if changed_paths else "no changed files"),
            "Keep this run to one tracked file or use the manual multi-file proof path.",
        )

    patch = _capture_git_patch(project_root, relative_file)
    verification_result = _capture_verification(
        project_root=project_root,
        relative_file=relative_file,
        verification_command=verification_command.strip(),
    )
    final_resolved_file, final_relative_file = _validated_changed_file(project_root, relative_file)
    final_patch = _capture_git_patch(project_root, relative_file)
    final_changed_paths = _changed_git_paths(project_root, artifact_root=artifact_root)
    if (
        final_relative_file != relative_file
        or final_resolved_file != resolved_file
        or _file_fingerprint(final_resolved_file) != initial_fingerprint
        or final_patch != patch
        or final_changed_paths != [relative_file]
    ):
        raise ProofRecordError(
            "WORKTREE_CHANGED_DURING_RECORD",
            "The changed file, its git patch, or the surrounding dirty-file scope changed while Synrail was recording proof.",
            "Stop concurrent edits, inspect the live diff, and rerun record.",
        )
    payload = {
        "request_id": str(state.get("run_id", "") or ""),
        "task_class": str(state.get("task_class", "") or "bounded_change"),
        "status": "PROVEN",
        "change_disposition": "modified",
        "summary": cleaned_summary,
        "modified_files": [relative_file],
        "git_diff": patch,
        "diff_provenance": {
            "method": "git_patch_plus_recheck",
            "changed_file": relative_file,
            "verification_command": verification_command.strip(),
            "verification_result": verification_result,
        },
        "_synrail": {
            "recorded_by": "synrail record",
            "patch_sha256": hashlib.sha256(patch.encode("utf-8")).hexdigest(),
            "acceptance_evaluated": False,
        },
    }
    output_path = artifact_root / "final_result.json"
    save_json(output_path, payload)
    return {
        "result": "PROOF_RECORDED",
        "accepted": False,
        "closure_evaluated": False,
        "artifact_root": str(artifact_root),
        "project_root": str(project_root),
        "final_result": str(output_path),
        "changed_file": relative_file,
        "verification_command": verification_command.strip(),
        "verification_result": verification_result,
        "patch_sha256": payload["_synrail"]["patch_sha256"],
    }


def record_all_modified_proof(
    *,
    artifact_root: Path,
    project_root: Path,
    summary: str,
) -> dict:
    """Record per-file proof for the complete clean-start tracked change set."""
    artifact_root = artifact_root.resolve()
    project_root = project_root.resolve()
    state, cleaned_summary = _active_record_context(
        artifact_root=artifact_root,
        project_root=project_root,
        summary=summary,
    )

    changed_paths = _changed_git_paths(project_root, artifact_root=artifact_root)
    if not changed_paths:
        raise ProofRecordError(
            "BATCH_SCOPE_REQUIRED",
            "The batch record path needs at least one tracked changed file in the active worktree.",
            "Make the bounded tracked changes first, then rerun synrail record --all-modified.",
        )
    if len(changed_paths) > MAX_BATCH_FILES:
        raise ProofRecordError(
            "BATCH_TOO_LARGE_FOR_THIN_RECORD",
            f"The batch record path is limited to {MAX_BATCH_FILES} changed files; this run has {len(changed_paths)}.",
            "Split the work into smaller bounded runs or use the manual proof path for the larger change set.",
        )

    captured: list[dict[str, object]] = []
    for changed_path in changed_paths:
        resolved_file, relative_file = _validated_changed_file(project_root, changed_path)
        patch = _capture_git_patch(project_root, relative_file)
        verification_command = _batch_verification_command(relative_file)
        verification_result = _capture_verification(
            project_root=project_root,
            relative_file=relative_file,
            verification_command=verification_command,
        )
        captured.append(
            {
                "resolved_file": resolved_file,
                "relative_file": relative_file,
                "fingerprint": _file_fingerprint(resolved_file),
                "patch": patch,
                "verification_command": verification_command,
                "verification_result": verification_result,
            }
        )

    expected_paths = [str(item["relative_file"]) for item in captured]
    recorded_worktree_patch = _capture_worktree_patch(project_root)
    if sorted(git_diff_patch_paths(recorded_worktree_patch)) != expected_paths:
        raise ProofRecordError(
            "BATCH_SCOPE_REQUIRED",
            "The full tracked patch does not match the complete changed-file set observed by Synrail.",
            "Stop concurrent edits, inspect git status, and rerun synrail record --all-modified.",
        )

    final_changed_paths = _changed_git_paths(project_root, artifact_root=artifact_root)
    final_worktree_patch = _capture_worktree_patch(project_root)
    stable = (
        final_changed_paths == expected_paths
        and final_worktree_patch == recorded_worktree_patch
        and sorted(git_diff_patch_paths(final_worktree_patch)) == expected_paths
    )
    for item in captured:
        relative_file = str(item["relative_file"])
        resolved_file = item["resolved_file"]
        final_resolved_file, final_relative_file = _validated_changed_file(project_root, relative_file)
        final_patch = _capture_git_patch(project_root, relative_file)
        stable = stable and bool(
            final_relative_file == relative_file
            and final_resolved_file == resolved_file
            and _file_fingerprint(final_resolved_file) == item["fingerprint"]
            and final_patch == item["patch"]
        )
    final_worktree_patch_after_files = _capture_worktree_patch(project_root)
    stable = stable and final_worktree_patch_after_files == recorded_worktree_patch
    if not stable:
        raise ProofRecordError(
            "WORKTREE_CHANGED_DURING_RECORD",
            "A changed file, its patch, or the surrounding dirty-file scope changed while Synrail was recording batch proof.",
            "Stop concurrent edits, inspect the live diff, and rerun synrail record --all-modified.",
        )

    provenance_records = [
        {
            "method": "git_patch_plus_recheck",
            "changed_file": str(item["relative_file"]),
            "verification_command": str(item["verification_command"]),
            "verification_result": str(item["verification_result"]),
        }
        for item in captured
    ]
    patch_sha256_by_file = {
        str(item["relative_file"]): hashlib.sha256(str(item["patch"]).encode("utf-8")).hexdigest()
        for item in captured
    }
    payload = {
        "request_id": str(state.get("run_id", "") or ""),
        "task_class": str(state.get("task_class", "") or "bounded_change"),
        "status": "PROVEN",
        "change_disposition": "modified",
        "summary": cleaned_summary,
        "modified_files": expected_paths,
        "git_diff": recorded_worktree_patch,
        "diff_provenance_records": provenance_records,
        "_synrail": {
            "recorded_by": "synrail record --all-modified",
            "patch_sha256_by_file": patch_sha256_by_file,
            "worktree_patch_sha256": hashlib.sha256(recorded_worktree_patch.encode("utf-8")).hexdigest(),
            "recorded_dirty_paths": expected_paths,
            "artifact_root_relative": _artifact_root_relative_to_project(
                artifact_root=artifact_root,
                project_root=project_root,
            ),
            "acceptance_evaluated": False,
        },
    }
    output_path = artifact_root / "final_result.json"
    save_json(output_path, payload)
    return {
        "result": "BATCH_PROOF_RECORDED",
        "accepted": False,
        "closure_evaluated": False,
        "artifact_root": str(artifact_root),
        "project_root": str(project_root),
        "final_result": str(output_path),
        "changed_files": expected_paths,
        "verification_commands": [str(item["verification_command"]) for item in captured],
        "patch_sha256_by_file": patch_sha256_by_file,
    }
