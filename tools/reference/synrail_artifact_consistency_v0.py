#!/usr/bin/env python3
"""Machine-readable artifact consistency checker for Synrail runtime surfaces."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CONFLICT_PRECEDENCE = [
    "RUN_ID_MISMATCH",
    "TASK_CLASS_MISMATCH",
    "DERIVED_FROM_STATE_MISMATCH",
    "RESULTING_STATE_MISMATCH",
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


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


def build_record(
    *,
    state: dict,
    report: dict | None = None,
    orchestration: dict | None = None,
    run_artifact: dict | None = None,
    repair_packet: dict | None = None,
    repair_handoff: dict | None = None,
    repair_receipt: dict | None = None,
) -> dict:
    failures: list[dict] = []
    checked_artifacts: list[str] = ["state_file"]
    stale_artifact_ids: list[str] = []
    conflicting_artifact_ids: list[str] = []

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

    result = "CONSISTENT" if not failures else "INCONSISTENT"
    dominant = dominant_conflict(failures)
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
        "next_action": (
            "continue using the current source-of-truth state and derived artifacts"
            if result == "CONSISTENT"
            else "re-emit derived artifacts from the current state or restore from a verified checkpoint"
        ),
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
    state = load_json(Path(args.state_file))
    record = build_record(
        state=state,
        report=load_json(Path(args.report_file)) if args.report_file else None,
        orchestration=load_json(Path(args.orchestration_file)) if args.orchestration_file else None,
        run_artifact=load_json(Path(args.run_file)) if args.run_file else None,
        repair_packet=load_json(Path(args.repair_packet_file)) if args.repair_packet_file else None,
        repair_handoff=load_json(Path(args.repair_handoff_file)) if args.repair_handoff_file else None,
        repair_receipt=load_json(Path(args.repair_receipt_file)) if args.repair_receipt_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": record["result"], "dominant_conflict": record["dominant_conflict"]}, ensure_ascii=True))
    return 0 if record["result"] == "CONSISTENT" else 2


if __name__ == "__main__":
    sys.exit(main())
