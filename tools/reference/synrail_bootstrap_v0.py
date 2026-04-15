#!/usr/bin/env python3
"""Runtime-owned controlled-start bootstrap helpers for Synrail."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path


BOOTSTRAP_SCHEMA_VERSION = "bootstrap_record_v0"
BOOTSTRAP_VALIDATION_SCHEMA_VERSION = "bootstrap_validation_record_v0"
PROOF_REQUEST_SCHEMA_VERSION = "proof_request_record_v0"


def _display_path(path: Path, *, base: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(base.resolve())) or "."
    except ValueError:
        return str(resolved)


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_bootstrap_record(
    *,
    run_id: str,
    task_class: str,
    started_via: str,
    project_root: Path,
    artifact_root: Path,
    task_identity: str,
    prompt_identity: str,
    target_path: str,
    target_classification: str,
    target_identity: str,
    baseline_identity: str,
    execution_surface_identity: str,
    intended_run_class: str,
    intended_proof_path: dict,
) -> dict:
    return {
        "schema_version": BOOTSTRAP_SCHEMA_VERSION,
        "run_id": run_id,
        "task_class": task_class,
        "started_via": started_via,
        "bootstrap_time_utc": utc_now_iso(),
        "controlled_mode": True,
        "project_root": str(project_root.resolve()),
        "artifact_root": str(artifact_root.resolve()),
        "task_identity": task_identity.strip(),
        "prompt_identity": prompt_identity.strip(),
        "bounded_scope": {
            "summary": "Only the bounded task request on the attested target surface for this run.",
            "project_root": _display_path(project_root, base=project_root),
            "artifact_root": _display_path(artifact_root, base=project_root),
        },
        "target_path": target_path,
        "target_classification": target_classification,
        "target_identity": target_identity,
        "baseline_identity": baseline_identity,
        "execution_surface_identity": execution_surface_identity,
        "intended_run_class": intended_run_class,
        "intended_proof_path": intended_proof_path,
    }


def build_proof_request_record(
    *,
    run_id: str,
    task_class: str,
    task_identity: str,
    project_root: Path,
    artifact_root: Path,
) -> dict:
    final_result = artifact_root / "final_result.json"
    readback = artifact_root / "readback.txt"
    scenario_proof = artifact_root / "scenario_proof.txt"
    return {
        "schema_version": PROOF_REQUEST_SCHEMA_VERSION,
        "run_id": run_id,
        "task_class": task_class,
        "task_identity": task_identity.strip(),
        "summary": "Synrail is waiting for proof artifacts from this controlled run.",
        "preferred_artifacts": {
            "final_result": _display_path(final_result, base=project_root),
            "readback": _display_path(readback, base=project_root),
            "scenario_proof": _display_path(scenario_proof, base=project_root),
        },
        "required_sections": [
            "final_result",
            "modified_files",
            "diff_provenance",
            "readback",
            "scenario_proof",
            "artifact_identity",
            "cleanup_status",
        ],
        "next_safe_step": "Leave the preferred proof artifacts in place, then run synrail check.",
    }


def validate_bootstrap_record(
    record: dict | None,
    *,
    state: dict,
    profile: dict,
    artifact_root: Path,
) -> dict:
    reason = "CONTROLLED_BOOTSTRAP_CONFIRMED"
    status = "VALID"

    run_id_matches = False
    task_class_matches = False
    task_identity_present = False
    prompt_identity_present = False
    project_root_matches = False
    artifact_root_matches = False
    target_path_matches = False
    target_classification_matches = False
    target_identity_matches = False
    baseline_identity_matches = False
    execution_surface_identity_matches = False
    intended_run_class_matches = False
    controlled_mode = False
    started_via = ""

    if record is None:
        status = "INVALID"
        reason = "CONTROLLED_BOOTSTRAP_MISSING"
    elif record.get("schema_version") != BOOTSTRAP_SCHEMA_VERSION:
        status = "INVALID"
        reason = "CONTROLLED_BOOTSTRAP_INVALID_SCHEMA"
    else:
        controlled_mode = bool(record.get("controlled_mode", False))
        started_via = record.get("started_via", "")
        run_id_matches = record.get("run_id", "") == state.get("run_id", "")
        task_class_matches = record.get("task_class", "") == state.get("task_class", "")
        task_identity_present = bool(record.get("task_identity", "").strip())
        prompt_identity_present = bool(record.get("prompt_identity", "").strip())
        project_root_matches = record.get("project_root", "") == profile.get("project_root", "")
        artifact_root_matches = record.get("artifact_root", "") == str(artifact_root.resolve())
        target_path_matches = record.get("target_path", "") == profile.get("target_path", "")
        target_classification_matches = record.get("target_classification", "") == profile.get("target_classification", "")
        target_identity_matches = record.get("target_identity", "") == profile.get("execution_surface_identity", "")
        baseline_identity_matches = record.get("baseline_identity", "") == profile.get("baseline_identity", "")
        execution_surface_identity_matches = record.get("execution_surface_identity", "") == profile.get("execution_surface_identity", "")
        intended_run_class_matches = record.get("intended_run_class", "") == profile.get("intended_run_class", "")

        if not controlled_mode:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_NOT_CONTROLLED"
        elif not run_id_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_RUN_ID_MISMATCH"
        elif not task_class_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_TASK_CLASS_MISMATCH"
        elif not project_root_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_PROJECT_ROOT_MISMATCH"
        elif not artifact_root_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_ARTIFACT_ROOT_MISMATCH"
        elif not task_identity_present:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_TASK_IDENTITY_MISSING"
        elif not prompt_identity_present:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_PROMPT_IDENTITY_MISSING"
        elif not target_path_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_TARGET_PATH_MISMATCH"
        elif not target_classification_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_TARGET_CLASSIFICATION_MISMATCH"
        elif not target_identity_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_TARGET_IDENTITY_MISMATCH"
        elif not baseline_identity_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_BASELINE_IDENTITY_MISMATCH"
        elif not execution_surface_identity_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_EXECUTION_SURFACE_IDENTITY_MISMATCH"
        elif not intended_run_class_matches:
            status = "INVALID"
            reason = "CONTROLLED_BOOTSTRAP_RUN_CLASS_MISMATCH"

    return {
        "schema_version": BOOTSTRAP_VALIDATION_SCHEMA_VERSION,
        "run_id": state.get("run_id", ""),
        "task_class": state.get("task_class", ""),
        "status": status,
        "reason": reason,
        "controlled_mode": controlled_mode,
        "started_via": started_via,
        "run_id_matches": run_id_matches,
        "task_class_matches": task_class_matches,
        "task_identity_present": task_identity_present,
        "prompt_identity_present": prompt_identity_present,
        "project_root_matches": project_root_matches,
        "artifact_root_matches": artifact_root_matches,
        "target_path_matches": target_path_matches,
        "target_classification_matches": target_classification_matches,
        "target_identity_matches": target_identity_matches,
        "baseline_identity_matches": baseline_identity_matches,
        "execution_surface_identity_matches": execution_surface_identity_matches,
        "intended_run_class_matches": intended_run_class_matches,
    }
