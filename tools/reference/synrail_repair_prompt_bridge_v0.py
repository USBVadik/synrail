#!/usr/bin/env python3
"""Controlled follow-up prompt generator from a Synrail repair packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def checkpoint_note(checkpoint: dict | None, *, repair_packet: dict) -> str:
    if not checkpoint:
        return ""
    verification = checkpoint.get("verification", {})
    if (
        checkpoint.get("safe_point_eligible", False)
        and verification.get("status", "") == "PASSED"
        and checkpoint.get("run_id", "") == repair_packet.get("run_id", "")
        and checkpoint.get("task_class", "") == repair_packet.get("task_class", "")
    ):
        return "A verified checkpoint is available if this repair path becomes unsafe."
    return ""


def build_record(*, repair_packet: dict, checkpoint: dict | None = None) -> dict:
    continuation = repair_packet.get("continuation_core", {})
    required_inputs = list(continuation.get("next_step_required_inputs", []) or continuation.get("required_inputs", []))
    stale_subsurfaces = list(continuation.get("next_step_subsurface_ids", []) or repair_packet.get("artifact_quality_summary", {}).get("stale_subsurface_ids", []))
    current_step_id = continuation.get("current_step_id", "") or repair_packet.get("repair_history", {}).get("current_step_id", "")
    allowed_scope = stale_subsurfaces or ["current_repair_step_only"]
    forbidden_scope = [
        "Do not broaden scope beyond the current repair step.",
        "Do not modify accepted or terminal-state logic.",
        "Do not claim closure or acceptance unless the repaired run actually reaches it.",
    ]
    must_pass = [
        f"Repair only the current step: {current_step_id or 'unknown_current_step'}",
        "Keep run_id and task_class consistent with the current contour.",
        "Do not remove or rewrite existing repair history.",
    ]
    for input_id in required_inputs:
        must_pass.append(f"Supply required repair input: {input_id}")
    checkpoint_hint = checkpoint_note(checkpoint, repair_packet=repair_packet)
    prompt_lines = [
        "Repair the current Synrail contour without broadening scope.",
        f"Current step: {current_step_id or 'unknown_current_step'}",
        f"Broken truth: {repair_packet.get('runtime_truth', {}).get('report_reason', '') or repair_packet.get('repair_termination', {}).get('reason', '')}",
        f"Allowed scope: {', '.join(allowed_scope)}",
        f"Required inputs: {', '.join(required_inputs) if required_inputs else 'none'}",
        f"Next safe step: {repair_packet.get('runtime_truth', {}).get('next_safe_step', '') or repair_packet.get('continuation_core', {}).get('next_safe_step', '')}",
        "Do not touch unrelated files, state transitions, or acceptance logic.",
        "Return only the bounded repair needed for this current step and preserve continuity truth.",
    ]
    if checkpoint_hint:
        prompt_lines.append(checkpoint_hint)
    return {
        "schema_version": "repair_prompt_bridge_record_v0",
        "run_id": repair_packet["run_id"],
        "task_class": repair_packet["task_class"],
        "current_step_id": current_step_id,
        "allowed_scope": allowed_scope,
        "forbidden_scope": forbidden_scope,
        "must_pass": must_pass,
        "prompt": "\n".join(prompt_lines),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-repair-prompt-bridge-v0")
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--checkpoint-record-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        repair_packet=load_json(Path(args.repair_packet_file)),
        checkpoint=load_json(Path(args.checkpoint_record_file)) if args.checkpoint_record_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "current_step_id": record["current_step_id"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
