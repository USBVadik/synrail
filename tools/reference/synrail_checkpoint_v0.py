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
    from .synrail_repair_handoff_v0 import build_resumability
    from .synrail_validate_v0 import load_json as load_json_document, validate_document
except ImportError:
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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


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


def _git_has_uncommitted(project_root: Path) -> bool:
    """Return True if the workspace has uncommitted changes (staged or unstaged)."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
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
        # First reset to the original HEAD
        reset = subprocess.run(
            ["git", "checkout", head_ref, "--force"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if reset.returncode != 0:
            return False, f"git checkout failed: {reset.stderr.strip()}"
        # Then apply stashed changes if any
        if stash_ref:
            apply = subprocess.run(
                ["git", "stash", "apply", stash_ref],
                cwd=str(project_root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if apply.returncode != 0:
                return False, f"git stash apply failed: {apply.stderr.strip()}"
        return True, ""
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)


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


def _file_copy_restore(snapshot_dir: Path, project_root: Path) -> tuple[bool, str]:
    """Restore project files from a file-copy snapshot. Returns (success, error_message).

    Removes existing non-excluded project content first, then copies back.
    """
    try:
        # Remove existing project files (except excluded dirs)
        for item in sorted(project_root.iterdir()):
            if item.name in _FILE_COPY_EXCLUDE_DIRS:
                continue
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        # Copy back from snapshot
        for item in sorted(snapshot_dir.iterdir()):
            dest = project_root / item.name
            if item.is_file():
                shutil.copy2(item, dest)
            elif item.is_dir():
                shutil.copytree(item, dest)
        return True, ""
    except Exception as exc:
        return False, str(exc)


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
            stash_ref = ""
            if _git_has_uncommitted(project_root):
                stash_ref = _git_stash_create(project_root)
            workspace_snapshot = {
                "type": "git",
                "project_root": str(project_root),
                "head_ref": head_ref,
                "stash_ref": stash_ref,
                "has_uncommitted": bool(stash_ref),
            }
        else:
            # No git HEAD available — fall back to file-copy snapshot.
            snapshot_dir = checkpoint_root / "workspace_files"
            ok, err, count = _file_copy_snapshot(project_root, snapshot_dir)
            if ok:
                workspace_snapshot = {
                    "type": "file_copy",
                    "project_root": str(project_root),
                    "snapshot_dir": str(snapshot_dir),
                    "file_count": count,
                }
            else:
                workspace_snapshot = {
                    "type": "none",
                    "project_root": str(project_root),
                    "reason": f"file-copy snapshot failed: {err}",
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
        document = load_json_document(artifact_path)
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
    state = load_json(checkpoint_root / state_entry["path"])
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
    missing, schema_errors = validate_manifest_artifacts(record, root_override=root_override)
    consistency_errors = [] if missing else state_consistency_errors(record, root_override=root_override)
    unexpected_paths = unexpected_artifact_paths(record, root_override=root_override)
    failure_reasons = []
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
    verified["result"] = "OK" if not (missing or schema_errors or consistency_errors or unexpected_paths) else "BLOCKED"
    verified["verification"] = {
        "status": "PASSED" if not (missing or schema_errors or consistency_errors or unexpected_paths) else "FAILED",
        "safe_point_eligible": record.get("safe_point_eligible", False) and not consistency_errors,
        "required_artifacts_present": not missing,
        "schema_validation_passed": not schema_errors,
        "state_consistency_passed": not consistency_errors,
        "stale_artifacts_detected": unexpected_paths,
        "failure_reasons": failure_reasons + missing + schema_errors + consistency_errors + unexpected_paths,
    }
    verified["next_safe_step"] = (
        "checkpoint verified; restore is now allowed"
        if verified["result"] == "OK"
        else "repair checkpoint artifact set before using restore"
    )
    return verified


def backup_target_artifacts(record: dict, target_root: Path) -> tuple[Path, list[str]]:
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


def restore_manifest(record: dict, target_root: Path) -> list[str]:
    restored_ids: list[str] = []
    checkpoint_root = Path(record["checkpoint_root"])
    for artifact in record.get("artifact_manifest", []):
        source_path = checkpoint_root / artifact["path"]
        target_path = target_root / artifact["path"]
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)
        restored_ids.append(artifact["artifact_id"])
    return restored_ids


def rollback_from_backup(record: dict, target_root: Path, backup_root: Path, backed_up_ids: list[str]) -> tuple[str, list[str], list[str]]:
    failures: list[str] = []
    rolled_back_ids: list[str] = []
    try:
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
    preverify = verify_record(record)
    if preverify["result"] != "OK":
        blocked = dict(preverify)
        blocked["event_type"] = "RESTORE"
        blocked["result"] = "BLOCKED"
        blocked["restore"] = {
            "status": "RESTORE_FAILED",
            "target_root": str(target_root),
            "restore_verification_required": True,
            "restored_artifact_ids": [],
            "failure_reasons": list(preverify["verification"].get("failure_reasons", [])),
        }
        blocked["rollback"] = rollback_template()
        blocked["next_safe_step"] = "verify checkpoint successfully before attempting restore"
        return blocked

    # For pre-run snapshots with a git workspace, restore the project files first.
    workspace_snapshot = record.get("workspace_snapshot", {})
    workspace_restored = False
    workspace_error = ""
    if workspace_snapshot.get("type") == "git" and workspace_snapshot.get("head_ref"):
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
    if workspace_snapshot and not workspace_restored:
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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.cmd == "create":
        record = create_record(args)
        save_json(Path(args.output), record)
        print(json.dumps({"result": record["result"], "checkpoint_id": record["checkpoint_id"]}, ensure_ascii=True))
        return 0

    if args.cmd == "verify":
        record = load_json(Path(args.checkpoint_record_file))
        verified = verify_record(record)
        save_json(Path(args.output), verified)
        print(json.dumps({"result": verified["result"], "verification_status": verified["verification"]["status"]}, ensure_ascii=True))
        return 0 if verified["result"] == "OK" else 2

    if args.cmd == "restore":
        record = load_json(Path(args.checkpoint_record_file))
        restored = restore_record(record, Path(args.target_root))
        save_json(Path(args.output), restored)
        print(json.dumps({"result": restored["result"], "event_type": restored["event_type"], "rollback_status": restored["rollback"]["status"]}, ensure_ascii=True))
        return 0 if restored["result"] == "OK" else 2

    parser.error(f"unknown command {args.cmd}")
    return 2


if __name__ == "__main__":
    sys.exit(main())
