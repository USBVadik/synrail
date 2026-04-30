#!/usr/bin/env python3
"""Explicit acceptance-criteria record and validation for Synrail."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

try:
    from .synrail_bundle_v0 import REQUIRED_SECTION_NAMES
    from .synrail_io_v0 import load_json, save_json
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_bundle_v0 import REQUIRED_SECTION_NAMES
    from synrail_io_v0 import load_json, save_json
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


ACCEPTANCE_BUILD_PATH_SCOPES = {
    "project_profile_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
}

ACCEPTANCE_VALIDATE_PATH_SCOPES = {
    "criteria_file": ARTIFACT_SCOPE,
    "state_file": ARTIFACT_SCOPE,
    "project_profile_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_acceptance_build_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=ACCEPTANCE_BUILD_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def validate_acceptance_validate_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=ACCEPTANCE_VALIDATE_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


REQUIRED_GATE_IDS = [
    "TARGET_SURFACE_ATTESTED",
    "DOCTOR_GREEN",
    "TASK_IDENTITY_CONFIRMED",
    "EXECUTION_COMPLETED",
    "PROOF_BUNDLE_COMPLETE",
    "RECOVERY_REVERIFIED_WHEN_PENDING",
]

ACCEPTANCE_RULES = [
    "The target surface must be attested before acceptance.",
    "Doctor must be green before acceptance.",
    "The exact task request and target must still be confirmed.",
    "Execution must be completed for the current run.",
    "The proof bundle must be complete and reviewable.",
    "If recovery is pending, reverification must finish before acceptance.",
]


def short_fingerprint(*parts: str) -> str:
    material = "|".join(parts)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]


def project_profile_fingerprint(profile: dict) -> str:
    # Acceptance truth should track stable project/run identity, not the currently
    # discovered final-result filename under that same contour.
    digest = short_fingerprint(
        profile.get("schema_version", ""),
        profile.get("project_root", ""),
        profile.get("project_type", ""),
        profile.get("task_class", ""),
        profile.get("target_classification", ""),
        profile.get("intended_run_class", ""),
        profile.get("baseline_identity", ""),
        profile.get("execution_surface_identity", ""),
    )
    return f"project_profile_v0:{digest}"


def criteria_revision_id(payload: dict) -> str:
    digest = short_fingerprint(
        payload.get("criteria_standard_id", ""),
        payload.get("criteria_owner", ""),
        payload.get("project_profile_fingerprint", ""),
        payload.get("task_class", ""),
        payload.get("project_type", ""),
        payload.get("target_classification", ""),
        payload.get("intended_run_class", ""),
        ",".join(payload.get("required_gate_ids", [])),
        ",".join(payload.get("required_bundle_sections", [])),
    )
    return f"acceptance_criteria_v0:{digest}"


def build_record(profile: dict, *, generated_by: str) -> dict:
    profile_fp = project_profile_fingerprint(profile)
    record = {
        "schema_version": "acceptance_criteria_record_v0",
        "criteria_standard_id": "exact_task_acceptance",
        "criteria_owner": "synrail_closure_v0",
        "criteria_revision_id": "",
        "project_profile_fingerprint": profile_fp,
        "task_class": profile.get("task_class", ""),
        "project_type": profile.get("project_type", "generic"),
        "target_classification": profile.get("target_classification", ""),
        "intended_run_class": profile.get("intended_run_class", ""),
        "required_gate_ids": list(REQUIRED_GATE_IDS),
        "required_bundle_sections": list(REQUIRED_SECTION_NAMES),
        "acceptance_rules": list(ACCEPTANCE_RULES),
        "criteria_provenance": {
            "source_profile_schema_version": profile.get("schema_version", ""),
            "source_profile_fingerprint": profile_fp,
            "generated_at_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "generated_by": generated_by,
        },
    }
    record["criteria_revision_id"] = criteria_revision_id(record)
    return record


def invalid_validation_record(reason: str, *, criteria_revision_id_value: str = "") -> dict:
    return {
        "schema_version": "acceptance_criteria_validation_record_v0",
        "criteria_revision_id": criteria_revision_id_value,
        "status": "INVALID",
        "reason": reason,
        "task_class_matches": False,
        "project_type_matches": False,
        "target_classification_matches": False,
        "intended_run_class_matches": False,
        "required_gate_ids_match": False,
        "required_bundle_sections_match": False,
        "criteria_standard_matches": False,
        "criteria_owner_matches": False,
        "project_profile_fingerprint_matches": False,
        "criteria_revision_matches": False,
        "provenance_complete": False,
        "provenance_profile_fingerprint_matches": False,
    }


def validate_record(criteria: dict, *, state: dict, profile: dict) -> dict:
    gate_ids = list(criteria.get("required_gate_ids", []))
    bundle_sections = list(criteria.get("required_bundle_sections", []))
    provenance = criteria.get("criteria_provenance", {})
    expected_profile_fingerprint = project_profile_fingerprint(profile)
    expected_revision_id = criteria_revision_id(criteria)

    task_class_matches = bool(criteria.get("task_class")) and criteria.get("task_class", "") == state.get("task_class", "") == profile.get("task_class", "")
    project_type_matches = criteria.get("project_type", "") == profile.get("project_type", "")
    target_classification_matches = criteria.get("target_classification", "") == profile.get("target_classification", "")
    intended_run_class_matches = criteria.get("intended_run_class", "") == profile.get("intended_run_class", "")
    required_gate_ids_match = gate_ids == REQUIRED_GATE_IDS
    required_bundle_sections_match = bundle_sections == REQUIRED_SECTION_NAMES
    criteria_standard_matches = criteria.get("criteria_standard_id", "") == "exact_task_acceptance"
    criteria_owner_matches = criteria.get("criteria_owner", "") == "synrail_closure_v0"
    project_profile_fingerprint_matches = criteria.get("project_profile_fingerprint", "") == expected_profile_fingerprint
    criteria_revision_matches = criteria.get("criteria_revision_id", "") == expected_revision_id
    provenance_complete = all(
        [
            bool(provenance.get("source_profile_schema_version", "")),
            bool(provenance.get("source_profile_fingerprint", "")),
            bool(provenance.get("generated_at_utc", "")),
            bool(provenance.get("generated_by", "")),
        ]
    )
    provenance_profile_fingerprint_matches = provenance.get("source_profile_fingerprint", "") == criteria.get("project_profile_fingerprint", "")

    status = "VALID"
    reason = "CRITERIA_VALID"

    if criteria.get("schema_version", "") != "acceptance_criteria_record_v0":
        status = "INVALID"
        reason = "CRITERIA_SCHEMA_UNSUPPORTED"
    elif not criteria_standard_matches:
        status = "INVALID"
        reason = "CRITERIA_STANDARD_UNSUPPORTED"
    elif not criteria_owner_matches:
        status = "INVALID"
        reason = "CRITERIA_OWNER_UNSUPPORTED"
    elif not criteria.get("criteria_revision_id", ""):
        status = "INVALID"
        reason = "CRITERIA_REVISION_MISSING"
    elif not criteria.get("project_profile_fingerprint", ""):
        status = "INVALID"
        reason = "CRITERIA_PROFILE_FINGERPRINT_MISSING"
    elif not provenance_complete:
        status = "INVALID"
        reason = "CRITERIA_PROVENANCE_INCOMPLETE"
    elif not provenance_profile_fingerprint_matches:
        status = "INVALID"
        reason = "CRITERIA_PROVENANCE_CONTRADICTS_PROFILE"
    elif not criteria_revision_matches:
        status = "INVALID"
        reason = "CRITERIA_REVISION_MISMATCH"
    elif not task_class_matches:
        status = "STALE"
        reason = "CRITERIA_TASK_CLASS_STALE"
    elif not project_type_matches:
        status = "STALE"
        reason = "CRITERIA_PROJECT_TYPE_STALE"
    elif not target_classification_matches:
        status = "STALE"
        reason = "CRITERIA_TARGET_CLASSIFICATION_STALE"
    elif not intended_run_class_matches:
        status = "STALE"
        reason = "CRITERIA_RUN_CLASS_STALE"
    elif not project_profile_fingerprint_matches:
        status = "STALE"
        reason = "CRITERIA_PROFILE_FINGERPRINT_STALE"
    elif not required_gate_ids_match:
        status = "STALE"
        reason = "CRITERIA_GATE_SET_STALE"
    elif not required_bundle_sections_match:
        status = "STALE"
        reason = "CRITERIA_PROOF_STANDARD_STALE"

    return {
        "schema_version": "acceptance_criteria_validation_record_v0",
        "criteria_revision_id": criteria.get("criteria_revision_id", ""),
        "status": status,
        "reason": reason,
        "task_class_matches": task_class_matches,
        "project_type_matches": project_type_matches,
        "target_classification_matches": target_classification_matches,
        "intended_run_class_matches": intended_run_class_matches,
        "required_gate_ids_match": required_gate_ids_match,
        "required_bundle_sections_match": required_bundle_sections_match,
        "criteria_standard_matches": criteria_standard_matches,
        "criteria_owner_matches": criteria_owner_matches,
        "project_profile_fingerprint_matches": project_profile_fingerprint_matches,
        "criteria_revision_matches": criteria_revision_matches,
        "provenance_complete": provenance_complete,
        "provenance_profile_fingerprint_matches": provenance_profile_fingerprint_matches,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-acceptance-criteria-v0")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("--project-profile-file", required=True)
    p_build.add_argument("--generated-by", default="synrail acceptance build")
    p_build.add_argument("--output", required=True)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--criteria-file", required=True)
    p_validate.add_argument("--state-file", required=True)
    p_validate.add_argument("--project-profile-file", required=True)
    p_validate.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        project_root = current_project_root()
        if args.cmd == "build":
            artifact_root = Path(args.project_profile_file).expanduser().resolve().parent
            validate_root_within_project(
                "project_profile_file",
                args.project_profile_file,
                root=artifact_root,
                project_root=project_root,
                artifact_root=artifact_root,
            )
            artifact_root.mkdir(parents=True, exist_ok=True)
            validate_acceptance_build_paths(args, artifact_root=artifact_root, project_root=project_root)
            record = build_record(load_json(Path(args.project_profile_file)), generated_by=args.generated_by)
            save_json(Path(args.output), record)
            print(json.dumps({"result": "OK", "criteria_revision_id": record["criteria_revision_id"]}, ensure_ascii=True))
            return 0

        artifact_root = Path(args.criteria_file).expanduser().resolve().parent
        validate_root_within_project(
            "criteria_file",
            args.criteria_file,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_acceptance_validate_paths(args, artifact_root=artifact_root, project_root=project_root)
        validation = validate_record(
            load_json(Path(args.criteria_file)),
            state=load_json(Path(args.state_file)),
            profile=load_json(Path(args.project_profile_file)),
        )
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2

    save_json(Path(args.output), validation)
    print(json.dumps({"result": "OK", "status": validation["status"], "reason": validation["reason"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
