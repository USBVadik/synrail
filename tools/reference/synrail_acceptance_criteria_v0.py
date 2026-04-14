#!/usr/bin/env python3
"""Explicit acceptance-criteria record and validation for Synrail."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

try:
    from .synrail_bundle_v0 import REQUIRED_SECTION_NAMES
except ImportError:
    from synrail_bundle_v0 import REQUIRED_SECTION_NAMES


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


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def criteria_revision_id(payload: dict) -> str:
    material = "|".join(
        [
            payload.get("criteria_standard_id", ""),
            payload.get("criteria_owner", ""),
            payload.get("task_class", ""),
            payload.get("project_type", ""),
            payload.get("target_classification", ""),
            payload.get("intended_run_class", ""),
            ",".join(payload.get("required_gate_ids", [])),
            ",".join(payload.get("required_bundle_sections", [])),
        ]
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"acceptance_criteria_v0:{digest}"


def build_record(profile: dict) -> dict:
    record = {
        "schema_version": "acceptance_criteria_record_v0",
        "criteria_standard_id": "exact_task_acceptance",
        "criteria_owner": "synrail_closure_v0",
        "criteria_revision_id": "",
        "task_class": profile.get("task_class", ""),
        "project_type": profile.get("project_type", "generic"),
        "target_classification": profile.get("target_classification", ""),
        "intended_run_class": profile.get("intended_run_class", ""),
        "required_gate_ids": list(REQUIRED_GATE_IDS),
        "required_bundle_sections": list(REQUIRED_SECTION_NAMES),
        "acceptance_rules": list(ACCEPTANCE_RULES),
    }
    record["criteria_revision_id"] = criteria_revision_id(record)
    return record


def validate_record(criteria: dict, *, state: dict, profile: dict) -> dict:
    gate_ids = list(criteria.get("required_gate_ids", []))
    bundle_sections = list(criteria.get("required_bundle_sections", []))

    task_class_matches = bool(criteria.get("task_class")) and criteria.get("task_class", "") == state.get("task_class", "") == profile.get("task_class", "")
    project_type_matches = criteria.get("project_type", "") == profile.get("project_type", "")
    target_classification_matches = criteria.get("target_classification", "") == profile.get("target_classification", "")
    intended_run_class_matches = criteria.get("intended_run_class", "") == profile.get("intended_run_class", "")
    required_gate_ids_match = gate_ids == REQUIRED_GATE_IDS
    required_bundle_sections_match = bundle_sections == REQUIRED_SECTION_NAMES

    status = "VALID"
    reason = "CRITERIA_VALID"

    if criteria.get("schema_version", "") != "acceptance_criteria_record_v0":
        status = "INVALID"
        reason = "CRITERIA_SCHEMA_UNSUPPORTED"
    elif not criteria.get("criteria_revision_id", ""):
        status = "INVALID"
        reason = "CRITERIA_REVISION_MISSING"
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
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-acceptance-criteria-v0")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("--project-profile-file", required=True)
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

    if args.cmd == "build":
        record = build_record(load_json(Path(args.project_profile_file)))
        save_json(Path(args.output), record)
        print(json.dumps({"result": "OK", "criteria_revision_id": record["criteria_revision_id"]}, ensure_ascii=True))
        return 0

    validation = validate_record(
        load_json(Path(args.criteria_file)),
        state=load_json(Path(args.state_file)),
        profile=load_json(Path(args.project_profile_file)),
    )
    save_json(Path(args.output), validation)
    print(json.dumps({"result": "OK", "status": validation["status"], "reason": validation["reason"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
