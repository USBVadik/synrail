#!/usr/bin/env python3
"""Controlled follow-up prompt generator from a Synrail repair packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def humanize_token(value: str) -> str:
    if not value:
        return ""
    return value.replace("_", " ").replace("-", " ").lower()


def human_step_label(step_id: str) -> str:
    labels = {
        "continue_forward_orchestration": "prepare the next bounded attempt",
        "repair_final_result_artifact": "repair the final result artifact",
        "restore_readiness_truth": "restore a trustworthy working surface",
        "complete_missing_proof_sections": "fill in the missing proof sections",
        "complete_recovery_reverification": "finish recovery reverification",
        "start_new_run": "start a new bounded run",
    }
    return labels.get(step_id, humanize_token(step_id) or "unknown current step")


def human_failure_label(reason: str) -> str:
    labels = {
        "EXACT_TASK_IDENTITY_NOT_CONFIRMED": "the original task request is not confirmed",
        "INVALID_PROOF_BUNDLE": "the final result proof could not be trusted",
        "MISSING_PROOF_SECTIONS": "the proof is still missing required sections",
        "ARTIFACT_BUNDLE_MISSING": "the result bundle is missing required proof files",
        "DOCTOR_NOT_GREEN": "the working surface is not ready yet",
        "CONTINUATION_INPUTS_MISSING": "the next repair step is still missing required inputs",
        "RECOVERY_REVERIFICATION_INCOMPLETE": "recovery reverification is still incomplete",
        "MAX_REPAIR_ATTEMPTS": "the bounded repair limit was reached",
        "NO_PROGRESS_DETECTED": "the repair loop stopped making progress",
        "NON_RESUMABLE": "this run cannot safely continue from the current state",
        "STATE_NOT_RESUMABLE": "this run cannot safely continue from the current state",
    }
    return labels.get(reason, humanize_token(reason) or "unknown blocker")


def human_scope_label(scope_id: str) -> str:
    labels = {
        "current_repair_step_only": "only the current bounded repair step",
        "helper_entrypoint_record": "the helper entrypoint that is blocking readiness",
        "clean_execution_surface_record": "the current working surface cleanliness and scope",
        "proof_bundle_surface": "the proof bundle for this run",
        "final_result_artifact": "the final result artifact for this run",
    }
    return labels.get(scope_id, humanize_token(scope_id))


def human_required_input(input_id: str) -> str:
    labels = {
        "clean_surface_confirmation": "confirmation that the working surface is clean and in scope",
        "helper_path": "the blocking helper path",
        "prompt_identity_file": "the original task request record",
        "target_identity_file": "the trusted target identity record",
        "refresh_recovery_complete": "confirmation that recovery completed",
        "refresh_reverification_complete": "confirmation that reverification completed",
    }
    return labels.get(input_id, humanize_token(input_id))


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


def failure_reason(repair_packet: dict) -> str:
    return (
        repair_packet.get("runtime_truth", {}).get("report_reason", "")
        or repair_packet.get("repair_termination", {}).get("reason", "")
    )


def next_safe_step(repair_packet: dict) -> str:
    return (
        repair_packet.get("runtime_truth", {}).get("next_safe_step", "")
        or repair_packet.get("continuation_core", {}).get("next_safe_step", "")
    )


def next_command(repair_packet: dict, current_step_id: str) -> str:
    resumability = repair_packet.get("resumability", {})
    termination = repair_packet.get("repair_termination", {})
    if (
        resumability.get("status", "") == "REPAIRABLE"
        and termination.get("status", "CONTINUE") != "TERMINATE"
    ):
        return "synrail continue"
    if (
        repair_packet.get("resumability_family", "") == "NOT_RESUMABLE_FRESH_ORCHESTRATION"
        or current_step_id == "continue_forward_orchestration"
    ):
        return "synrail check"
    return ""


def build_record(*, repair_packet: dict, checkpoint: dict | None = None) -> dict:
    continuation = repair_packet.get("continuation_core", {})
    required_inputs = list(continuation.get("next_step_required_inputs", []) or continuation.get("required_inputs", []))
    artifact_quality = repair_packet.get("artifact_quality_summary", {})
    stale_subsurfaces = list(continuation.get("next_step_subsurface_ids", []) or artifact_quality.get("stale_subsurface_ids", []))
    stale_artifacts = list(artifact_quality.get("stale_artifact_ids", []))
    current_step_id = continuation.get("current_step_id", "") or repair_packet.get("repair_history", {}).get("current_step_id", "")
    current_step_label = human_step_label(current_step_id)
    allowed_scope = stale_subsurfaces or ["current_repair_step_only"]
    allowed_scope_labels = [human_scope_label(scope_id) for scope_id in allowed_scope]
    required_input_labels = [human_required_input(input_id) for input_id in required_inputs]
    forbidden_scope = [
        "Do not broaden scope beyond the current repair step.",
        "Do not modify accepted or terminal-state logic.",
        "Do not claim closure or acceptance unless the repaired run actually reaches it.",
    ]
    broken_truth = failure_reason(repair_packet)
    failure_label = human_failure_label(broken_truth)
    continuation_next_step = next_safe_step(repair_packet)
    next_safe_step_label = (
        "restore the original task request and intended target, then run the next bounded check"
        if continuation_next_step == "restore exact prompt and task identity"
        else (
            "move to a clean or clearly verified-safe working surface"
            if continuation_next_step == "move to a clean or explicitly observed-safe execution surface"
            else continuation_next_step
        )
    )
    must_pass = [
        f"Repair only this task: {current_step_label}",
        "Keep run_id and task_class consistent with the current contour.",
        "Do not remove or rewrite existing repair history.",
    ]
    for input_id in required_inputs:
        must_pass.append(f"Provide required input: {human_required_input(input_id)}")
    if next_safe_step_label:
        must_pass.append(f"Keep the next safe step aligned with: {next_safe_step_label}")
    acceptance_criteria = list(must_pass)
    checkpoint_hint = checkpoint_note(checkpoint, repair_packet=repair_packet)
    prompt_lines = [
        "Repair the current Synrail contour without broadening scope.",
        f"Current repair task: {current_step_label}. (technical step id: {current_step_id or 'unknown_current_step'})",
        f"What failed: {failure_label}. (technical reason: {broken_truth or 'unknown_reason'})",
        f"Stale artifacts: {', '.join(stale_artifacts) if stale_artifacts else 'none'}",
        f"Stale subsurfaces: {', '.join(stale_subsurfaces) if stale_subsurfaces else 'none'}",
        f"Allowed scope: {', '.join(allowed_scope_labels) if allowed_scope_labels else 'only the current bounded repair step'}",
        f"Required inputs: {', '.join(required_input_labels) if required_input_labels else 'none'}",
        f"What must be true after repair: {next_safe_step_label or 'follow the next safe step from the repair packet'}",
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
        "current_step_label": current_step_label,
        "failure_reason": broken_truth,
        "failure_label": failure_label,
        "stale_artifact_ids": stale_artifacts,
        "stale_subsurface_ids": stale_subsurfaces,
        "allowed_scope": allowed_scope,
        "allowed_scope_labels": allowed_scope_labels,
        "required_inputs": required_inputs,
        "required_input_labels": required_input_labels,
        "forbidden_scope": forbidden_scope,
        "must_pass": must_pass,
        "acceptance_criteria": acceptance_criteria,
        "next_safe_step_label": next_safe_step_label,
        "next_command": next_command(repair_packet, current_step_id),
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
