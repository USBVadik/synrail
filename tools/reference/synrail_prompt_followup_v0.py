#!/usr/bin/env python3
"""Check that a generated repair prompt preserves bounded next-step truth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_record(*, repair_packet: dict, prompt_bridge: dict, thin_output: dict | None = None) -> dict:
    continuation = repair_packet.get("continuation_core", {})
    expected_current_step = continuation.get("current_step_id", "") or repair_packet.get("repair_history", {}).get("current_step_id", "")
    expected_required_inputs = list(continuation.get("next_step_required_inputs", []) or continuation.get("required_inputs", []))
    expected_scope = list(continuation.get("next_step_subsurface_ids", []) or repair_packet.get("artifact_quality_summary", {}).get("stale_subsurface_ids", []))
    prompt_text = prompt_bridge.get("prompt", "")
    missing_markers: list[str] = []

    if prompt_bridge.get("current_step_id", "") != expected_current_step:
        missing_markers.append("current_step_id")
    if expected_scope and prompt_bridge.get("allowed_scope", []) != expected_scope:
        missing_markers.append("allowed_scope")
    for required_input in expected_required_inputs:
        marker = f"Supply required repair input: {required_input}"
        if marker not in prompt_bridge.get("must_pass", []):
            missing_markers.append(f"required_input:{required_input}")
        if required_input not in prompt_text:
            missing_markers.append(f"prompt_mentions:{required_input}")
    if expected_current_step and expected_current_step not in prompt_text:
        missing_markers.append("prompt_mentions_current_step")
    if "Do not touch unrelated files, state transitions, or acceptance logic." not in prompt_text:
        missing_markers.append("forbidden_scope_guardrail")
    if thin_output and thin_output.get("next_step", "") and thin_output["next_step"] not in prompt_text:
        missing_markers.append("prompt_mentions_next_step")

    verdict = "FOLLOWUP_SCOPE_PRESERVED" if not missing_markers else "FOLLOWUP_SCOPE_DRIFT"
    return {
        "schema_version": "prompt_followup_record_v0",
        "run_id": repair_packet["run_id"],
        "task_class": repair_packet["task_class"],
        "current_step_id": expected_current_step,
        "required_inputs": expected_required_inputs,
        "allowed_scope": expected_scope,
        "missing_markers": missing_markers,
        "verdict": verdict,
        "why": (
            "the generated prompt preserves the bounded repair step, scope, and must-pass constraints for the next agent call"
            if verdict == "FOLLOWUP_SCOPE_PRESERVED"
            else "the generated prompt dropped one or more bounded follow-up constraints from the repair packet"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-prompt-followup-v0")
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--prompt-bridge-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--thin-output-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        repair_packet=load_json(Path(args.repair_packet_file)),
        prompt_bridge=load_json(Path(args.prompt_bridge_file)),
        thin_output=load_json(Path(args.thin_output_file)) if args.thin_output_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0 if record["verdict"] == "FOLLOWUP_SCOPE_PRESERVED" else 2


if __name__ == "__main__":
    sys.exit(main())
