#!/usr/bin/env python3
"""Controlled follow-up prompt generator from a Synrail repair packet."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_repair_focus_v0 import (
        focused_repair_action_instruction,
        focused_repair_summary,
        focused_repair_surface,
        proof_target_paths as shared_proof_target_paths,
    )
except ImportError:
    from synrail_repair_focus_v0 import (
        focused_repair_action_instruction,
        focused_repair_summary,
        focused_repair_surface,
        proof_target_paths as shared_proof_target_paths,
    )


def humanize_token(value: str) -> str:
    if not value:
        return ""
    return value.replace("_", " ").replace("-", " ").lower()


def human_step_label(step_id: str) -> str:
    labels = {
        "continue_forward_orchestration": "prepare the next bounded attempt",
        "repair_final_result_artifact": "repair the final result artifact",
        "restore_readiness_truth": "restore a trustworthy workspace",
        "complete_missing_proof_sections": "fill in the missing proof sections",
        "complete_recovery_reverification": "finish recovery reverification",
        "start_new_run": "start a new bounded run",
    }
    return labels.get(step_id, humanize_token(step_id) or "unknown current step")


def human_failure_label(reason: str) -> str:
    labels = {
        "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED": "this run was not started in controlled mode",
        "REMOTE_TARGET_UNSUPPORTED": "the current alpha lane does not support remote or ops targets yet",
        "EXACT_TASK_IDENTITY_NOT_CONFIRMED": "the original task request is not confirmed",
        "INVALID_PROOF_BUNDLE": "the final result proof could not be trusted",
        "SEMANTIC_PROOF_INSUFFICIENT": "the proof is present but still too thin to trust",
        "MISSING_PROOF_SECTIONS": "the proof is still missing required sections",
        "ARTIFACT_BUNDLE_MISSING": "the result bundle is missing required proof files",
        "DOCTOR_NOT_GREEN": "the current workspace is not ready yet",
        "ACCEPTANCE_CRITERIA_STALE": "the acceptance rules no longer match this project state",
        "ACCEPTANCE_CRITERIA_INVALID": "the acceptance rules could not be trusted",
        "CONTINUATION_INPUTS_MISSING": "the next repair step is still missing required inputs",
        "RECOVERY_REVERIFICATION_INCOMPLETE": "recovery reverification is still incomplete",
        "MAX_REPAIR_ATTEMPTS": "the bounded repair limit was reached",
        "NO_PROGRESS_DETECTED": "the repair loop stopped making progress",
        "NON_RESUMABLE": "this run cannot safely continue from the current state",
        "STATE_NOT_RESUMABLE": "this run cannot safely continue from the current state",
    }
    return labels.get(reason, humanize_token(reason) or "unknown blocker")


def doctor_coverage_block(doctor: dict | None) -> bool:
    return "doctor-coverage incomplete" in list((doctor or {}).get("blocking_failure_classes", []))


def proof_target_paths(repair_packet: dict) -> dict[str, str]:
    return shared_proof_target_paths(
        artifact_root=repair_packet.get("output_defaults", {}).get("artifact_root", ""),
        target_path=repair_packet.get("resume_context", {}).get("target_path", ""),
    )


def human_scope_label(scope_id: str, *, repair_packet: dict | None = None) -> str:
    proof_paths = proof_target_paths(repair_packet or {})
    labels = {
        "current_repair_step_only": "only the current bounded repair step",
        "helper_entrypoint_record": "the helper entrypoint that is blocking readiness",
        "clean_execution_surface_record": "the current workspace for this run",
        "proof_bundle_surface": "the proof bundle for this run",
        "final_result_artifact": "the final result artifact for this run",
        "final_result_payload": f"the result payload in {proof_paths['final_result']}",
        "final_result_status_record": f"the trust-bearing status field in {proof_paths['final_result']}",
        "scope_alignment_record": f"the scope-alignment section in {proof_paths['final_result']}",
        "presentation_alignment_record": f"the presentation-alignment section in {proof_paths['final_result']}",
        "diff_provenance_record": f"the diff provenance section in {proof_paths['final_result']}",
        "artifact_identity_record": f"the artifact identity section in {proof_paths['final_result']}",
        "cleanup_status_record": f"the cleanup status section in {proof_paths['final_result']}",
        "readback_record": f"the readback starter file at {proof_paths['readback']}",
        "scenario_proof_record": f"the scenario proof starter file at {proof_paths['scenario_proof']}",
        "target_identity_record": "the task target for this run",
    }
    return labels.get(scope_id, humanize_token(scope_id))


def human_required_input(input_id: str) -> str:
    labels = {
        "clean_surface_confirmation": "confirmation that the workspace is clean and safe to use (`--clean-surface` on the next retry)",
        "helper_path": "the blocking helper path",
        "prompt_identity_file": "the original task request record",
        "target_identity_file": "the task target record",
        "refresh_recovery_complete": "confirmation that recovery completed",
        "refresh_reverification_complete": "confirmation that reverification completed",
    }
    return labels.get(input_id, humanize_token(input_id))


def focused_step_details(repair_packet: dict, current_step_id: str, stale_subsurfaces: list[str]) -> tuple[str, str, str]:
    proof_paths = proof_target_paths(repair_packet)
    focused = focused_repair_surface(
        current_step_id=current_step_id,
        stale_subsurfaces=stale_subsurfaces,
        artifact_root=repair_packet.get("output_defaults", {}).get("artifact_root", ""),
        target_path=repair_packet.get("resume_context", {}).get("target_path", ""),
    )
    subsurface_id = focused.get("current_step_subsurface_id", "")
    target_path = focused.get("current_step_target_path", "")
    if current_step_id == "repair_final_result_artifact":
        labels = {
            "final_result_payload": f"repair the result payload in {proof_paths['final_result']}",
            "final_result_status_record": f"set a trust-bearing final_result.status in {proof_paths['final_result']}",
            "scope_alignment_record": f"remove unrelated adjacent edits in {proof_paths['final_result']}",
            "presentation_alignment_record": f"remove extra emphasis styling in {proof_paths['final_result']}",
            "diff_provenance_record": f"record diff provenance in {proof_paths['final_result']}",
            "artifact_identity_record": f"record artifact identity in {proof_paths['final_result']}",
            "cleanup_status_record": f"record cleanup status in {proof_paths['final_result']}",
        }
        if subsurface_id:
            return labels.get(subsurface_id, human_step_label(current_step_id)), subsurface_id, target_path
    if current_step_id == "complete_missing_proof_sections":
        labels = {
            "readback_record": f"record readback in {proof_paths['readback']}",
            "scenario_proof_record": f"record scenario proof in {proof_paths['scenario_proof']}",
        }
        if subsurface_id:
            return labels.get(subsurface_id, human_step_label(current_step_id)), subsurface_id, target_path
    if current_step_id == "restore_readiness_truth" and subsurface_id:
        return human_step_label(current_step_id), subsurface_id, target_path
    return human_step_label(current_step_id), "", ""


def final_result_repair_checklist(*, current_step_subsurface_id: str, current_step_target_path: str) -> list[str]:
    if not current_step_target_path or not current_step_target_path.endswith("final_result.json"):
        return []
    common = [
        f"Checklist for {current_step_target_path}:",
        "- final_result.status: use PROVEN for an evidenced modification run, or ALREADY_SATISFIED only when the requested state was already present before any edit",
        "- change_disposition: use modified for a real edit, or already_satisfied only when the requested state was already present before any edit",
        "- modified_files: list each concrete changed file path, or keep [] only for a truthful already_satisfied no-op attestation",
        "- scope: if the task only asked you to add or insert something, do not also rewrite adjacent spacing, classes, or layout just to make room for it",
        "- presentation: if the task only asked for a small added label or subtitle, keep the new surface visually plain and avoid extra emphasis styling unless the task explicitly asked for it",
        "- git_diff: include a real patch with diff --git, ---, +++, @@, and the named changed files when you can produce one; keep it empty for a truthful already_satisfied no-op attestation",
        "- diff_provenance: if git_diff is unavailable or the file is untracked, record method, changed_file, one exact added_line or removed_line, one stable context_before or context_after anchor, and verification_command plus verification_result",
        "- If diff_provenance.method is missing but the rest of the direct-observation record is strong, Synrail can normalize it to direct_file_observation during a normal check; still include it explicitly when you can",
        "- diff_provenance for already_satisfied: record changed_file, observed_line, verification_command, verification_result, and provenance_note instead of inventing a patch",
        "- artifact_identity: when identity is missing, fill baseline_identity, execution_surface_identity, prompt_identity, and task_identity for this run",
        "- cleanup_status.success: true when the workspace is clean after the intended change",
        "- cleanup_status.summary: say the workspace is clean and only the intended files changed",
        "- Need a canonical shape? run `synrail final-result-template`",
        "- Need exact semantic reasons after a check? run `synrail explain-proof`",
    ]
    if current_step_subsurface_id == "final_result_payload":
        return common
    if current_step_subsurface_id == "final_result_status_record":
        return [
            f"Checklist for {current_step_target_path}:",
            "- final_result.status: use PROVEN for an evidenced modification run",
            "- final_result.status: use ALREADY_SATISFIED only for a truthful no-op attestation where the requested state was already present before any edit",
            "- Do not use decorative execution labels like SUCCESS, COMPLETED, DONE, or OK when the bundle is making a trust claim",
            "- Keep final_result.status aligned with change_disposition and the actual proof contour",
            "- Need a canonical shape? run `synrail final-result-template`",
            "- Need exact semantic reasons after a check? run `synrail explain-proof`",
        ]
    if current_step_subsurface_id == "scope_alignment_record":
        return [
            f"Checklist for {current_step_target_path}:",
            "- Keep only the user-requested additive change in scope",
            "- If the task asked for a small inserted label, subtitle, or caption, do not also tweak adjacent margin, padding, class, or layout lines unless the task explicitly asked for that too",
            "- modified_files and git_diff should describe only the requested additive change",
            "- If the requested state was already present before any edit, use change_disposition=already_satisfied instead of inventing cleanup edits",
            "- Need a canonical shape? run `synrail final-result-template`",
            "- Need exact semantic reasons after a check? run `synrail explain-proof`",
        ]
    if current_step_subsurface_id == "presentation_alignment_record":
        return [
            f"Checklist for {current_step_target_path}:",
            "- Keep the newly added line visually plain unless the task explicitly asked for styling",
            "- Avoid extra emphasis classes such as italic, uppercase, tracking, opacity, animation, shadow, or heavy font-weight when the task only asked for a simple subtitle or label",
            "- Keep the added line consistent with the nearby UI instead of improvising a new visual treatment",
            "- Need a canonical shape? run `synrail final-result-template`",
            "- Need exact semantic reasons after a check? run `synrail explain-proof`",
        ]
    if current_step_subsurface_id == "diff_provenance_record":
        return [
            f"Checklist for {current_step_target_path}:",
            "- change_disposition: use modified for a real edit, or already_satisfied only when the requested state was already present before any edit",
            "- modified_files: list each concrete changed file path first, or keep [] only for a truthful already_satisfied no-op attestation",
            "- git_diff: include a real patch with diff --git, ---, +++, @@, and the named changed files when you can produce one; keep it empty for a truthful already_satisfied no-op attestation",
            "- diff_provenance.method: name how you captured the evidence (for example direct_file_observation); if it is omitted but the direct-observation record is otherwise complete, Synrail can infer direct_file_observation during a normal check",
            "- diff_provenance.changed_file: name one concrete modified file from modified_files",
            "- diff_provenance.added_line or diff_provenance.removed_line: record the exact changed line for a real edit",
            "- diff_provenance.context_before or diff_provenance.context_after: copy one stable neighbor line from the same file so the direct observation has a concrete anchor, not just an isolated changed line",
            "- diff_provenance.observed_line: for already_satisfied, record the concrete line that was already present",
            "- diff_provenance.verification_command and diff_provenance.verification_result: capture the command and observed output that proved the changed line or observed line; for tiny edits, prefer output that includes the changed line plus a stable neighbor",
            "- diff_provenance.provenance_note: explain why this is direct observation, especially for already_satisfied or untracked files",
            "- Need a canonical shape? run `synrail final-result-template`",
            "- Need exact semantic reasons after a check? run `synrail explain-proof`",
        ]
    if current_step_subsurface_id == "artifact_identity_record":
        return [
            f"Checklist for {current_step_target_path}:",
            "- artifact_identity.baseline_identity: use the current run baseline identity",
            "- artifact_identity.execution_surface_identity: use the current worktree or execution surface identity",
            "- artifact_identity.prompt_identity: use the prompt identity already attached to this run",
            "- artifact_identity.task_identity: use the task identity already attached to this run",
            "- If check or retry already knows these values, mirroring them here keeps low-level bundle-check reproducible too",
            "- Need a canonical shape? run `synrail final-result-template`",
            "- Need exact semantic reasons after a check? run `synrail explain-proof`",
        ]
    if current_step_subsurface_id == "cleanup_status_record":
        return [
            f"Checklist for {current_step_target_path}:",
            "- cleanup_status.success: true when the workspace is clean after the intended change",
            "- cleanup_status.summary: say the workspace is clean and only the intended files changed",
            "- Need a canonical shape? run `synrail final-result-template`",
            "- Need exact semantic reasons after a check? run `synrail explain-proof`",
        ]
    return common


def readback_repair_checklist(*, current_step_subsurface_id: str, current_step_target_path: str) -> list[str]:
    if current_step_subsurface_id != "readback_record":
        return []
    if not current_step_target_path or not current_step_target_path.endswith("readback.txt"):
        return []
    return [
        f"Checklist for {current_step_target_path}:",
        "- Changed surface: name the actual changed file path explicitly (e.g. src/app.js, not 'the file')",
        "- Observed: describe a concrete property from the changed surface — a function name, class name, line content, or rendered element",
        "- Do not paraphrase or restate the task description — prove you read the actual changed code or output",
        "- At least 2 lines with at least one concrete identifier (file path, function/class name, line number, or code token)",
        "- For UI or rendered changes, prefer local runtime evidence (curl, test output) over source-only grep when possible",
        "- If final_result.json already carries structured diff_provenance with verification_command plus verification_result, keep readback short and explanatory instead of duplicating the main proof payload",
    ]


def scenario_proof_repair_checklist(*, current_step_subsurface_id: str, current_step_target_path: str) -> list[str]:
    if current_step_subsurface_id != "scenario_proof_record":
        return []
    if not current_step_target_path or not current_step_target_path.endswith("scenario_proof.txt"):
        return []
    return [
        f"Checklist for {current_step_target_path}:",
        "- Scenario: name the exact runtime context (file path, URL, command)",
        "- Command: include the actual command, request, or test that was run (e.g. 'python -m pytest tests/test_x.py', 'curl localhost:3000/api')",
        "- Observed: include concrete output — a status code, a rendered fragment, a returned value, not just 'it works'",
        "- Status: PASSED when the expected outcome was observed; otherwise use FAILED or BLOCKED truthfully",
        "- At least 3 lines with at least one concrete identifier or command",
        "- Do not restate the task description — prove the verification actually happened",
        "- If final_result.json already carries structured diff_provenance with verification_command plus verification_result, keep scenario proof short and explanatory instead of duplicating the main proof payload",
    ]


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
        return "A verified restore point is available if this repair path becomes unsafe."
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
        return "synrail check"
    if (
        repair_packet.get("resumability_family", "") == "NOT_RESUMABLE_FRESH_ORCHESTRATION"
        or current_step_id == "continue_forward_orchestration"
    ):
        return "synrail check"
    return ""


def build_record(*, repair_packet: dict, checkpoint: dict | None = None, doctor: dict | None = None) -> dict:
    continuation = repair_packet.get("continuation_core", {})
    required_inputs = list(continuation.get("next_step_required_inputs", []) or continuation.get("required_inputs", []))
    artifact_quality = repair_packet.get("artifact_quality_summary", {})
    stale_subsurfaces = list(continuation.get("next_step_subsurface_ids", []) or artifact_quality.get("stale_subsurface_ids", []))
    stale_artifacts = list(artifact_quality.get("stale_artifact_ids", []))
    current_step_id = continuation.get("current_step_id", "") or repair_packet.get("repair_history", {}).get("current_step_id", "")
    current_step_label, current_step_subsurface_id, current_step_target_path = focused_step_details(
        repair_packet,
        current_step_id,
        stale_subsurfaces,
    )
    current_step_focus_summary = focused_repair_summary(
        current_step_id=current_step_id,
        current_step_subsurface_id=current_step_subsurface_id,
        current_step_target_path=current_step_target_path,
    )
    current_step_action_instruction = focused_repair_action_instruction(
        current_step_id=current_step_id,
        current_step_subsurface_id=current_step_subsurface_id,
        current_step_target_path=current_step_target_path,
    )
    allowed_scope = [current_step_subsurface_id] if current_step_subsurface_id else (stale_subsurfaces or ["current_repair_step_only"])
    allowed_scope_labels = [human_scope_label(scope_id, repair_packet=repair_packet) for scope_id in allowed_scope]
    required_input_labels = [human_required_input(input_id) for input_id in required_inputs]
    forbidden_scope = [
        "Do not broaden scope beyond the current repair step.",
        "Do not modify accepted or terminal-state logic.",
        "Do not claim closure or acceptance unless the repaired run actually reaches it.",
    ]
    broken_truth = failure_reason(repair_packet)
    failure_label = (
        "the current doctor coverage is still too narrow to trust readiness"
        if doctor_coverage_block(doctor)
        else human_failure_label(broken_truth)
    )
    continuation_next_step = next_safe_step(repair_packet)
    next_safe_step_label = (
        "restore the original task request and intended task target, then run the next bounded check"
        if continuation_next_step == "restore exact prompt and task identity"
        else (
            "move back to a clean or clearly verified-safe workspace"
            if continuation_next_step == "move to a clean or explicitly observed-safe execution surface"
            else continuation_next_step
        )
    )
    must_pass = [
        f"Repair only this task: {current_step_label}",
        "Keep this repair on the same run and task.",
        "Do not rewrite previous repair progress.",
    ]
    for input_id in required_inputs:
        must_pass.append(f"Provide required input: {human_required_input(input_id)}")
    if next_safe_step_label:
        must_pass.append(f"Keep the next safe step aligned with: {next_safe_step_label}")
    if current_step_target_path:
        must_pass.append(f"Edit only this starter file in place: {current_step_target_path}")
    acceptance_criteria = list(must_pass)
    checkpoint_hint = checkpoint_note(checkpoint, repair_packet=repair_packet)
    prompt_lines = [
        "Repair the current run without broadening scope.",
        (
            f"Do this now: {current_step_action_instruction}"
            if current_step_action_instruction
            else "Do this now: keep the repair inside the current bounded repair surface."
        ),
        f"Current repair task: {current_step_label}.",
        f"What failed: {failure_label}.",
        (
            f"Repair target: {current_step_focus_summary}."
            if current_step_focus_summary
            else "Repair target: stay inside the current bounded repair surface."
        ),
        f"Stale artifacts: {', '.join(stale_artifacts) if stale_artifacts else 'none'}",
        f"Stale subsurfaces: {', '.join(stale_subsurfaces) if stale_subsurfaces else 'none'}",
        f"Allowed scope: {', '.join(allowed_scope_labels) if allowed_scope_labels else 'only the current bounded repair step'}",
        f"Required inputs: {', '.join(required_input_labels) if required_input_labels else 'none'}",
        f"What must be true after repair: {next_safe_step_label or 'follow the next safe step from the repair packet'}",
        (
            f"Edit in place: {current_step_target_path}."
            if current_step_target_path
            else "Edit in place: keep the repair inside the current bounded proof surface."
        ),
        "Do not touch unrelated files, state transitions, or acceptance logic.",
        "Return only the bounded repair needed for this current step and keep this same repair path intact.",
    ]
    if checkpoint_hint:
        prompt_lines.append(checkpoint_hint)
    prompt_lines.extend(final_result_repair_checklist(
        current_step_subsurface_id=current_step_subsurface_id,
        current_step_target_path=current_step_target_path,
    ))
    prompt_lines.extend(readback_repair_checklist(
        current_step_subsurface_id=current_step_subsurface_id,
        current_step_target_path=current_step_target_path,
    ))
    prompt_lines.extend(scenario_proof_repair_checklist(
        current_step_subsurface_id=current_step_subsurface_id,
        current_step_target_path=current_step_target_path,
    ))
    return {
        "schema_version": "repair_prompt_bridge_record_v0",
        "run_id": repair_packet["run_id"],
        "task_class": repair_packet["task_class"],
        "current_step_id": current_step_id,
        "current_step_label": current_step_label,
        "current_step_subsurface_id": current_step_subsurface_id,
        "current_step_target_path": current_step_target_path,
        "current_step_focus_summary": current_step_focus_summary,
        "current_step_action_instruction": current_step_action_instruction,
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
    parser.add_argument("--doctor-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        repair_packet=load_json(Path(args.repair_packet_file)),
        checkpoint=load_json(Path(args.checkpoint_record_file)) if args.checkpoint_record_file else None,
        doctor=load_json(Path(args.doctor_file)) if args.doctor_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "current_step_id": record["current_step_id"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
