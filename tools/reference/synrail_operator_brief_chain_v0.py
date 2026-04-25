#!/usr/bin/env python3
"""Aggregate stage-level operator briefs into one compact multi-stage operator chain."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json


def stage_id_for(path: Path, index: int) -> str:
    stem = path.stem
    if "stage" in stem:
        for part in stem.split("_"):
            if part.startswith("stage"):
                return part
    return f"stage{index}"


def build_record(paths: list[Path]) -> dict:
    briefs = [load_json(path) for path in paths]
    if not briefs:
        raise ValueError("at least one operator brief is required")
    for brief in briefs:
        if brief.get("schema_version") != "operator_brief_record_v0":
            raise ValueError("all inputs must use operator_brief_record_v0")
    first = briefs[0]
    final = briefs[-1]
    stage_summaries = []
    action_counts: dict[str, int] = {}
    repairable_stage_ids: list[str] = []
    stop_stage_ids: list[str] = []
    continue_stage_ids: list[str] = []
    for index, (path, brief) in enumerate(zip(paths, briefs)):
        stage_id = stage_id_for(path, index)
        primary_action = brief["primary_action"]
        action_counts[primary_action] = action_counts.get(primary_action, 0) + 1
        if primary_action == "STOP_AND_START_NEW_RUN":
            stop_stage_ids.append(stage_id)
        if primary_action in {"REPAIR_CURRENT_STEP", "CONTINUE_RUNTIME"}:
            continue_stage_ids.append(stage_id)
        if brief.get("resumability_family", "").startswith("REPAIRABLE"):
            repairable_stage_ids.append(stage_id)
        stage_summaries.append(
            {
                "stage_id": stage_id,
                "resulting_state": brief["resulting_state"],
                "result": brief["result"],
                "stopping_stage": brief["stopping_stage"],
                "reason": brief["reason"],
                "primary_action": primary_action,
                "next_safe_step": brief["next_safe_step"],
                "current_step_id": brief["current_step_id"],
                "current_step_subsurface_id": brief.get("current_step_subsurface_id", ""),
                "current_step_target_path": brief.get("current_step_target_path", ""),
                "current_step_action_instruction": brief.get("current_step_action_instruction", ""),
                "next_step_required_inputs": list(brief["next_step_required_inputs"]),
                "reusable_proof_surfaces": list(brief.get("reusable_proof_surfaces", [])),
                "termination_reason": brief["termination_reason"],
            }
        )
    final_action = final["primary_action"]
    return {
        "schema_version": "operator_brief_chain_record_v0",
        "run_id": first["run_id"],
        "task_class": first["task_class"],
        "stage_count": len(stage_summaries),
        "source_briefs": [
            {
                "path": str(path),
                "stage_id": summary["stage_id"],
                "primary_action": summary["primary_action"],
            }
            for path, summary in zip(paths, stage_summaries)
        ],
        "action_counts": action_counts,
        "repairable_stage_ids": repairable_stage_ids,
        "continue_stage_ids": continue_stage_ids,
        "stop_stage_ids": stop_stage_ids,
        "final_action": final_action,
        "final_next_safe_step": final["next_safe_step"],
        "final_resumability_family": final["resumability_family"],
        "stage_summaries": stage_summaries,
        "why": (
            "the operator chain preserves one explicit sequence of repair, continue, and terminal decisions across the multi-stage contour"
            if len(stage_summaries) > 1
            else "the operator chain currently contains only one stage summary"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-operator-brief-chain-v0")
    parser.add_argument("--brief", action="append", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        record = build_record([Path(p) for p in args.brief])
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "stage_count": record["stage_count"], "final_action": record["final_action"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
