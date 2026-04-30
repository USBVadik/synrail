#!/usr/bin/env python3
"""Machine-readable artifact consistency checker for Synrail runtime surfaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json
from typing import Any

try:
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


ARTIFACT_CONSISTENCY_PATH_SCOPES = {
    "state_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
    "report_file": ARTIFACT_SCOPE,
    "orchestration_file": ARTIFACT_SCOPE,
    "run_file": ARTIFACT_SCOPE,
    "repair_packet_file": ARTIFACT_SCOPE,
    "repair_handoff_file": ARTIFACT_SCOPE,
    "repair_receipt_file": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_artifact_consistency_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=ARTIFACT_CONSISTENCY_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


CONFLICT_PRECEDENCE = [
    "CORRUPT_DERIVED_ARTIFACT",
    "RUN_ID_MISMATCH",
    "TASK_CLASS_MISMATCH",
    "DERIVED_FROM_STATE_MISMATCH",
    "RESULTING_STATE_MISMATCH",
]




def load_json_safe(path: Path) -> tuple[dict | None, str]:
    try:
        return json.loads(path.read_text()), ""
    except (OSError, json.JSONDecodeError) as exc:
        return None, str(exc)




def append_unique(values: list[str], value: str) -> None:
    if value and value not in values:
        values.append(value)


def compare_identity(*, artifact_id: str, payload: dict, state: dict, failures: list[dict], conflicting_ids: list[str]) -> None:
    if payload.get("run_id", state["run_id"]) != state["run_id"]:
        append_unique(conflicting_ids, artifact_id)
        failures.append(
            {
                "type": "RUN_ID_MISMATCH",
                "artifact_id": artifact_id,
                "detail": f"{artifact_id} does not match source run_id",
            }
        )
    if payload.get("task_class", state["task_class"]) != state["task_class"]:
        append_unique(conflicting_ids, artifact_id)
        failures.append(
            {
                "type": "TASK_CLASS_MISMATCH",
                "artifact_id": artifact_id,
                "detail": f"{artifact_id} does not match source task_class",
            }
        )


def compare_state_field(
    *,
    artifact_id: str,
    field_value: str,
    expected_state: str,
    failure_type: str,
    failures: list[dict],
    stale_ids: list[str],
) -> None:
    if not field_value or field_value == expected_state:
        return
    append_unique(stale_ids, artifact_id)
    failures.append(
        {
            "type": failure_type,
            "artifact_id": artifact_id,
            "detail": f"{artifact_id} refers to {field_value} while source-of-truth state is {expected_state}",
        }
    )


def dominant_conflict(failures: list[dict]) -> str:
    seen = {failure["type"] for failure in failures}
    for failure_type in CONFLICT_PRECEDENCE:
        if failure_type in seen:
            return failure_type
    return ""


def record_corrupt_artifact(
    *,
    artifact_id: str,
    detail: str,
    failures: list[dict],
    corrupt_ids: list[str],
) -> None:
    append_unique(corrupt_ids, artifact_id)
    failures.append(
        {
            "type": "CORRUPT_DERIVED_ARTIFACT",
            "artifact_id": artifact_id,
            "detail": f"{artifact_id} is corrupt or unreadable: {detail}",
        }
    )


def build_record(
    *,
    state: dict,
    report: dict | None = None,
    orchestration: dict | None = None,
    run_artifact: dict | None = None,
    repair_packet: dict | None = None,
    repair_handoff: dict | None = None,
    repair_receipt: dict | None = None,
    artifact_errors: dict[str, str] | None = None,
) -> dict:
    failures: list[dict] = []
    checked_artifacts: list[str] = ["state_file"]
    stale_artifact_ids: list[str] = []
    conflicting_artifact_ids: list[str] = []
    corrupt_artifact_ids: list[str] = []
    artifact_actions: dict[str, str] = {"state_file": "TRUST_SOURCE_OF_TRUTH"}
    artifact_errors = artifact_errors or {}

    for artifact_id, detail in artifact_errors.items():
        checked_artifacts.append(artifact_id)
        record_corrupt_artifact(
            artifact_id=artifact_id,
            detail=detail,
            failures=failures,
            corrupt_ids=corrupt_artifact_ids,
        )
        artifact_actions[artifact_id] = "RESTORE_FROM_CHECKPOINT_OR_REEMIT"

    if report:
        checked_artifacts.append("report")
        compare_identity(artifact_id="report", payload=report, state=state, failures=failures, conflicting_ids=conflicting_artifact_ids)
        compare_state_field(
            artifact_id="report",
            field_value=report.get("resulting_state", ""),
            expected_state=state["state"],
            failure_type="RESULTING_STATE_MISMATCH",
            failures=failures,
            stale_ids=stale_artifact_ids,
        )
        artifact_actions["report"] = "KEEP_DERIVED_ARTIFACT" if "report" not in stale_artifact_ids and "report" not in conflicting_artifact_ids else "REEMIT_FROM_STATE"

    if orchestration:
        checked_artifacts.append("orchestration")
        compare_identity(artifact_id="orchestration", payload=orchestration, state=state, failures=failures, conflicting_ids=conflicting_artifact_ids)
        compare_state_field(
            artifact_id="orchestration",
            field_value=orchestration.get("resulting_state", ""),
            expected_state=state["state"],
            failure_type="RESULTING_STATE_MISMATCH",
            failures=failures,
            stale_ids=stale_artifact_ids,
        )
        artifact_actions["orchestration"] = (
            "KEEP_DERIVED_ARTIFACT"
            if "orchestration" not in stale_artifact_ids and "orchestration" not in conflicting_artifact_ids
            else "REEMIT_FROM_STATE"
        )

    if run_artifact:
        checked_artifacts.append("run")
        compare_identity(artifact_id="run", payload=run_artifact, state=state, failures=failures, conflicting_ids=conflicting_artifact_ids)
        compare_state_field(
            artifact_id="run",
            field_value=run_artifact.get("resulting_state", {}).get("state", ""),
            expected_state=state["state"],
            failure_type="RESULTING_STATE_MISMATCH",
            failures=failures,
            stale_ids=stale_artifact_ids,
        )
        artifact_actions["run"] = "KEEP_DERIVED_ARTIFACT" if "run" not in stale_artifact_ids and "run" not in conflicting_artifact_ids else "REEMIT_FROM_STATE"

    if repair_packet:
        checked_artifacts.append("repair_packet")
        compare_identity(artifact_id="repair_packet", payload=repair_packet, state=state, failures=failures, conflicting_ids=conflicting_artifact_ids)
        compare_state_field(
            artifact_id="repair_packet",
            field_value=repair_packet.get("from_state", ""),
            expected_state=state["state"],
            failure_type="DERIVED_FROM_STATE_MISMATCH",
            failures=failures,
            stale_ids=stale_artifact_ids,
        )
        artifact_actions["repair_packet"] = (
            "KEEP_DERIVED_ARTIFACT"
            if "repair_packet" not in stale_artifact_ids and "repair_packet" not in conflicting_artifact_ids
            else "REEMIT_FROM_STATE"
        )

    if repair_handoff:
        checked_artifacts.append("repair_handoff")
        compare_identity(artifact_id="repair_handoff", payload=repair_handoff, state=state, failures=failures, conflicting_ids=conflicting_artifact_ids)
        compare_state_field(
            artifact_id="repair_handoff",
            field_value=repair_handoff.get("from_state", ""),
            expected_state=state["state"],
            failure_type="DERIVED_FROM_STATE_MISMATCH",
            failures=failures,
            stale_ids=stale_artifact_ids,
        )
        artifact_actions["repair_handoff"] = (
            "KEEP_DERIVED_ARTIFACT"
            if "repair_handoff" not in stale_artifact_ids and "repair_handoff" not in conflicting_artifact_ids
            else "REEMIT_FROM_STATE"
        )

    if repair_receipt:
        checked_artifacts.append("repair_receipt")
        compare_identity(artifact_id="repair_receipt", payload=repair_receipt, state=state, failures=failures, conflicting_ids=conflicting_artifact_ids)
        compare_state_field(
            artifact_id="repair_receipt",
            field_value=repair_receipt.get("resulting_state", ""),
            expected_state=state["state"],
            failure_type="RESULTING_STATE_MISMATCH",
            failures=failures,
            stale_ids=stale_artifact_ids,
        )
        artifact_actions["repair_receipt"] = (
            "KEEP_DERIVED_ARTIFACT"
            if "repair_receipt" not in stale_artifact_ids and "repair_receipt" not in conflicting_artifact_ids
            else "REEMIT_FROM_STATE"
        )

    result = "CONSISTENT" if not failures else "INCONSISTENT"
    dominant = dominant_conflict(failures)
    if corrupt_artifact_ids:
        next_action = "restore corrupt derived artifacts from a verified checkpoint or re-emit them from the current state"
    elif result == "CONSISTENT":
        next_action = "continue using the current source-of-truth state and derived artifacts"
    else:
        next_action = "re-emit derived artifacts from the current state or restore from a verified checkpoint"
    return {
        "schema_version": "artifact_consistency_record_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "source_of_truth": {
            "artifact_id": "state_file",
            "state": state["state"],
            "run_id": state["run_id"],
            "task_class": state["task_class"],
        },
        "checked_artifacts": checked_artifacts,
        "update_model": "ATOMIC_OR_ROLLBACKABLE_DERIVED_SURFACES",
        "conflict_precedence": list(CONFLICT_PRECEDENCE),
        "result": result,
        "dominant_conflict": dominant,
        "failure_reasons": [failure["detail"] for failure in failures],
        "stale_artifact_ids": stale_artifact_ids,
        "conflicting_artifact_ids": conflicting_artifact_ids,
        "corrupt_artifact_ids": corrupt_artifact_ids,
        "artifact_actions": artifact_actions,
        "next_action": next_action,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-artifact-consistency-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report-file")
    parser.add_argument("--orchestration-file")
    parser.add_argument("--run-file")
    parser.add_argument("--repair-packet-file")
    parser.add_argument("--repair-handoff-file")
    parser.add_argument("--repair-receipt-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        artifact_root = Path(args.state_file).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "state_file",
            args.state_file,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_artifact_consistency_paths(args, artifact_root=artifact_root, project_root=project_root)
        state = load_json(Path(args.state_file))

        artifact_errors: dict[str, str] = {}

        def optional_artifact(path_value: str | None, artifact_id: str) -> dict | None:
            if not path_value:
                return None
            payload, error = load_json_safe(Path(path_value))
            if error:
                artifact_errors[artifact_id] = error
                return None
            return payload

        record = build_record(
            state=state,
            report=optional_artifact(args.report_file, "report"),
            orchestration=optional_artifact(args.orchestration_file, "orchestration"),
            run_artifact=optional_artifact(args.run_file, "run"),
            repair_packet=optional_artifact(args.repair_packet_file, "repair_packet"),
            repair_handoff=optional_artifact(args.repair_handoff_file, "repair_handoff"),
            repair_receipt=optional_artifact(args.repair_receipt_file, "repair_receipt"),
            artifact_errors=artifact_errors,
        )
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(json.dumps({"result": record["result"], "dominant_conflict": record["dominant_conflict"]}, ensure_ascii=True))
    return 0 if record["result"] == "CONSISTENT" else 2


if __name__ == "__main__":
    sys.exit(main())
