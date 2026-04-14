#!/usr/bin/env python3
"""Check that repeated repair prompts stay bounded on the same retry step."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def required_inputs(packet: dict) -> list[str]:
    continuation = packet.get("continuation_core", {})
    return list(continuation.get("next_step_required_inputs", []) or continuation.get("required_inputs", []))


def current_step(packet: dict) -> str:
    continuation = packet.get("continuation_core", {})
    return continuation.get("current_step_id", "") or packet.get("repair_history", {}).get("current_step_id", "")


def next_safe_step(packet: dict) -> str:
    return (
        packet.get("runtime_truth", {}).get("next_safe_step", "")
        or packet.get("continuation_core", {}).get("next_safe_step", "")
    )


def build_record(*, packet_a: dict, prompt_a: dict, packet_b: dict, prompt_b: dict) -> dict:
    initial_step = current_step(packet_a)
    retry_step = current_step(packet_b)
    initial_scope = list(prompt_a.get("allowed_scope", []))
    retry_scope = list(prompt_b.get("allowed_scope", []))
    initial_inputs = required_inputs(packet_a)
    retry_inputs = required_inputs(packet_b)
    initial_next = next_safe_step(packet_a)
    retry_next = next_safe_step(packet_b)
    missing_markers: list[str] = []

    if initial_step != retry_step:
        missing_markers.append("current_step_id_changed")
    if initial_scope != retry_scope:
        missing_markers.append("allowed_scope_changed")
    if initial_inputs != retry_inputs:
        missing_markers.append("required_inputs_changed")
    if initial_next != retry_next:
        missing_markers.append("next_safe_step_changed")
    if prompt_a.get("forbidden_scope", []) != prompt_b.get("forbidden_scope", []):
        missing_markers.append("forbidden_scope_changed")

    prompt_b_text = prompt_b.get("prompt", "")
    if initial_step and initial_step not in prompt_b_text:
        missing_markers.append("retry_prompt_missing_current_step")
    for input_id in retry_inputs:
        if input_id not in prompt_b_text:
            missing_markers.append(f"retry_prompt_missing_input:{input_id}")

    verdict = "RETRY_SCOPE_STABLE" if not missing_markers else "RETRY_SCOPE_BROADENED"
    return {
        "schema_version": "prompt_retry_guard_record_v0",
        "run_id": packet_b["run_id"],
        "task_class": packet_b["task_class"],
        "initial_current_step_id": initial_step,
        "retry_current_step_id": retry_step,
        "initial_allowed_scope": initial_scope,
        "retry_allowed_scope": retry_scope,
        "initial_required_inputs": initial_inputs,
        "retry_required_inputs": retry_inputs,
        "initial_next_safe_step": initial_next,
        "retry_next_safe_step": retry_next,
        "missing_markers": missing_markers,
        "verdict": verdict,
        "why": (
            "the repeated retry prompt keeps the same bounded step, scope, required inputs, and next-safe-step truth"
            if verdict == "RETRY_SCOPE_STABLE"
            else "the repeated retry prompt drifted away from the bounded repair truth for the same retry step"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-prompt-retry-guard-v0")
    parser.add_argument("--packet-a-file", required=True)
    parser.add_argument("--prompt-a-file", required=True)
    parser.add_argument("--packet-b-file", required=True)
    parser.add_argument("--prompt-b-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        packet_a=load_json(Path(args.packet_a_file)),
        prompt_a=load_json(Path(args.prompt_a_file)),
        packet_b=load_json(Path(args.packet_b_file)),
        prompt_b=load_json(Path(args.prompt_b_file)),
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0 if record["verdict"] == "RETRY_SCOPE_STABLE" else 2


if __name__ == "__main__":
    sys.exit(main())
