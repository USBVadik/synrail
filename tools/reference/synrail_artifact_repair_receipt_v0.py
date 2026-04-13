#!/usr/bin/env python3
"""Machine-readable artifact repair receipt builder for Synrail continuation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from synrail_repair_handoff_v0 import build_repair_handoff


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def ids_for_step(packet: dict, step_id: str, *, kind: str) -> list[str]:
    values: list[str] = []
    for hint in packet.get("artifact_quality_hints", []):
        if hint.get("repair_step") != step_id:
            continue
        if kind == "artifact":
            artifact_id = hint.get("artifact_id", "")
            if artifact_id and artifact_id not in values:
                values.append(artifact_id)
        else:
            for subsurface in hint.get("stale_subsurfaces", []):
                subsurface_id = subsurface.get("subsurface_id", "")
                if subsurface_id and subsurface_id not in values:
                    values.append(subsurface_id)
    return values


def stale_ids(handoff: dict, *, quality: str, kind: str) -> list[str]:
    values: list[str] = []
    for hint in handoff.get("artifact_quality_hints", []):
        if hint.get("quality") != quality:
            continue
        if kind == "artifact":
            artifact_id = hint.get("artifact_id", "")
            if artifact_id and artifact_id not in values:
                values.append(artifact_id)
        else:
            for subsurface in hint.get("stale_subsurfaces", []):
                subsurface_id = subsurface.get("subsurface_id", "")
                if subsurface_id and subsurface_id not in values:
                    values.append(subsurface_id)
    return values


def hints_for_quality(handoff: dict, *, quality: str) -> list[dict]:
    hints: list[dict] = []
    for hint in handoff.get("artifact_quality_hints", []):
        if hint.get("quality") != quality:
            continue
        hints.append(
            {
                "artifact_id": hint.get("artifact_id", ""),
                "quality": hint.get("quality", ""),
                "repair_step": hint.get("repair_step", ""),
                "still_stale_parts": list(hint.get("still_stale_parts", [])),
                "stale_subsurfaces": [
                    {
                        "subsurface_id": subsurface.get("subsurface_id", ""),
                        "why": subsurface.get("why", ""),
                    }
                    for subsurface in hint.get("stale_subsurfaces", [])
                    if subsurface.get("subsurface_id", "")
                ],
            }
        )
    return hints


def build_repair_history(packet: dict, previous_receipt: dict | None, resulting_handoff: dict) -> dict:
    prior_completed = list(previous_receipt.get("repair_history", {}).get("completed_step_ids", [])) if previous_receipt else []
    prior_current = packet.get("repair_history", {}).get("current_step_id", "")
    current_step_id = packet.get("repair_policy", {}).get("next_step_id", "") or prior_current
    resulting_next_step = resulting_handoff.get("repair_policy", {}).get("next_step_id", "")

    completed = list(prior_completed)
    last_completed = ""
    if current_step_id and current_step_id != resulting_next_step and current_step_id not in completed:
        completed.append(current_step_id)
        last_completed = current_step_id
    elif previous_receipt:
        last_completed = previous_receipt.get("repair_history", {}).get("last_completed_step_id", "")

    ordered = [step.get("step_id", "") for step in resulting_handoff.get("repair_policy", {}).get("ordered_steps", []) if step.get("step_id", "")]
    waiting = [step_id for step_id in ordered if step_id and step_id not in completed and step_id != resulting_next_step]
    return {
        "applied": bool(previous_receipt),
        "completed_step_ids": completed,
        "last_completed_step_id": last_completed,
        "current_step_id": resulting_next_step,
        "waiting_step_ids": waiting,
    }


def receipt_result(report: dict, starting_packet: dict, resulting_handoff: dict) -> str:
    reason = report.get("reason", "")
    if reason in {"CONTINUATION_INPUTS_MISSING", "REPAIR_POLICY_STEP_OUT_OF_ORDER"}:
        return "STEP_NOT_COMPLETED"
    if resulting_handoff.get("resumability", {}).get("status") == "NOT_RESUMABLE":
        return "NON_RESUMABLE_BOUNDARY_REACHED"
    current_step_id = starting_packet.get("repair_policy", {}).get("next_step_id", "")
    next_step_id = resulting_handoff.get("repair_policy", {}).get("next_step_id", "")
    if current_step_id and current_step_id != next_step_id:
        return "STEP_COMPLETED"
    return "STEP_PROGRESS_RECORDED"


def build_receipt(*, starting_packet: dict, resulting_state: dict, report: dict, previous_receipt: dict | None = None) -> dict:
    resulting_handoff = build_repair_handoff(resulting_state)
    starting_step = starting_packet.get("repair_policy", {}).get("next_step_id", "")
    completed_artifact_ids = ids_for_step(starting_packet, starting_step, kind="artifact")
    completed_subsurface_ids = ids_for_step(starting_packet, starting_step, kind="subsurface")
    history = build_repair_history(starting_packet, previous_receipt, resulting_handoff)
    result = receipt_result(report, starting_packet, resulting_handoff)
    return {
        "schema_version": "artifact_repair_receipt_v0",
        "run_id": starting_packet["run_id"],
        "task_class": starting_packet["task_class"],
        "from_state": starting_packet["from_state"],
        "resulting_state": resulting_state.get("state", ""),
        "result": result,
        "completed_step_id": history["last_completed_step_id"],
        "completed_artifact_ids": completed_artifact_ids if history["last_completed_step_id"] else [],
        "completed_subsurface_ids": completed_subsurface_ids if history["last_completed_step_id"] else [],
        "remaining_stale_artifact_ids": stale_ids(resulting_handoff, quality="STALE", kind="artifact"),
        "remaining_stale_subsurface_ids": stale_ids(resulting_handoff, quality="STALE", kind="subsurface"),
        "remaining_non_resumable_artifact_ids": stale_ids(resulting_handoff, quality="NON_RESUMABLE", kind="artifact"),
        "remaining_non_resumable_subsurface_ids": stale_ids(resulting_handoff, quality="NON_RESUMABLE", kind="subsurface"),
        "remaining_stale_hints": hints_for_quality(resulting_handoff, quality="STALE"),
        "remaining_non_resumable_hints": hints_for_quality(resulting_handoff, quality="NON_RESUMABLE"),
        "next_step_id": resulting_handoff.get("repair_policy", {}).get("next_step_id", ""),
        "ready_now_step_ids": list(resulting_handoff.get("repair_policy", {}).get("ready_now_step_ids", [])),
        "repair_history": history,
        "resumability": {
            "status": resulting_handoff.get("resumability", {}).get("status", ""),
            "family": resulting_handoff.get("resumability", {}).get("family", ""),
        },
        "why": {
            "STEP_NOT_COMPLETED": "the current repair step is still blocked, so the receipt records no completed step yet",
            "NON_RESUMABLE_BOUNDARY_REACHED": "the continuation crossed into a non-resumable boundary, so the next move is no longer another repair step",
            "STEP_COMPLETED": "the current repair step no longer leads the policy order, so the runtime records it as completed",
            "STEP_PROGRESS_RECORDED": "the runtime recorded continuation progress even though the same repair step is still current",
        }[result],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-artifact-repair-receipt-v0")
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--resulting-state-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous-receipt-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    packet = load_json(Path(args.repair_packet_file))
    resulting_state = load_json(Path(args.resulting_state_file))
    report = load_json(Path(args.report_file))
    previous_receipt = load_json(Path(args.previous_receipt_file)) if args.previous_receipt_file else None
    receipt = build_receipt(starting_packet=packet, resulting_state=resulting_state, report=report, previous_receipt=previous_receipt)
    save_json(Path(args.output), receipt)
    print(json.dumps({"result": receipt["result"], "completed_step_id": receipt["completed_step_id"], "next_step_id": receipt["next_step_id"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
