#!/usr/bin/env python3
"""Minimal checkpoint lifecycle helper for Synrail v0."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json_safe as save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json_safe as save_json

try:
    from .synrail_path_scope_v0 import PROJECT_SCOPE, PathScopeValidationError, path_in_root, symlinked_ancestor_within, validate_namespace_paths, validate_root_within_project
    from .synrail_repair_handoff_v0 import build_resumability
    from .synrail_validate_v0 import load_json as load_json_document, validate_document
except ImportError:
    from synrail_path_scope_v0 import PROJECT_SCOPE, PathScopeValidationError, path_in_root, symlinked_ancestor_within, validate_namespace_paths, validate_root_within_project
    from synrail_repair_handoff_v0 import build_resumability
    from synrail_validate_v0 import load_json as load_json_document, validate_document


HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
SCHEMAS = REPO_ROOT / "schemas"

SCHEMA_BY_KIND = {
    "STATE": SCHEMAS / "run_state_v0.schema.json",
    "REPORT": SCHEMAS / "orchestration_report_v0.schema.json",
    "ORCHESTRATION": SCHEMAS / "worked_orchestration_artifact_v0.schema.json",
    "BUNDLE": SCHEMAS / "proof_bundle_v0.schema.json",
    "CLOSURE": SCHEMAS / "closure_verdict_v0.schema.json",
    "REFRESH": SCHEMAS / "refresh_report_v0.schema.json",
    "SELECTION": SCHEMAS / "mode_selection_receipt_v0.schema.json",
    "PREPARATION": SCHEMAS / "governed_path_preparation_receipt_v0.schema.json",
    "REPAIR_PACKET": SCHEMAS / "repair_packet_v0.schema.json",
    "REPAIR_HANDOFF": SCHEMAS / "repair_handoff_v0.schema.json",
    "REPAIR_RECEIPT": SCHEMAS / "artifact_repair_receipt_v0.schema.json",
}

SAFE_POINT_CLASSES = {
    ("CLOSURE_ACCEPTED", "ACCEPTED"): "VERIFIED_ACCEPTED_STATE",
    ("READY", "CLAIMED_NOT_ACCEPTED"): "VERIFIED_WORKING_STATE",
}

# States eligible for a lightweight pre-run snapshot. These do not require
# doctor/target_surface/integrity to pass — the user is saving workspace
# state *before* changes, not after verification.
PRE_RUN_SNAPSHOT_STATES = {"INITIALIZED"}

ARTIFACT_FLAGS = [
    ("state_file", "state", "STATE", True),
    ("report_file", "report", "REPORT", False),
    ("orchestration_file", "orchestration", "ORCHESTRATION", False),
    ("bundle_file", "bundle", "BUNDLE", False),
    ("closure_file", "closure", "CLOSURE", False),
    ("refresh_file", "refresh", "REFRESH", False),
    ("selection_file", "selection_receipt", "SELECTION", False),
    ("preparation_file", "preparation_receipt", "PREPARATION", False),
    ("repair_packet_file", "repair_packet", "REPAIR_PACKET", False),
    ("repair_handoff_file", "repair_handoff", "REPAIR_HANDOFF", False),
    ("repair_receipt_file", "repair_receipt", "REPAIR_RECEIPT", False),
]

CHECKPOINT_CREATE_PATH_SCOPES = {
    "checkpoint_root": PROJECT_SCOPE,
    "output": PROJECT_SCOPE,
}

CHECKPOINT_VERIFY_PATH_SCOPES = {
    "checkpoint_record_file": PROJECT_SCOPE,
    "output": PROJECT_SCOPE,
}

CHECKPOINT_RESTORE_PATH_SCOPES = {
    "checkpoint_record_file": PROJECT_SCOPE,
    "target_root": PROJECT_SCOPE,
    "output": PROJECT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_checkpoint_create_paths(args: argparse.Namespace, *, project_root: Path) -> None:
    validate_namespace_paths(args, field_scopes=CHECKPOINT_CREATE_PATH_SCOPES, project_root=project_root, artifact_root=None)


def validate_checkpoint_verify_paths(args: argparse.Namespace, *, project_root: Path) -> None:
    validate_namespace_paths(args, field_scopes=CHECKPOINT_VERIFY_PATH_SCOPES, project_root=project_root, artifact_root=None)


def validate_checkpoint_restore_paths(args: argparse.Namespace, *, project_root: Path) -> None:
    validate_namespace_paths(args, field_scopes=CHECKPOINT_RESTORE_PATH_SCOPES, project_root=project_root, artifact_root=None)






def _git_head_ref(project_root: Path) -> str:
    """Return the current git HEAD commit hash, or empty string if not in a git repo."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def _git_is_repository(project_root: Path) -> bool:
    """Return True when project_root is inside a git work tree, even without commits."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return result.stdout.strip() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def _git_has_uncommitted(project_root: Path) -> bool:
    """Return True if the workspace has tracked staged/unstaged changes."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def _git_has_untracked(project_root: Path) -> bool:
    """Return True if the workspace has untracked files (not covered by git stash create)."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            visible_untracked = [
                line.strip()
                for line in result.stdout.splitlines()
                if line.strip() and not line.strip().startswith(".synrail/")
            ]
            return bool(visible_untracked)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False


def _git_stash_create(project_root: Path) -> str:
    """Create a git stash entry without modifying the working tree. Returns stash ref or empty."""
    try:
        result = subprocess.run(
            ["git", "stash", "create", "synrail pre-run snapshot"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return ""


def _git_restore_snapshot(project_root: Path, *, head_ref: str, stash_ref: str) -> tuple[bool, str]:
    """Restore workspace to the snapshot state. Returns (success, error_message)."""
    try:
        rollback_head_ref = _git_head_ref(project_root)
        rollback_stash_ref = _git_stash_create(project_root)

        reset = subprocess.run(
            ["git", "checkout", head_ref, "--force"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if reset.returncode != 0:
            return False, f"git checkout failed: {reset.stderr.strip()}"
        if stash_ref:
            apply = subprocess.run(
                ["git", "stash", "apply", stash_ref],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if apply.returncode != 0:
                rollback_failures: list[str] = []
                if rollback_head_ref:
                    rollback_reset = subprocess.run(
                        ["git", "checkout", rollback_head_ref, "--force"],
                        cwd=str(project_root),
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if rollback_reset.returncode != 0:
                        rollback_failures.append(f"git rollback checkout failed: {rollback_reset.stderr.strip()}")
                else:
                    rollback_failures.append("git rollback checkout failed: current HEAD is unavailable")
                if rollback_stash_ref:
                    rollback_apply = subprocess.run(
                        ["git", "stash", "apply", rollback_stash_ref],
                        cwd=str(project_root),
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if rollback_apply.returncode != 0:
                        rollback_failures.append(f"git rollback stash apply failed: {rollback_apply.stderr.strip()}")
                error = f"git stash apply failed: {apply.stderr.strip()}"
                if rollback_failures:
                    error += " | rollback restore failed: " + "; ".join(rollback_failures)
                return False, error
        return True, ""
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


def classify_workspace_family(workspace_snapshot: dict) -> str:
    """Classify the workspace snapshot into a restore family.

    Families:
        clean_commit    — git, no uncommitted changes, restore is a simple checkout
        dirty_tracked   — git, uncommitted tracked changes captured via stash
        dirty_untracked — git, untracked files preserved via file-copy fallback
        mixed_file_state — git, tracked + untracked changes preserved via file-copy fallback
        file_copy       — non-git, full directory snapshot
        unsupported     — no snapshot available
    """
    explicit_family = workspace_snapshot.get("workspace_family", "")
    if explicit_family:
        return explicit_family
    ws_type = workspace_snapshot.get("type", "none")
    if ws_type == "file_copy":
        return "file_copy"
    if ws_type == "none":
        return "unsupported"
    if ws_type == "git":
        if workspace_snapshot.get("has_untracked") and workspace_snapshot.get("has_uncommitted"):
            return "mixed_file_state"
        if workspace_snapshot.get("has_untracked"):
            return "dirty_untracked"
        if workspace_snapshot.get("has_uncommitted"):
            return "dirty_tracked"
        return "clean_commit"
    return "unsupported"


# Directories to exclude from file-copy snapshots (relative to project root).
_FILE_COPY_EXCLUDE_DIRS = {".synrail", ".git", "__pycache__", "node_modules", ".venv", "venv"}
# Maximum total size (bytes) we'll copy. Prevents accidental multi-GB snapshots.
_FILE_COPY_MAX_BYTES = 50 * 1024 * 1024  # 50 MB


def _file_copy_snapshot(project_root: Path, snapshot_dir: Path) -> tuple[bool, str, int]:
    """Copy project files (excluding .synrail/ etc.) into snapshot_dir.

    Returns (success, error_message, file_count).
    """
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    total_bytes = 0
    file_count = 0
    try:
        for item in sorted(project_root.iterdir()):
            if item.name in _FILE_COPY_EXCLUDE_DIRS:
                continue
            if item.is_file():
                size = item.stat().st_size
                if total_bytes + size > _FILE_COPY_MAX_BYTES:
                    return False, f"project exceeds {_FILE_COPY_MAX_BYTES // (1024*1024)} MB file-copy limit", file_count
                shutil.copy2(item, snapshot_dir / item.name)
                total_bytes += size
                file_count += 1
            elif item.is_dir():
                dir_dest = snapshot_dir / item.name
                # Walk the subtree respecting limits
                for root_dir, dirs, files in os.walk(item):
                    dirs[:] = [d for d in dirs if d not in _FILE_COPY_EXCLUDE_DIRS]
                    rel = Path(root_dir).relative_to(project_root)
                    dest = snapshot_dir / rel
                    dest.mkdir(parents=True, exist_ok=True)
                    for fname in files:
                        src_file = Path(root_dir) / fname
                        size = src_file.stat().st_size
                        if total_bytes + size > _FILE_COPY_MAX_BYTES:
                            return False, f"project exceeds {_FILE_COPY_MAX_BYTES // (1024*1024)} MB file-copy limit", file_count
                        shutil.copy2(src_file, dest / fname)
                        total_bytes += size
                        file_count += 1
        return True, "", file_count
    except Exception as exc:
        return False, str(exc), file_count


def _remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink(missing_ok=True)


def _file_copy_restore(snapshot_dir: Path, project_root: Path) -> tuple[bool, str]:
    """Restore project files from a file-copy snapshot. Returns (success, error_message)."""
    temp_root = Path(tempfile.mkdtemp(prefix="synrail_file_copy_restore_", dir=str(project_root.parent)))
    stage_root = temp_root / "stage"
    backup_root = temp_root / "backup"
    moved_stage_names: list[str] = []
    try:
        stage_root.mkdir(parents=True, exist_ok=True)
        backup_root.mkdir(parents=True, exist_ok=True)

        for item in sorted(snapshot_dir.iterdir()):
            dest = stage_root / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest)

        snapshot_names = sorted(item.name for item in snapshot_dir.iterdir())
        staged_names = sorted(item.name for item in stage_root.iterdir())
        if staged_names != snapshot_names:
            return False, "staged snapshot validation failed"

        for item in sorted(project_root.iterdir()):
            if item.name in _FILE_COPY_EXCLUDE_DIRS:
                continue
            os.replace(str(item), str(backup_root / item.name))

        for item in sorted(stage_root.iterdir()):
            dest = project_root / item.name
            os.replace(str(item), str(dest))
            moved_stage_names.append(item.name)

        return True, ""
    except Exception as exc:
        rollback_failures: list[str] = []
        try:
            for name in moved_stage_names:
                restored_path = project_root / name
                if restored_path.exists() or restored_path.is_symlink():
                    _remove_path(restored_path)
            if backup_root.exists():
                for item in sorted(backup_root.iterdir()):
                    os.replace(str(item), str(project_root / item.name))
        except Exception as rollback_exc:
            rollback_failures.append(str(rollback_exc))
        error = str(exc)
        if rollback_failures:
            error = error + " | rollback failed: " + "; ".join(rollback_failures)
        return False, error
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def build_manifest(args: argparse.Namespace, checkpoint_root: Path) -> list[dict]:
    manifest: list[dict] = []
    artifacts_dir = checkpoint_root / "artifacts"
    if artifacts_dir.exists():
        shutil.rmtree(artifacts_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    for attr, artifact_id, kind, always_required in ARTIFACT_FLAGS:
        value = getattr(args, attr, None)
        if not value:
            continue
        source = Path(value)
        suffix = source.suffix or ".json"
        destination = artifacts_dir / f"{artifact_id}{suffix}"
        shutil.copy2(source, destination)
        manifest.append(
            {
                "artifact_id": artifact_id,
                "path": str(destination.relative_to(checkpoint_root)),
                "required": always_required,
                "kind": kind,
            }
        )
    return manifest


def verification_template() -> dict:
    return {
        "status": "NOT_RUN",
        "safe_point_eligible": False,
        "required_artifacts_present": False,
        "schema_validation_passed": False,
        "state_consistency_passed": False,
        "stale_artifacts_detected": [],
        "failure_reasons": [],
    }


def restore_template() -> dict:
    return {
        "status": "NOT_RUN",
        "target_root": "",
        "restore_verification_required": True,
        "restored_artifact_ids": [],
        "failure_reasons": [],
    }


def rollback_template() -> dict:
    return {
        "status": "NOT_NEEDED",
        "trigger": "NONE",
        "rolled_back_artifact_ids": [],
        "failure_reasons": [],
    }


def restore_contract(record: dict) -> dict:
    workspace_snapshot = record.get("workspace_snapshot", {})
    safe_point_class = record.get("safe_point_class", "")
    artifact_restore_count = len(record.get("artifact_manifest", []))
    workspace_family = classify_workspace_family(workspace_snapshot) if workspace_snapshot else ""
    contract = {
        "supported_contour": "",
        "workspace_family": workspace_family,
        "restore_supported": True,
        "workspace_restore_mode": "artifacts_only",
        "workspace_restore_supported": False,
        "workspace_restore_destructive": False,
        "artifact_restore_count": artifact_restore_count,
        "summary": "Restore will rehydrate checkpoint-owned artifacts only. It will not revert project workspace files.",
        "notes": [
            "This contour restores the checkpoint artifact set under the target root only.",
            "Do not treat this as a full workspace rollback.",
        ],
        "next_safe_step": "use restore only if you need the saved checkpoint artifacts again",
    }
    if safe_point_class != "PRE_RUN_SNAPSHOT":
        contract["supported_contour"] = "artifact_only_verified_state"
        return contract

    workspace_type = workspace_snapshot.get("type", "none")
    project_root = workspace_snapshot.get("project_root", "")
    if workspace_family == "clean_commit" and workspace_type == "git" and workspace_snapshot.get("head_ref"):
        contract.update(
            {
                "supported_contour": "pre_run_snapshot_git_clean_commit",
                "workspace_restore_mode": "git",
                "workspace_restore_supported": True,
                "workspace_restore_destructive": True,
                "summary": "Restore will reset the saved clean git workspace state and then rehydrate checkpoint artifacts.",
                "notes": [
                    "This restore modifies project files in the saved project root.",
                    "Workspace family: clean_commit.",
                    ("Saved commit: " + workspace_snapshot.get("commit_sha", workspace_snapshot.get("head_ref", ""))) if workspace_snapshot.get("commit_sha", workspace_snapshot.get("head_ref", "")) else "Saved commit is recorded in the checkpoint.",
                    ("Saved project root: " + project_root) if project_root else "Saved project root is recorded in the checkpoint.",
                ],
                "next_safe_step": "preview this restore carefully, then run restore only if you want to return to the saved pre-run workspace",
            }
        )
        return contract
    if workspace_family == "dirty_tracked" and workspace_type == "git" and workspace_snapshot.get("head_ref"):
        if not workspace_snapshot.get("stash_ref"):
            contract.update(
                {
                    "supported_contour": "pre_run_snapshot_git_dirty_tracked_unsupported",
                    "restore_supported": False,
                    "workspace_restore_mode": "none",
                    "workspace_restore_supported": False,
                    "workspace_restore_destructive": False,
                    "summary": "This dirty tracked git workspace cannot be restored because the tracked-change snapshot was not captured.",
                    "notes": [
                        "Workspace family: dirty_tracked.",
                        workspace_snapshot.get("reason", "Tracked git changes were present, but no stash-backed snapshot is available."),
                    ],
                    "next_safe_step": "create a new restore point after capturing tracked changes successfully",
                }
            )
            return contract
        contract.update(
            {
                "supported_contour": "pre_run_snapshot_git_dirty_tracked",
                "workspace_restore_mode": "git",
                "workspace_restore_supported": True,
                "workspace_restore_destructive": True,
                "summary": "Restore will reset the saved dirty tracked git workspace state, reapply the captured tracked changes, and then rehydrate checkpoint artifacts.",
                "notes": [
                    "This restore modifies project files in the saved project root.",
                    "Workspace family: dirty_tracked.",
                    ("Saved commit: " + workspace_snapshot.get("commit_sha", workspace_snapshot.get("head_ref", ""))) if workspace_snapshot.get("commit_sha", workspace_snapshot.get("head_ref", "")) else "Saved commit is recorded in the checkpoint.",
                    ("Saved project root: " + project_root) if project_root else "Saved project root is recorded in the checkpoint.",
                ],
                "next_safe_step": "preview this restore carefully, then run restore only if you want to recover the saved tracked git workspace state",
            }
        )
        return contract
    if workspace_type == "file_copy":
        contour = "pre_run_snapshot_file_copy"
        summary = "Restore will atomically replace non-excluded project files from the saved file-copy snapshot and then rehydrate checkpoint artifacts."
        notes = [
            "This restore atomically swaps current non-excluded project files with the saved snapshot and rolls back if the swap fails.",
            ("Saved project root: " + project_root) if project_root else "Saved project root is recorded in the checkpoint.",
        ]
        if workspace_snapshot.get("source_control") == "git" and not workspace_snapshot.get("head_ref"):
            contour = "pre_run_snapshot_git_no_commit_file_copy"
            summary = "Restore will use a file-copy workspace snapshot because this git workspace had no committed HEAD to restore from."
            notes.insert(1, "Workspace contour: git repository without a committed HEAD.")
        if workspace_family in {"dirty_untracked", "mixed_file_state"}:
            contour = f"pre_run_snapshot_git_{workspace_family}_file_copy"
            summary = "Restore will use a file-copy workspace snapshot because plain git restore cannot faithfully recover the saved untracked state."
            notes.insert(1, f"Workspace family: {workspace_family}.")
        contract.update(
            {
                "supported_contour": contour,
                "workspace_restore_mode": "file_copy",
                "workspace_restore_supported": True,
                "workspace_restore_destructive": True,
                "summary": summary,
                "notes": notes,
                "next_safe_step": "preview this restore carefully, then run restore only if you want to replace the current pre-run workspace with the saved snapshot",
            }
        )
        return contract
    unsupported_reason = workspace_snapshot.get("reason", "No workspace snapshot is available for this checkpoint.")
    if workspace_family in {"dirty_untracked", "mixed_file_state", "dirty_tracked"}:
        unsupported_reason = (
            f"workspace family {workspace_family} could not be captured as a trustworthy restore snapshot: "
            f"{unsupported_reason}"
        )
    contract.update(
        {
            "supported_contour": "pre_run_snapshot_unsupported",
            "restore_supported": False,
            "workspace_restore_mode": "none",
            "workspace_restore_supported": False,
            "workspace_restore_destructive": False,
            "summary": "This pre-run snapshot cannot restore workspace files because no supported workspace snapshot was saved.",
            "notes": [
                unsupported_reason,
                "Synrail will not treat this as a trustworthy workspace rollback contour.",
            ],
            "next_safe_step": "create a new restore point on a supported workspace contour before depending on restore",
        }
    )
    return contract


def restore_preview(record: dict, target_root: Path) -> dict:
    verified = verify_record(record)
    contract = restore_contract(record)
    target_path_errors = restore_target_path_errors(record, target_root.resolve())
    verification_ok = verified["result"] == "OK"
    restore_supported = verification_ok and contract["restore_supported"] and not target_path_errors
    restore_status = "READY"
    summary = contract["summary"]
    notes = list(contract["notes"])
    failure_reasons: list[str] = []
    next_safe_step = contract["next_safe_step"]
    if not verification_ok:
        restore_status = "BLOCKED"
        summary = "Restore is not safe to run yet because the checkpoint has not been verified successfully."
        failure_reasons = list(verified["verification"].get("failure_reasons", []))
        notes = failure_reasons or ["Checkpoint verification must pass before restore is allowed."]
        next_safe_step = "verify checkpoint successfully before attempting restore"
    elif target_path_errors:
        restore_status = "BLOCKED"
        summary = "Restore is not safe to run because the target surface is not a direct in-scope restore path."
        failure_reasons = list(target_path_errors)
        notes = failure_reasons
        next_safe_step = "repair the restore target path before attempting restore"
    elif not contract["restore_supported"]:
        restore_status = "UNSUPPORTED"
        failure_reasons = [contract["summary"]]
    elif not contract["workspace_restore_supported"]:
        restore_status = "LIMITED"
    return {
        "schema_version": "checkpoint_restore_preview_v0",
        "checkpoint_id": record.get("checkpoint_id", ""),
        "run_id": record.get("run_id", ""),
        "task_class": record.get("task_class", ""),
        "target_root": str(target_root),
        "verification_status": verified["verification"].get("status", ""),
        "restore_status": restore_status,
        "restore_supported": restore_supported,
        "safe_point_class": record.get("safe_point_class", ""),
        "supported_contour": contract["supported_contour"],
        "workspace_family": contract["workspace_family"],
        "workspace_restore_mode": contract["workspace_restore_mode"],
        "workspace_restore_supported": contract["workspace_restore_supported"],
        "workspace_restore_destructive": contract["workspace_restore_destructive"],
        "artifact_restore_count": contract["artifact_restore_count"],
        "summary": summary,
        "notes": notes,
        "failure_reasons": failure_reasons,
        "next_safe_step": next_safe_step,
    }


def classify_safe_point(state: dict) -> tuple[str, bool, list[str]]:
    failures: list[str] = []
    current_state = state.get("state", "")

    # Pre-run snapshot: allow saving from INITIALIZED before any check has run.
    # No doctor/target_surface/integrity requirements — the user is preserving
    # the workspace before making changes, not after verification.
    if current_state in PRE_RUN_SNAPSHOT_STATES:
        return "PRE_RUN_SNAPSHOT", True, []

    safe_point_class = SAFE_POINT_CLASSES.get(
        (current_state, state.get("closure", {}).get("status", ""))
    )
    if not safe_point_class:
        failures.append("state is not an eligible accepted or working checkpoint surface")
        safe_point_class = "NOT_SAFE_POINT"
    if state.get("doctor", {}).get("status", "") != "PASS":
        failures.append("doctor must pass before checkpoint can be trusted")
    if state.get("target_surface", {}).get("status", "") != "ATTESTED":
        failures.append("target surface must be attested before checkpoint can be trusted")
    if state.get("integrity", {}).get("status", "") != "PASS":
        failures.append("integrity must pass before checkpoint can be trusted")
    return safe_point_class, not failures, failures


def create_record(args: argparse.Namespace) -> dict:
    checkpoint_root = Path(args.checkpoint_root)
    checkpoint_root.mkdir(parents=True, exist_ok=True)
    state = load_json(Path(args.state_file))
    resumability = build_resumability(state)
    safe_point_class, safe_point_eligible, safe_point_failures = classify_safe_point(state)
    manifest = build_manifest(args, checkpoint_root) if safe_point_eligible else []

    # For pre-run snapshots, capture the git workspace state so restore can
    # bring back the actual project files, not just .synrail/ artifacts.
    # Always include workspace_snapshot for PRE_RUN_SNAPSHOT so that
    # restore_record can detect when workspace recovery is impossible.
    workspace_snapshot: dict = {}
    if safe_point_class == "PRE_RUN_SNAPSHOT":
        project_root = Path(getattr(args, "project_root", "") or ".").resolve()
        head_ref = _git_head_ref(project_root)
        if head_ref:
            has_uncommitted = _git_has_uncommitted(project_root)
            has_untracked = _git_has_untracked(project_root)
            if has_untracked:
                family = "mixed_file_state" if has_uncommitted else "dirty_untracked"
                snapshot_dir = checkpoint_root / "workspace_files"
                ok, err, count = _file_copy_snapshot(project_root, snapshot_dir)
                if ok:
                    workspace_snapshot = {
                        "type": "file_copy",
                        "workspace_family": family,
                        "source_control": "git",
                        "project_root": str(project_root),
                        "head_ref": head_ref,
                        "snapshot_dir": str(snapshot_dir),
                        "file_count": count,
                        "has_uncommitted": has_uncommitted,
                        "has_untracked": has_untracked,
                    }
                else:
                    workspace_snapshot = {
                        "type": "none",
                        "workspace_family": family,
                        "source_control": "git",
                        "project_root": str(project_root),
                        "head_ref": head_ref,
                        "has_uncommitted": has_uncommitted,
                        "has_untracked": has_untracked,
                        "reason": f"file-copy snapshot failed: {err}",
                    }
            else:
                stash_ref = ""
                if has_uncommitted:
                    stash_ref = _git_stash_create(project_root)
                if has_uncommitted and not stash_ref:
                    workspace_snapshot = {
                        "type": "none",
                        "workspace_family": "dirty_tracked",
                        "source_control": "git",
                        "project_root": str(project_root),
                        "head_ref": head_ref,
                        "has_uncommitted": True,
                        "has_untracked": False,
                        "reason": "git stash create failed to capture tracked changes",
                    }
                else:
                    workspace_snapshot = {
                        "type": "git",
                        "workspace_family": "dirty_tracked" if has_uncommitted else "clean_commit",
                        "project_root": str(project_root),
                        "head_ref": head_ref,
                        "commit_sha": head_ref,
                        "stash_ref": stash_ref,
                        "has_uncommitted": has_uncommitted,
                        "has_untracked": False,
                    }
        else:
            # No git HEAD available — either not a git repo, or a git repo with no commits yet.
            snapshot_dir = checkpoint_root / "workspace_files"
            ok, err, count = _file_copy_snapshot(project_root, snapshot_dir)
            source_control = "git" if _git_is_repository(project_root) else "none"
            reason = (
                "git repository has no committed HEAD; using file-copy snapshot"
                if source_control == "git"
                else ""
            )
            if ok:
                workspace_snapshot = {
                    "type": "file_copy",
                    "workspace_family": "file_copy",
                    "source_control": source_control,
                    "project_root": str(project_root),
                    "snapshot_dir": str(snapshot_dir),
                    "file_count": count,
                }
                if reason:
                    workspace_snapshot["reason"] = reason
            else:
                workspace_snapshot = {
                    "type": "none",
                    "workspace_family": "unsupported",
                    "source_control": source_control,
                    "project_root": str(project_root),
                    "reason": (
                        f"git repository has no committed HEAD and file-copy snapshot failed: {err}"
                        if source_control == "git"
                        else f"file-copy snapshot failed: {err}"
                    ),
                }

    record = {
        "schema_version": "checkpoint_record_v0",
        "checkpoint_id": args.checkpoint_id,
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "event_type": "CREATE",
        "result": "OK" if safe_point_eligible else "BLOCKED",
        "checkpoint_root": str(checkpoint_root),
        "source_state": state["state"],
        "source_closure_status": state["closure"]["status"],
        "source_doctor_status": state.get("doctor", {}).get("status", ""),
        "source_target_surface_status": state.get("target_surface", {}).get("status", ""),
        "source_integrity_status": state.get("integrity", {}).get("status", ""),
        "source_resumability_status": resumability["status"],
        "source_resumability_family": resumability["family"],
        "safe_point_class": safe_point_class,
        "safe_point_eligible": safe_point_eligible,
        "artifact_manifest": manifest,
        "verification": verification_template(),
        "restore": restore_template(),
        "rollback": rollback_template(),
        "next_safe_step": (
            "verify checkpoint before trusting restore"
            if safe_point_eligible
            else "; ".join(safe_point_failures)
        ),
    }
    if workspace_snapshot:
        record["workspace_snapshot"] = workspace_snapshot
    # For PRE_RUN_SNAPSHOT, workspace_snapshot must always be present so
    # restore_record can detect when workspace recovery is impossible.
    elif safe_point_class == "PRE_RUN_SNAPSHOT":
        record["workspace_snapshot"] = {"type": "none", "reason": "no workspace snapshot available"}
    return record


def normalized_manifest_document(artifact: dict, document: object) -> object:
    if artifact.get("kind") != "STATE" or not isinstance(document, dict):
        return document
    payload = dict(document)
    doctor = dict(payload.get("doctor", {})) if isinstance(payload.get("doctor", {}), dict) else {}
    doctor.setdefault("override_gates", [])
    payload["doctor"] = doctor
    proof_bundle = dict(payload.get("proof_bundle", {})) if isinstance(payload.get("proof_bundle", {}), dict) else {}
    proof_bundle.setdefault("artifact_integrity_warning", False)
    payload["proof_bundle"] = proof_bundle
    closure = dict(payload.get("closure", {})) if isinstance(payload.get("closure", {}), dict) else {}
    closure.setdefault("warnings", [])
    payload["closure"] = closure
    payload.setdefault("start_timestamp_utc", "")
    payload.setdefault("closure_timestamp_utc", "")
    payload.setdefault("check_count", 0)
    payload.setdefault("last_known_final_result_hash", "")
    return payload


def checkpoint_record_path_errors(record: dict, *, root_override: Path | None = None) -> list[str]:
    effective_root = (root_override or Path(record["checkpoint_root"])).resolve()
    checkpoint_root = Path(record["checkpoint_root"]).resolve()
    errors: list[str] = []
    for artifact in record.get("artifact_manifest", []):
        artifact_path = effective_root / str(artifact.get("path", ""))
        if not path_in_root(artifact_path.resolve(), effective_root):
            errors.append(f"artifact path escapes checkpoint root: {artifact.get('artifact_id', '')}")
    workspace_snapshot = record.get("workspace_snapshot", {})
    if not isinstance(workspace_snapshot, dict):
        return errors
    snapshot_dir = workspace_snapshot.get("snapshot_dir", "")
    if isinstance(snapshot_dir, str) and snapshot_dir.strip():
        snapshot_dir_path = Path(snapshot_dir).expanduser().resolve()
        if not path_in_root(snapshot_dir_path, checkpoint_root):
            errors.append("workspace snapshot directory escapes checkpoint root")
    return errors


def validate_manifest_artifacts(record: dict, *, root_override: Path | None = None) -> tuple[list[str], list[str]]:
    checkpoint_root = root_override or Path(record["checkpoint_root"])
    schema_errors: list[str] = []
    missing: list[str] = []
    for artifact in record.get("artifact_manifest", []):
        artifact_path = checkpoint_root / artifact["path"]
        if not artifact_path.exists():
            if artifact.get("required", False):
                missing.append(artifact["artifact_id"])
            continue
        schema_path = SCHEMA_BY_KIND.get(artifact["kind"])
        if not schema_path:
            continue
        schema = load_json_document(schema_path)
        document = normalized_manifest_document(artifact, load_json_document(artifact_path))
        for error in validate_document(document, schema):
            schema_errors.append(f"{artifact['artifact_id']}: {error}")
    return missing, schema_errors


def unexpected_artifact_paths(record: dict, *, root_override: Path | None = None) -> list[str]:
    checkpoint_root = root_override or Path(record["checkpoint_root"])
    allowed = {artifact["path"] for artifact in record.get("artifact_manifest", [])}
    unexpected: list[str] = []
    artifacts_root = checkpoint_root / "artifacts"
    if not artifacts_root.exists():
        return unexpected
    for path in sorted(artifacts_root.rglob("*")):
        if not path.is_file():
            continue
        relative_path = str(path.relative_to(checkpoint_root))
        if relative_path not in allowed:
            unexpected.append(relative_path)
    return unexpected


def state_consistency_errors(record: dict, *, root_override: Path | None = None) -> list[str]:
    checkpoint_root = root_override or Path(record["checkpoint_root"])
    entries = {artifact["artifact_id"]: artifact for artifact in record.get("artifact_manifest", [])}
    errors: list[str] = []
    state_entry = entries.get("state")
    if not state_entry:
        return ["state artifact missing from checkpoint manifest"]
    state = normalized_manifest_document(state_entry, load_json(checkpoint_root / state_entry["path"]))
    if state.get("run_id") != record.get("run_id"):
        errors.append("state.run_id does not match checkpoint run_id")
    if state.get("task_class") != record.get("task_class"):
        errors.append("state.task_class does not match checkpoint task_class")
    if state.get("state") != record.get("source_state"):
        errors.append("state.state does not match checkpoint source_state")
    closure_status = state.get("closure", {}).get("status", "")
    if closure_status != record.get("source_closure_status"):
        errors.append("state.closure.status does not match checkpoint source_closure_status")
    # For pre-run snapshots, classify_safe_point will return PRE_RUN_SNAPSHOT
    # with no failures — skip the strict gate checks that don't apply here.
    safe_point_class, safe_point_eligible, safe_point_failures = classify_safe_point(state)
    if safe_point_class != record.get("safe_point_class", ""):
        errors.append("state safe_point_class does not match checkpoint safe_point_class")
    if safe_point_eligible != record.get("safe_point_eligible", False):
        errors.append("state safe_point_eligible does not match checkpoint safe_point_eligible")
    if record.get("safe_point_class") != "PRE_RUN_SNAPSHOT":
        for failure in safe_point_failures:
            errors.append(f"safe point eligibility failed: {failure}")
    return errors


def verify_record(record: dict, *, root_override: Path | None = None) -> dict:
    path_errors = checkpoint_record_path_errors(record, root_override=root_override)
    missing, schema_errors = validate_manifest_artifacts(record, root_override=root_override)
    consistency_errors = [] if (missing or path_errors) else state_consistency_errors(record, root_override=root_override)
    unexpected_paths = unexpected_artifact_paths(record, root_override=root_override)
    failure_reasons = []
    if path_errors:
        failure_reasons.append("checkpoint record path validation failed")
    if missing:
        failure_reasons.append("required checkpoint artifacts missing")
    if schema_errors:
        failure_reasons.append("schema validation failed")
    if consistency_errors:
        failure_reasons.append("state consistency failed")
    if unexpected_paths:
        failure_reasons.append("unexpected checkpoint artifacts present")
    verified = dict(record)
    verified["event_type"] = "VERIFY"
    verified["result"] = "OK" if not (path_errors or missing or schema_errors or consistency_errors or unexpected_paths) else "BLOCKED"
    verified["verification"] = {
        "status": "PASSED" if not (path_errors or missing or schema_errors or consistency_errors or unexpected_paths) else "FAILED",
        "safe_point_eligible": record.get("safe_point_eligible", False) and not (path_errors or consistency_errors),
        "required_artifacts_present": not missing,
        "schema_validation_passed": not schema_errors,
        "state_consistency_passed": not consistency_errors,
        "stale_artifacts_detected": unexpected_paths,
        "failure_reasons": failure_reasons + path_errors + missing + schema_errors + consistency_errors + unexpected_paths,
    }
    verified["next_safe_step"] = (
        "checkpoint verified; restore is now allowed"
        if verified["result"] == "OK"
        else "repair checkpoint artifact set before using restore"
    )
    return verified


def backup_target_artifacts(record: dict, target_root: Path) -> tuple[Path, list[str]]:
    assert_direct_restore_target_paths(record, target_root)
    backup_root = Path(tempfile.mkdtemp(prefix=f"synrail_checkpoint_backup_{record['checkpoint_id']}_"))
    backed_up_ids: list[str] = []
    for artifact in record.get("artifact_manifest", []):
        target_path = target_root / artifact["path"]
        if not target_path.exists():
            continue
        backup_path = backup_root / artifact["path"]
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_path, backup_path)
        backed_up_ids.append(artifact["artifact_id"])
    return backup_root, backed_up_ids


def restore_runtime_failures(record: dict, target_root: Path) -> list[str]:
    try:
        assert_direct_restore_target_paths(record, target_root)
    except RuntimeError as exc:
        return [str(exc)]
    return []


def checkpoint_owned_project_root(checkpoint_root: Path) -> Path | None:
    resolved_checkpoint_root = checkpoint_root.resolve()
    for candidate in [resolved_checkpoint_root, *resolved_checkpoint_root.parents]:
        if candidate.name != ".synrail":
            continue
        try:
            relative = resolved_checkpoint_root.relative_to(candidate)
        except ValueError:
            continue
        if relative.parts and relative.parts[0] == "checkpoints":
            return candidate.parent.resolve()
    return None



def restore_target_path_errors(record: dict, target_root: Path) -> list[str]:
    errors: list[str] = []
    resolved_target_root = target_root.resolve()
    for artifact in record.get("artifact_manifest", []):
        target_path = target_root / artifact["path"]
        if target_path.is_symlink():
            errors.append(f"restore target path is a symlink: {artifact.get('artifact_id', '')}")
            continue
        parent = target_path.parent
        if parent.is_symlink():
            errors.append(f"restore target path parent is a symlink: {artifact.get('artifact_id', '')}")
            continue
        ancestor = symlinked_ancestor_within(parent, stop_at=resolved_target_root)
        if ancestor is not None:
            errors.append(f"restore target path ancestor is a symlink: {artifact.get('artifact_id', '')}")
    return errors


def assert_direct_restore_target_paths(record: dict, target_root: Path) -> None:
    target_path_errors = restore_target_path_errors(record, target_root)
    if target_path_errors:
        raise RuntimeError(target_path_errors[0])


def restore_manifest(record: dict, target_root: Path) -> list[str]:
    assert_direct_restore_target_paths(record, target_root)
    restored_ids: list[str] = []
    checkpoint_root = Path(record["checkpoint_root"])
    for artifact in record.get("artifact_manifest", []):
        source_path = checkpoint_root / artifact["path"]
        target_path = target_root / artifact["path"]
        target_path.parent.mkdir(parents=True, exist_ok=True)
        if artifact.get("kind") == "STATE":
            document = normalized_manifest_document(artifact, load_json_document(source_path))
            target_path.write_text(json.dumps(document, indent=2, ensure_ascii=True) + "\n")
        else:
            shutil.copy2(source_path, target_path)
        restored_ids.append(artifact["artifact_id"])
    return restored_ids


def rollback_from_backup(record: dict, target_root: Path, backup_root: Path, backed_up_ids: list[str]) -> tuple[str, list[str], list[str]]:
    failures: list[str] = []
    rolled_back_ids: list[str] = []
    try:
        assert_direct_restore_target_paths(record, target_root)
        for artifact in record.get("artifact_manifest", []):
            target_path = target_root / artifact["path"]
            backup_path = backup_root / artifact["path"]
            if artifact["artifact_id"] in backed_up_ids and backup_path.exists():
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_path, target_path)
                if artifact["artifact_id"] not in rolled_back_ids:
                    rolled_back_ids.append(artifact["artifact_id"])
            else:
                target_path.unlink(missing_ok=True)
                if artifact["artifact_id"] not in rolled_back_ids:
                    rolled_back_ids.append(artifact["artifact_id"])
        return "ROLLED_BACK", rolled_back_ids, failures
    except Exception as exc:  # pragma: no cover - defensive path
        failures.append(str(exc))
        return "ROLLBACK_FAILED", rolled_back_ids, failures
    finally:
        shutil.rmtree(backup_root, ignore_errors=True)


def restore_record(record: dict, target_root: Path) -> dict:
    preview = restore_preview(record, target_root)
    preverify = verify_record(record)
    if preverify["result"] != "OK" or not preview["restore_supported"]:
        blocked = dict(preverify if preverify["result"] != "OK" else record)
        blocked["event_type"] = "RESTORE"
        blocked["result"] = "BLOCKED"
        blocked["restore"] = {
            "status": "RESTORE_FAILED",
            "target_root": str(target_root),
            "restore_verification_required": True,
            "restored_artifact_ids": [],
            "failure_reasons": (
                list(preview["failure_reasons"])
                if preview["failure_reasons"]
                else list(preverify["verification"].get("failure_reasons", []))
            ),
            "workspace_restored": False,
        }
        blocked["rollback"] = rollback_template()
        blocked["next_safe_step"] = preview["next_safe_step"]
        return blocked

    # For pre-run snapshots with a git workspace, restore the project files first.
    workspace_snapshot = record.get("workspace_snapshot", {})
    workspace_restored = False
    workspace_error = ""
    requested_target_root = target_root.resolve()
    target_path_errors = restore_target_path_errors(record, requested_target_root)
    snapshot_project_root = Path(workspace_snapshot.get("project_root", "")).expanduser().resolve() if workspace_snapshot.get("project_root") else None
    checkpoint_project_root = checkpoint_owned_project_root(Path(record["checkpoint_root"]))
    if target_path_errors:
        workspace_error = target_path_errors[0]
    elif snapshot_project_root is not None and checkpoint_project_root is None:
        workspace_error = "workspace snapshot project_root is present but checkpoint_root is not inside a checkpoint-owned artifact root"
    elif snapshot_project_root is not None and snapshot_project_root != checkpoint_project_root:
        workspace_error = "workspace snapshot project_root does not match checkpoint-owned project_root"
    elif workspace_snapshot.get("type") == "git" and workspace_snapshot.get("head_ref"):
        project_root = Path(workspace_snapshot["project_root"])
        ok, err = _git_restore_snapshot(
            project_root,
            head_ref=workspace_snapshot["head_ref"],
            stash_ref=workspace_snapshot.get("stash_ref", ""),
        )
        workspace_restored = ok
        workspace_error = err
    elif workspace_snapshot.get("type") == "file_copy":
        snapshot_dir = Path(workspace_snapshot["snapshot_dir"])
        project_root = Path(workspace_snapshot["project_root"])
        if snapshot_dir.exists():
            ok, err = _file_copy_restore(snapshot_dir, project_root)
            workspace_restored = ok
            workspace_error = err
        else:
            workspace_error = f"snapshot directory missing: {snapshot_dir}"
    elif workspace_snapshot.get("type") == "none":
        workspace_error = workspace_snapshot.get("reason", "no workspace snapshot available")

    restored = dict(record)
    restored["restore"] = restore_template()
    restored["rollback"] = rollback_template()
    runtime_target_failures = restore_runtime_failures(record, requested_target_root)
    if runtime_target_failures:
        restored["event_type"] = "RESTORE"
        restored["result"] = "BLOCKED"
        restored["restore"] = {
            "status": "RESTORE_FAILED",
            "target_root": str(target_root),
            "restore_verification_required": True,
            "restored_artifact_ids": [],
            "failure_reasons": runtime_target_failures,
            "workspace_restored": False,
        }
        restored["rollback"] = rollback_template()
        restored["next_safe_step"] = "repair the restore target path before attempting restore"
        return restored
    backup_root, backed_up_ids = backup_target_artifacts(record, target_root)
    restored_ids = restore_manifest(record, target_root)
    verify_after_restore = verify_record(record, root_override=target_root)
    restored["verification"] = verify_after_restore["verification"]

    artifact_ok = verify_after_restore["result"] == "OK"
    # For pre-run snapshots, success means workspace was restored (or no snapshot needed)
    overall_ok = artifact_ok and (not workspace_snapshot or workspace_restored)

    restore_failures = []
    if not artifact_ok:
        restore_failures.extend(list(verify_after_restore["verification"].get("failure_reasons", [])))
    if target_path_errors:
        restore_failures.extend(target_path_errors)
    if workspace_snapshot and not workspace_restored:
        restore_failures.append(f"workspace restore failed: {workspace_error}")
    elif target_path_errors:
        restore_failures.append(f"workspace restore failed: {workspace_error}")

    restored["restore"] = {
        "status": "RESTORED" if overall_ok else "RESTORE_FAILED",
        "target_root": str(target_root),
        "restore_verification_required": True,
        "restored_artifact_ids": restored_ids,
        "failure_reasons": restore_failures,
        "workspace_restored": workspace_restored,
    }
    if overall_ok:
        restored["event_type"] = "RESTORE"
        restored["result"] = "OK"
        restored["rollback"] = rollback_template()
        restored["next_safe_step"] = "inspect or continue from the restored checkpoint state"
        shutil.rmtree(backup_root, ignore_errors=True)
        return restored

    rollback_status, rolled_back_ids, rollback_failures = rollback_from_backup(record, target_root, backup_root, backed_up_ids)
    restored["event_type"] = "RESTORE_ROLLBACK"
    restored["result"] = "BLOCKED" if rollback_status == "ROLLED_BACK" else "ERROR"
    restored["rollback"] = {
        "status": rollback_status,
        "trigger": "RESTORE_VERIFICATION_FAILED",
        "rolled_back_artifact_ids": rolled_back_ids,
        "failure_reasons": rollback_failures,
    }
    restored["next_safe_step"] = (
        "inspect restore verification failure before attempting another restore"
        if rollback_status == "ROLLED_BACK"
        else "manual recovery required because rollback failed"
    )
    return restored


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-checkpoint-v0")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create")
    p_create.add_argument("--checkpoint-id", required=True)
    p_create.add_argument("--checkpoint-root", required=True)
    p_create.add_argument("--state-file", required=True)
    p_create.add_argument("--project-root")
    p_create.add_argument("--report-file")
    p_create.add_argument("--orchestration-file")
    p_create.add_argument("--bundle-file")
    p_create.add_argument("--closure-file")
    p_create.add_argument("--refresh-file")
    p_create.add_argument("--selection-file")
    p_create.add_argument("--preparation-file")
    p_create.add_argument("--repair-packet-file")
    p_create.add_argument("--repair-handoff-file")
    p_create.add_argument("--repair-receipt-file")
    p_create.add_argument("--output", required=True)

    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--checkpoint-record-file", required=True)
    p_verify.add_argument("--output", required=True)

    p_restore = sub.add_parser("restore")
    p_restore.add_argument("--checkpoint-record-file", required=True)
    p_restore.add_argument("--target-root", required=True)
    p_restore.add_argument("--output", required=True)

    p_preview = sub.add_parser("preview")
    p_preview.add_argument("--checkpoint-record-file", required=True)
    p_preview.add_argument("--target-root", required=True)
    p_preview.add_argument("--output", required=True)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        project_root = current_project_root()

        if args.cmd == "create":
            checkpoint_root = Path(args.checkpoint_root).expanduser().resolve()
            validate_root_within_project(
                "checkpoint_root",
                args.checkpoint_root,
                root=checkpoint_root,
                project_root=project_root,
                artifact_root=None,
            )
            validate_checkpoint_create_paths(args, project_root=project_root)
            record = create_record(args)
            save_json(Path(args.output), record)
            print(json.dumps({"result": record["result"], "checkpoint_id": record["checkpoint_id"]}, ensure_ascii=True))
            return 0

        if args.cmd == "verify":
            validate_checkpoint_verify_paths(args, project_root=project_root)
            record = load_json(Path(args.checkpoint_record_file))
            verified = verify_record(record)
            save_json(Path(args.output), verified)
            print(json.dumps({"result": verified["result"], "verification_status": verified["verification"]["status"]}, ensure_ascii=True))
            return 0 if verified["result"] == "OK" else 2

        if args.cmd == "restore":
            target_root = Path(args.target_root).expanduser().resolve()
            validate_root_within_project(
                "target_root",
                args.target_root,
                root=target_root,
                project_root=project_root,
                artifact_root=None,
            )
            validate_checkpoint_restore_paths(args, project_root=project_root)
            record = load_json(Path(args.checkpoint_record_file))
            restored = restore_record(record, Path(args.target_root))
            save_json(Path(args.output), restored)
            print(json.dumps({"result": restored["result"], "event_type": restored["event_type"], "rollback_status": restored["rollback"]["status"]}, ensure_ascii=True))
            return 0 if restored["result"] == "OK" else 2

        if args.cmd == "preview":
            target_root = Path(args.target_root).expanduser().resolve()
            validate_root_within_project(
                "target_root",
                args.target_root,
                root=target_root,
                project_root=project_root,
                artifact_root=None,
            )
            validate_checkpoint_restore_paths(args, project_root=project_root)
            record = load_json(Path(args.checkpoint_record_file))
            preview = restore_preview(record, Path(args.target_root))
            save_json(Path(args.output), preview)
            print(json.dumps({"result": "OK", "restore_status": preview["restore_status"], "restore_supported": preview["restore_supported"]}, ensure_ascii=True))
            return 0
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
