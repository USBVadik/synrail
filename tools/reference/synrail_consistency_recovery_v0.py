#!/usr/bin/env python3
"""Derive a concrete recovery plan from artifact consistency plus an optional verified checkpoint."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def checkpoint_matches(consistency: dict, checkpoint: dict | None) -> bool:
    if not checkpoint:
        return False
    verification = checkpoint.get("verification", {})
    return (
        checkpoint.get("safe_point_eligible", False)
        and verification.get("status", "") == "PASSED"
        and checkpoint.get("run_id", "") == consistency.get("run_id", "")
        and checkpoint.get("task_class", "") == consistency.get("task_class", "")
    )


def build_record(*, consistency: dict, checkpoint: dict | None = None) -> dict:
    restore_available = checkpoint_matches(consistency, checkpoint)
    artifact_plan = []
    restore_ids: list[str] = []
    reemit_ids: list[str] = []
    keep_ids: list[str] = []

    for artifact_id, action in consistency.get("artifact_actions", {}).items():
        if artifact_id == "state_file":
            continue
        if action == "RESTORE_FROM_CHECKPOINT_OR_REEMIT":
            concrete = "RESTORE_FROM_CHECKPOINT" if restore_available else "REEMIT_FROM_STATE"
        else:
            concrete = action
        artifact_plan.append(
            {
                "artifact_id": artifact_id,
                "requested_action": action,
                "concrete_action": concrete,
            }
        )
        if concrete == "RESTORE_FROM_CHECKPOINT":
            restore_ids.append(artifact_id)
        elif concrete == "REEMIT_FROM_STATE":
            reemit_ids.append(artifact_id)
        elif concrete == "KEEP_DERIVED_ARTIFACT":
            keep_ids.append(artifact_id)

    if restore_ids and reemit_ids:
        primary_action = "RESTORE_CORRUPT_AND_REEMIT_STALE"
    elif restore_ids:
        primary_action = "RESTORE_FROM_CHECKPOINT"
    elif reemit_ids:
        primary_action = "REEMIT_FROM_STATE"
    else:
        primary_action = "KEEP_CURRENT_ARTIFACTS"

    instructions: list[str] = []
    for artifact_id in restore_ids:
        instructions.append(f"restore {artifact_id} from the verified checkpoint")
    for artifact_id in reemit_ids:
        instructions.append(f"re-emit {artifact_id} from state_file")
    for artifact_id in keep_ids:
        instructions.append(f"keep {artifact_id} as-is")

    return {
        "schema_version": "consistency_recovery_record_v0",
        "run_id": consistency["run_id"],
        "task_class": consistency["task_class"],
        "consistency_result": consistency.get("result", ""),
        "dominant_conflict": consistency.get("dominant_conflict", ""),
        "checkpoint_restore_available": restore_available,
        "primary_action": primary_action,
        "restore_artifact_ids": restore_ids,
        "reemit_artifact_ids": reemit_ids,
        "keep_artifact_ids": keep_ids,
        "artifact_plan": artifact_plan,
        "operator_instructions": instructions,
        "ambiguous": False,
        "why": "the recovery bridge converts consistency failures into a concrete restore-or-reemit plan using the verified checkpoint when it matches the same run/task contour",
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-consistency-recovery-v0")
    parser.add_argument("--consistency-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--checkpoint-record-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        consistency=load_json(Path(args.consistency_file)),
        checkpoint=load_json(Path(args.checkpoint_record_file)) if args.checkpoint_record_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "primary_action": record["primary_action"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
