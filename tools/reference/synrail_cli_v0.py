#!/usr/bin/env python3
"""Minimal terminal-first CLI facade for Synrail v0."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

try:
    from .synrail_agent_adoption_v0 import (
        preferred_repo_native_alpha_command,
        preferred_synrail_command,
        preferred_synrail_fallback_command as preferred_synrail_fallback_command_for_runtime,
        relative_artifact_root_for_project,
        render_agent_policy_block,
        render_agent_policy_markdown,
        render_agents_policy_block,
        render_claude_policy_block,
        render_claude_policy_markdown,
        render_gemini_policy_block,
        render_gemini_policy_markdown,
        write_agent_policy_file,
    )
except ImportError:
    from synrail_agent_adoption_v0 import (
        preferred_repo_native_alpha_command,
        preferred_synrail_command,
        preferred_synrail_fallback_command as preferred_synrail_fallback_command_for_runtime,
        relative_artifact_root_for_project,
        render_agent_policy_block,
        render_agent_policy_markdown,
        render_agents_policy_block,
        render_claude_policy_block,
        render_claude_policy_markdown,
        render_gemini_policy_block,
        render_gemini_policy_markdown,
        write_agent_policy_file,
    )

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json

try:
    from .synrail_repair_packet_v0 import build_packet_from_runtime_truth
except ImportError:
    from synrail_repair_packet_v0 import build_packet_from_runtime_truth

try:
    from .synrail_alpha_telemetry_v0 import (
        append_command_event,
        build_command_event,
        default_issue_body_file,
        default_session_replay_file,
        enable_telemetry,
        export_session_replay,
        telemetry_enabled,
    )
except ImportError:
    from synrail_alpha_telemetry_v0 import (
        append_command_event,
        build_command_event,
        default_issue_body_file,
        default_session_replay_file,
        enable_telemetry,
        export_session_replay,
        telemetry_enabled,
    )

try:
    from .synrail_bootstrap_v0 import (
        build_bootstrap_record,
        build_proof_request_record,
        build_proof_starter_contents,
        load_json as load_bootstrap_json,
        project_prefers_runtime_evidence,
        save_json as save_bootstrap_json,
        validate_bootstrap_record,
        write_proof_starter_files,
    )
except ImportError:
    from synrail_bootstrap_v0 import (
        build_bootstrap_record,
        build_proof_request_record,
        build_proof_starter_contents,
        load_json as load_bootstrap_json,
        project_prefers_runtime_evidence,
        save_json as save_bootstrap_json,
        validate_bootstrap_record,
        write_proof_starter_files,
    )

try:
    from .synrail_checkpoint_v0 import restore_contract
except ImportError:
    from synrail_checkpoint_v0 import restore_contract

try:
    from .synrail_commands_v0 import (
        AgentAdoptionContext,
        CiPreflightContext,
        ApplyRefreshValidateContext,
        DoctorCompareSubstituteContext,
        HybridModeContext,
        ProofPreparationCostContext,
        CheckpointCreateSaveVerifyContext,
        RestoreConsistencyThinContext,
        PromptReadingFollowupContext,
        RetryRecoveryReadingContext,
        RecoveryPromptObservabilityContext,
        OperatorBriefRenderReadingContext,
        OperatorRenderAdoptionPressureContext,
        RepairBundleClosureContext,
        ReproducibilityOperatorBriefContext,
        SessionExportBugPacketContext,
        TelemetryContext,
        cmd_apply_bundle as extracted_cmd_apply_bundle,
        cmd_apply_closure as extracted_cmd_apply_closure,
        cmd_artifact_consistency as extracted_cmd_artifact_consistency,
        cmd_bug_packet as extracted_cmd_bug_packet,
        cmd_bundle_check as extracted_cmd_bundle_check,
        cmd_checkpoint_operator_reading as extracted_cmd_checkpoint_operator_reading,
        cmd_closure as extracted_cmd_closure,
        cmd_compare as extracted_cmd_compare,
        cmd_consistency_recovery as extracted_cmd_consistency_recovery,
        cmd_consistency_recovery_prompt as extracted_cmd_consistency_recovery_prompt,
        cmd_consistency_recovery_prompt_reading as extracted_cmd_consistency_recovery_prompt_reading,
        cmd_create_checkpoint as extracted_cmd_create_checkpoint,
        cmd_deploy as extracted_cmd_deploy,
        cmd_deploy_check as extracted_cmd_deploy_check,
        cmd_doctor as extracted_cmd_doctor,
        cmd_externality_pressure as extracted_cmd_externality_pressure,
        cmd_generate_prompt as extracted_cmd_generate_prompt,
        cmd_governed_cost as extracted_cmd_governed_cost,
        cmd_hybrid_status as extracted_cmd_hybrid_status,
        cmd_init_agent as extracted_cmd_init_agent,
        cmd_init_ci as extracted_cmd_init_ci,
        cmd_install_agent_files as extracted_cmd_install_agent_files,
        cmd_observability as extracted_cmd_observability,
        cmd_operator_brief as extracted_cmd_operator_brief,
        cmd_operator_brief_chain as extracted_cmd_operator_brief_chain,
        cmd_operator_reading as extracted_cmd_operator_reading,
        cmd_operator_render as extracted_cmd_operator_render,
        cmd_operator_render_adoption as extracted_cmd_operator_render_adoption,
        cmd_operator_render_adoption_delta as extracted_cmd_operator_render_adoption_delta,
        cmd_orchestrate as extracted_cmd_orchestrate,
        cmd_plan_proof as extracted_cmd_plan_proof,
        cmd_preflight as extracted_cmd_preflight,
        cmd_preparation_receipt as extracted_cmd_preparation_receipt,
        cmd_prompt_followup as extracted_cmd_prompt_followup,
        cmd_prompt_retry_guard as extracted_cmd_prompt_retry_guard,
        cmd_recommend_mode as extracted_cmd_recommend_mode,
        cmd_refresh as extracted_cmd_refresh,
        cmd_repair_handoff as extracted_cmd_repair_handoff,
        cmd_repair_packet as extracted_cmd_repair_packet,
        cmd_reproducibility as extracted_cmd_reproducibility,
        cmd_restore_checkpoint as extracted_cmd_restore_checkpoint,
        cmd_resume as extracted_cmd_resume,
        cmd_save as extracted_cmd_save,
        cmd_second_operator as extracted_cmd_second_operator,
        cmd_select_mode as extracted_cmd_select_mode,
        cmd_session_export as extracted_cmd_session_export,
        cmd_substitute_pressure as extracted_cmd_substitute_pressure,
        cmd_telemetry_enable as extracted_cmd_telemetry_enable,
        cmd_telemetry_export as extracted_cmd_telemetry_export,
        cmd_thin_output as extracted_cmd_thin_output,
        cmd_thin_output_reading as extracted_cmd_thin_output_reading,
        cmd_validate as extracted_cmd_validate,
        cmd_verify_checkpoint as extracted_cmd_verify_checkpoint,
        run_install_agent_files_command,
    )
    from .synrail_controlled_start_shell_v0 import (
        ControlledStartShellContext,
        cmd_init as extracted_cmd_init,
        cmd_refresh_acceptance as extracted_cmd_refresh_acceptance,
        cmd_start as extracted_cmd_start,
    )
    from .synrail_public_shell_v0 import (
        PublicShellContext,
        cmd_explain_proof as extracted_cmd_explain_proof,
        cmd_final_result_template as extracted_cmd_final_result_template,
        cmd_readback_template as extracted_cmd_readback_template,
        cmd_runtime_helper as extracted_cmd_runtime_helper,
        cmd_scenario_proof_template as extracted_cmd_scenario_proof_template,
        cmd_status as extracted_cmd_status,
    )
except ImportError:
    from synrail_commands_v0 import (
        AgentAdoptionContext,
        CiPreflightContext,
        ApplyRefreshValidateContext,
        DoctorCompareSubstituteContext,
        HybridModeContext,
        ProofPreparationCostContext,
        CheckpointCreateSaveVerifyContext,
        RestoreConsistencyThinContext,
        PromptReadingFollowupContext,
        RetryRecoveryReadingContext,
        RecoveryPromptObservabilityContext,
        OperatorBriefRenderReadingContext,
        OperatorRenderAdoptionPressureContext,
        RepairBundleClosureContext,
        ReproducibilityOperatorBriefContext,
        SessionExportBugPacketContext,
        TelemetryContext,
        cmd_apply_bundle as extracted_cmd_apply_bundle,
        cmd_apply_closure as extracted_cmd_apply_closure,
        cmd_artifact_consistency as extracted_cmd_artifact_consistency,
        cmd_bug_packet as extracted_cmd_bug_packet,
        cmd_bundle_check as extracted_cmd_bundle_check,
        cmd_checkpoint_operator_reading as extracted_cmd_checkpoint_operator_reading,
        cmd_closure as extracted_cmd_closure,
        cmd_compare as extracted_cmd_compare,
        cmd_consistency_recovery as extracted_cmd_consistency_recovery,
        cmd_consistency_recovery_prompt as extracted_cmd_consistency_recovery_prompt,
        cmd_consistency_recovery_prompt_reading as extracted_cmd_consistency_recovery_prompt_reading,
        cmd_create_checkpoint as extracted_cmd_create_checkpoint,
        cmd_deploy as extracted_cmd_deploy,
        cmd_deploy_check as extracted_cmd_deploy_check,
        cmd_doctor as extracted_cmd_doctor,
        cmd_externality_pressure as extracted_cmd_externality_pressure,
        cmd_generate_prompt as extracted_cmd_generate_prompt,
        cmd_governed_cost as extracted_cmd_governed_cost,
        cmd_hybrid_status as extracted_cmd_hybrid_status,
        cmd_init_agent as extracted_cmd_init_agent,
        cmd_init_ci as extracted_cmd_init_ci,
        cmd_install_agent_files as extracted_cmd_install_agent_files,
        cmd_observability as extracted_cmd_observability,
        cmd_operator_brief as extracted_cmd_operator_brief,
        cmd_operator_brief_chain as extracted_cmd_operator_brief_chain,
        cmd_operator_reading as extracted_cmd_operator_reading,
        cmd_operator_render as extracted_cmd_operator_render,
        cmd_operator_render_adoption as extracted_cmd_operator_render_adoption,
        cmd_operator_render_adoption_delta as extracted_cmd_operator_render_adoption_delta,
        cmd_orchestrate as extracted_cmd_orchestrate,
        cmd_plan_proof as extracted_cmd_plan_proof,
        cmd_preflight as extracted_cmd_preflight,
        cmd_preparation_receipt as extracted_cmd_preparation_receipt,
        cmd_prompt_followup as extracted_cmd_prompt_followup,
        cmd_prompt_retry_guard as extracted_cmd_prompt_retry_guard,
        cmd_recommend_mode as extracted_cmd_recommend_mode,
        cmd_refresh as extracted_cmd_refresh,
        cmd_repair_handoff as extracted_cmd_repair_handoff,
        cmd_repair_packet as extracted_cmd_repair_packet,
        cmd_reproducibility as extracted_cmd_reproducibility,
        cmd_restore_checkpoint as extracted_cmd_restore_checkpoint,
        cmd_resume as extracted_cmd_resume,
        cmd_save as extracted_cmd_save,
        cmd_second_operator as extracted_cmd_second_operator,
        cmd_select_mode as extracted_cmd_select_mode,
        cmd_session_export as extracted_cmd_session_export,
        cmd_substitute_pressure as extracted_cmd_substitute_pressure,
        cmd_telemetry_enable as extracted_cmd_telemetry_enable,
        cmd_telemetry_export as extracted_cmd_telemetry_export,
        cmd_thin_output as extracted_cmd_thin_output,
        cmd_thin_output_reading as extracted_cmd_thin_output_reading,
        cmd_validate as extracted_cmd_validate,
        cmd_verify_checkpoint as extracted_cmd_verify_checkpoint,
        run_install_agent_files_command,
    )
    from synrail_controlled_start_shell_v0 import (
        ControlledStartShellContext,
        cmd_init as extracted_cmd_init,
        cmd_refresh_acceptance as extracted_cmd_refresh_acceptance,
        cmd_start as extracted_cmd_start,
    )
    from synrail_public_shell_v0 import (
        PublicShellContext,
        cmd_explain_proof as extracted_cmd_explain_proof,
        cmd_final_result_template as extracted_cmd_final_result_template,
        cmd_readback_template as extracted_cmd_readback_template,
        cmd_runtime_helper as extracted_cmd_runtime_helper,
        cmd_scenario_proof_template as extracted_cmd_scenario_proof_template,
        cmd_status as extracted_cmd_status,
    )

try:
    from .synrail_path_scope_v0 import (
        ARTIFACT_SCOPE,
        DUAL_SCOPE,
        PROJECT_SCOPE,
        PathScopeValidationError,
        validate_namespace_paths,
        validate_root_within_project,
    )
except ImportError:
    from synrail_path_scope_v0 import (
        ARTIFACT_SCOPE,
        DUAL_SCOPE,
        PROJECT_SCOPE,
        PathScopeValidationError,
        validate_namespace_paths,
        validate_root_within_project,
    )


HERE = Path(__file__).resolve().parent
SPINE = HERE / "synrail_spine_v0.py"
BUNDLE = HERE / "synrail_bundle_v0.py"
CLOSURE = HERE / "synrail_closure_v0.py"
REFRESH = HERE / "synrail_refresh_v0.py"
VALIDATE = HERE / "synrail_validate_v0.py"
DOCTOR = HERE / "synrail_doctor_v1.py"
HARNESS_V0 = HERE / "synrail_baseline_harness_v0.py"
HARNESS_V1 = HERE / "synrail_baseline_harness_v1.py"
HARNESS_V2 = HERE / "synrail_substitute_harness_v0.py"
SUBSTITUTE_PRESSURE = HERE / "synrail_substitute_pressure_v0.py"
HYBRID_STATUS = HERE / "synrail_hybrid_status_v0.py"
MODE_SELECTOR = HERE / "synrail_mode_selector_v0.py"
MODE_RECEIPT = HERE / "synrail_mode_receipt_v0.py"
PROOF_PLAN = HERE / "synrail_proof_plan_v0.py"
PREPARATION_RECEIPT = HERE / "synrail_preparation_receipt_v0.py"
GOVERNED_COST = HERE / "synrail_governed_cost_delta_v0.py"
REPAIR_HANDOFF = HERE / "synrail_repair_handoff_v0.py"
REPAIR_PACKET = HERE / "synrail_repair_packet_v0.py"
CHECKPOINT = HERE / "synrail_checkpoint_v0.py"
ARTIFACT_CONSISTENCY = HERE / "synrail_artifact_consistency_v0.py"
OBSERVABILITY = HERE / "synrail_observability_v0.py"
BUG_PACKET = HERE / "synrail_bug_packet_v0.py"
REPRODUCIBILITY = HERE / "synrail_reproducibility_v0.py"
SECOND_OPERATOR = HERE / "synrail_second_operator_v0.py"
OPERATOR_BRIEF = HERE / "synrail_operator_brief_v0.py"
OPERATOR_BRIEF_CHAIN = HERE / "synrail_operator_brief_chain_v0.py"
OPERATOR_RENDER = HERE / "synrail_operator_render_v0.py"
OPERATOR_RENDER_ADOPTION = HERE / "synrail_operator_render_adoption_v0.py"
OPERATOR_RENDER_ADOPTION_DELTA = HERE / "synrail_operator_render_adoption_delta_v0.py"
OPERATOR_READING = HERE / "synrail_operator_reading_v0.py"
EXTERNALITY_PRESSURE = HERE / "synrail_externality_pressure_v0.py"
THIN_OUTPUT = HERE / "synrail_thin_output_v0.py"
PROMPT_BRIDGE = HERE / "synrail_repair_prompt_bridge_v0.py"
THIN_OUTPUT_READING = HERE / "synrail_thin_output_reading_v0.py"
PROMPT_FOLLOWUP = HERE / "synrail_prompt_followup_v0.py"
PROMPT_RETRY_GUARD = HERE / "synrail_prompt_retry_guard_v0.py"
ACCEPTANCE_CRITERIA = HERE / "synrail_acceptance_criteria_v0.py"
CONSISTENCY_RECOVERY = HERE / "synrail_consistency_recovery_v0.py"
CHECKPOINT_OPERATOR_READING = HERE / "synrail_checkpoint_operator_reading_v0.py"
CONSISTENCY_RECOVERY_PROMPT = HERE / "synrail_consistency_recovery_prompt_v0.py"
CONSISTENCY_RECOVERY_PROMPT_READING = HERE / "synrail_consistency_recovery_prompt_reading_v0.py"
ALPHA_TELEMETRY = HERE / "synrail_alpha_telemetry_v0.py"
REFERENCE_RUNNER_MODULE = "reference_runner"

DEFAULT_ALPHA_ARTIFACT_ROOT = ".synrail"
DEFAULT_ALPHA_TASK_CLASS = "bounded_change"
DEFAULT_EPHEMERAL_STALE_SECONDS = 24 * 60 * 60
SUPPORTED_ALPHA_TARGET_CLASSIFICATIONS = {"trusted_worktree", "resume_surface"}
ALPHA_FILE_NAMES = {
    "state": "state.json",
    "project_profile": "project_profile.json",
    "bootstrap": "bootstrap.json",
    "bootstrap_validation": "bootstrap_validation.json",
    "proof_request": "proof_request.json",
    "acceptance_criteria": "acceptance_criteria.json",
    "acceptance_validation": "acceptance_validation.json",
    "doctor": "doctor.json",
    "bundle": "bundle.json",
    "closure": "closure.json",
    "closure_certificate": "closure_certificate.json",
    "refresh": "refresh.json",
    "report": "report.json",
    "orchestration": "orchestration.json",
    "run": "run.json",
    "repair_packet": "repair_packet.json",
    "repair_handoff": "repair_handoff.json",
    "repair_receipt": "repair_receipt.json",
    "observability": "observability.json",
    "bug_packet": "bug_packet.json",
    "session_export": "session_export.json",
    "artifact_consistency": "artifact_consistency.json",
    "consistency_recovery": "consistency_recovery.json",
    "plan": "plan.json",
    "preparation_receipt": "preparation_receipt.json",
    "selection_receipt": "selection_receipt.json",
    "thin_output": "thin_output.json",
    "prompt": "prompt.json",
    "checkpoint_restore": "checkpoint_restore.json",
    "checkpoint_restore_preview": "checkpoint_restore_preview.json",
    "deploy_receipt": "deploy_receipt.json",
}
CHECKPOINT_RECORD_BASENAME = "checkpoint_record.json"
CHECKPOINT_VERIFY_BASENAME = "checkpoint_verify.json"
PROJECT_PROFILE_BASENAME = "project_profile.json"


def run_python(script: Path, args: list[str]) -> int:
    if __package__:
        cmd = [sys.executable, "-m", REFERENCE_RUNNER_MODULE, script.stem, *args]
    else:
        cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, check=False, env=python_subprocess_env()).returncode


def run_python_capture(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    if __package__:
        cmd = [sys.executable, "-m", REFERENCE_RUNNER_MODULE, script.stem, *args]
    else:
        cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, check=False, capture_output=True, text=True, env=python_subprocess_env())


def python_subprocess_env() -> dict[str, str]:
    env = os.environ.copy()
    source_root = HERE.parents[1]
    existing = env.get("PYTHONPATH", "")
    paths = [str(source_root)]
    if existing:
        paths.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    return env




def normalize_repo_relative_path(value: str) -> str:
    return value.strip().replace("\\", "/").strip("/")


def dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        candidate = value.strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        ordered.append(candidate)
    return ordered


def filter_artifact_root_changes(changed_files: list[str], artifact_root: str) -> list[str]:
    normalized_root = normalize_repo_relative_path(artifact_root)

    filtered: list[str] = []
    for value in changed_files:
        normalized = normalize_repo_relative_path(value)
        top_level = normalized.split("/", 1)[0] if normalized else ""
        if top_level.startswith(".synrail"):
            continue
        if normalized_root and (normalized == normalized_root or normalized.startswith(f"{normalized_root}/")):
            continue
        filtered.append(value)
    return filtered


def git_status_changed_paths(target: Path) -> list[str] | None:
    completed = subprocess.run(
        ["git", "-C", str(target), "status", "--porcelain", "--untracked-files=all"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None

    changed_paths: list[str] = []
    for raw_line in completed.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        candidate = raw_line[3:].strip()
        if not candidate:
            continue
        if " -> " in candidate:
            candidate = candidate.split(" -> ", 1)[1].strip()
        changed_paths.append(candidate)
    return dedupe_preserving_order(changed_paths)


def diff_provenance_records_from_final_result(final_result: dict) -> list[dict]:
    records: list[dict] = []
    diff_provenance = final_result.get("diff_provenance", {})
    if isinstance(diff_provenance, dict):
        records.append(diff_provenance)
    elif isinstance(diff_provenance, list):
        records.extend(value for value in diff_provenance if isinstance(value, dict))

    for key in ("diff_provenance_records", "per_file_diff_provenance", "per_file_diff_provenance_records"):
        value = final_result.get(key, [])
        if isinstance(value, list):
            records.extend(item for item in value if isinstance(item, dict))
    return records


def patch_shaped_git_diff_paths(git_diff: object) -> list[str]:
    if not isinstance(git_diff, str):
        return []

    diff_text = git_diff.strip()
    if not diff_text:
        return []
    if "diff --git " not in diff_text or "\n--- " not in diff_text or "\n+++ " not in diff_text or "\n@@" not in diff_text:
        return []

    changed_paths: list[str] = []
    for raw_line in diff_text.splitlines():
        if not raw_line.startswith("diff --git "):
            continue
        payload = raw_line[len("diff --git ") :].strip()
        if not payload.startswith("a/") or " b/" not in payload:
            continue
        before, after = payload.split(" b/", 1)
        before_path = normalize_repo_relative_path(before[2:])
        after_path = normalize_repo_relative_path(after)
        candidate = after_path or before_path
        if candidate and candidate != "dev/null":
            changed_paths.append(candidate)
    return dedupe_preserving_order(changed_paths)


def proof_backed_scope_paths_from_final_result(final_result_path: Path) -> list[str]:
    if not final_result_path.exists():
        return []
    try:
        final_result = load_json(final_result_path)
    except (OSError, json.JSONDecodeError):
        return []

    allowed_scope_paths = list(patch_shaped_git_diff_paths(final_result.get("git_diff", "")))
    for record in diff_provenance_records_from_final_result(final_result):
        changed_file = record.get("changed_file", "")
        if not isinstance(changed_file, str):
            continue
        normalized = normalize_repo_relative_path(changed_file)
        if normalized:
            allowed_scope_paths.append(normalized)
    return dedupe_preserving_order(allowed_scope_paths)


def observed_changes_within_allowed_scope(changed_files: list[str], allowed_scope_paths: list[str]) -> bool:
    normalized_allowed = [normalize_repo_relative_path(value) for value in allowed_scope_paths if normalize_repo_relative_path(value)]
    if not changed_files or not normalized_allowed:
        return False

    for value in changed_files:
        normalized = normalize_repo_relative_path(value)
        if not normalized:
            continue
        if any(normalized == allowed or normalized.startswith(f"{allowed}/") for allowed in normalized_allowed):
            continue
        return False
    return True


def maybe_apply_observed_git_scope_defaults(args: argparse.Namespace, *, state: dict | None = None) -> None:
    if getattr(args, "clean_surface", False):
        return
    target_path_text = getattr(args, "target_path", "") or ""
    final_result_text = getattr(args, "final_result", "") or ""
    state_file_text = getattr(args, "state_file", "") or ""
    if not target_path_text or not final_result_text or not state_file_text:
        return

    target_path = Path(target_path_text)
    if not (target_path / ".git").exists():
        return

    if state is None:
        state_path = Path(state_file_text)
        if not state_path.exists():
            return
        state = ensure_run_state_extensions(load_json(state_path))

    current_state = state.get("state", "")
    if not current_state or current_state in {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}:
        return

    changed_files = list(getattr(args, "changed_file", []) or [])
    allowed_scope_paths = list(getattr(args, "allowed_scope_path", []) or [])
    if not changed_files:
        observed_changed = git_status_changed_paths(target_path)
        if observed_changed:
            changed_files = filter_artifact_root_changes(
                observed_changed,
                getattr(args, "artifact_root", "") or "",
            )
    if not allowed_scope_paths:
        allowed_scope_paths = proof_backed_scope_paths_from_final_result(Path(final_result_text))

    if changed_files:
        args.changed_file = changed_files
    if allowed_scope_paths:
        args.allowed_scope_path = allowed_scope_paths
    if observed_changes_within_allowed_scope(changed_files, allowed_scope_paths):
        args.clean_surface = True


def comparison_harness_for_inputs(baseline_file: str, synrail_file: str) -> Path:
    baseline = load_json(Path(baseline_file))
    synrail = load_json(Path(synrail_file))
    baseline_version = baseline.get("schema_version", "")
    synrail_version = synrail.get("schema_version", "")

    if baseline_version != synrail_version:
        raise ValueError("comparison input schema versions do not match")

    if baseline_version == "comparison_input_v1":
        return HARNESS_V1
    if baseline_version == "comparison_input_v2":
        return HARNESS_V2

    return HARNESS_V0


def default_alpha_run_id() -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"ALPHA_RUN_{stamp}_{uuid.uuid4().hex[:6]}"


def project_profile_file(root: Path) -> Path:
    return root / PROJECT_PROFILE_BASENAME


def write_acceptance_criteria(root: Path, *, generated_by: str) -> subprocess.CompletedProcess[str]:
    return run_python_capture(
        ACCEPTANCE_CRITERIA,
        [
            "build",
            "--project-profile-file", str(project_profile_file(root)),
            "--generated-by", generated_by,
            "--output", str(alpha_file(root, "acceptance_criteria")),
        ],
    )


def write_acceptance_validation(root: Path, *, criteria_file: Path, state_file: Path) -> subprocess.CompletedProcess[str]:
    return run_python_capture(
        ACCEPTANCE_CRITERIA,
        [
            "validate",
            "--criteria-file", str(criteria_file),
            "--state-file", str(state_file),
            "--project-profile-file", str(project_profile_file(root)),
            "--output", str(alpha_file(root, "acceptance_validation")),
        ],
    )


def save_project_profile(root: Path, payload: dict) -> None:
    save_json(project_profile_file(root), payload)


def save_alpha_identity_files(root: Path, *, task_identity: str = "", prompt_identity: str = "") -> None:
    task_text = (task_identity or "").strip()
    prompt_text = (prompt_identity or "").strip() or task_text
    if task_text:
        (root / "task_identity.txt").write_text(task_text + "\n")
    if prompt_text:
        (root / "prompt_identity.txt").write_text(prompt_text + "\n")


def save_alpha_target_identity_file(root: Path, *, target_identity: str) -> None:
    text = (target_identity or "").strip()
    if text:
        (root / "target_identity.txt").write_text(text + "\n")


def preferred_synrail_fallback_command() -> str | None:
    return preferred_synrail_fallback_command_for_runtime(
        argv0=sys.argv[0],
        python_executable=sys.executable,
    )


def agent_adoption_context() -> AgentAdoptionContext:
    return AgentAdoptionContext(
        relative_artifact_root_for_project=relative_artifact_root_for_project,
        preferred_synrail_command=preferred_synrail_command,
        preferred_synrail_fallback_command=preferred_synrail_fallback_command,
        preferred_repo_native_alpha_command=preferred_repo_native_alpha_command,
        workspace_git_context=workspace_git_context,
        project_prefers_runtime_evidence=project_prefers_runtime_evidence,
        render_agent_policy_markdown=render_agent_policy_markdown,
        render_gemini_policy_markdown=render_gemini_policy_markdown,
        render_claude_policy_markdown=render_claude_policy_markdown,
        render_agents_policy_block=render_agents_policy_block,
        render_gemini_policy_block=render_gemini_policy_block,
        render_claude_policy_block=render_claude_policy_block,
        write_agent_policy_file=write_agent_policy_file,
    )


def cmd_install_agent_files(args: argparse.Namespace) -> int:
    return extracted_cmd_install_agent_files(args, context=agent_adoption_context())


def cmd_init_agent(args: argparse.Namespace) -> int:
    return extracted_cmd_init_agent(args, context=agent_adoption_context())


def ci_preflight_context() -> CiPreflightContext:
    return CiPreflightContext(
        relative_artifact_root_for_project=relative_artifact_root_for_project,
        preferred_repo_native_alpha_command=preferred_repo_native_alpha_command,
        current_project_root=current_project_root,
        preferred_synrail_command=preferred_synrail_command,
        preferred_synrail_fallback_command=preferred_synrail_fallback_command,
        workspace_git_context=workspace_git_context,
    )


def cmd_init_ci(args: argparse.Namespace) -> int:
    return extracted_cmd_init_ci(args, context=ci_preflight_context())


def cmd_preflight(args: argparse.Namespace) -> int:
    return extracted_cmd_preflight(args, context=ci_preflight_context())


def telemetry_context() -> TelemetryContext:
    return TelemetryContext(
        alpha_root_from_args=alpha_root_from_args,
        enable_telemetry=enable_telemetry,
        default_session_replay_file=default_session_replay_file,
        default_issue_body_file=default_issue_body_file,
        export_session_replay=export_session_replay,
    )


def session_export_bug_packet_context() -> SessionExportBugPacketContext:
    return SessionExportBugPacketContext(
        alpha_root_from_args=alpha_root_from_args,
        maybe_existing_alpha_file=maybe_existing_alpha_file,
        alpha_file=alpha_file,
        cmd_observability=cmd_observability,
        run_python=run_python,
        bug_packet_script=BUG_PACKET,
    )


def reproducibility_operator_brief_context() -> ReproducibilityOperatorBriefContext:
    return ReproducibilityOperatorBriefContext(
        run_python=run_python,
        reproducibility_script=REPRODUCIBILITY,
        second_operator_script=SECOND_OPERATOR,
        operator_brief_script=OPERATOR_BRIEF,
    )


def operator_brief_render_reading_context() -> OperatorBriefRenderReadingContext:
    return OperatorBriefRenderReadingContext(
        run_python=run_python,
        operator_brief_chain_script=OPERATOR_BRIEF_CHAIN,
        operator_render_script=OPERATOR_RENDER,
        operator_reading_script=OPERATOR_READING,
    )


def operator_render_adoption_pressure_context() -> OperatorRenderAdoptionPressureContext:
    return OperatorRenderAdoptionPressureContext(
        run_python=run_python,
        operator_render_adoption_script=OPERATOR_RENDER_ADOPTION,
        operator_render_adoption_delta_script=OPERATOR_RENDER_ADOPTION_DELTA,
        externality_pressure_script=EXTERNALITY_PRESSURE,
    )


def repair_bundle_closure_context() -> RepairBundleClosureContext:
    return RepairBundleClosureContext(
        run_python=run_python,
        repair_handoff_script=REPAIR_HANDOFF,
        bundle_script=BUNDLE,
        closure_script=CLOSURE,
    )


def apply_refresh_validate_context() -> ApplyRefreshValidateContext:
    return ApplyRefreshValidateContext(
        run_python=run_python,
        spine_script=SPINE,
        refresh_script=REFRESH,
        validate_script=VALIDATE,
    )


def doctor_compare_substitute_context() -> DoctorCompareSubstituteContext:
    return DoctorCompareSubstituteContext(
        alpha_root_from_args=alpha_root_from_args,
        current_project_root=current_project_root,
        validate_root_within_project=validate_root_within_project,
        validate_doctor_paths=validate_doctor_paths,
        load_json=load_json,
        comparison_harness_for_inputs=comparison_harness_for_inputs,
        run_python=run_python,
        doctor_script=DOCTOR,
        substitute_pressure_script=SUBSTITUTE_PRESSURE,
    )


def hybrid_mode_context() -> HybridModeContext:
    return HybridModeContext(
        run_python=run_python,
        hybrid_status_script=HYBRID_STATUS,
        mode_selector_script=MODE_SELECTOR,
        mode_receipt_script=MODE_RECEIPT,
    )


def proof_preparation_cost_context() -> ProofPreparationCostContext:
    return ProofPreparationCostContext(
        run_python=run_python,
        proof_plan_script=PROOF_PLAN,
        preparation_receipt_script=PREPARATION_RECEIPT,
        governed_cost_script=GOVERNED_COST,
    )


def checkpoint_create_save_verify_context() -> CheckpointCreateSaveVerifyContext:
    return CheckpointCreateSaveVerifyContext(
        alpha_root_from_args=alpha_root_from_args,
        checkpoint_record_file=checkpoint_record_file,
        checkpoint_root=checkpoint_root,
        alpha_file=alpha_file,
        maybe_existing_alpha_file=maybe_existing_alpha_file,
        checkpoint_verify_file=checkpoint_verify_file,
        discover_checkpoint_record=discover_checkpoint_record,
        run_python=run_python,
        run_python_capture=run_python_capture,
        print_checkpoint_summary=print_checkpoint_summary,
        print_save_summary=print_save_summary,
        shell_command=shell_command,
        checkpoint_script=CHECKPOINT,
    )


def restore_consistency_thin_context() -> RestoreConsistencyThinContext:
    return RestoreConsistencyThinContext(
        alpha_root_from_args=alpha_root_from_args,
        discover_checkpoint_record=discover_checkpoint_record,
        alpha_file=alpha_file,
        load_json=load_json,
        maybe_existing_alpha_file=maybe_existing_alpha_file,
        run_python=run_python,
        run_python_capture=run_python_capture,
        print_checkpoint_summary=print_checkpoint_summary,
        shell_command=shell_command,
        sync_restored_checkpoint_artifacts=sync_restored_checkpoint_artifacts,
        print_thin_output_summary=print_thin_output_summary,
        checkpoint_script=CHECKPOINT,
        artifact_consistency_script=ARTIFACT_CONSISTENCY,
        thin_output_script=THIN_OUTPUT,
    )


def prompt_reading_followup_context() -> PromptReadingFollowupContext:
    return PromptReadingFollowupContext(
        alpha_root_from_args=alpha_root_from_args,
        alpha_file=alpha_file,
        maybe_existing_alpha_file=maybe_existing_alpha_file,
        discover_checkpoint_record=discover_checkpoint_record,
        load_json=load_json,
        apply_resume_output_defaults=apply_resume_output_defaults,
        ensure_repair_packet_synthesis_defaults=ensure_repair_packet_synthesis_defaults,
        synthesize_repair_packet=synthesize_repair_packet,
        run_python=run_python,
        run_python_capture=run_python_capture,
        maybe_materialize_requested_fallback_surface=maybe_materialize_requested_fallback_surface,
        print_prompt_summary=print_prompt_summary,
        load_project_profile=load_project_profile,
        plain_shell_command=plain_shell_command,
        prompt_bridge_script=PROMPT_BRIDGE,
        thin_output_reading_script=THIN_OUTPUT_READING,
        prompt_followup_script=PROMPT_FOLLOWUP,
    )


def retry_recovery_reading_context() -> RetryRecoveryReadingContext:
    return RetryRecoveryReadingContext(
        run_python=run_python,
        prompt_retry_guard_script=PROMPT_RETRY_GUARD,
        consistency_recovery_script=CONSISTENCY_RECOVERY,
        checkpoint_operator_reading_script=CHECKPOINT_OPERATOR_READING,
    )


def recovery_prompt_observability_context() -> RecoveryPromptObservabilityContext:
    return RecoveryPromptObservabilityContext(
        run_python=run_python,
        consistency_recovery_prompt_script=CONSISTENCY_RECOVERY_PROMPT,
        consistency_recovery_prompt_reading_script=CONSISTENCY_RECOVERY_PROMPT_READING,
        observability_script=OBSERVABILITY,
    )


def load_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text().strip()


def expected_target_identity_for_root(root: Path) -> str:
    target_identity = load_text_if_exists(root / "target_identity.txt")
    if target_identity:
        return target_identity
    bootstrap_file = alpha_file(root, "bootstrap")
    if bootstrap_file.exists():
        bootstrap = load_bootstrap_json(bootstrap_file)
        for field in ["target_identity", "execution_surface_identity"]:
            value = (bootstrap.get(field, "") or "").strip()
            if value:
                return value
    profile = load_project_profile(root) or {}
    return (profile.get("execution_surface_identity", "") or "").strip()


def load_project_profile(root: Path | None) -> dict | None:
    if not root:
        return None
    profile_path = project_profile_file(root)
    if not profile_path.exists():
        return None
    return load_json(profile_path)


def detect_project_type(project_root: Path) -> str:
    markers = [
        ("package.json", "node"),
        ("pyproject.toml", "python"),
        ("setup.py", "python"),
        ("setup.cfg", "python"),
        ("requirements.txt", "python"),
        ("go.mod", "go"),
        ("Cargo.toml", "rust"),
        ("Gemfile", "ruby"),
        ("composer.json", "php"),
    ]
    for marker, project_type in markers:
        if (project_root / marker).exists():
            return project_type
    return "generic"


def candidate_paths(project_root: Path, root: Path, names: list[str]) -> list[str]:
    ordered: list[Path] = []
    for base in [root, project_root]:
        for name in names:
            candidate = (base / name).resolve()
            if candidate not in ordered:
                ordered.append(candidate)
    return [str(path) for path in ordered]


def find_enclosing_git_root(project_root: Path) -> Path | None:
    resolved = project_root.resolve()
    for candidate in [resolved, *resolved.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def workspace_git_context(project_root: Path) -> dict:
    enclosing_git_root = find_enclosing_git_root(project_root)
    if enclosing_git_root is None:
        return {
            "workspace_git_mode": "no_git",
            "workspace_git_root": "",
            "parent_git_root": "",
            "workspace_isolation_note": "",
        }
    if enclosing_git_root == project_root.resolve():
        return {
            "workspace_git_mode": "workspace_git_root",
            "workspace_git_root": str(enclosing_git_root),
            "parent_git_root": "",
            "workspace_isolation_note": "",
        }
    return {
        "workspace_git_mode": "nested_parent_git",
        "workspace_git_root": str(enclosing_git_root),
        "parent_git_root": str(enclosing_git_root),
        "workspace_isolation_note": (
            f"Parent git repo detected above the project root at {enclosing_git_root}. "
            "Treat only this project root as the execution surface for the run. "
            "If git status or git diff climbs to the parent repo, do not use that parent output as proof here."
        ),
    }


def build_project_profile(*, project_root: Path, root: Path, task_class: str) -> dict:
    project_type = detect_project_type(project_root)
    git_context = workspace_git_context(project_root)
    return {
        "schema_version": "alpha_project_profile_v0",
        "project_root": str(project_root),
        "artifact_root": str(root.resolve()),
        "project_type": project_type,
        "prefers_runtime_evidence": project_prefers_runtime_evidence(project_root),
        "task_class": task_class,
        "target_path": str(project_root),
        "target_classification": "trusted_worktree",
        "intended_run_class": "core_probe",
        "baseline_identity": f"autodetected_{project_type}_baseline",
        "execution_surface_identity": f"autodetected_{project_type}_worktree",
        "artifact_path": str((root / "final_result.json").resolve()),
        "final_result_candidates": candidate_paths(project_root, root, ["final_result.json", "final_result.txt", "result.json", "result.txt"]),
        "readback_candidates": candidate_paths(project_root, root, ["readback.json", "readback.txt"]),
        "scenario_proof_candidates": candidate_paths(project_root, root, ["scenario_proof.json", "scenario_proof.md", "scenario_proof.txt"]),
        **git_context,
    }


def discover_candidate_file(candidates: list[str]) -> str | None:
    return discover_candidate_file_filtered(candidates, ignored_paths=set())


def discover_candidate_file_filtered(candidates: list[str], *, ignored_paths: set[Path]) -> str | None:
    for value in candidates:
        candidate = Path(value)
        if candidate.exists() and candidate.is_file() and candidate.resolve() not in ignored_paths:
            return str(candidate)
    return None


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        return str(resolved)
    text = str(relative)
    return text or "."


def display_path_from_base(path: Path, *, base: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(base.resolve())
    except ValueError:
        return str(resolved)
    text = str(relative)
    return text or "."


def default_workspace_artifact_root(*, project_root: Path | None = None) -> Path:
    base = (project_root or Path.cwd()).resolve()
    return (base / DEFAULT_ALPHA_ARTIFACT_ROOT).resolve()


def default_cache_root() -> Path:
    explicit_cache = os.environ.get("SYNRAIL_CACHE_HOME", "").strip()
    if explicit_cache:
        return Path(explicit_cache).expanduser().resolve()
    if sys.platform == "darwin":
        return (Path.home() / "Library" / "Caches" / "synrail").resolve()
    xdg_cache = os.environ.get("XDG_CACHE_HOME", "").strip()
    if xdg_cache:
        return (Path(xdg_cache).expanduser() / "synrail").resolve()
    return (Path.home() / ".cache" / "synrail").resolve()


def ephemeral_artifact_root(*, project_root: Path | None = None) -> Path:
    base = (project_root or Path.cwd()).resolve()
    key = hashlib.sha256(str(base).encode("utf-8")).hexdigest()[:16]
    return (default_cache_root() / "runs" / key / "current").resolve()


def artifact_root_last_activity(root: Path) -> float:
    latest = root.stat().st_mtime
    for path in root.rglob("*"):
        try:
            latest = max(latest, path.stat().st_mtime)
        except OSError:
            continue
    return latest


def ephemeral_max_age_seconds(args: argparse.Namespace) -> float:
    hours = getattr(args, "ephemeral_max_age_hours", None)
    if hours is None:
        return float(DEFAULT_EPHEMERAL_STALE_SECONDS)
    return max(0.0, float(hours) * 60 * 60)


def prune_stale_ephemeral_runs(*, max_age_seconds: float) -> int:
    runs_root = default_cache_root() / "runs"
    if not runs_root.is_dir():
        return 0
    cutoff = time.time() - max_age_seconds
    removed = 0
    for current_root in runs_root.glob("*/current"):
        if not current_root.is_dir():
            continue
        try:
            stale = artifact_root_last_activity(current_root) < cutoff
        except OSError:
            stale = True
        if not stale:
            continue
        shutil.rmtree(current_root, ignore_errors=True)
        removed += 1
        parent = current_root.parent
        try:
            parent.rmdir()
        except OSError:
            pass
    return removed


def is_default_workspace_artifact_root(root: Path, *, project_root: Path | None = None) -> bool:
    return root.resolve() == default_workspace_artifact_root(project_root=project_root)


def preferred_cli_executable(*, project_root: Path | None = None) -> str:
    if shutil.which("synrail"):
        return "synrail"
    search_roots: list[Path] = []
    if project_root is not None:
        search_roots.append(project_root.resolve())
    cwd = Path.cwd().resolve()
    if cwd not in search_roots:
        search_roots.append(cwd)
    for base in search_roots:
        candidate = base / ".venv" / "bin" / "synrail"
        if candidate.exists() and candidate.is_file():
            return display_path(candidate)
    return "synrail"


def plain_shell_command(*parts: str, project_root: Path | None = None) -> str:
    command = [preferred_cli_executable(project_root=project_root), *parts]
    return " ".join(shlex.quote(part) for part in command)


def shell_command(root: Path | None, *parts: str, project_root: Path | None = None) -> str:
    command = [preferred_cli_executable(project_root=project_root), *parts]
    if root is not None and not is_default_workspace_artifact_root(root, project_root=project_root):
        command.extend(["--artifact-root", display_path(root)])
    return " ".join(shlex.quote(part) for part in command)


def preferred_proof_paths(root: Path, *, project_root: Path) -> dict[str, str]:
    payload = build_proof_request_record(
        run_id="PROOF_REQUEST_PREVIEW",
        task_class=DEFAULT_ALPHA_TASK_CLASS,
        task_identity="proof request preview",
        project_root=project_root,
        artifact_root=root,
    )
    return dict(payload["preferred_artifacts"])


def preferred_proof_artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "final_result": root / "final_result.json",
        "readback": root / "readback.txt",
        "scenario_proof": root / "scenario_proof.txt",
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure_run_state_extensions(state: dict) -> dict:
    state.setdefault("start_timestamp_utc", "")
    state.setdefault("closure_timestamp_utc", "")
    state.setdefault("check_count", 0)
    state.setdefault("last_known_final_result_hash", "")
    state.setdefault("doctor", {}).setdefault("override_gates", [])
    state.setdefault("proof_bundle", {}).setdefault("artifact_integrity_warning", False)
    state.setdefault("closure", {}).setdefault("warnings", [])
    return state


def update_last_known_final_result_hash(state_path: Path, final_result_path: Path | None) -> None:
    if final_result_path is None or not final_result_path.exists() or not state_path.exists():
        return
    state = ensure_run_state_extensions(load_json(state_path))
    state["last_known_final_result_hash"] = file_sha256(final_result_path)
    save_json(state_path, state)


def starter_hash_for_artifact(root: Path | None, artifact_id: str) -> str:
    if not root:
        return ""
    proof_request_file = alpha_file(root, "proof_request")
    if not proof_request_file.exists():
        return ""
    proof_request = load_bootstrap_json(proof_request_file)
    starter_hashes = proof_request.get("starter_hashes", {})
    if not isinstance(starter_hashes, dict):
        return ""
    value = starter_hashes.get(artifact_id, "")
    return value.strip() if isinstance(value, str) else ""


def untouched_preferred_proof_paths(root: Path | None) -> set[Path]:
    if not root:
        return set()
    untouched: set[Path] = set()
    for artifact_id, path in preferred_proof_artifact_paths(root).items():
        expected_hash = starter_hash_for_artifact(root, artifact_id)
        if expected_hash and path.exists() and path.is_file() and file_sha256(path) == expected_hash:
            untouched.add(path.resolve())
    return untouched


def unsupported_remote_target_reason(*, target_path: str, target_classification: str) -> str:
    classification = (target_classification or "").strip()
    path = (target_path or "").strip()
    if classification and classification not in SUPPORTED_ALPHA_TARGET_CLASSIFICATIONS:
        return "REMOTE_TARGET_UNSUPPORTED"
    if "://" in path:
        return "REMOTE_TARGET_UNSUPPORTED"
    if "@" in path and ":" in path and not path.startswith("/"):
        return "REMOTE_TARGET_UNSUPPORTED"
    return ""


def command_path_from_args(args: argparse.Namespace) -> list[str]:
    path = [args.cmd]
    if args.cmd == "checkpoint" and getattr(args, "checkpoint_cmd", None):
        path.append(args.checkpoint_cmd)
    if args.cmd == "telemetry" and getattr(args, "telemetry_cmd", None):
        path.append(args.telemetry_cmd)
    return path


def telemetry_flag_names(argv: list[str]) -> list[str]:
    return [token.split("=", 1)[0] for token in argv if token.startswith("--")]


def should_capture_alpha_telemetry(args: argparse.Namespace) -> bool:
    path = command_path_from_args(args)
    return path[0] in {"init", "start", "check", "cleanup", "refresh-acceptance", "generate-prompt", "next-step", "repair-step", "restore", "resume", "continue", "checkpoint", "session-export", "bug-packet"}


def maybe_capture_alpha_telemetry(
    args: argparse.Namespace,
    *,
    exit_code: int,
    explicit_error_class: str = "",
) -> None:
    if not should_capture_alpha_telemetry(args):
        return
    root = alpha_root_from_args(args)
    if not root or not telemetry_enabled(root):
        return
    event = build_command_event(
        root,
        command_path=command_path_from_args(args),
        flag_names=telemetry_flag_names(sys.argv[1:]),
        exit_code=exit_code,
        explicit_error_class=explicit_error_class,
    )
    append_command_event(root, event)


CHECK_PATH_SCOPES = {
    "state_file": ARTIFACT_SCOPE,
    "report_file": ARTIFACT_SCOPE,
    "doctor_file": ARTIFACT_SCOPE,
    "repair_packet_file": ARTIFACT_SCOPE,
    "repair_handoff_file": ARTIFACT_SCOPE,
    "repair_handoff_output": ARTIFACT_SCOPE,
    "repair_packet_output": ARTIFACT_SCOPE,
    "repair_receipt_file": ARTIFACT_SCOPE,
    "repair_receipt_output": ARTIFACT_SCOPE,
    "mode_selection_receipt": ARTIFACT_SCOPE,
    "consistency_recovery_file": ARTIFACT_SCOPE,
    "checkpoint_record_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
    "plan_output": ARTIFACT_SCOPE,
    "preparation_receipt_output": ARTIFACT_SCOPE,
    "refresh_output": ARTIFACT_SCOPE,
    "observability_output": ARTIFACT_SCOPE,
    "artifact_consistency_output": ARTIFACT_SCOPE,
    "worked_artifact_output": ARTIFACT_SCOPE,
    "run_artifact_output": ARTIFACT_SCOPE,
    "acceptance_criteria_file": ARTIFACT_SCOPE,
    "acceptance_validation_output": ARTIFACT_SCOPE,
    "project_profile_file": ARTIFACT_SCOPE,
    "target_path": PROJECT_SCOPE,
    "baseline_file": ARTIFACT_SCOPE,
    "synrail_file": ARTIFACT_SCOPE,
    "comparison_output": ARTIFACT_SCOPE,
    "artifact_path": DUAL_SCOPE,
    "helper_path": PROJECT_SCOPE,
    "prompt_identity_file": ARTIFACT_SCOPE,
    "target_identity_file": DUAL_SCOPE,
    "final_result": DUAL_SCOPE,
    "readback": DUAL_SCOPE,
    "scenario_proof": DUAL_SCOPE,
}

REPAIR_PACKET_PATH_SCOPES = {
    "state_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
    "previous_packet_file": ARTIFACT_SCOPE,
    "repair_handoff_file": ARTIFACT_SCOPE,
    "mode_selection_receipt": ARTIFACT_SCOPE,
    "preparation_receipt_file": ARTIFACT_SCOPE,
    "repair_receipt_file": ARTIFACT_SCOPE,
    "report_file": ARTIFACT_SCOPE,
    "target_path": PROJECT_SCOPE,
    "final_result": DUAL_SCOPE,
    "readback": DUAL_SCOPE,
    "scenario_proof": DUAL_SCOPE,
    "target_identity_file": DUAL_SCOPE,
    "artifact_path": DUAL_SCOPE,
    "helper_path": PROJECT_SCOPE,
    "coverage_profile_file": PROJECT_SCOPE,
    "coverage_corpus_file": PROJECT_SCOPE,
    "refresh_output": ARTIFACT_SCOPE,
}

DOCTOR_PATH_SCOPES = {
    "output": ARTIFACT_SCOPE,
    "state_file": ARTIFACT_SCOPE,
    "target_path": PROJECT_SCOPE,
    "artifact_path": DUAL_SCOPE,
    "helper_path": PROJECT_SCOPE,
    "prompt_identity_file": ARTIFACT_SCOPE,
    "target_identity_file": DUAL_SCOPE,
    "coverage_profile_file": PROJECT_SCOPE,
    "coverage_corpus_file": PROJECT_SCOPE,
}


def alpha_root_from_args(args: argparse.Namespace, *, ensure: bool = False) -> Path | None:
    if getattr(args, "ephemeral", False):
        project_root = default_project_root_from_args(args)
        root = ephemeral_artifact_root(project_root=project_root)
        setattr(args, "artifact_root", str(root))
        if ensure:
            root.mkdir(parents=True, exist_ok=True)
        return root
    value = getattr(args, "artifact_root", None)
    if not value:
        return None
    root = Path(value).expanduser().resolve()
    if ensure:
        root.mkdir(parents=True, exist_ok=True)
    return root


def project_root_from_profile(root: Path | None) -> Path | None:
    profile = load_project_profile(root)
    project_root_text = (profile or {}).get("project_root", "")
    if not project_root_text:
        return None
    return Path(project_root_text).expanduser().resolve()


def discover_git_project_root(start: Path) -> Path | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    root_text = completed.stdout.strip()
    if not root_text:
        return None
    return Path(root_text).expanduser().resolve()


def current_project_root() -> Path:
    return discover_git_project_root(Path.cwd().resolve()) or Path.cwd().resolve()


def default_project_root_from_args(args: argparse.Namespace) -> Path:
    value = getattr(args, "project_root", None)
    return Path(value).expanduser().resolve() if value else current_project_root()


def ensure_default_project_root_arg(args: argparse.Namespace) -> None:
    if not getattr(args, "project_root", None):
        setattr(args, "project_root", str(current_project_root()))


def validate_check_like_paths(args: argparse.Namespace, *, artifact_root: Path | None, project_root: Path | None) -> None:
    validate_namespace_paths(
        args,
        field_scopes=CHECK_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def validate_repair_packet_paths(args: argparse.Namespace, *, artifact_root: Path | None, project_root: Path | None) -> None:
    validate_namespace_paths(
        args,
        field_scopes=REPAIR_PACKET_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def validate_doctor_paths(args: argparse.Namespace, *, artifact_root: Path | None, project_root: Path | None) -> None:
    validate_namespace_paths(
        args,
        field_scopes=DOCTOR_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def alpha_file(root: Path, file_id: str) -> Path:
    return root / ALPHA_FILE_NAMES[file_id]


def maybe_existing_alpha_file(root: Path | None, file_id: str) -> str | None:
    if not root:
        return None
    candidate = alpha_file(root, file_id)
    if candidate.exists():
        return str(candidate)
    return None


def apply_alpha_profile_defaults(args: argparse.Namespace, *, root: Path | None) -> None:
    profile = load_project_profile(root)
    if not profile:
        return
    ignored_paths = untouched_preferred_proof_paths(root)
    profile_artifact_path = profile.get("artifact_path", "")
    for field in [
        "target_path",
        "target_classification",
        "baseline_identity",
        "execution_surface_identity",
        "artifact_path",
        "intended_run_class",
    ]:
        if not getattr(args, field, None):
            value = profile.get(field)
            if value:
                setattr(args, field, value)
    if not getattr(args, "final_result", None):
        discovered = discover_candidate_file_filtered(list(profile.get("final_result_candidates", [])), ignored_paths=ignored_paths)
        if discovered:
            args.final_result = discovered
            current_artifact_path = getattr(args, "artifact_path", None)
            if (
                not current_artifact_path
                or (
                    root is not None
                    and current_artifact_path == profile_artifact_path
                    and Path(current_artifact_path).resolve() == (root / "final_result.json").resolve()
                )
            ):
                args.artifact_path = discovered
                if root is not None and profile.get("artifact_path", "") != discovered:
                    profile["artifact_path"] = discovered
                    save_project_profile(root, profile)
    if not getattr(args, "readback", None):
        discovered = discover_candidate_file_filtered(list(profile.get("readback_candidates", [])), ignored_paths=ignored_paths)
        if discovered:
            args.readback = discovered
    if not getattr(args, "scenario_proof", None):
        discovered = discover_candidate_file_filtered(list(profile.get("scenario_proof_candidates", [])), ignored_paths=ignored_paths)
        if discovered:
            args.scenario_proof = discovered


def checkpoint_root(root: Path, checkpoint_id: str) -> Path:
    return root / "checkpoints" / checkpoint_id


def checkpoint_record_file(root: Path, checkpoint_id: str) -> Path:
    return checkpoint_root(root, checkpoint_id) / CHECKPOINT_RECORD_BASENAME


def checkpoint_verify_file(root: Path, checkpoint_id: str) -> Path:
    return checkpoint_root(root, checkpoint_id) / CHECKPOINT_VERIFY_BASENAME


def discover_checkpoint_record(root: Path, checkpoint_id: str | None) -> str | None:
    checkpoints_root = root / "checkpoints"
    if checkpoint_id:
        verified = checkpoint_verify_file(root, checkpoint_id)
        if verified.exists():
            return str(verified)
        created = checkpoint_record_file(root, checkpoint_id)
        if created.exists():
            return str(created)
        return None
    if not checkpoints_root.exists():
        return None
    working_verified = checkpoint_verify_file(root, "working")
    if working_verified.exists():
        return str(working_verified)
    working_created = checkpoint_record_file(root, "working")
    if working_created.exists():
        return str(working_created)
    verified_candidates = sorted(
        list(checkpoints_root.glob("*/checkpoint_verify.json")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if verified_candidates:
        return str(verified_candidates[0])
    created_candidates = sorted(
        list(checkpoints_root.glob("*/checkpoint_record.json")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not created_candidates:
        return None
    return str(created_candidates[0])


def apply_alpha_runtime_file_defaults(args: argparse.Namespace) -> None:
    root = alpha_root_from_args(args, ensure=True)
    if not root:
        return

    def existing_alpha_variant(*names: str) -> Path | None:
        for name in names:
            candidate = root / name
            if candidate.exists():
                return candidate
        return None

    if not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    for attr, file_id in [
        ("doctor_output", "doctor"),
        ("bundle_output", "bundle"),
        ("closure_output", "closure"),
        ("closure_certificate_output", "closure_certificate"),
        ("refresh_output", "refresh"),
        ("report_output", "report"),
        ("worked_artifact_output", "orchestration"),
        ("run_artifact_output", "run"),
        ("repair_packet_output", "repair_packet"),
        ("repair_handoff_output", "repair_handoff"),
        ("repair_receipt_output", "repair_receipt"),
        ("acceptance_validation_output", "acceptance_validation"),
        ("observability_output", "observability"),
        ("artifact_consistency_output", "artifact_consistency"),
        ("plan_output", "plan"),
        ("preparation_receipt_output", "preparation_receipt"),
    ]:
        if not getattr(args, attr, None):
            setattr(args, attr, str(alpha_file(root, file_id)))
    if not getattr(args, "repair_packet_file", None):
        existing = maybe_existing_alpha_file(root, "repair_packet")
        if existing:
            args.repair_packet_file = existing
    if not getattr(args, "acceptance_criteria_file", None):
        existing = maybe_existing_alpha_file(root, "acceptance_criteria")
        if existing:
            args.acceptance_criteria_file = existing
    if not getattr(args, "project_profile_file", None):
        profile = project_profile_file(root)
        if profile.exists():
            args.project_profile_file = str(profile)
    if not getattr(args, "prompt_identity_file", None):
        candidate = existing_alpha_variant("prompt_identity.txt")
        if candidate:
            args.prompt_identity_file = str(candidate)
    if not getattr(args, "target_identity_file", None):
        candidate = existing_alpha_variant("target_identity.txt")
        if candidate:
            args.target_identity_file = str(candidate)
    if not getattr(args, "prompt_identity", None):
        candidate = existing_alpha_variant("prompt_identity.txt")
        if candidate:
            args.prompt_identity = candidate.read_text().strip()
    if not getattr(args, "task_identity", None):
        candidate = existing_alpha_variant("task_identity.txt")
        if candidate:
            args.task_identity = candidate.read_text().strip()


def write_controlled_start_artifacts(
    root: Path,
    *,
    project_root: Path,
    run_id: str,
    task_class: str,
    task_identity: str,
    prompt_identity: str,
    profile: dict,
    started_via: str,
) -> None:
    starter_contents = build_proof_starter_contents(
        run_id=run_id,
        task_class=task_class,
        task_identity=task_identity,
        project_root=project_root,
    )
    proof_request = build_proof_request_record(
        run_id=run_id,
        task_class=task_class,
        task_identity=task_identity,
        project_root=project_root,
        artifact_root=root,
    )
    write_proof_starter_files(artifact_root=root, starter_contents=starter_contents)
    save_alpha_target_identity_file(root, target_identity=profile["execution_surface_identity"])
    bootstrap = build_bootstrap_record(
        run_id=run_id,
        task_class=task_class,
        started_via=started_via,
        project_root=project_root,
        artifact_root=root,
        task_identity=task_identity,
        prompt_identity=prompt_identity,
        target_path=profile["target_path"],
        target_classification=profile["target_classification"],
        target_identity=profile["execution_surface_identity"],
        baseline_identity=profile["baseline_identity"],
        execution_surface_identity=profile["execution_surface_identity"],
        intended_run_class=profile["intended_run_class"],
        intended_proof_path=dict(proof_request["preferred_artifacts"]),
    )
    save_bootstrap_json(alpha_file(root, "bootstrap"), bootstrap)
    save_bootstrap_json(alpha_file(root, "proof_request"), proof_request)


def resolve_start_identities(args: argparse.Namespace, *, root: Path) -> tuple[str, str]:
    task_identity = (getattr(args, "task_identity", "") or "").strip()
    if not task_identity:
        task_identity = (getattr(args, "task_request", "") or "").strip()
    prompt_identity = (getattr(args, "prompt_identity", "") or "").strip()
    if not task_identity:
        task_identity = load_text_if_exists(root / "task_identity.txt")
    if not prompt_identity:
        prompt_identity = load_text_if_exists(root / "prompt_identity.txt")
    if not prompt_identity:
        prompt_identity = task_identity
    return task_identity, prompt_identity


def existing_preferred_proof_artifacts(root: Path) -> list[str]:
    discovered: list[str] = []
    untouched = untouched_preferred_proof_paths(root)
    for artifact_id, path in preferred_proof_artifact_paths(root).items():
        if path.exists() and path.resolve() not in untouched:
            discovered.append(f"{artifact_id}:{display_path(path)}")
    return discovered


def clear_runtime_artifacts_for_start(root: Path) -> None:
    keep = {
        "state",
        "project_profile",
        "bootstrap",
        "bootstrap_validation",
        "proof_request",
        "acceptance_criteria",
    }
    for file_id, name in ALPHA_FILE_NAMES.items():
        if file_id in keep:
            continue
        (root / name).unlink(missing_ok=True)


def apply_bootstrap_defaults(args: argparse.Namespace, *, root: Path | None) -> dict | None:
    if not root:
        return None
    state_file = Path(getattr(args, "state_file", "") or alpha_file(root, "state"))
    profile = load_project_profile(root)
    if not state_file.exists() or not profile:
        return None
    bootstrap_path = alpha_file(root, "bootstrap")
    record = load_bootstrap_json(bootstrap_path) if bootstrap_path.exists() else None
    validation = validate_bootstrap_record(record, state=load_json(state_file), profile=profile, artifact_root=root)
    save_bootstrap_json(alpha_file(root, "bootstrap_validation"), validation)
    args.bootstrap_provenance_ok = validation["status"] == "VALID"
    args.bootstrap_provenance_reason = validation["reason"]
    if record and validation["status"] == "VALID":
        bootstrap_defaults = {
            "task_identity": record.get("task_identity", ""),
            "prompt_identity": record.get("prompt_identity", ""),
            "target_path": record.get("target_path", ""),
            "target_classification": record.get("target_classification", ""),
            "baseline_identity": record.get("baseline_identity", ""),
            "execution_surface_identity": record.get("execution_surface_identity", ""),
            "intended_run_class": record.get("intended_run_class", ""),
        }
        for field, value in bootstrap_defaults.items():
            if value and not getattr(args, field, None):
                setattr(args, field, value)
        if not getattr(args, "target_identity_file", None):
            candidate = root / "target_identity.txt"
            if candidate.exists():
                args.target_identity_file = str(candidate)
    return validation


def write_bootstrap_required_block(*, args: argparse.Namespace, root: Path, validation: dict) -> int:
    state_path = Path(args.state_file)
    state = ensure_run_state_extensions(load_json(state_path))
    task_identity = (getattr(args, "task_identity", "") or "").strip() or load_text_if_exists(root / "task_identity.txt")
    prompt_identity = (getattr(args, "prompt_identity", "") or "").strip() or load_text_if_exists(root / "prompt_identity.txt")
    state["integrity"]["status"] = "FAIL"
    state["integrity"]["exact_task_identity_ok"] = bool(task_identity and prompt_identity)
    state["integrity"]["bootstrap_provenance_ok"] = False
    state["integrity"]["bootstrap_provenance_reason"] = validation["reason"]
    state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
    state["closure"]["blocking_reason"] = "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"
    state["closure"]["next_allowed_transition"] = "CONTROLLED_START"
    state["closure"]["narrow_next_safe_step"] = "start the run in controlled mode before trusting any proof or acceptance"
    state["closure"]["missing_sections"] = []
    state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
    save_json(state_path, state)
    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "BLOCKED",
        "stopping_stage": "bootstrap",
        "reason": "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED",
        "doctor_verdict": "",
        "resume_applied": False,
        "resume_from_state": "",
        "repair_handoff_applied": False,
        "repair_handoff_from_state": "",
        "repair_handoff_required_inputs": [],
        "missing_continuation_inputs": [],
        "selection_applied": False,
        "selected_mode": "",
        "selected_with_preparation": False,
        "preparation_applied": False,
        "preparation_ready_for_closure": False,
        "bundle_status": state["proof_bundle"]["status"],
        "closure_status": state["closure"]["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "repair_termination_status": "",
        "repair_termination_reason": "",
        "repair_attempt_count": 0,
        "repair_max_attempts": 0,
        "repair_no_progress_window": 0,
        "repair_stalled_step_id": "",
        "blockers": ["CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"],
        "dominant_blocker": "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED",
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }
    save_json(Path(args.report_file), report)
    args._suppress_summary = True
    thin_code = cmd_thin_output(args)
    if thin_code == 0 and args.mode == "default":
        print_thin_output_summary(Path(args.output))
    return thin_code


def write_remote_unsupported_block(*, args: argparse.Namespace, root: Path) -> int:
    state_path = Path(args.state_file)
    state = ensure_run_state_extensions(load_json(state_path))
    state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
    state["closure"]["blocking_reason"] = "REMOTE_TARGET_UNSUPPORTED"
    state["closure"]["next_allowed_transition"] = "LOCAL_TRUSTED_WORKTREE_START"
    state["closure"]["narrow_next_safe_step"] = "rerun this alpha lane on a local trusted worktree; the remote or ops lane is not supported yet"
    state["closure"]["missing_sections"] = []
    state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
    save_json(state_path, state)
    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "BLOCKED",
        "stopping_stage": "target_support",
        "reason": "REMOTE_TARGET_UNSUPPORTED",
        "doctor_verdict": "",
        "resume_applied": False,
        "resume_from_state": "",
        "repair_handoff_applied": False,
        "repair_handoff_from_state": "",
        "repair_handoff_required_inputs": [],
        "missing_continuation_inputs": [],
        "selection_applied": False,
        "selected_mode": "",
        "selected_with_preparation": False,
        "preparation_applied": False,
        "preparation_ready_for_closure": False,
        "bundle_status": state["proof_bundle"]["status"],
        "closure_status": state["closure"]["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "repair_termination_status": "",
        "repair_termination_reason": "",
        "repair_attempt_count": 0,
        "repair_max_attempts": 0,
        "repair_no_progress_window": 0,
        "repair_stalled_step_id": "",
        "blockers": ["REMOTE_TARGET_UNSUPPORTED"],
        "dominant_blocker": "REMOTE_TARGET_UNSUPPORTED",
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }
    save_json(Path(args.report_file), report)
    args._suppress_summary = True
    thin_code = cmd_thin_output(args)
    if thin_code == 0 and args.mode == "default":
        print_thin_output_summary(Path(args.output))
    return thin_code


def sync_restored_checkpoint_artifacts(target_root: Path) -> list[str]:
    restored_root = target_root / "artifacts"
    if not restored_root.exists():
        return []
    synced: list[str] = []
    for artifact in sorted(restored_root.glob("*.json")):
        destination = target_root / artifact.name
        shutil.copy2(artifact, destination)
        synced.append(destination.name)
    return synced


def print_thin_output_summary(output_file: Path) -> None:
    if not output_file.exists():
        return
    payload = load_json(output_file)
    lines = [
        f"Status: {payload.get('status_label', payload.get('outcome_class', ''))}",
    ]
    action_now = payload.get("action_now", "")
    if action_now:
        lines.append(f"Do this now: {action_now}")
    final_answer_guard = payload.get("final_answer_guard", "")
    if final_answer_guard:
        lines.append(final_answer_guard)
    lines.extend([
        f"What happened: {payload.get('what_happened', payload.get('summary', ''))}",
        f"What it means: {payload.get('what_it_means', payload.get('diagnosis', ''))}",
        f"What to do next: {payload.get('what_to_do_next', payload.get('next_step', ''))}",
    ])
    change_impact_focus = payload.get("change_impact_focus", "")
    if change_impact_focus:
        lines.append(change_impact_focus[:1].upper() + change_impact_focus[1:])
    change_impact_scope = payload.get("change_impact_scope", "")
    if change_impact_scope:
        lines.append(change_impact_scope[:1].upper() + change_impact_scope[1:])
    focused_repair_summary = payload.get("focused_repair_summary", "")
    if focused_repair_summary:
        lines.append(f"Repair target: {focused_repair_summary}")
    thin_sections = list(payload.get("thin_section_guidance", []))
    if thin_sections:
        lines.append("Thin proof sections:")
        lines.extend([f"- {item}" for item in thin_sections])
    next_command = payload.get("next_command", "")
    restore_command = payload.get("restore_command", "")
    if next_command:
        lines.append(f"Next command: {next_command}")
    elif payload.get("suggested_command", "") and payload.get("suggested_command", "") != "no next command required":
        lines.append(f"Suggested path: {payload.get('suggested_command', '')}")
    if restore_command:
        lines.append(f"Restore option: {restore_command}")
    print("\n".join(line for line in lines if line))


def maybe_print_doctor_override_warning(doctor_file: Path | None, *, file = sys.stdout) -> None:
    if doctor_file is None or not doctor_file.exists():
        return
    record = load_json(doctor_file)
    override_summary = (record.get("override_summary", "") or "").strip()
    if not override_summary:
        return
    lines = [f"Warning: {override_summary}"]
    for item in record.get("override_warnings", []):
        if item:
            lines.append(f"- {item}")
    print("\n".join(lines), file=file)


def print_prompt_summary(output_file: Path) -> None:
    print_prompt_summary_compact(output_file, include_prompt=True)


def print_prompt_summary_compact(output_file: Path, *, include_prompt: bool = False) -> None:
    if not output_file.exists():
        return
    payload = load_json(output_file)
    stale_artifacts = list(payload.get("stale_artifact_ids", []))
    stale_subsurfaces = list(payload.get("stale_subsurface_ids", []))
    allowed_scope = list(payload.get("allowed_scope", []))
    allowed_scope_labels = list(payload.get("allowed_scope_labels", []))
    required_input_labels = list(payload.get("required_input_labels", []))
    forbidden_scope = list(payload.get("forbidden_scope", []))
    lines = [
        (
            f"Do this now: {payload.get('current_step_action_instruction', '')}"
            if payload.get("current_step_action_instruction", "")
            else "Do this now: fix the issue described above."
        ),
        f"What failed: {payload.get('failure_label', payload.get('failure_reason', ''))}",
        f"Repair task: {payload.get('current_step_label', payload.get('current_step_id', ''))}",
        f"Allowed scope: {', '.join(allowed_scope_labels) if allowed_scope_labels else (', '.join(allowed_scope) if allowed_scope else 'current repair step only')}",
        f"Do not touch: {', '.join(forbidden_scope) if forbidden_scope else 'unrelated files or acceptance logic'}",
    ]
    current_step_focus_summary = payload.get("current_step_focus_summary", "")
    if current_step_focus_summary:
        lines.append(f"Repair target: {current_step_focus_summary}")
    current_step_target_path = payload.get("current_step_target_path", "")
    if current_step_target_path:
        lines.append(f"Edit in place: {current_step_target_path}")
    elif payload.get("current_step_id", "") == "continue_forward_orchestration":
        lines.append("No proof-file edit: run synrail start for this task; do not add forward_orchestration_entrypoint to final_result.json.")
    acceptance = payload.get("acceptance_criteria", [])
    if acceptance:
        lines.append("Must pass:")
        lines.extend([f"- {item}" for item in acceptance])
    next_command = payload.get("next_command", "")
    if next_command:
        lines.append(f"After this repair, run: {next_command}")
    prompt = payload.get("prompt", "")
    if include_prompt and prompt:
        lines.append("")
        lines.append("Prompt for the next agent attempt:")
        lines.append(prompt)
    print("\n".join(line for line in lines if line))


def print_init_summary(*, root: Path, state_file: Path) -> None:
    profile = load_project_profile(root) or {}
    lines = [
        "Synrail setup is ready.",
        f"Artifact root: {display_path(root)}",
        f"Detected project type: {profile.get('project_type', 'generic')}",
        "This setup is not a controlled run yet.",
        "Quick status: " + shell_command(root, project_root=Path.cwd().resolve()),
        'Start a controlled run: ' + shell_command(root, "start", "Describe the bounded local change.", project_root=Path.cwd().resolve()),
    ]
    if profile.get("workspace_isolation_note", ""):
        lines.append("Workspace note: " + profile["workspace_isolation_note"])
    if profile.get("prefers_runtime_evidence", False):
        lines.append("Runtime helper: " + plain_shell_command("runtime-helper", project_root=Path.cwd().resolve()))
    print("\n".join(lines))


def print_start_summary(*, root: Path, state_file: Path, project_root: Path) -> None:
    state = load_json(state_file)
    proof_request = load_bootstrap_json(alpha_file(root, "proof_request"))
    preferred = proof_request.get("preferred_artifacts", {})
    profile = load_project_profile(root) or {}
    lines = [
        "Controlled run started.",
        "Do this now: make the bounded change, run local verification, then strengthen final_result.json first.",
        f"Artifact root: {display_path(root)}",
        f"Run id: {state.get('run_id', '')}",
        "Starter proof surface is ready for this run.",
        f"- final result: {preferred.get('final_result', display_path_from_base(root / 'final_result.json', base=project_root))}",
        "- fallback note: readback.txt and scenario_proof.txt stay hidden by default unless a later synrail check names one.",
        "Need a canonical final_result shape? run " + plain_shell_command("final-result-template", project_root=project_root),
        "Then run: " + shell_command(root, "check", project_root=project_root),
    ]
    if profile.get("workspace_isolation_note", ""):
        lines.append("Workspace note: " + profile["workspace_isolation_note"])
    if profile.get("prefers_runtime_evidence", False):
        lines.append("Runtime helper: " + plain_shell_command("runtime-helper", project_root=project_root))
    print("\n".join(lines))


def print_existing_run_summary(*, root: Path, state_file: Path, project_root: Path) -> None:
    state = load_json(state_file)
    proof_request = load_bootstrap_json(alpha_file(root, "proof_request")) if alpha_file(root, "proof_request").exists() else {}
    preferred = proof_request.get("preferred_artifacts", {})
    profile = load_project_profile(root) or {}
    lines = [
        "Synrail already has a controlled run in progress.",
        "What happened: this artifact root still points at the current untouched run, so Synrail did not start a second one.",
        f"Artifact root: {display_path(root)}",
        f"Run id: {state.get('run_id', '')}",
        "Continue this run by making the bounded change, running local verification, and strengthening final_result.json first.",
        f"- final result: {preferred.get('final_result', display_path_from_base(root / 'final_result.json', base=project_root))}",
        "- fallback note: readback.txt and scenario_proof.txt stay hidden by default unless a later synrail check names one.",
        "Need a canonical final_result shape? run " + plain_shell_command("final-result-template", project_root=project_root),
        "Next command: " + shell_command(root, "check", project_root=project_root),
    ]
    if profile.get("prefers_runtime_evidence", False):
        lines.append("Runtime helper: " + plain_shell_command("runtime-helper", project_root=project_root))
    print("\n".join(lines))


TERMINAL_RUN_STATES = {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}


def agent_wiring_label(project_root: Path) -> str:
    installed: list[str] = []
    if (project_root / "AGENTS.md").exists():
        installed.append("AGENTS.md")
    if (project_root / "GEMINI.md").exists():
        installed.append("GEMINI.md")
    if (project_root / "CLAUDE.md").exists():
        installed.append("CLAUDE.md")
    return " + ".join(installed) if installed else "not installed"


def format_run_label(state: dict | None) -> str:
    if not state:
        return "none"
    run_id = (state.get("run_id", "") or "").strip()
    run_state = (state.get("state", "") or "").strip()
    if run_id and run_state:
        return f"{run_id} — {run_state}"
    if run_id:
        return run_id
    if run_state:
        return run_state
    return "present but unreadable"


def humanize_dashboard_next_step(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return value
    mapping = {
        "attest target surface": "confirm that this repo/worktree is the intended place for the run",
        "confirm exact task identity": "confirm that the saved task request still matches this run",
        "run doctor and clear blocking failure classes": "run readiness checks and clear the blocking failure classes",
        "start the run in controlled mode before trusting any proof or acceptance": "start this task through Synrail before trusting any proof or acceptance",
        "restore exact prompt and task identity": "restore the exact task request and prompt identity",
        "complete bounded execution on the attested target surface": "finish the bounded change on the verified target surface",
        "capture the final result artifact and rebuild the proof bundle": "capture the final result and rebuild the proof bundle",
        "repair the final result artifact and rebuild the proof bundle": "repair final_result.json and rebuild the proof bundle",
        "complete the missing proof sections": "fill in the missing proof sections",
        "run reverification against the attested target surface": "rerun verification against the verified target surface",
    }
    return mapping.get(value, value)


def build_workspace_status(root: Path, *, project_root: Path, state_path: Path | None = None) -> dict:
    state_path = (state_path or alpha_file(root, "state")).resolve()
    state = load_json(state_path) if state_path.exists() else None
    profile = load_project_profile(root) or {}
    bootstrap_exists = alpha_file(root, "bootstrap").exists()
    run_state = ((state or {}).get("state", "") or "").strip()
    active_run = bool(state and bootstrap_exists and run_state not in TERMINAL_RUN_STATES)
    if active_run:
        workspace_state = "controlled run in progress"
    elif state and not bootstrap_exists:
        workspace_state = "setup ready; no controlled run yet"
    elif state:
        workspace_state = "controlled run history available"
    elif root.exists() or profile:
        workspace_state = "workspace initialized"
    else:
        workspace_state = "no Synrail artifacts yet"

    next_step = ""
    if active_run:
        next_step = (state or {}).get("next_safe_step", "") or shell_command(root, "check", project_root=project_root)
    elif state and not bootstrap_exists:
        next_step = shell_command(root, "start", "Describe the bounded local change.", project_root=project_root)
    elif state and run_state and run_state not in TERMINAL_RUN_STATES:
        next_step = (state or {}).get("next_safe_step", "") or shell_command(root, "check", project_root=project_root)
    else:
        next_step = shell_command(root, "start", "Describe the bounded local change.", project_root=project_root)
    human_next_step = humanize_dashboard_next_step(next_step)

    return {
        "type": "cli_control_kernel",
        "daemon": False,
        "workspace": display_path(project_root),
        "workspace_state": workspace_state,
        "artifact_root": display_path_from_base(root, base=project_root),
        "project_type": profile.get("project_type", detect_project_type(project_root)),
        "agent_wiring": agent_wiring_label(project_root),
        "workspace_warning": profile.get("workspace_isolation_note", ""),
        "active_run": format_run_label(state) if active_run else "none",
        "last_run": format_run_label(state),
        "next_step": human_next_step,
        "next_step_raw": next_step,
        "start_command": shell_command(root, "start", "Describe the bounded local change.", project_root=project_root),
        "help_command": plain_shell_command("--help", project_root=project_root),
    }


def print_workspace_dashboard(summary: dict) -> None:
    lines = [
        "Synrail: local governance dashboard",
        "Type: CLI control kernel (not a background daemon)",
        "",
        f"Workspace: {summary['workspace_state']}",
        f"Artifact root: {summary['artifact_root']}",
        f"Project type: {summary['project_type']}",
        f"Agent wiring: {summary['agent_wiring']}",
        f"Active run: {summary['active_run']}",
        f"Last run: {summary['last_run']}",
        f"Next step: {summary['next_step']}",
        f"Start new run: {summary['start_command']}",
        f"Full help: {summary['help_command']}",
    ]
    if summary.get("workspace_warning", ""):
        lines.insert(8, f"Workspace note: {summary['workspace_warning']}")
    print("\n".join(lines))


def final_result_template_payload(*, root: Path | None) -> dict:
    state: dict = {}
    if root and alpha_file(root, "state").exists():
        state = load_json(alpha_file(root, "state"))
    profile = load_project_profile(root) or {}
    task_identity = load_text_if_exists(root / "task_identity.txt") if root else ""
    prompt_identity = load_text_if_exists(root / "prompt_identity.txt") if root else ""
    baseline_identity = (profile.get("baseline_identity", "") or "").strip()
    execution_surface_identity = (profile.get("execution_surface_identity", "") or "").strip()
    changed_file = "path/to/changed_file.ext"
    notes = [
        "Replace the sample changed file path with the actual file paths for this run; use diff_provenance for a single-file change, or diff_provenance_records/per_file_diff_provenance with one changed_file-backed record per modified file for a multi-file change.",
        "Set status to PROVEN when this run made and verified a real bounded edit.",
        "Set status to ALREADY_SATISFIED only when the requested state was already present before any edit and the no-op attestation is truthful.",
        "Set change_disposition to already_satisfied only when the requested state was already present before any edit.",
        "Keep the scope tight: do not smuggle adjacent spacing, class, or layout tweaks into a task that only asked you to add or insert a small surface change.",
        "If the task only asked for a simple subtitle or label, keep the new line visually plain and avoid extra emphasis styling unless the task explicitly asked for it.",
        "Keep git_diff as a real patch with diff --git, ---, +++, and @@ markers when you can produce one.",
        "If git is not installed, do not invent git_diff; leave git_diff empty and use structured diff_provenance instead.",
        "If git_diff is unavailable, keep structured provenance explicit: use diff_provenance for a single-file change, or diff_provenance_records/per_file_diff_provenance with one direct-observation record per modified file for a multi-file change. Each record should include method, changed_file, one exact added_line or removed_line, one stable context_before or context_after anchor, and verification command plus result. If method is omitted but the direct-observation record is otherwise complete, Synrail can normalize it to direct_file_observation during a normal check.",
        "Keep diff_provenance.verification_command recheckable: use one repo-relative read-only command such as grep -n, cat, head, tail, git diff -- <path>, git show -- <path>, or git log -- <path>. Git recheck commands must use exactly git diff/show/log -- <path> with no git -c, --ext-diff, --textconv, or other options before --. Do not use pipes, &&, sed, awk, perl, subshells, or multi-command snippets.",
        "For tiny edits, do not leave the exact changed line and its stable neighbor only in readback or scenario_proof; copy those anchors into diff_provenance too.",
        "For an already_satisfied no-op, keep modified_files empty, keep git_diff empty, and use diff_provenance.changed_file plus observed_line, verification command/result, and provenance_note.",
        "In the normal synrail check path, run identity is already carried from the current controlled context; only fill artifact_identity manually when you are doing a standalone bundle check without that context.",
        "In the normal synrail check path, leave cleanup_status absent and let doctor-ready cleanup truth satisfy it automatically; only fill cleanup_status manually when standalone proof or a later synrail check explicitly asks for an explicit cleanup attestation.",
        "Use synrail explain-proof after a check to see exact semantic gaps and reasons.",
    ]
    if profile.get("workspace_isolation_note", ""):
        notes.append(profile["workspace_isolation_note"])
    return {
        "request_id": state.get("run_id", "RUN_ID_FOR_THIS_CONTROLLED_RUN"),
        "task_class": state.get("task_class", DEFAULT_ALPHA_TASK_CLASS),
        "status": "PROVEN",
        "change_disposition": "modified",
        "summary": "Describe the bounded change that was actually completed for this run.",
        "modified_files": [changed_file],
        "git_diff": (
            f"diff --git a/{changed_file} b/{changed_file}\n"
            f"--- a/{changed_file}\n"
            f"+++ b/{changed_file}\n"
            "@@ -1,1 +1,2 @@\n"
            "- old\n"
            "+ new\n"
            "+ describe the concrete patch on the named file"
        ),
        "diff_provenance": {
            "method": "direct_file_observation",
            "changed_file": changed_file,
            "added_line": "copy one exact added or changed line from the file",
            "observed_line": "if no edit was required because the requested state was already present, record that exact existing line here instead of inventing a patch",
            "context_before": "copy one stable line immediately before the changed or observed line",
            "context_after": "copy one stable line immediately after the changed or observed line",
            "verification_command": f"grep -n 'needle' {changed_file}",
            "verification_result": "12:stable neighbor line\n13:exact changed or observed line",
            "provenance_note": "Use this when git_diff is unavailable or the file is not tracked by git.",
        },
        "artifact_identity": {
            "baseline_identity": baseline_identity or "autodetected_generic_baseline",
            "execution_surface_identity": execution_surface_identity or "autodetected_generic_worktree",
            "prompt_identity": prompt_identity or task_identity or "TASK_PROMPT_IDENTITY_FOR_THIS_RUN",
            "task_identity": task_identity or "TASK_IDENTITY_FOR_THIS_RUN",
        },
        "_synrail": {
            "template_mode": True,
            "task_identity": task_identity,
            "notes": notes,
        },
    }


def runtime_helper_text(*, root: Path | None) -> str:
    profile = load_project_profile(root) or {}
    project_root = Path(profile.get("project_root", "") or Path.cwd()).resolve()
    project_type = profile.get("project_type", detect_project_type(project_root))
    prefers_runtime = bool(profile.get("prefers_runtime_evidence", False) or project_prefers_runtime_evidence(project_root))
    lines = [
        "Synrail runtime helper",
        f"Project root: {display_path(project_root)}",
    ]
    workspace_note = (profile.get("workspace_isolation_note", "") or "").strip()
    if workspace_note:
        lines.append(f"Workspace note: {workspace_note}")
    if not prefers_runtime:
        lines.extend(
            [
                "This repo does not look render-first.",
                "Use the smallest local verification you already trust for this task.",
                "If you still need UI or rendered-output evidence, prefer a local request or direct template render as manual runtime evidence before browser automation.",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "For UI, route, or rendered-output tasks, prefer a small local response/render check before browser automation.",
            "Treat the suggestions below as manual runtime evidence, not as verification_command candidates for bundle recheck.",
            "If you need bundle recheck evidence, keep verification_command to the direct file-observation allowlist instead of copying these runtime examples into final_result.json.",
            "Try one of these paths first:",
            "1. HTTP path (if the local app is already running):",
            "   curl -s http://localhost:8000/  # then inspect the local response for the expected fragment",
        ]
    )
    template_root = project_root / "templates"
    if template_root.exists() or any((child / "templates").exists() for child in project_root.iterdir() if child.is_dir()):
        lines.extend(
            [
                "2. Template/render path (no browser required):",
                "   python3 - <<'PY'",
                "   from jinja2 import Environment, FileSystemLoader",
                "   env = Environment(loader=FileSystemLoader('templates'))",
                "   html = env.get_template('index.html').render()",
                "   print(html)",
                "   PY",
            ]
        )
    if project_type == "python":
        lines.append("If you need the running app first, start the same local Python entrypoint you already use for this repo and then use curl.")
    lines.append("Reach for Playwright or browser automation only after one of the smaller local paths above is blocked.")
    return "\n".join(lines) + "\n"


def scenario_proof_template_text(*, root: Path | None) -> str:
    state: dict = {}
    if root and alpha_file(root, "state").exists():
        state = load_json(alpha_file(root, "state"))
    profile = load_project_profile(root) or {}
    task_identity = load_text_if_exists(root / "task_identity.txt") if root else ""
    title = task_identity or "Describe the bounded verification for this run."
    run_id = state.get("run_id", "RUN_ID_FOR_THIS_CONTROLLED_RUN")
    lines = [
        f"### SCENARIO PROOF: {title}",
        f"Run id: {run_id}",
        "Scenario: name only the exact runtime context needed for the blocker Synrail explicitly targeted",
        "Command: paste only the local command, request, or test that verified this named blocker",
        "Observed: paste only the concrete output, rendered fragment, or behavior needed to unblock it",
    ]
    lines.append("Fallback-only note: if final_result.json already carries explicit structured verification, leave this scenario proof untouched unless Synrail explicitly targets this file.")
    lines.append("When Synrail does explicitly target this file, keep it minimal and concrete; do not add extra narrative beyond the named blocker.")
    if profile.get("prefers_runtime_evidence", False):
        lines.append("Runtime hint: prefer a local request, rendered response, or observed runtime output over a source-only grep when possible; run `synrail runtime-helper` for a small curl or template-render path before browser automation")
    lines.extend(["Status: PASSED", ""])
    return "\n".join(lines)


def readback_template_text(*, root: Path | None) -> str:
    state: dict = {}
    if root and alpha_file(root, "state").exists():
        state = load_json(alpha_file(root, "state"))
    profile = load_project_profile(root) or {}
    task_identity = load_text_if_exists(root / "task_identity.txt") if root else ""
    title = task_identity or "Describe the bounded readback for this run."
    changed_surface = "path/to/changed_file.ext"
    final_result_path = root / "final_result.json" if root else None
    if final_result_path and final_result_path.exists():
        final_result = load_json(final_result_path)
        modified_files = list(final_result.get("modified_files", []))
        if modified_files:
            changed_surface = str(modified_files[0])
    lines = [
        f"### READBACK: {title}",
        f"Run id: {state.get('run_id', 'RUN_ID_FOR_THIS_CONTROLLED_RUN')}",
        f"Changed surface: {changed_surface}",
        "Observed: record only the concrete property needed for the blocker Synrail explicitly targeted",
    ]
    lines.append("Fallback-only note: if final_result.json already carries explicit structured verification, leave this readback untouched unless Synrail explicitly targets this file.")
    lines.append("When Synrail does explicitly target this file, keep it minimal and concrete; do not add extra narrative beyond the named blocker.")
    if profile.get("prefers_runtime_evidence", False):
        lines.append("Runtime hint: for UI, route, or rendered output changes, prefer a local response or rendered fragment over source-only grep when possible; run `synrail runtime-helper` for a small curl or template-render path before browser automation")
    lines.append("")
    return "\n".join(lines)


def maybe_materialize_requested_fallback_surface(*, root: Path | None, prompt_file: Path) -> str:
    if not root or not prompt_file.exists():
        return ""
    payload = load_json(prompt_file)
    subsurface_id = payload.get("current_step_subsurface_id", "")
    if subsurface_id == "readback_record":
        target = root / "readback.txt"
        if not target.exists():
            target.write_text(readback_template_text(root=root))
            return display_path(target)
        return ""
    if subsurface_id == "scenario_proof_record":
        target = root / "scenario_proof.txt"
        if not target.exists():
            target.write_text(scenario_proof_template_text(root=root))
            return display_path(target)
        return ""
    return ""


def build_proof_explanation(bundle: dict, *, root: Path | None) -> dict:
    structural_gaps = [
        {
            "section": entry.get("section", ""),
            "why": entry.get("why", ""),
            "recommended_action": entry.get("recommended_action", ""),
        }
        for entry in bundle.get("structural_decision_trace", [])
        if not entry.get("structurally_complete", False)
    ]
    semantic_gaps = [
        {
            "section": entry.get("section", ""),
            "why": entry.get("why", ""),
            "recommended_action": entry.get("recommended_action", ""),
        }
        for entry in bundle.get("semantic_decision_trace", [])
        if entry.get("evaluated", False) and not entry.get("semantically_sufficient", False)
    ]
    helper_commands: list[str] = []
    if any(section["section"] in {"final_result", "final_result_status", "modified_files", "diff_provenance", "verification_corroboration", "cleanup_status"} for section in structural_gaps + semantic_gaps):
        helper_commands.append("synrail final-result-template")
    if any(section["section"] == "readback" for section in structural_gaps + semantic_gaps):
        helper_commands.append("synrail readback-template")
    if any(section["section"] in {"scenario_proof", "verification_corroboration"} for section in structural_gaps + semantic_gaps):
        helper_commands.append("synrail scenario-proof-template")
    profile = load_project_profile(root) or {}
    if profile.get("prefers_runtime_evidence", False) and any(
        section["section"] in {"readback", "scenario_proof", "verification_corroboration"} for section in structural_gaps + semantic_gaps
    ):
        helper_commands.append("synrail runtime-helper")
    helper_commands.append("synrail check")
    final_result_target = display_path(root / "final_result.json") if root else "final_result.json"
    readback_target = display_path(root / "readback.txt") if root else "readback.txt"
    scenario_proof_target = display_path(root / "scenario_proof.txt") if root else "scenario_proof.txt"
    identity_sources = {
        "baseline_identity": (profile.get("baseline_identity", "") or "").strip(),
        "execution_surface_identity": (profile.get("execution_surface_identity", "") or "").strip(),
        "prompt_identity": load_text_if_exists(root / "prompt_identity.txt") if root else "",
        "task_identity": load_text_if_exists(root / "task_identity.txt") if root else "",
    }
    return {
        "bundle_status": bundle.get("status", ""),
        "structural_status": bundle.get("structural_status", ""),
        "semantic_status": bundle.get("semantic_status", ""),
        "semantic_next_safe_step": bundle.get("semantic_next_safe_step", ""),
        "missing_sections": list(bundle.get("missing_sections", [])),
        "semantically_insufficient_sections": list(bundle.get("semantically_insufficient_sections", [])),
        "structural_gaps": structural_gaps,
        "semantic_gaps": semantic_gaps,
        "helper_commands": helper_commands,
        "final_result_target": final_result_target,
        "readback_target": readback_target,
        "scenario_proof_target": scenario_proof_target,
        "identity_sources": identity_sources,
    }


def print_proof_explanation(explanation: dict, *, root: Path | None) -> None:
    lines = [
        "Synrail proof explanation",
        f"Bundle status: {explanation['bundle_status']}",
        f"Structural status: {explanation['structural_status']}",
        f"Semantic status: {explanation['semantic_status']}",
    ]
    if explanation.get("semantic_next_safe_step", ""):
        lines.append(f"Current semantic next step: {explanation['semantic_next_safe_step']}")
    structural_gaps = explanation.get("structural_gaps", [])
    semantic_gaps = explanation.get("semantic_gaps", [])
    if structural_gaps:
        lines.append("Structural gaps:")
        for gap in structural_gaps:
            lines.append(f"- {gap['section']}")
            if gap["why"]:
                lines.append(f"  Why: {gap['why']}")
            if gap["recommended_action"]:
                lines.append(f"  What to do: {gap['recommended_action']}")
            if gap["section"] == "diff_provenance":
                lines.append("  Concrete fix: keep git_diff patch-shaped with diff --git, ---, +++, @@, and the named changed files, or add structured provenance. Use diff_provenance for a single-file change, or diff_provenance_records/per_file_diff_provenance with one changed_file-backed record per modified file for a multi-file change.")
                lines.append("  No-op fix: if the requested state was already present before any edit, set change_disposition to already_satisfied, keep modified_files empty, keep git_diff empty, and use diff_provenance.changed_file plus observed_line, verification command/result, and provenance_note.")
            if gap["section"] == "artifact_identity":
                lines.append("  Concrete fix: ensure baseline_identity, execution_surface_identity, prompt_identity, and task_identity are all non-empty for this run.")
                lines.append("  Normal check path: Synrail usually carries these identity values from the current run context automatically; only fill them manually when a standalone bundle-check lacks that context.")
            if gap["section"] == "modified_files":
                lines.append("  No-op fix: if no file had to change because the requested state already existed, set change_disposition to already_satisfied and keep modified_files empty instead of inventing a changed file list.")
            if gap["section"] == "scope_alignment":
                lines.append("  Concrete fix: keep only the requested additive change. Remove adjacent spacing, class, or layout rewrites unless the task explicitly asked for them.")
            if gap["section"] == "presentation_alignment":
                lines.append("  Concrete fix: keep the newly added line visually plain. Remove extra emphasis styling like italic, opacity, uppercase, or tracking unless the task explicitly asked for it.")
            if gap["section"] == "verification_corroboration":
                lines.append("  Concrete fix: keep acceptance tied to explicit local verification. Either add structured diff_provenance with verification command and result in final_result.json, or record a labeled scenario proof with Command and Observed or Result lines instead of prose-only proof text.")
            if gap["section"] == "final_result_status":
                lines.append("  Concrete fix: use a trust-bearing closure claim in final_result.json. Set status to PROVEN for an evidenced modification run, or ALREADY_SATISFIED for a truthful no-op attestation.")
                lines.append("  Avoid generic execution labels like SUCCESS, COMPLETED, or DONE when the bundle is making a trust claim.")
            if gap["section"] == "cleanup_status":
                lines.append("  Normal check path: if doctor already reports an acceptable clean execution surface, Synrail can satisfy cleanup_status from that current readiness truth.")
                lines.append("  Concrete fix: if final_result.json still carries a stale starter cleanup placeholder, delete it and rerun synrail check before authoring a manual cleanup attestation.")
    if semantic_gaps:
        lines.append("Semantic gaps:")
        for gap in semantic_gaps:
            lines.append(f"- {gap['section']}")
            if gap["why"]:
                lines.append(f"  Why: {gap['why']}")
            if gap["recommended_action"]:
                lines.append(f"  What to do: {gap['recommended_action']}")
            if gap["section"] == "diff_provenance":
                lines.append("  Concrete fix: keep git_diff patch-shaped with diff --git, ---, +++, @@, and the named changed files, or add structured provenance. Use diff_provenance for a single-file change, or diff_provenance_records/per_file_diff_provenance with one changed_file-backed record per modified file for a multi-file change.")
                lines.append("  No-op fix: if the requested state was already present before any edit, set change_disposition to already_satisfied, keep modified_files empty, keep git_diff empty, and use diff_provenance.changed_file plus observed_line, verification command/result, and provenance_note.")
            if gap["section"] == "artifact_identity":
                lines.append("  Concrete fix: ensure baseline_identity, execution_surface_identity, prompt_identity, and task_identity are all non-empty for this run.")
                lines.append("  Normal check path: Synrail usually carries these identity values from the current run context automatically; only fill them manually when a standalone bundle-check lacks that context.")
            if gap["section"] == "modified_files":
                lines.append("  No-op fix: if no file had to change because the requested state already existed, set change_disposition to already_satisfied and keep modified_files empty instead of inventing a changed file list.")
            if gap["section"] == "scope_alignment":
                lines.append("  Concrete fix: keep only the requested additive change. Remove adjacent spacing, class, or layout rewrites unless the task explicitly asked for them.")
            if gap["section"] == "presentation_alignment":
                lines.append("  Concrete fix: keep the newly added line visually plain. Remove extra emphasis styling like italic, opacity, uppercase, or tracking unless the task explicitly asked for it.")
            if gap["section"] == "verification_corroboration":
                lines.append("  Concrete fix: keep acceptance tied to explicit local verification. Either add structured diff_provenance with verification command and result in final_result.json, or record a labeled scenario proof with Command and Observed or Result lines instead of prose-only proof text.")
            if gap["section"] == "final_result_status":
                lines.append("  Concrete fix: use a trust-bearing closure claim in final_result.json. Set status to PROVEN for an evidenced modification run, or ALREADY_SATISFIED for a truthful no-op attestation.")
                lines.append("  Avoid generic execution labels like SUCCESS, COMPLETED, or DONE when the bundle is making a trust claim.")
            if gap["section"] == "cleanup_status":
                lines.append("  Normal check path: if doctor already reports an acceptable clean execution surface, Synrail can satisfy cleanup_status from that current readiness truth.")
                lines.append("  Concrete fix: if final_result.json still carries a stale starter cleanup placeholder, delete it and rerun synrail check before authoring a manual cleanup attestation.")
    if not structural_gaps and not semantic_gaps:
        lines.append("Synrail did not find structural or semantic proof gaps in the current bundle.")
    if any(gap["section"] in {"final_result", "final_result_status", "modified_files", "diff_provenance", "verification_corroboration", "artifact_identity", "cleanup_status"} for gap in structural_gaps + semantic_gaps):
        lines.append(f"final_result target: {explanation['final_result_target']}")
    if any(gap["section"] == "artifact_identity" for gap in structural_gaps + semantic_gaps):
        identity_sources = explanation.get("identity_sources", {})
        lines.append("Current run identity hints:")
        for key in ["baseline_identity", "execution_surface_identity", "prompt_identity", "task_identity"]:
            value = identity_sources.get(key, "")
            if value:
                lines.append(f"- {key}: {value}")
    if any(gap["section"] == "readback" for gap in structural_gaps + semantic_gaps):
        lines.append(f"readback target: {explanation['readback_target']}")
    if any(gap["section"] in {"scenario_proof", "verification_corroboration"} for gap in structural_gaps + semantic_gaps):
        lines.append(f"scenario_proof target: {explanation['scenario_proof_target']}")
    if any(gap["section"] in {"readback", "scenario_proof", "verification_corroboration"} for gap in structural_gaps + semantic_gaps):
        profile = load_project_profile(root) or {}
        if profile.get("prefers_runtime_evidence", False):
            lines.append("Runtime nudge: prefer `synrail runtime-helper` and a small curl or template-render check before browser automation.")
    if explanation.get("helper_commands", []):
        lines.append("Helpful commands:")
        for command in explanation["helper_commands"]:
            lines.append(f"- {command}")
    print("\n".join(lines))


def print_acceptance_refresh_summary(*, root: Path) -> None:
    criteria = load_json(alpha_file(root, "acceptance_criteria"))
    lines = [
        "Acceptance rules refreshed.",
        "Revision: " + criteria.get("criteria_revision_id", ""),
    ]
    validation_file = alpha_file(root, "acceptance_validation")
    if validation_file.exists():
        validation = load_json(validation_file)
        lines.append("Validation: " + validation.get("status", ""))
        if validation.get("reason", "") and validation.get("reason", "") != "CRITERIA_VALID":
            lines.append("Why: " + validation.get("reason", ""))
    lines.append("Next command: " + shell_command(root, "check"))
    print("\n".join(lines))


def human_safe_point_class(value: str) -> str:
    mapping = {
        "VERIFIED_WORKING_STATE": "Verified working state",
        "VERIFIED_ACCEPTED_STATE": "Verified accepted state",
        "PRE_RUN_SNAPSHOT": "Pre-run workspace snapshot",
        "NOT_SAFE_POINT": "Not a verified restore point",
    }
    return mapping.get(value, value)


def human_restore_preview_status(value: str) -> str:
    mapping = {
        "READY": "Ready",
        "LIMITED": "Limited",
        "UNSUPPORTED": "Unsupported",
        "BLOCKED": "Blocked",
    }
    return mapping.get(value, value)


def human_workspace_restore_mode(value: str) -> str:
    mapping = {
        "git": "Git workspace snapshot",
        "file_copy": "File-copy workspace snapshot",
        "artifacts_only": "Checkpoint artifacts only",
        "none": "No supported workspace snapshot",
    }
    return mapping.get(value, value)


def human_supported_contour(value: str) -> str:
    mapping = {
        "pre_run_snapshot_git": "Pre-run snapshot on a git workspace",
        "pre_run_snapshot_file_copy": "Pre-run snapshot on a file-copy workspace",
        "pre_run_snapshot_unsupported": "Pre-run snapshot without supported workspace recovery",
        "artifact_only_verified_state": "Verified checkpoint artifact restore only",
    }
    return mapping.get(value, value)


def print_checkpoint_summary(record_file: Path, *, action: str, root: Path | None = None) -> None:
    if not record_file.exists():
        return
    payload = load_json(record_file)

    def human_checkpoint_step(text: str) -> str:
        mapping = {
            "checkpoint verified; restore is now allowed": "This restore point is ready. You can use synrail restore if you need it.",
            "inspect or continue from the restored checkpoint state": "Inspect the restored state or continue from it.",
        }
        return mapping.get(text, text)

    lines = []
    if action == "create":
        lines = [
            f"Fallback saved: {payload.get('checkpoint_id', '')}",
            f"Fallback type: {human_safe_point_class(payload.get('safe_point_class', ''))}",
            "What to do next: confirm this fallback only if you want to re-check it explicitly before restore.",
            "Next command: " + (
                shell_command(root, "confirm-restore")
                if root
                else payload.get("next_safe_step", "")
            ),
        ]
    elif action == "verify":
        lines = [
            f"Restore point confirmation: {payload.get('verification', {}).get('status', '')}",
            human_checkpoint_step(payload.get("next_safe_step", "")),
        ]
        if root and payload.get("verification", {}).get("status", "") == "PASSED":
            lines.append("Preview command: " + shell_command(root, "restore") + " --preview")
    elif action == "preview":
        lines = [
            f"Restore preview: {human_restore_preview_status(payload.get('restore_status', ''))}",
            f"Fallback type: {human_safe_point_class(payload.get('safe_point_class', ''))}",
            f"Supported contour: {human_supported_contour(payload.get('supported_contour', ''))}",
            f"Workspace restore mode: {human_workspace_restore_mode(payload.get('workspace_restore_mode', ''))}",
            "What it means: " + payload.get("summary", ""),
        ]
        if payload.get("workspace_restore_destructive", False):
            lines.append("Caution: this restore will modify project workspace files on the saved project root.")
        for note in payload.get("notes", []):
            lines.append("- " + note)
        if payload.get("restore_supported", False) and root:
            restore_command = shell_command(root, "restore")
            if payload.get("workspace_restore_destructive", False):
                restore_command += " --confirm"
            lines.append("Next command: " + restore_command)
        elif payload.get("next_safe_step", ""):
            lines.append("What to do next: " + payload.get("next_safe_step", ""))
    elif action == "restore":
        restore = payload.get("restore", {})
        rollback = payload.get("rollback", {})
        lines = [
            f"Restore result: {restore.get('status', '')}",
            human_checkpoint_step(payload.get("next_safe_step", "")),
        ]
        if rollback.get("status", "") == "ROLLED_BACK":
            lines.append("Restore rollback was applied because verification failed.")
    print("\n".join(line for line in lines if line))


def print_save_summary(record_file: Path, verify_file: Path, *, root: Path | None = None) -> None:
    if not verify_file.exists():
        print_checkpoint_summary(record_file, action="create", root=root)
        return
    record = load_json(record_file) if record_file.exists() else {}
    verify = load_json(verify_file)
    verification = verify.get("verification", {})
    lines = [
        f"Fallback ready: {verify.get('checkpoint_id', record.get('checkpoint_id', ''))}",
        f"Fallback type: {human_safe_point_class(record.get('safe_point_class', verify.get('safe_point_class', '')))}",
    ]
    if verification.get("status") == "PASSED":
        lines.extend(
            [
                "What it means: You now have a trusted fallback if this run goes non-green.",
                "What to do next: continue the current workflow. Preview the restore contract before using restore on a live workspace.",
            ]
        )
        if root:
            lines.append("Preview command: " + shell_command(root, "restore") + " --preview")
            contract = restore_contract(record)
            if contract.get("restore_supported", False):
                restore_command = shell_command(root, "restore")
                if contract.get("workspace_restore_destructive", False):
                    restore_command += " --confirm"
                lines.append("Restore command: " + restore_command)
    else:
        lines.extend(
            [
                "What happened: Synrail saved the restore point but could not fully confirm it yet.",
                "What to do next: inspect the save and rerun restore-point confirmation before depending on restore.",
            ]
        )
        if root:
            lines.append("Next command: " + shell_command(root, "confirm-restore"))
    print("\n".join(line for line in lines if line))


def public_shell_context() -> PublicShellContext:
    return PublicShellContext(
        alpha_root_from_args=alpha_root_from_args,
        default_workspace_artifact_root=default_workspace_artifact_root,
        alpha_file=alpha_file,
        load_json=load_json,
        display_path=display_path,
        ensure_run_state_extensions=ensure_run_state_extensions,
        build_workspace_status=build_workspace_status,
        print_workspace_dashboard=print_workspace_dashboard,
        build_proof_explanation=build_proof_explanation,
        print_proof_explanation=print_proof_explanation,
        final_result_template_payload=final_result_template_payload,
        scenario_proof_template_text=scenario_proof_template_text,
        readback_template_text=readback_template_text,
        runtime_helper_text=runtime_helper_text,
    )


def cmd_status(args: argparse.Namespace) -> int:
    return extracted_cmd_status(args, context=public_shell_context())


def cmd_explain_proof(args: argparse.Namespace) -> int:
    return extracted_cmd_explain_proof(args, context=public_shell_context())


def cmd_final_result_template(args: argparse.Namespace) -> int:
    return extracted_cmd_final_result_template(args, context=public_shell_context())


def cmd_scenario_proof_template(args: argparse.Namespace) -> int:
    return extracted_cmd_scenario_proof_template(args, context=public_shell_context())


def cmd_readback_template(args: argparse.Namespace) -> int:
    return extracted_cmd_readback_template(args, context=public_shell_context())


def cmd_runtime_helper(args: argparse.Namespace) -> int:
    return extracted_cmd_runtime_helper(args, context=public_shell_context())


def controlled_start_shell_context() -> ControlledStartShellContext:
    return ControlledStartShellContext(
        alpha_root_from_args=alpha_root_from_args,
        default_alpha_run_id=default_alpha_run_id,
        alpha_file=alpha_file,
        default_task_class=DEFAULT_ALPHA_TASK_CLASS,
        spine_script=SPINE,
        run_python=run_python,
        run_python_capture=run_python_capture,
        save_project_profile=save_project_profile,
        build_project_profile=build_project_profile,
        save_alpha_identity_files=save_alpha_identity_files,
        write_acceptance_criteria=write_acceptance_criteria,
        print_init_summary=print_init_summary,
        load_json=load_json,
        resolve_start_identities=resolve_start_identities,
        plain_shell_command=plain_shell_command,
        existing_preferred_proof_artifacts=existing_preferred_proof_artifacts,
        terminal_run_states=TERMINAL_RUN_STATES,
        shell_command=shell_command,
        print_existing_run_summary=print_existing_run_summary,
        clear_runtime_artifacts_for_start=clear_runtime_artifacts_for_start,
        write_controlled_start_artifacts=write_controlled_start_artifacts,
        apply_bootstrap_defaults=apply_bootstrap_defaults,
        save_bootstrap_json=save_bootstrap_json,
        update_last_known_final_result_hash=update_last_known_final_result_hash,
        preferred_proof_artifact_paths=preferred_proof_artifact_paths,
        print_start_summary=print_start_summary,
        write_acceptance_validation=write_acceptance_validation,
        print_acceptance_refresh_summary=print_acceptance_refresh_summary,
    )


def cmd_init(args: argparse.Namespace) -> int:
    ensure_default_project_root_arg(args)
    return extracted_cmd_init(args, context=controlled_start_shell_context())


def cmd_start(args: argparse.Namespace) -> int:
    ensure_default_project_root_arg(args)
    if getattr(args, "ephemeral", False):
        prune_stale_ephemeral_runs(max_age_seconds=ephemeral_max_age_seconds(args))
    return extracted_cmd_start(args, context=controlled_start_shell_context())


def cmd_cleanup(args: argparse.Namespace) -> int:
    ensure_default_project_root_arg(args)
    if getattr(args, "ephemeral", False) and getattr(args, "stale", False):
        removed = prune_stale_ephemeral_runs(max_age_seconds=ephemeral_max_age_seconds(args))
        print(f"Synrail stale ephemeral artifacts removed: {removed}")
        print(f"Cache root: {display_path(default_cache_root())}")
        return 0
    root = alpha_root_from_args(args)
    if root is None:
        root = default_workspace_artifact_root(project_root=Path(getattr(args, "project_root", "") or Path.cwd()).resolve())
    if not root.exists():
        print("Synrail artifacts already clean.")
        print(f"Artifact root: {display_path(root)}")
        return 0
    if not root.is_dir():
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_NOT_DIRECTORY", "artifact_root": str(root)}, ensure_ascii=True))
        return 2
    shutil.rmtree(root)
    print("Synrail artifacts removed.")
    print(f"Artifact root: {display_path(root)}")
    return 0


def cmd_refresh_acceptance(args: argparse.Namespace) -> int:
    return extracted_cmd_refresh_acceptance(args, context=controlled_start_shell_context())


def cmd_telemetry_enable(args: argparse.Namespace) -> int:
    return extracted_cmd_telemetry_enable(args, context=telemetry_context())


def cmd_telemetry_export(args: argparse.Namespace) -> int:
    return extracted_cmd_telemetry_export(args, context=telemetry_context())


def cmd_bundle_check(args: argparse.Namespace) -> int:
    return extracted_cmd_bundle_check(args, context=repair_bundle_closure_context())


def cmd_apply_bundle(args: argparse.Namespace) -> int:
    return extracted_cmd_apply_bundle(
        args,
        run_python=run_python,
        spine_script=SPINE,
    )


def cmd_closure(args: argparse.Namespace) -> int:
    return extracted_cmd_closure(args, context=repair_bundle_closure_context())


def cmd_apply_closure(args: argparse.Namespace) -> int:
    return extracted_cmd_apply_closure(args, context=apply_refresh_validate_context())


def cmd_refresh(args: argparse.Namespace) -> int:
    return extracted_cmd_refresh(args, context=apply_refresh_validate_context())


def cmd_validate(args: argparse.Namespace) -> int:
    return extracted_cmd_validate(args, context=apply_refresh_validate_context())


def cmd_doctor(args: argparse.Namespace) -> int:
    result = extracted_cmd_doctor(args, context=doctor_compare_substitute_context())
    if result == 0:
        maybe_print_doctor_override_warning(Path(args.output), file=sys.stderr)
    return result


def cmd_compare(args: argparse.Namespace) -> int:
    return extracted_cmd_compare(args, context=doctor_compare_substitute_context())


def cmd_substitute_pressure(args: argparse.Namespace) -> int:
    return extracted_cmd_substitute_pressure(args, context=doctor_compare_substitute_context())


def cmd_hybrid_status(args: argparse.Namespace) -> int:
    return extracted_cmd_hybrid_status(args, context=hybrid_mode_context())


def cmd_recommend_mode(args: argparse.Namespace) -> int:
    return extracted_cmd_recommend_mode(args, context=hybrid_mode_context())


def cmd_select_mode(args: argparse.Namespace) -> int:
    return extracted_cmd_select_mode(args, context=hybrid_mode_context())


def cmd_plan_proof(args: argparse.Namespace) -> int:
    return extracted_cmd_plan_proof(args, context=proof_preparation_cost_context())


def cmd_preparation_receipt(args: argparse.Namespace) -> int:
    return extracted_cmd_preparation_receipt(args, context=proof_preparation_cost_context())


def cmd_governed_cost(args: argparse.Namespace) -> int:
    return extracted_cmd_governed_cost(args, context=proof_preparation_cost_context())


def cmd_create_checkpoint(args: argparse.Namespace) -> int:
    return extracted_cmd_create_checkpoint(args, context=checkpoint_create_save_verify_context())


def cmd_save(args: argparse.Namespace) -> int:
    if args.mode == "dev":
        return cmd_create_checkpoint(args)
    return extracted_cmd_save(args, context=checkpoint_create_save_verify_context())


def cmd_restore_checkpoint(args: argparse.Namespace) -> int:
    return extracted_cmd_restore_checkpoint(args, context=restore_consistency_thin_context())


def cmd_restore(args: argparse.Namespace) -> int:
    return cmd_restore_checkpoint(args)


def cmd_artifact_consistency(args: argparse.Namespace) -> int:
    return extracted_cmd_artifact_consistency(args, context=restore_consistency_thin_context())


def cmd_thin_output(args: argparse.Namespace) -> int:
    return extracted_cmd_thin_output(args, context=restore_consistency_thin_context())


def cmd_generate_prompt(args: argparse.Namespace) -> int:
    return extracted_cmd_generate_prompt(args, context=prompt_reading_followup_context())


def cmd_thin_output_reading(args: argparse.Namespace) -> int:
    return extracted_cmd_thin_output_reading(args, context=prompt_reading_followup_context())


def cmd_prompt_followup(args: argparse.Namespace) -> int:
    return extracted_cmd_prompt_followup(args, context=prompt_reading_followup_context())


def cmd_prompt_retry_guard(args: argparse.Namespace) -> int:
    return extracted_cmd_prompt_retry_guard(args, context=retry_recovery_reading_context())


def cmd_consistency_recovery(args: argparse.Namespace) -> int:
    return extracted_cmd_consistency_recovery(args, context=retry_recovery_reading_context())


def cmd_checkpoint_operator_reading(args: argparse.Namespace) -> int:
    return extracted_cmd_checkpoint_operator_reading(args, context=retry_recovery_reading_context())


def cmd_consistency_recovery_prompt(args: argparse.Namespace) -> int:
    return extracted_cmd_consistency_recovery_prompt(args, context=recovery_prompt_observability_context())


def cmd_consistency_recovery_prompt_reading(args: argparse.Namespace) -> int:
    return extracted_cmd_consistency_recovery_prompt_reading(args, context=recovery_prompt_observability_context())


def cmd_observability(args: argparse.Namespace) -> int:
    return extracted_cmd_observability(args, context=recovery_prompt_observability_context())


def cmd_deploy(args: argparse.Namespace) -> int:
    return extracted_cmd_deploy(
        args,
        alpha_root_from_args=alpha_root_from_args,
        alpha_file=alpha_file,
        load_json=load_json,
        expected_target_identity_for_root=expected_target_identity_for_root,
        save_json=save_json,
        display_path=display_path,
    )


def cmd_deploy_check(args: argparse.Namespace) -> int:
    return extracted_cmd_deploy_check(
        args,
        alpha_root_from_args=alpha_root_from_args,
        alpha_file=alpha_file,
        load_json=load_json,
        expected_target_identity_for_root=expected_target_identity_for_root,
    )


def cmd_bug_packet(args: argparse.Namespace) -> int:
    return extracted_cmd_bug_packet(args, context=session_export_bug_packet_context())


def cmd_reproducibility(args: argparse.Namespace) -> int:
    return extracted_cmd_reproducibility(args, context=reproducibility_operator_brief_context())


def cmd_second_operator(args: argparse.Namespace) -> int:
    return extracted_cmd_second_operator(args, context=reproducibility_operator_brief_context())


def cmd_operator_brief(args: argparse.Namespace) -> int:
    return extracted_cmd_operator_brief(args, context=reproducibility_operator_brief_context())


def cmd_operator_brief_chain(args: argparse.Namespace) -> int:
    return extracted_cmd_operator_brief_chain(args, context=operator_brief_render_reading_context())


def cmd_operator_render(args: argparse.Namespace) -> int:
    return extracted_cmd_operator_render(args, context=operator_brief_render_reading_context())


def cmd_operator_render_adoption(args: argparse.Namespace) -> int:
    return extracted_cmd_operator_render_adoption(args, context=operator_render_adoption_pressure_context())


def cmd_operator_render_adoption_delta(args: argparse.Namespace) -> int:
    return extracted_cmd_operator_render_adoption_delta(args, context=operator_render_adoption_pressure_context())


def cmd_operator_reading(args: argparse.Namespace) -> int:
    return extracted_cmd_operator_reading(args, context=operator_brief_render_reading_context())


def cmd_externality_pressure(args: argparse.Namespace) -> int:
    return extracted_cmd_externality_pressure(args, context=operator_render_adoption_pressure_context())


def cmd_repair_handoff(args: argparse.Namespace) -> int:
    return extracted_cmd_repair_handoff(args, context=repair_bundle_closure_context())


def cmd_repair_packet(args: argparse.Namespace) -> int:
    return extracted_cmd_repair_packet(
        args,
        current_project_root=current_project_root,
        validate_root_within_project=validate_root_within_project,
        validate_repair_packet_paths=validate_repair_packet_paths,
        run_python=run_python,
        repair_packet_script=REPAIR_PACKET,
    )


def cmd_session_export(args: argparse.Namespace) -> int:
    return extracted_cmd_session_export(args, context=session_export_bug_packet_context())


def cmd_verify_checkpoint(args: argparse.Namespace) -> int:
    return extracted_cmd_verify_checkpoint(args, context=checkpoint_create_save_verify_context())


def cmd_orchestrate(args: argparse.Namespace) -> int:
    return extracted_cmd_orchestrate(
        args,
        alpha_root_from_args=alpha_root_from_args,
        current_project_root=current_project_root,
        validate_root_within_project=validate_root_within_project,
        apply_alpha_runtime_file_defaults=apply_alpha_runtime_file_defaults,
        project_root_from_profile=project_root_from_profile,
        validate_check_like_paths=validate_check_like_paths,
        run_python=run_python,
        run_python_capture=run_python_capture,
        spine_script=SPINE,
    )


def cmd_resume(args: argparse.Namespace) -> int:
    return extracted_cmd_resume(
        args,
        alpha_root_from_args=alpha_root_from_args,
        current_project_root=current_project_root,
        validate_root_within_project=validate_root_within_project,
        apply_alpha_runtime_file_defaults=apply_alpha_runtime_file_defaults,
        project_root_from_profile=project_root_from_profile,
        validate_check_like_paths=validate_check_like_paths,
        load_json=load_json,
        ensure_run_state_extensions=ensure_run_state_extensions,
        apply_bootstrap_defaults=apply_bootstrap_defaults,
        apply_resume_output_defaults=apply_resume_output_defaults,
        maybe_apply_repair_packet=maybe_apply_repair_packet,
        cmd_orchestrate=cmd_orchestrate,
        cmd_thin_output=cmd_thin_output,
        print_thin_output_summary=print_thin_output_summary,
        alpha_file=alpha_file,
    )


def cmd_check(args: argparse.Namespace) -> int:
    ensure_default_project_root_arg(args)
    root = alpha_root_from_args(args)
    project_root = default_project_root_from_args(args)
    if root:
        try:
            validate_root_within_project(
                "artifact_root" if getattr(args, "artifact_root", None) else "state_file",
                getattr(args, "artifact_root", None) or getattr(args, "state_file", ""),
                root=root,
                project_root=project_root,
                artifact_root=root,
            )
        except PathScopeValidationError as exc:
            print(json.dumps(exc.as_payload(), ensure_ascii=True))
            return 2
        root.mkdir(parents=True, exist_ok=True)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and getattr(args, "state_file", None):
        state_path = Path(args.state_file)
        if state_path.exists():
            state = ensure_run_state_extensions(load_json(state_path))
            state["check_count"] = int(state.get("check_count", 0)) + 1
            save_json(state_path, state)
    if root and not getattr(args, "report_file", None):
        args.report_file = str(alpha_file(root, "report"))
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "thin_output"))
    if root and not getattr(args, "doctor_file", None):
        existing = maybe_existing_alpha_file(root, "doctor")
        if existing:
            args.doctor_file = existing
    if root and not getattr(args, "repair_packet_file", None):
        existing = maybe_existing_alpha_file(root, "repair_packet")
        if existing:
            args.repair_packet_file = existing
    if root and not getattr(args, "consistency_recovery_file", None):
        existing = maybe_existing_alpha_file(root, "consistency_recovery")
        if existing:
            args.consistency_recovery_file = existing
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    apply_alpha_profile_defaults(args, root=root)
    apply_alpha_runtime_file_defaults(args)
    bootstrap_validation = apply_bootstrap_defaults(args, root=root) if root else None
    if root and project_profile_file(root).exists():
        args.acceptance_validation_output = str(alpha_file(root, "acceptance_validation"))
        args.project_profile_file = str(project_profile_file(root))
        existing_criteria = maybe_existing_alpha_file(root, "acceptance_criteria")
        if existing_criteria:
            args.acceptance_criteria_file = existing_criteria

    project_profile = load_project_profile(root) or {} if root else {}
    project_root_text = (project_profile.get("project_root", "") or "").strip()
    project_root = Path(project_root_text).resolve() if project_root_text else project_root
    validate_check_like_paths(args, artifact_root=root, project_root=project_root)

    if (
        root
        and bootstrap_validation
        and bootstrap_validation.get("status", "") != "VALID"
        and Path(getattr(args, "state_file", "")).exists()
    ):
        return write_bootstrap_required_block(args=args, root=root, validation=bootstrap_validation)

    if (
        root
        and unsupported_remote_target_reason(
            target_path=getattr(args, "target_path", ""),
            target_classification=getattr(args, "target_classification", ""),
        )
        and Path(getattr(args, "state_file", "")).exists()
    ):
        return write_remote_unsupported_block(args=args, root=root)

    runtime_requested = all(
        [
            getattr(args, "target_path", None),
            getattr(args, "baseline_identity", None),
            getattr(args, "execution_surface_identity", None),
            getattr(args, "final_result", None),
        ]
    )

    if runtime_requested:
        state = ensure_run_state_extensions(load_json(Path(args.state_file)))
        maybe_apply_observed_git_scope_defaults(args, state=state)
        orchestrate_args = argparse.Namespace(
            artifact_root=args.artifact_root,
            state_file=args.state_file,
            resume_from_state="",
            repair_handoff_file=getattr(args, "repair_handoff_file", None),
            repair_handoff_output=getattr(args, "repair_handoff_output", None),
            repair_packet_file=getattr(args, "repair_packet_file", None),
            repair_packet_output=getattr(args, "repair_packet_output", None),
            repair_receipt_file=getattr(args, "repair_receipt_file", None),
            repair_receipt_output=getattr(args, "repair_receipt_output", None),
            mode_selection_receipt=getattr(args, "mode_selection_receipt", None),
            doctor_run_id=args.doctor_run_id or state["run_id"],
            doctor_level=args.doctor_level,
            target_path=args.target_path,
            target_classification=args.target_classification,
            baseline_identity=args.baseline_identity,
            intended_run_class=args.intended_run_class,
            doctor_output=getattr(args, "doctor_output", None),
            final_result=args.final_result,
            task_class=state["task_class"],
            bundle_output=getattr(args, "bundle_output", None),
            closure_output=getattr(args, "closure_output", None),
            closure_certificate_output=getattr(args, "closure_certificate_output", None),
            report_output=args.report_file,
            execution_surface_identity=args.execution_surface_identity,
            prompt_identity=args.prompt_identity or "",
            task_identity=args.task_identity or "",
            bootstrap_provenance_ok=getattr(args, "bootstrap_provenance_ok", False),
            bootstrap_provenance_reason=getattr(args, "bootstrap_provenance_reason", ""),
            readback=getattr(args, "readback", None),
            scenario_proof=getattr(args, "scenario_proof", None),
            plan_output=getattr(args, "plan_output", None),
            preparation_receipt_output=getattr(args, "preparation_receipt_output", None),
            preparation_artifact_root=getattr(args, "preparation_artifact_root", None),
            refresh_output=getattr(args, "refresh_output", None),
            observability_output=getattr(args, "observability_output", None),
            artifact_consistency_output=getattr(args, "artifact_consistency_output", None),
            refresh_event_type=getattr(args, "refresh_event_type", None),
            refresh_doctor_status=getattr(args, "refresh_doctor_status", None),
            refresh_recovery_status=getattr(args, "refresh_recovery_status", None),
            refresh_reverification_complete=getattr(args, "refresh_reverification_complete", False),
            refresh_use_bundle=getattr(args, "refresh_use_bundle", False),
            refresh_use_closure=getattr(args, "refresh_use_closure", False),
            baseline_file=getattr(args, "baseline_file", None),
            synrail_file=getattr(args, "synrail_file", None),
            comparison_output=getattr(args, "comparison_output", None),
            worked_artifact_output=getattr(args, "worked_artifact_output", None),
            run_artifact_output=getattr(args, "run_artifact_output", None),
            clean_surface=getattr(args, "clean_surface", False),
            artifact_viable=getattr(args, "artifact_viable", False),
            helper_ok=getattr(args, "helper_ok", False),
            credentials_ok=getattr(args, "credentials_ok", False),
            prompt_identity_ok=getattr(args, "prompt_identity_ok", False),
            artifact_path=getattr(args, "artifact_path", None),
            helper_path=getattr(args, "helper_path", None),
            credential_env=list(getattr(args, "credential_env", [])),
            prompt_identity_file=getattr(args, "prompt_identity_file", None),
            target_identity_file=getattr(args, "target_identity_file", None),
            coverage_profile_file=getattr(args, "coverage_profile_file", None),
            coverage_corpus_file=getattr(args, "coverage_corpus_file", None),
            changed_file=list(getattr(args, "changed_file", [])),
            allowed_scope_path=list(getattr(args, "allowed_scope_path", [])),
            _capture_output=(args.mode == "default"),
        )
        orchestrate_code = cmd_orchestrate(orchestrate_args)
        if orchestrate_code != 0 and not Path(args.report_file).exists():
            return orchestrate_code
    elif not Path(args.report_file).exists():
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "CHECK_CONTEXT_INCOMPLETE", "detail": "report file is missing and runtime check inputs were not supplied"}, ensure_ascii=True))
        else:
            print("Synrail could not start the check yet.")
            if not getattr(args, "final_result", None):
                proof_request_file = alpha_file(root, "proof_request") if root else None
                if proof_request_file and proof_request_file.exists():
                    proof_request = load_bootstrap_json(proof_request_file)
                    preferred = proof_request.get("preferred_artifacts", {})
                    check_command = (
                        plain_shell_command("check", "--ephemeral", project_root=project_root)
                        if getattr(args, "ephemeral", False)
                        else plain_shell_command("check", project_root=project_root)
                    )
                    template_command = (
                        plain_shell_command("final-result-template", "--ephemeral", project_root=project_root)
                        if getattr(args, "ephemeral", False)
                        else plain_shell_command("final-result-template", project_root=project_root)
                    )
                    print("What is missing: Synrail is still waiting for explicit proof artifacts and local verification evidence for this controlled run.")
                    print(
                        "What to do next: make the bounded change, run local verification, then strengthen final_result.json first and rerun "
                        + check_command
                        + "."
                    )
                    if preferred.get("final_result", ""):
                        print(f"- final_result: {preferred['final_result']}")
                    print("- fallback note: readback.txt and scenario_proof.txt stay hidden by default unless a later synrail check names one.")
                    print("Need a canonical final_result shape? run " + template_command)
                    profile = load_project_profile(root) or {}
                    if profile.get("prefers_runtime_evidence", False):
                        print("Need a small UI/runtime verification path? run " + plain_shell_command("runtime-helper", project_root=project_root))
                else:
                    profile = load_project_profile(root)
                    candidates = (profile or {}).get("final_result_candidates", [])
                    print("What is missing: Synrail could not find the agent's final result yet.")
                    if candidates:
                        print("What to do next: pass --final-result or place one result file at one of these paths:")
                        for candidate in candidates[:4]:
                            print(f"- {candidate}")
            else:
                print("What to do next: provide the missing runtime context or rerun with --mode dev for full technical detail.")
        return 2

    report_path = Path(args.report_file)
    report_payload = load_json(report_path) if report_path.exists() else {}
    doctor_path = None
    if root:
        doctor_path = alpha_file(root, "doctor")
    elif getattr(args, "doctor_output", None):
        doctor_path = Path(args.doctor_output)
    if args.mode == "default":
        maybe_print_doctor_override_warning(doctor_path)
    if root and report_payload.get("result", "") == "OK":
        update_last_known_final_result_hash(
            Path(args.state_file),
            preferred_proof_artifact_paths(root)["final_result"],
        )

    args._suppress_summary = True
    thin_code = cmd_thin_output(args)
    if thin_code == 0 and args.mode == "default":
        print_thin_output_summary(Path(args.output))
        thin_payload = load_json(Path(args.output)) if Path(args.output).exists() else {}
        outcome_class = thin_payload.get("outcome_class", "")
        if thin_payload.get("next_command", "") == "synrail refresh-acceptance":
            return thin_code
        if Path(args.report_file).exists():
            report_payload = load_json(Path(args.report_file))
            if report_payload.get("reason", "") in {"CONTROLLED_BOOTSTRAP_NOT_CONFIRMED", "REMOTE_TARGET_UNSUPPORTED"}:
                return thin_code
        if outcome_class not in {"ACCEPTED", ""} and getattr(args, "repair_packet_file", None):
            prompt_output = str(alpha_file(root, "prompt")) if root else str(Path(args.output).with_name("prompt.json"))
            forwarded = [
                "--repair-packet-file", args.repair_packet_file,
                "--output", prompt_output,
            ]
            if getattr(args, "checkpoint_record_file", None):
                forwarded.extend(["--checkpoint-record-file", args.checkpoint_record_file])
            if getattr(args, "doctor_file", None):
                forwarded.extend(["--doctor-file", args.doctor_file])
            prompt_completed = run_python_capture(PROMPT_BRIDGE, forwarded)
            if prompt_completed.returncode == 0:
                created_fallback = maybe_materialize_requested_fallback_surface(root=root, prompt_file=Path(prompt_output))
                print("")
                if created_fallback:
                    print(f"Prepared fallback surface: {created_fallback}")
                print("What to fix:")
                print_prompt_summary_compact(Path(prompt_output), include_prompt=False)
    return thin_code


def normalize_repair_packet(packet: dict) -> dict:
    normalized = dict(packet)
    if normalized.get("schema_version") != "repair_packet_v0":
        raise ValueError("repair packet must use repair_packet_v0")
    handoff = dict(normalized.get("repair_handoff", {})) if isinstance(normalized.get("repair_handoff", {}), dict) else {}
    repair_policy = dict(normalized.get("repair_policy", {})) if isinstance(normalized.get("repair_policy", {}), dict) else {}
    continuation_core = dict(normalized.get("continuation_core", {})) if isinstance(normalized.get("continuation_core", {}), dict) else {}
    artifact_quality_summary = dict(normalized.get("artifact_quality_summary", {})) if isinstance(normalized.get("artifact_quality_summary", {}), dict) else {}
    resumability = dict(normalized.get("resumability", {})) if isinstance(normalized.get("resumability", {}), dict) else {}
    missing_inputs = list(normalized.get("missing_inputs", [])) if isinstance(normalized.get("missing_inputs", []), list) else []

    if not continuation_core:
        next_step_id = continuation_core.get("current_step_id", "") or repair_policy.get("next_step_id", "")
        continuation_core = {
            "contract_version": "continuation_core_v0",
            "entrypoint": normalized.get("continuation_entrypoint", "resume"),
            "ready_for_resume": bool(normalized.get("ready_for_resume", False)),
            "resumability_status": resumability.get("status", ""),
            "resumability_family": resumability.get("family", ""),
            "current_step_id": next_step_id,
            "current_step_subsurface_id": "",
            "current_step_target_path": "",
            "required_inputs": [
                item.get("input_id", "")
                for item in handoff.get("required_inputs", [])
                if isinstance(item, dict) and item.get("input_id", "")
            ],
            "missing_inputs": missing_inputs,
            "next_step_required_inputs": list(missing_inputs),
            "next_step_subsurface_ids": list(artifact_quality_summary.get("stale_subsurface_ids", [])),
            "operator_focus": normalized.get("next_safe_step", ""),
            "next_safe_step": normalized.get("next_safe_step", ""),
            "history_chain_length": 0,
            "selection_applied": bool((normalized.get("selection_context", {}) or {}).get("applied", False)),
            "selected_with_preparation": bool((normalized.get("selection_context", {}) or {}).get("selected_with_preparation", False)),
            "packet_supplies_resume_context": bool(normalized.get("resume_context", {})),
            "packet_supplies_repair_inputs": bool(normalized.get("repair_inputs", {})),
            "packet_supplies_output_defaults": bool(normalized.get("output_defaults", {})),
            "requires_sibling_discovery": False,
            "authoritative_entry_artifacts": ["repair_packet"],
            "source_of_truth_precedence": ["repair_packet", "repair_handoff", "state"],
            "packet_replay_ready": True,
        }
    normalized["continuation_core"] = continuation_core
    return normalized


def load_repair_packet(path: Path) -> dict:
    packet = load_json(path)
    return normalize_repair_packet(packet)


def apply_resume_input_overrides(args: argparse.Namespace, path: Path) -> None:
    payload = load_json(path)
    if payload.get("schema_version", "resume_input_overrides_v0") != "resume_input_overrides_v0":
        raise ValueError("resume input overrides must use resume_input_overrides_v0")
    scalar_fields = [
        "final_result",
        "readback",
        "scenario_proof",
        "prompt_identity",
        "task_identity",
        "target_identity_file",
        "artifact_path",
        "helper_path",
        "refresh_event_type",
        "refresh_recovery_status",
    ]
    for field in scalar_fields:
        value = payload.get(field)
        if value in {None, ""}:
            continue
        current = getattr(args, field, None)
        if current in {None, ""}:
            setattr(args, field, value)

    truthy_fields = [
        "refresh_reverification_complete",
        "refresh_use_bundle",
        "refresh_use_closure",
        "clean_surface",
        "artifact_viable",
        "helper_ok",
        "credentials_ok",
        "prompt_identity_ok",
    ]
    for field in truthy_fields:
        if payload.get(field) and not getattr(args, field, False):
            setattr(args, field, True)

    if payload.get("credential_env") and not getattr(args, "credential_env", []):
        args.credential_env = list(payload["credential_env"])


def discover_repair_packet_file(args: argparse.Namespace) -> Path | None:
    if getattr(args, "repair_packet_file", None):
        return Path(args.repair_packet_file)
    state_path = Path(args.state_file)
    state_stem = state_path.stem
    prefixed_name = f"{state_stem.removesuffix('_state')}_repair_packet.json" if state_stem.endswith("_state") and state_stem != "state" else ""
    previous_stage_candidate = None
    if state_stem.startswith("stage") and state_stem.endswith("_state"):
        stage_number = state_stem.removeprefix("stage").removesuffix("_state")
        if stage_number.isdigit() and int(stage_number) > 0:
            previous_stage_candidate = state_path.with_name(f"stage{int(stage_number) - 1}_repair_packet.json")
    candidates = [
        state_path.with_name(prefixed_name) if prefixed_name else None,
        previous_stage_candidate,
        state_path.with_name("repair_packet.json"),
    ]
    if getattr(args, "report_output", None):
        candidates.append(Path(args.report_output).with_name("repair_packet.json"))
    for candidate in candidates:
        if candidate is None:
            continue
        if candidate.exists():
            return candidate
    return None


def discover_resume_sibling_inputs(args: argparse.Namespace, state: dict) -> None:
    root = Path(args.state_file).parent
    state_stem = Path(args.state_file).stem
    state_prefix = f"{state_stem.removesuffix('_state')}_" if state_stem.endswith("_state") and state_stem != "state" else ""

    def existing(name: str) -> Path | None:
        candidate = root / name
        return candidate if candidate.exists() else None

    def existing_variants(*names: str) -> Path | None:
        seen: set[str] = set()
        candidates: list[str] = []
        for name in names:
            if state_prefix:
                candidates.append(f"{state_prefix}{name}")
            candidates.append(name)
        for name in candidates:
            if name in seen:
                continue
            seen.add(name)
            candidate = existing(name)
            if candidate:
                return candidate
        return None

    if not getattr(args, "mode_selection_receipt", None):
        candidate = existing_variants("selection_receipt.json")
        if candidate:
            args.mode_selection_receipt = str(candidate)

    if not getattr(args, "repair_receipt_file", None):
        candidate = existing_variants("repair_receipt.json")
        if candidate:
            args.repair_receipt_file = str(candidate)

    if not getattr(args, "repair_handoff_file", None):
        candidate = existing_variants("repair_handoff.json")
        if candidate:
            args.repair_handoff_file = str(candidate)

    if not getattr(args, "final_result", None):
        candidate = existing_variants("fixed_final_result.json", "final_result.json")
        if candidate:
            args.final_result = str(candidate)

    if not getattr(args, "readback", None):
        candidate = existing_variants("later_readback.txt", "readback.txt")
        if candidate:
            args.readback = str(candidate)

    if not getattr(args, "scenario_proof", None):
        candidate = existing_variants("later_scenario_proof.txt", "scenario_proof.txt", "later_scenario.txt", "scenario.txt")
        if candidate:
            args.scenario_proof = str(candidate)

    if not getattr(args, "target_identity_file", None):
        for name in ["target_identity.txt", "target_identity.json"]:
            candidate = existing_variants(name)
            if candidate:
                args.target_identity_file = str(candidate)
                break

    if not getattr(args, "artifact_path", None) and getattr(args, "final_result", None):
        args.artifact_path = args.final_result

    if not getattr(args, "prompt_identity_file", None):
        candidate = existing_variants("prompt_identity.txt")
        if candidate:
            args.prompt_identity_file = str(candidate)

    if not getattr(args, "prompt_identity", None):
        candidate = existing_variants("prompt_identity.txt")
        if candidate:
            args.prompt_identity = candidate.read_text().strip()

    if not getattr(args, "task_identity", None):
        candidate = existing_variants("task_identity.txt")
        if candidate:
            args.task_identity = candidate.read_text().strip()

    resume_inputs_candidate = existing_variants("resume_inputs.json")
    if resume_inputs_candidate:
        apply_resume_input_overrides(args, resume_inputs_candidate)


def synthesize_repair_packet(args: argparse.Namespace, state: dict) -> Path:
    discover_resume_sibling_inputs(args, state)
    root = Path(args.state_file).parent
    state_stem = Path(args.state_file).stem
    state_prefix = f"{state_stem.removesuffix('_state')}_" if state_stem.endswith("_state") and state_stem != "state" else ""

    def sibling_variant(name: str) -> Path | None:
        for candidate_name in ([f"{state_prefix}{name}"] if state_prefix else []) + [name]:
            candidate = root / candidate_name
            if candidate.exists():
                return candidate
        return None

    packet_output = Path(args.repair_packet_output)
    selection_receipt = load_json(Path(args.mode_selection_receipt)) if getattr(args, "mode_selection_receipt", None) else None
    repair_receipt = load_json(Path(args.repair_receipt_file)) if getattr(args, "repair_receipt_file", None) else None

    preparation_receipt = None
    preparation_candidate = sibling_variant("preparation_receipt.json")
    if preparation_candidate:
        preparation_receipt = load_json(preparation_candidate)

    report = None
    report_candidate = sibling_variant("report.json")
    if report_candidate:
        report = load_json(report_candidate)

    packet = build_packet_from_runtime_truth(
        state=state,
        artifact_root=root,
        doctor_run_id=args.doctor_run_id,
        doctor_level=args.doctor_level,
        target_path=args.target_path,
        target_classification=args.target_classification,
        baseline_identity=args.baseline_identity,
        intended_run_class=args.intended_run_class,
        execution_surface_identity=args.execution_surface_identity,
        final_result=args.final_result or "",
        prompt_identity=args.prompt_identity or "",
        task_identity=args.task_identity or "",
        prompt_identity_ok=getattr(args, "prompt_identity_ok", False),
        readback=args.readback or "",
        scenario_proof=args.scenario_proof or "",
        target_identity_file=args.target_identity_file or "",
        clean_surface=getattr(args, "clean_surface", False),
        artifact_viable=getattr(args, "artifact_viable", False),
        helper_ok=getattr(args, "helper_ok", False),
        credentials_ok=getattr(args, "credentials_ok", False),
        artifact_path=args.artifact_path or "",
        helper_path=args.helper_path or "",
        credential_env=list(getattr(args, "credential_env", [])),
        refresh_output=args.refresh_output or "",
        refresh_event_type=args.refresh_event_type or "",
        refresh_recovery_status=args.refresh_recovery_status or "NOT_REQUIRED",
        refresh_reverification_complete=getattr(args, "refresh_reverification_complete", False),
        refresh_use_bundle=getattr(args, "refresh_use_bundle", False),
        refresh_use_closure=getattr(args, "refresh_use_closure", False),
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        repair_receipt=repair_receipt,
        report=report,
    )
    packet_output.write_text(json.dumps(packet, indent=2, ensure_ascii=True) + "\n")
    args.repair_packet_file = str(packet_output)
    return packet_output


def apply_resume_output_defaults(args: argparse.Namespace, state: dict) -> None:
    state_path = Path(args.state_file)
    root = state_path.parent
    state_stem = state_path.stem
    state_prefix = f"{state_stem.removesuffix('_state')}_" if state_stem.endswith("_state") and state_stem != "state" else ""

    def runtime_name(name: str) -> str:
        return f"{state_prefix}{name}" if state_prefix else name

    defaults = {
        "doctor_output": str(root / runtime_name("doctor.json")),
        "bundle_output": str(root / runtime_name("bundle.json")),
        "closure_output": str(root / runtime_name("closure.json")),
        "closure_certificate_output": str(root / runtime_name("closure_certificate.json")),
        "refresh_output": str(root / runtime_name("refresh.json")),
        "observability_output": str(root / runtime_name("observability.json")),
        "report_output": str(root / runtime_name("report.json")),
        "worked_artifact_output": str(root / runtime_name("orchestration.json")),
        "run_artifact_output": str(root / runtime_name("run.json")),
        "repair_packet_output": str(root / runtime_name("repair_packet.json")),
        "plan_output": str(root / runtime_name("plan.json")),
        "preparation_receipt_output": str(root / runtime_name("preparation_receipt.json")),
    }
    for attr, value in defaults.items():
        if not getattr(args, attr, None):
            setattr(args, attr, value)

    project_profile: dict = {}
    for candidate_name in [runtime_name("project_profile.json"), "project_profile.json"]:
        candidate = root / candidate_name
        if candidate.exists():
            project_profile = load_json(candidate)
            break

    baseline_identity = state.get("target_surface", {}).get("identity", "") or state["run_id"]
    execution_surface_identity = state.get("target_surface", {}).get("identity", "") or baseline_identity
    target_path = (
        project_profile.get("target_path", "")
        or project_profile.get("project_root", "")
        or (str(root.parent) if root.name.startswith(".synrail") else str(root))
    )
    context_defaults = {
        "doctor_run_id": f"{state['run_id']}_RESUME",
        "doctor_level": "CORE_DOCTOR",
        "target_path": target_path,
        "target_classification": "resume_surface",
        "baseline_identity": baseline_identity,
        "intended_run_class": "core_probe",
        "task_class": state["task_class"],
        "execution_surface_identity": execution_surface_identity,
    }
    for attr, value in context_defaults.items():
        if not getattr(args, attr, None):
            setattr(args, attr, value)

    if getattr(args, "prompt_identity", None) is None:
        args.prompt_identity = ""
    if getattr(args, "task_identity", None) is None:
        args.task_identity = ""
    if getattr(args, "final_result", None) is None:
        args.final_result = ""


def ensure_repair_packet_synthesis_defaults(args: argparse.Namespace) -> None:
    string_defaults = {
        "final_result": "",
        "readback": "",
        "scenario_proof": "",
        "target_identity_file": "",
        "artifact_path": "",
        "helper_path": "",
        "prompt_identity": "",
        "task_identity": "",
        "refresh_output": "",
        "refresh_event_type": "",
        "refresh_recovery_status": "NOT_REQUIRED",
    }
    bool_defaults = {
        "prompt_identity_ok": False,
        "clean_surface": False,
        "artifact_viable": False,
        "helper_ok": False,
        "credentials_ok": False,
        "refresh_reverification_complete": False,
        "refresh_use_bundle": False,
        "refresh_use_closure": False,
    }
    list_defaults = {
        "credential_env": [],
    }
    for attr, value in string_defaults.items():
        if getattr(args, attr, None) is None:
            setattr(args, attr, value)
    for attr, value in bool_defaults.items():
        if getattr(args, attr, None) is None:
            setattr(args, attr, value)
    for attr, value in list_defaults.items():
        if getattr(args, attr, None) is None:
            setattr(args, attr, list(value))


def maybe_apply_repair_packet(args: argparse.Namespace, state: dict) -> list[str]:
    packet_path = discover_repair_packet_file(args)
    packet = None
    if packet_path:
        args.repair_packet_file = str(packet_path)
        try:
            packet = load_repair_packet(packet_path)
            if packet["run_id"] != state["run_id"] or packet["from_state"] != state["state"]:
                raise ValueError("repair packet does not match the requested state")
        except ValueError:
            packet = None

    if packet is None:
        discover_resume_sibling_inputs(args, state)
        packet_path = synthesize_repair_packet(args, state)
        packet = load_repair_packet(packet_path)
    else:
        core = dict(packet.get("continuation_core", {}))
        if core.get("requires_sibling_discovery", False):
            discover_resume_sibling_inputs(args, state)

    if packet.get("resumability", {}).get("status", "REPAIRABLE") != "REPAIRABLE":
        return []

    context = packet["resume_context"]
    continuation_plan = packet.get("continuation_plan", {})
    repair_inputs = packet["repair_inputs"]
    output_defaults = packet["output_defaults"]
    temp_files: list[str] = []

    for attr, value in [
        ("doctor_run_id", context["doctor_run_id"]),
        ("doctor_level", context["doctor_level"]),
        ("target_path", context["target_path"]),
        ("target_classification", context["target_classification"]),
        ("baseline_identity", context["baseline_identity"]),
        ("intended_run_class", context["intended_run_class"]),
        ("execution_surface_identity", context["execution_surface_identity"]),
        ("task_class", packet["task_class"]),
        ("final_result", repair_inputs["final_result"]),
        ("prompt_identity", repair_inputs["prompt_identity"]),
        ("task_identity", repair_inputs["task_identity"]),
        ("readback", repair_inputs["readback"]),
        ("scenario_proof", repair_inputs["scenario_proof"]),
        ("artifact_path", repair_inputs["artifact_path"]),
        ("helper_path", repair_inputs["helper_path"]),
        ("prompt_identity_file", ""),
        ("target_identity_file", repair_inputs["target_identity_file"]),
        ("doctor_output", output_defaults["doctor_output"]),
        ("bundle_output", output_defaults["bundle_output"]),
        ("closure_output", output_defaults["closure_output"]),
        ("closure_certificate_output", output_defaults.get("closure_certificate_output", str(Path(output_defaults["closure_output"]).with_name("closure_certificate.json")))),
        ("refresh_output", output_defaults["refresh_output"]),
        ("report_output", output_defaults["report_output"]),
        ("worked_artifact_output", output_defaults["worked_artifact_output"]),
        ("run_artifact_output", output_defaults["run_artifact_output"]),
        ("repair_handoff_output", output_defaults["repair_handoff_output"]),
        ("repair_packet_output", output_defaults["repair_packet_output"]),
        ("repair_receipt_output", output_defaults.get("repair_receipt_output", str(Path(output_defaults["repair_packet_output"]).with_name("repair_receipt.json")))),
        ("plan_output", output_defaults["plan_output"]),
        ("preparation_receipt_output", output_defaults["preparation_receipt_output"]),
    ]:
        current = getattr(args, attr, None)
        if current in {None, ""} and value is not None:
            setattr(args, attr, value)

    if not getattr(args, "preparation_artifact_root", None):
        args.preparation_artifact_root = output_defaults["artifact_root"]

    if not getattr(args, "refresh_recovery_status", None):
        args.refresh_recovery_status = repair_inputs["refresh_recovery_status"]
    if not getattr(args, "refresh_event_type", None) and continuation_plan.get("refresh_event_type"):
        args.refresh_event_type = continuation_plan["refresh_event_type"]
    if repair_inputs["refresh_reverification_complete"]:
        args.refresh_reverification_complete = True
    if continuation_plan.get("refresh_use_bundle"):
        args.refresh_use_bundle = True
    if continuation_plan.get("refresh_use_closure"):
        args.refresh_use_closure = True
    if repair_inputs["clean_surface"]:
        args.clean_surface = True
    if repair_inputs["artifact_viable"]:
        args.artifact_viable = True
    if repair_inputs["helper_ok"]:
        args.helper_ok = True
    if repair_inputs["credentials_ok"]:
        args.credentials_ok = True
    if repair_inputs["prompt_identity_ok"]:
        args.prompt_identity_ok = True
    if not args.credential_env:
        args.credential_env = list(repair_inputs["credential_env"])

    return temp_files


def add_orchestration_args(
    parser: argparse.ArgumentParser,
    *,
    include_resume_from_state: bool,
    relaxed_runtime: bool = False,
) -> None:
    parser.add_argument("--state-file")
    parser.add_argument("--artifact-root")
    if include_resume_from_state:
        parser.add_argument("--resume-from-state")
    parser.add_argument("--repair-handoff-file")
    parser.add_argument("--repair-handoff-output")
    parser.add_argument("--repair-packet-file")
    parser.add_argument("--repair-packet-output")
    parser.add_argument("--repair-receipt-file")
    parser.add_argument("--repair-receipt-output")
    parser.add_argument("--mode-selection-receipt")
    parser.add_argument("--doctor-run-id", required=not relaxed_runtime)
    parser.add_argument("--doctor-level", required=not relaxed_runtime, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    parser.add_argument("--target-path", required=not relaxed_runtime)
    parser.add_argument("--target-classification", required=not relaxed_runtime)
    parser.add_argument("--baseline-identity", required=not relaxed_runtime)
    parser.add_argument("--intended-run-class", required=not relaxed_runtime, choices=["core_probe", "support_run", "exact_retry"])
    parser.add_argument("--doctor-output", required=not relaxed_runtime)
    parser.add_argument("--final-result", required=not relaxed_runtime)
    parser.add_argument("--task-class", required=not relaxed_runtime)
    parser.add_argument("--bundle-output", required=not relaxed_runtime)
    parser.add_argument("--closure-output", required=not relaxed_runtime)
    parser.add_argument("--report-output", required=not relaxed_runtime)
    parser.add_argument("--execution-surface-identity", required=not relaxed_runtime)
    parser.add_argument("--prompt-identity", required=not relaxed_runtime, default="")
    parser.add_argument("--task-identity", required=not relaxed_runtime, default="")
    parser.add_argument("--readback")
    parser.add_argument("--scenario-proof")
    parser.add_argument("--plan-output")
    parser.add_argument("--preparation-receipt-output")
    parser.add_argument("--preparation-artifact-root")
    parser.add_argument("--refresh-output")
    parser.add_argument("--observability-output")
    parser.add_argument("--refresh-event-type")
    parser.add_argument("--refresh-doctor-status", choices=["PASS", "FAIL"])
    parser.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    parser.add_argument("--refresh-reverification-complete", action="store_true", default=None)
    parser.add_argument("--refresh-use-bundle", action="store_true", default=None)
    parser.add_argument("--refresh-use-closure", action="store_true", default=None)
    parser.add_argument("--baseline-file")
    parser.add_argument("--synrail-file")
    parser.add_argument("--comparison-output")
    parser.add_argument("--artifact-consistency-output")
    parser.add_argument("--worked-artifact-output")
    parser.add_argument("--run-artifact-output")
    parser.add_argument("--clean-surface", action="store_true", default=None)
    parser.add_argument("--artifact-viable", action="store_true", default=None)
    parser.add_argument("--helper-ok", action="store_true", default=None)
    parser.add_argument("--credentials-ok", action="store_true", default=None)
    parser.add_argument("--prompt-identity-ok", action="store_true", default=None)
    parser.add_argument("--artifact-path")
    parser.add_argument("--helper-path")
    parser.add_argument("--credential-env", action="append", default=[])
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--allowed-scope-path", action="append", default=[])
    parser.add_argument("--prompt-identity-file")
    parser.add_argument("--target-identity-file")
    parser.add_argument("--coverage-profile-file")
    parser.add_argument("--coverage-corpus-file")
    parser.add_argument("--bootstrap-provenance-ok", action="store_true")
    parser.add_argument("--bootstrap-provenance-reason", default="")
    parser.add_argument("--acceptance-criteria-file")
    parser.add_argument("--acceptance-validation-output")
    parser.add_argument("--project-profile-file")


class _SuppressingHelpFormatter(argparse.HelpFormatter):
    """Formatter that genuinely hides subcommands with help=SUPPRESS."""

    def _format_action(self, action: argparse.Action) -> str:
        if isinstance(action, argparse._SubParsersAction):
            parts: list[str] = []
            for choice_action in action._get_subactions():
                if choice_action.help != argparse.SUPPRESS:
                    parts.append(self._format_action(choice_action))
            return self._join_parts(parts)
        return super()._format_action(action)

    def _format_usage(self, usage, actions, groups, prefix):  # type: ignore[override]
        # Show only visible subcommands in the usage line
        for action in actions:
            if isinstance(action, argparse._SubParsersAction):
                visible_names = {
                    ca.dest for ca in action._choices_actions
                    if ca.help != argparse.SUPPRESS
                }
                if visible_names:
                    orig_choices = action.choices
                    action.choices = {k: v for k, v in orig_choices.items() if k in visible_names}
                    result = super()._format_usage(usage, actions, groups, prefix)
                    action.choices = orig_choices
                    return result
        return super()._format_usage(usage, actions, groups, prefix)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail", formatter_class=_SuppressingHelpFormatter)
    sub = parser.add_subparsers(dest="cmd")

    p_init = sub.add_parser("init", help=argparse.SUPPRESS)
    p_init.add_argument("--run-id")
    p_init.add_argument("--task-class", default=DEFAULT_ALPHA_TASK_CLASS)
    p_init.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_init.add_argument("--ephemeral", action="store_true", help="Store Synrail artifacts outside the repo in the user cache")
    p_init.add_argument("--ephemeral-max-age-hours", type=float, default=24.0, help="Stale ephemeral cleanup horizon")
    p_init.add_argument("--project-root")
    p_init.add_argument("--task-identity")
    p_init.add_argument("--prompt-identity")
    p_init.add_argument("--telemetry-opt-in", action="store_true")
    p_init.add_argument("--tester-id", default="alpha_tester")
    p_init.add_argument("--mode", default="default", choices=["default", "dev"])
    p_init.add_argument("--output")
    p_init.set_defaults(func=cmd_init)

    p_start = sub.add_parser("start", help="Begin a new controlled run")
    p_start.add_argument("--run-id")
    p_start.add_argument("--task-class", default=DEFAULT_ALPHA_TASK_CLASS)
    p_start.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_start.add_argument("--ephemeral", action="store_true", help="Store Synrail artifacts outside the repo in the user cache")
    p_start.add_argument("--ephemeral-max-age-hours", type=float, default=24.0, help="Prune older ephemeral cache runs before starting")
    p_start.add_argument("--project-root")
    p_start.add_argument("--task-identity")
    p_start.add_argument("--prompt-identity")
    p_start.add_argument("--telemetry-opt-in", action="store_true")
    p_start.add_argument("--tester-id", default="alpha_tester")
    p_start.add_argument("--mode", default="default", choices=["default", "dev"])
    p_start.add_argument("--output")
    p_start.add_argument("task_request", nargs="?")
    p_start.set_defaults(func=cmd_start)

    p_init_agent = sub.add_parser("init-agent", help="Write agent onboarding files for one supported agent")
    p_init_agent.add_argument("--agent", required=True, choices=["claude", "gemini", "codex", "cursor"])
    p_init_agent.add_argument("--project-root", default=".")
    p_init_agent.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_init_agent.add_argument("--force", action="store_true")
    p_init_agent.set_defaults(func=cmd_init_agent)

    p_init_ci = sub.add_parser("init-ci", help="Write a bounded GitHub Action adapter or workflow scaffold for Synrail check")
    p_init_ci.add_argument("--project-root", default=".")
    p_init_ci.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_init_ci.add_argument("--workflow", action="store_true")
    p_init_ci.add_argument("--force", action="store_true")
    p_init_ci.set_defaults(func=cmd_init_ci)

    p_preflight = sub.add_parser("preflight", aliases=["doctor-install"], help="Check local install and fallback readiness")
    p_preflight.add_argument("--project-root", default=".")
    p_preflight.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_preflight.add_argument("--json", action="store_true")
    p_preflight.set_defaults(func=cmd_preflight)

    p_install_agent_files = sub.add_parser("install-agent-files", help=argparse.SUPPRESS)
    p_install_agent_files.add_argument("--project-root", default=".")
    p_install_agent_files.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_install_agent_files.add_argument("--force", action="store_true")
    p_install_agent_files.set_defaults(func=cmd_install_agent_files)

    p_refresh_acceptance = sub.add_parser("refresh-acceptance", aliases=["acceptance-refresh"], help=argparse.SUPPRESS)
    p_refresh_acceptance.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_refresh_acceptance.add_argument("--mode", default="default", choices=["default", "dev"])
    p_refresh_acceptance.set_defaults(func=cmd_refresh_acceptance)

    p_check = sub.add_parser("check", help="Run the full verification pipeline")
    p_check.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_check.add_argument("--ephemeral", action="store_true", help="Use the repo-keyed user-cache artifact root for this checkout")
    p_check.add_argument("--project-root")
    p_check.add_argument("--state-file")
    p_check.add_argument("--report-file")
    p_check.add_argument("--doctor-file")
    p_check.add_argument("--repair-packet-file")
    p_check.add_argument("--repair-handoff-file")
    p_check.add_argument("--repair-handoff-output")
    p_check.add_argument("--repair-packet-output")
    p_check.add_argument("--repair-receipt-file")
    p_check.add_argument("--repair-receipt-output")
    p_check.add_argument("--mode-selection-receipt")
    p_check.add_argument("--checkpoint-id")
    p_check.add_argument("--checkpoint-record-file")
    p_check.add_argument("--consistency-recovery-file")
    p_check.add_argument("--mode", default="default", choices=["default", "dev"])
    p_check.add_argument("--output")
    p_check.add_argument("--doctor-run-id")
    p_check.add_argument("--doctor-level", default="CORE_DOCTOR", choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_check.add_argument("--target-path")
    p_check.add_argument("--target-classification", default="trusted_worktree")
    p_check.add_argument("--baseline-identity")
    p_check.add_argument("--intended-run-class", default="core_probe", choices=["core_probe", "support_run", "exact_retry"])
    p_check.add_argument("--final-result")
    p_check.add_argument("--execution-surface-identity")
    p_check.add_argument("--prompt-identity", default="")
    p_check.add_argument("--task-identity", default="")
    p_check.add_argument("--readback")
    p_check.add_argument("--scenario-proof")
    p_check.add_argument("--plan-output")
    p_check.add_argument("--preparation-receipt-output")
    p_check.add_argument("--preparation-artifact-root")
    p_check.add_argument("--refresh-output")
    p_check.add_argument("--observability-output")
    p_check.add_argument("--artifact-consistency-output")
    p_check.add_argument("--refresh-event-type")
    p_check.add_argument("--refresh-doctor-status", choices=["PASS", "FAIL"])
    p_check.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    p_check.add_argument("--refresh-reverification-complete", action="store_true", default=None)
    p_check.add_argument("--refresh-use-bundle", action="store_true", default=None)
    p_check.add_argument("--refresh-use-closure", action="store_true", default=None)
    p_check.add_argument("--baseline-file")
    p_check.add_argument("--synrail-file")
    p_check.add_argument("--comparison-output")
    p_check.add_argument("--worked-artifact-output")
    p_check.add_argument("--run-artifact-output")
    p_check.add_argument("--clean-surface", action="store_true", default=None)
    p_check.add_argument("--artifact-viable", action="store_true", default=None)
    p_check.add_argument("--helper-ok", action="store_true", default=None)
    p_check.add_argument("--credentials-ok", action="store_true", default=None)
    p_check.add_argument("--prompt-identity-ok", action="store_true", default=None)
    p_check.add_argument("--artifact-path")
    p_check.add_argument("--helper-path")
    p_check.add_argument("--credential-env", action="append", default=[])
    p_check.add_argument("--changed-file", action="append", default=[])
    p_check.add_argument("--allowed-scope-path", action="append", default=[])
    p_check.add_argument("--prompt-identity-file")
    p_check.add_argument("--target-identity-file")
    p_check.add_argument("--coverage-profile-file")
    p_check.add_argument("--coverage-corpus-file")
    p_check.set_defaults(func=cmd_check)

    p_cleanup = sub.add_parser("cleanup", help="Remove Synrail artifacts for this checkout")
    p_cleanup.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_cleanup.add_argument("--ephemeral", action="store_true", help="Remove the repo-keyed user-cache artifact root for this checkout")
    p_cleanup.add_argument("--stale", action="store_true", help="With --ephemeral, remove stale cache runs for all checkouts")
    p_cleanup.add_argument("--ephemeral-max-age-hours", type=float, default=24.0, help="Stale cleanup horizon")
    p_cleanup.add_argument("--project-root")
    p_cleanup.set_defaults(func=cmd_cleanup)

    p_status = sub.add_parser("status", aliases=["dashboard"], help="Show current run state")
    p_status.add_argument("state_file", nargs="?")
    p_status.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_status.add_argument("--ephemeral", action="store_true", help="Use the repo-keyed user-cache artifact root for this checkout")
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_explain_proof = sub.add_parser("explain-proof", aliases=["proof-explain"], help="Show what proof files are needed and why")
    p_explain_proof.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_explain_proof.add_argument("--ephemeral", action="store_true")
    p_explain_proof.add_argument("--bundle-file")
    p_explain_proof.add_argument("--json", action="store_true")
    p_explain_proof.set_defaults(func=cmd_explain_proof)

    p_final_result_template = sub.add_parser("final-result-template", help=argparse.SUPPRESS)
    p_final_result_template.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_final_result_template.add_argument("--ephemeral", action="store_true")
    p_final_result_template.add_argument("--output")
    p_final_result_template.set_defaults(func=cmd_final_result_template)

    p_readback_template = sub.add_parser("readback-template", help=argparse.SUPPRESS)
    p_readback_template.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_readback_template.add_argument("--ephemeral", action="store_true")
    p_readback_template.add_argument("--output")
    p_readback_template.set_defaults(func=cmd_readback_template)

    p_scenario_proof_template = sub.add_parser("scenario-proof-template", help=argparse.SUPPRESS)
    p_scenario_proof_template.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_scenario_proof_template.add_argument("--ephemeral", action="store_true")
    p_scenario_proof_template.add_argument("--output")
    p_scenario_proof_template.set_defaults(func=cmd_scenario_proof_template)

    p_runtime_helper = sub.add_parser("runtime-helper", help=argparse.SUPPRESS)
    p_runtime_helper.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_runtime_helper.add_argument("--ephemeral", action="store_true")
    p_runtime_helper.add_argument("--output")
    p_runtime_helper.set_defaults(func=cmd_runtime_helper)

    p_bundle = sub.add_parser("bundle-check", help=argparse.SUPPRESS)
    p_bundle.add_argument("--final-result", required=True)
    p_bundle.add_argument("--task-class", required=True)
    p_bundle.add_argument("--output", required=True)
    p_bundle.add_argument("--run-id")
    p_bundle.add_argument("--readback")
    p_bundle.add_argument("--scenario-proof")
    p_bundle.add_argument("--baseline-identity")
    p_bundle.add_argument("--execution-surface-identity")
    p_bundle.add_argument("--prompt-identity")
    p_bundle.add_argument("--task-identity")
    p_bundle.add_argument("--doctor-file")
    p_bundle.add_argument("--state-file")
    p_bundle.set_defaults(func=cmd_bundle_check)

    p_apply_bundle = sub.add_parser("apply-bundle", help=argparse.SUPPRESS)
    p_apply_bundle.add_argument("state_file")
    p_apply_bundle.add_argument("bundle_file")
    p_apply_bundle.set_defaults(func=cmd_apply_bundle)

    p_closure = sub.add_parser("closure", help=argparse.SUPPRESS)
    p_closure.add_argument("--state-file", required=True)
    p_closure.add_argument("--bundle-file", required=True)
    p_closure.add_argument("--output", required=True)
    p_closure.add_argument("--update-state", action="store_true")
    p_closure.set_defaults(func=cmd_closure)

    p_apply_closure = sub.add_parser("apply-closure", help=argparse.SUPPRESS)
    p_apply_closure.add_argument("state_file")
    p_apply_closure.add_argument("closure_file")
    p_apply_closure.set_defaults(func=cmd_apply_closure)

    p_refresh = sub.add_parser("refresh", help=argparse.SUPPRESS)
    p_refresh.add_argument("--state-file", required=True)
    p_refresh.add_argument("--event-type", required=True)
    p_refresh.add_argument("--output", required=True)
    p_refresh.add_argument("--doctor-status", choices=["PASS", "FAIL"])
    p_refresh.add_argument("--bundle-file")
    p_refresh.add_argument("--closure-file")
    p_refresh.add_argument("--recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    p_refresh.add_argument("--reverification-complete", action="store_true")
    p_refresh.add_argument("--update-state", action="store_true")
    p_refresh.set_defaults(func=cmd_refresh)

    p_validate = sub.add_parser("validate", help=argparse.SUPPRESS)
    p_validate.add_argument("--schema", required=True)
    p_validate.add_argument("--document", required=True)
    p_validate.set_defaults(func=cmd_validate)

    p_doctor = sub.add_parser("doctor", help=argparse.SUPPRESS)
    p_doctor.add_argument("--doctor-run-id", required=True)
    p_doctor.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_doctor.add_argument("--target-path", required=True)
    p_doctor.add_argument("--target-classification", required=True)
    p_doctor.add_argument("--baseline-identity", required=True)
    p_doctor.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    p_doctor.add_argument("--output", required=True)
    p_doctor.add_argument("--state-file")
    p_doctor.add_argument("--update-state", action="store_true")
    p_doctor.add_argument("--clean-surface", action="store_true", default=None)
    p_doctor.add_argument("--artifact-viable", action="store_true", default=None)
    p_doctor.add_argument("--helper-ok", action="store_true", default=None)
    p_doctor.add_argument("--credentials-ok", action="store_true", default=None)
    p_doctor.add_argument("--prompt-identity-ok", action="store_true", default=None)
    p_doctor.add_argument("--artifact-path")
    p_doctor.add_argument("--helper-path")
    p_doctor.add_argument("--credential-env", action="append", default=[])
    p_doctor.add_argument("--prompt-identity-file")
    p_doctor.add_argument("--expected-task-identity")
    p_doctor.add_argument("--target-identity-file")
    p_doctor.add_argument("--expected-target-identity")
    p_doctor.add_argument("--coverage-profile-file")
    p_doctor.add_argument("--coverage-corpus-file")
    p_doctor.add_argument("--changed-file", action="append", default=[])
    p_doctor.add_argument("--allowed-scope-path", action="append", default=[])
    p_doctor.set_defaults(func=cmd_doctor)

    p_compare = sub.add_parser("compare", help=argparse.SUPPRESS)
    p_compare.add_argument("--baseline-file", required=True)
    p_compare.add_argument("--synrail-file", required=True)
    p_compare.add_argument("--output", required=True)
    p_compare.set_defaults(func=cmd_compare)

    p_substitute_pressure = sub.add_parser("substitute-pressure", help=argparse.SUPPRESS)
    p_substitute_pressure.add_argument("--record", action="append", required=True)
    p_substitute_pressure.add_argument("--output", required=True)
    p_substitute_pressure.set_defaults(func=cmd_substitute_pressure)

    p_hybrid = sub.add_parser("hybrid-status", help=argparse.SUPPRESS)
    p_hybrid.add_argument("--cost-record", required=True)
    p_hybrid.add_argument("--hybrid-record", action="append", required=True)
    p_hybrid.add_argument("--output", required=True)
    p_hybrid.set_defaults(func=cmd_hybrid_status)

    p_mode = sub.add_parser("recommend-mode", help=argparse.SUPPRESS)
    p_mode.add_argument("--cost-record", required=True)
    p_mode.add_argument("--hybrid-status")
    p_mode.add_argument("--scenario-class", required=True)
    p_mode.add_argument("--task-class", required=True)
    p_mode.add_argument("--false-success-risk", required=True, choices=["LOW", "MEDIUM", "HIGH"])
    p_mode.add_argument("--recovery-cost", required=True, choices=["LOW", "MEDIUM", "HIGH"])
    p_mode.add_argument("--execution-surface-ambiguous", action="store_true")
    p_mode.add_argument("--artifact-truth-nontrivial", action="store_true")
    p_mode.add_argument("--explicit-hybrid-ambiguity")
    p_mode.add_argument("--governed-cost-delta")
    p_mode.add_argument("--output", required=True)
    p_mode.set_defaults(func=cmd_recommend_mode)

    p_select = sub.add_parser("select-mode", help=argparse.SUPPRESS)
    p_select.add_argument("--recommendation-file", required=True)
    p_select.add_argument("--selected-mode", choices=["FULL_GOVERNED_PATH", "LIGHTWEIGHT_BASELINE", "HYBRID_EXCEPTION"])
    p_select.add_argument("--selected-with-preparation", action="store_true")
    p_select.add_argument("--output", required=True)
    p_select.set_defaults(func=cmd_select_mode)

    p_plan = sub.add_parser("plan-proof", help=argparse.SUPPRESS)
    p_plan.add_argument("--run-id", required=True)
    p_plan.add_argument("--task-class", required=True)
    p_plan.add_argument("--artifact-root", required=True)
    p_plan.add_argument("--baseline-identity", required=True)
    p_plan.add_argument("--execution-surface-identity", required=True)
    p_plan.add_argument("--prompt-identity", required=True)
    p_plan.add_argument("--task-identity", required=True)
    p_plan.add_argument("--output", required=True)
    p_plan.set_defaults(func=cmd_plan_proof)

    p_prep = sub.add_parser("preparation-receipt", help=argparse.SUPPRESS)
    p_prep.add_argument("--plan-file", required=True)
    p_prep.add_argument("--bundle-file", required=True)
    p_prep.add_argument("--output", required=True)
    p_prep.set_defaults(func=cmd_preparation_receipt)

    p_governed_cost = sub.add_parser("governed-cost", help=argparse.SUPPRESS)
    p_governed_cost.add_argument("--unprepared-file", required=True)
    p_governed_cost.add_argument("--prepared-file", required=True)
    p_governed_cost.add_argument("--output", required=True)
    p_governed_cost.set_defaults(func=cmd_governed_cost)

    p_checkpoint_create = sub.add_parser("create-checkpoint", help=argparse.SUPPRESS)
    p_checkpoint_create.add_argument("--checkpoint-id")
    p_checkpoint_create.add_argument("--artifact-root")
    p_checkpoint_create.add_argument("--checkpoint-root")
    p_checkpoint_create.add_argument("--state-file")
    p_checkpoint_create.add_argument("--report-file")
    p_checkpoint_create.add_argument("--orchestration-file")
    p_checkpoint_create.add_argument("--bundle-file")
    p_checkpoint_create.add_argument("--closure-file")
    p_checkpoint_create.add_argument("--refresh-file")
    p_checkpoint_create.add_argument("--selection-file")
    p_checkpoint_create.add_argument("--preparation-file")
    p_checkpoint_create.add_argument("--repair-packet-file")
    p_checkpoint_create.add_argument("--repair-handoff-file")
    p_checkpoint_create.add_argument("--repair-receipt-file")
    p_checkpoint_create.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_create.add_argument("--output")
    p_checkpoint_create.set_defaults(func=cmd_create_checkpoint)

    p_save = sub.add_parser("save", help="Save a checkpoint of the current verified state")
    p_save.add_argument("--checkpoint-id", default="working")
    p_save.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_save.add_argument("--checkpoint-root")
    p_save.add_argument("--state-file")
    p_save.add_argument("--project-root")
    p_save.add_argument("--report-file")
    p_save.add_argument("--orchestration-file")
    p_save.add_argument("--bundle-file")
    p_save.add_argument("--closure-file")
    p_save.add_argument("--refresh-file")
    p_save.add_argument("--selection-file")
    p_save.add_argument("--preparation-file")
    p_save.add_argument("--repair-packet-file")
    p_save.add_argument("--repair-handoff-file")
    p_save.add_argument("--repair-receipt-file")
    p_save.add_argument("--mode", default="default", choices=["default", "dev"])
    p_save.add_argument("--output")
    p_save.set_defaults(func=cmd_save)

    p_checkpoint_verify = sub.add_parser("verify-checkpoint", aliases=["confirm-restore"], help=argparse.SUPPRESS)
    p_checkpoint_verify.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_checkpoint_verify.add_argument("--checkpoint-id")
    p_checkpoint_verify.add_argument("--checkpoint-record-file")
    p_checkpoint_verify.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_verify.add_argument("--output")
    p_checkpoint_verify.set_defaults(func=cmd_verify_checkpoint)

    p_checkpoint_restore = sub.add_parser("restore-checkpoint", help=argparse.SUPPRESS)
    p_checkpoint_restore.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_checkpoint_restore.add_argument("--checkpoint-id")
    p_checkpoint_restore.add_argument("--checkpoint-record-file")
    p_checkpoint_restore.add_argument("--target-root")
    p_checkpoint_restore.add_argument("--preview", action="store_true")
    p_checkpoint_restore.add_argument("--confirm", action="store_true")
    p_checkpoint_restore.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_restore.add_argument("--output")
    p_checkpoint_restore.set_defaults(func=cmd_restore_checkpoint)

    p_checkpoint = sub.add_parser("checkpoint", help=argparse.SUPPRESS)
    checkpoint_sub = p_checkpoint.add_subparsers(dest="checkpoint_cmd", required=True)

    p_checkpoint_nested_create = checkpoint_sub.add_parser("create")
    p_checkpoint_nested_create.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_checkpoint_nested_create.add_argument("--checkpoint-id", default="working")
    p_checkpoint_nested_create.add_argument("--checkpoint-root")
    p_checkpoint_nested_create.add_argument("--state-file")
    p_checkpoint_nested_create.add_argument("--report-file")
    p_checkpoint_nested_create.add_argument("--orchestration-file")
    p_checkpoint_nested_create.add_argument("--bundle-file")
    p_checkpoint_nested_create.add_argument("--closure-file")
    p_checkpoint_nested_create.add_argument("--refresh-file")
    p_checkpoint_nested_create.add_argument("--selection-file")
    p_checkpoint_nested_create.add_argument("--preparation-file")
    p_checkpoint_nested_create.add_argument("--repair-packet-file")
    p_checkpoint_nested_create.add_argument("--repair-handoff-file")
    p_checkpoint_nested_create.add_argument("--repair-receipt-file")
    p_checkpoint_nested_create.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_nested_create.add_argument("--output")
    p_checkpoint_nested_create.set_defaults(func=cmd_create_checkpoint)

    p_checkpoint_nested_verify = checkpoint_sub.add_parser("verify")
    p_checkpoint_nested_verify.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_checkpoint_nested_verify.add_argument("--checkpoint-id")
    p_checkpoint_nested_verify.add_argument("--checkpoint-record-file")
    p_checkpoint_nested_verify.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_nested_verify.add_argument("--output")
    p_checkpoint_nested_verify.set_defaults(func=cmd_verify_checkpoint)

    p_checkpoint_nested_restore = checkpoint_sub.add_parser("restore")
    p_checkpoint_nested_restore.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_checkpoint_nested_restore.add_argument("--checkpoint-id")
    p_checkpoint_nested_restore.add_argument("--checkpoint-record-file")
    p_checkpoint_nested_restore.add_argument("--target-root")
    p_checkpoint_nested_restore.add_argument("--preview", action="store_true")
    p_checkpoint_nested_restore.add_argument("--confirm", action="store_true")
    p_checkpoint_nested_restore.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_nested_restore.add_argument("--output")
    p_checkpoint_nested_restore.set_defaults(func=cmd_restore_checkpoint)

    p_restore = sub.add_parser("restore", help="Restore workspace from a saved checkpoint")
    p_restore.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_restore.add_argument("--checkpoint-id")
    p_restore.add_argument("--checkpoint-record-file")
    p_restore.add_argument("--target-root")
    p_restore.add_argument("--preview", action="store_true")
    p_restore.add_argument("--confirm", action="store_true")
    p_restore.add_argument("--mode", default="default", choices=["default", "dev"])
    p_restore.add_argument("--output")
    p_restore.set_defaults(func=cmd_restore)

    p_telemetry = sub.add_parser("telemetry", help=argparse.SUPPRESS)
    telemetry_sub = p_telemetry.add_subparsers(dest="telemetry_cmd", required=True)

    p_telemetry_enable = telemetry_sub.add_parser("enable")
    p_telemetry_enable.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_telemetry_enable.add_argument("--tester-id", default="alpha_tester")
    p_telemetry_enable.set_defaults(func=cmd_telemetry_enable)

    p_telemetry_export = telemetry_sub.add_parser("export")
    p_telemetry_export.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_telemetry_export.add_argument("--output")
    p_telemetry_export.add_argument("--issue-output")
    p_telemetry_export.set_defaults(func=cmd_telemetry_export)

    p_artifact_consistency = sub.add_parser("artifact-consistency", help=argparse.SUPPRESS)
    p_artifact_consistency.add_argument("--artifact-root")
    p_artifact_consistency.add_argument("--state-file")
    p_artifact_consistency.add_argument("--bundle-file")
    p_artifact_consistency.add_argument("--output")
    p_artifact_consistency.add_argument("--report-file")
    p_artifact_consistency.add_argument("--orchestration-file")
    p_artifact_consistency.add_argument("--run-file")
    p_artifact_consistency.add_argument("--closure-certificate-file")
    p_artifact_consistency.add_argument("--repair-packet-file")
    p_artifact_consistency.add_argument("--repair-handoff-file")
    p_artifact_consistency.add_argument("--repair-receipt-file")
    p_artifact_consistency.set_defaults(func=cmd_artifact_consistency)

    p_observability = sub.add_parser("observability", help=argparse.SUPPRESS)
    p_observability.add_argument("--state-file", required=True)
    p_observability.add_argument("--report-file", required=True)
    p_observability.add_argument("--output", required=True)
    p_observability.add_argument("--repair-packet-file")
    p_observability.add_argument("--repair-receipt-file")
    p_observability.add_argument("--refresh-file")
    p_observability.set_defaults(func=cmd_observability)

    p_session_export = sub.add_parser("session-export", help=argparse.SUPPRESS)
    p_session_export.add_argument("--artifact-root")
    p_session_export.add_argument("--state-file")
    p_session_export.add_argument("--report-file")
    p_session_export.add_argument("--output")
    p_session_export.add_argument("--repair-packet-file")
    p_session_export.add_argument("--repair-receipt-file")
    p_session_export.add_argument("--refresh-file")
    p_session_export.set_defaults(func=cmd_session_export)

    p_deploy = sub.add_parser("deploy", help=argparse.SUPPRESS)
    p_deploy.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_deploy.add_argument("--state-file")
    p_deploy.add_argument("--deploy-run-id")
    p_deploy.add_argument("--deploy-target")
    p_deploy.add_argument("--mode", default="default", choices=["default", "dev"])
    p_deploy.set_defaults(func=cmd_deploy)

    p_deploy_check = sub.add_parser("deploy-check", help=argparse.SUPPRESS)
    p_deploy_check.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_deploy_check.add_argument("--state-file")
    p_deploy_check.set_defaults(func=cmd_deploy_check)

    p_bug_packet = sub.add_parser("bug-packet", help=argparse.SUPPRESS)
    p_bug_packet.add_argument("--artifact-root")
    p_bug_packet.add_argument("--state-file")
    p_bug_packet.add_argument("--report-file")
    p_bug_packet.add_argument("--output")
    p_bug_packet.add_argument("--doctor-file")
    p_bug_packet.add_argument("--acceptance-validation-file")
    p_bug_packet.add_argument("--repair-packet-file")
    p_bug_packet.add_argument("--observability-file")
    p_bug_packet.add_argument("--thin-output-file")
    p_bug_packet.add_argument("--issue-output")
    p_bug_packet.set_defaults(func=cmd_bug_packet)

    p_thin_output = sub.add_parser("thin-output", help=argparse.SUPPRESS)
    p_thin_output.add_argument("--artifact-root")
    p_thin_output.add_argument("--state-file")
    p_thin_output.add_argument("--report-file")
    p_thin_output.add_argument("--mode", required=True, choices=["default", "dev"])
    p_thin_output.add_argument("--output")
    p_thin_output.add_argument("--repair-packet-file")
    p_thin_output.add_argument("--doctor-file")
    p_thin_output.add_argument("--refresh-file")
    p_thin_output.add_argument("--checkpoint-id")
    p_thin_output.add_argument("--checkpoint-record-file")
    p_thin_output.add_argument("--consistency-recovery-file")
    p_thin_output.set_defaults(func=cmd_thin_output)

    p_generate_prompt = sub.add_parser("generate-prompt", aliases=["next-step", "repair-step"], help=argparse.SUPPRESS)
    p_generate_prompt.add_argument("--artifact-root")
    p_generate_prompt.add_argument("--ephemeral", action="store_true")
    p_generate_prompt.add_argument("--repair-packet-file")
    p_generate_prompt.add_argument("--mode", default="default", choices=["default", "dev"])
    p_generate_prompt.add_argument("--output")
    p_generate_prompt.add_argument("--checkpoint-id")
    p_generate_prompt.add_argument("--checkpoint-record-file")
    p_generate_prompt.add_argument("--doctor-file")
    p_generate_prompt.set_defaults(func=cmd_generate_prompt)

    p_thin_output_reading = sub.add_parser("thin-output-reading", help=argparse.SUPPRESS)
    p_thin_output_reading.add_argument("--thin-output-file", required=True)
    p_thin_output_reading.add_argument("--prompt-bridge-file", required=True)
    p_thin_output_reading.add_argument("--report-file", required=True)
    p_thin_output_reading.add_argument("--repair-packet-file", required=True)
    p_thin_output_reading.add_argument("--output", required=True)
    p_thin_output_reading.set_defaults(func=cmd_thin_output_reading)

    p_prompt_followup = sub.add_parser("prompt-followup", help=argparse.SUPPRESS)
    p_prompt_followup.add_argument("--repair-packet-file", required=True)
    p_prompt_followup.add_argument("--prompt-bridge-file", required=True)
    p_prompt_followup.add_argument("--output", required=True)
    p_prompt_followup.add_argument("--thin-output-file")
    p_prompt_followup.set_defaults(func=cmd_prompt_followup)

    p_prompt_retry_guard = sub.add_parser("prompt-retry-guard", help=argparse.SUPPRESS)
    p_prompt_retry_guard.add_argument("--packet-a-file", required=True)
    p_prompt_retry_guard.add_argument("--prompt-a-file", required=True)
    p_prompt_retry_guard.add_argument("--packet-b-file", required=True)
    p_prompt_retry_guard.add_argument("--prompt-b-file", required=True)
    p_prompt_retry_guard.add_argument("--output", required=True)
    p_prompt_retry_guard.set_defaults(func=cmd_prompt_retry_guard)

    p_consistency_recovery = sub.add_parser("consistency-recovery", help=argparse.SUPPRESS)
    p_consistency_recovery.add_argument("--consistency-file", required=True)
    p_consistency_recovery.add_argument("--output", required=True)
    p_consistency_recovery.add_argument("--checkpoint-record-file")
    p_consistency_recovery.set_defaults(func=cmd_consistency_recovery)

    p_checkpoint_operator_reading = sub.add_parser("checkpoint-operator-reading", help=argparse.SUPPRESS)
    p_checkpoint_operator_reading.add_argument("--second-operator-file", required=True)
    p_checkpoint_operator_reading.add_argument("--thin-output-file", required=True)
    p_checkpoint_operator_reading.add_argument("--repair-packet-file", required=True)
    p_checkpoint_operator_reading.add_argument("--output", required=True)
    p_checkpoint_operator_reading.set_defaults(func=cmd_checkpoint_operator_reading)

    p_consistency_recovery_prompt = sub.add_parser("consistency-recovery-prompt", help=argparse.SUPPRESS)
    p_consistency_recovery_prompt.add_argument("--consistency-recovery-file", required=True)
    p_consistency_recovery_prompt.add_argument("--output", required=True)
    p_consistency_recovery_prompt.add_argument("--thin-output-file")
    p_consistency_recovery_prompt.set_defaults(func=cmd_consistency_recovery_prompt)

    p_consistency_recovery_prompt_reading = sub.add_parser("consistency-recovery-prompt-reading", help=argparse.SUPPRESS)
    p_consistency_recovery_prompt_reading.add_argument("--consistency-recovery-file", required=True)
    p_consistency_recovery_prompt_reading.add_argument("--prompt-file", required=True)
    p_consistency_recovery_prompt_reading.add_argument("--output", required=True)
    p_consistency_recovery_prompt_reading.set_defaults(func=cmd_consistency_recovery_prompt_reading)

    p_reproducibility = sub.add_parser("reproducibility", help=argparse.SUPPRESS)
    p_reproducibility.add_argument("--run-a", required=True)
    p_reproducibility.add_argument("--run-b", required=True)
    p_reproducibility.add_argument("--output", required=True)
    p_reproducibility.set_defaults(func=cmd_reproducibility)

    p_second_operator = sub.add_parser("second-operator", help=argparse.SUPPRESS)
    p_second_operator.add_argument("--state-file", required=True)
    p_second_operator.add_argument("--repair-packet-file", required=True)
    p_second_operator.add_argument("--run-file", required=True)
    p_second_operator.add_argument("--output", required=True)
    p_second_operator.set_defaults(func=cmd_second_operator)

    p_operator_brief = sub.add_parser("operator-brief", help=argparse.SUPPRESS)
    p_operator_brief.add_argument("--state-file", required=True)
    p_operator_brief.add_argument("--report-file", required=True)
    p_operator_brief.add_argument("--repair-packet-file", required=True)
    p_operator_brief.add_argument("--doctor-file")
    p_operator_brief.add_argument("--output", required=True)
    p_operator_brief.set_defaults(func=cmd_operator_brief)

    p_operator_brief_chain = sub.add_parser("operator-brief-chain", help=argparse.SUPPRESS)
    p_operator_brief_chain.add_argument("--brief", action="append", required=True)
    p_operator_brief_chain.add_argument("--output", required=True)
    p_operator_brief_chain.set_defaults(func=cmd_operator_brief_chain)

    p_operator_render = sub.add_parser("operator-render", help=argparse.SUPPRESS)
    p_operator_render.add_argument("--brief-file")
    p_operator_render.add_argument("--chain-file")
    p_operator_render.add_argument("--output", required=True)
    p_operator_render.set_defaults(func=cmd_operator_render)

    p_operator_render_adoption = sub.add_parser("operator-render-adoption", help=argparse.SUPPRESS)
    p_operator_render_adoption.add_argument("--source", required=True)
    p_operator_render_adoption.add_argument("--render", required=True)
    p_operator_render_adoption.add_argument("--label", required=True)
    p_operator_render_adoption.add_argument("--output", required=True)
    p_operator_render_adoption.set_defaults(func=cmd_operator_render_adoption)

    p_operator_render_adoption_delta = sub.add_parser("operator-render-adoption-delta", help=argparse.SUPPRESS)
    p_operator_render_adoption_delta.add_argument("--record", action="append", required=True)
    p_operator_render_adoption_delta.add_argument("--output", required=True)
    p_operator_render_adoption_delta.set_defaults(func=cmd_operator_render_adoption_delta)

    p_operator_reading = sub.add_parser("operator-reading", help=argparse.SUPPRESS)
    p_operator_reading.add_argument("--second-operator-file", required=True)
    p_operator_reading.add_argument("--brief-file", required=True)
    p_operator_reading.add_argument("--render-file", required=True)
    p_operator_reading.add_argument("--label", required=True)
    p_operator_reading.add_argument("--output", required=True)
    p_operator_reading.set_defaults(func=cmd_operator_reading)

    p_externality_pressure = sub.add_parser("externality-pressure", help=argparse.SUPPRESS)
    p_externality_pressure.add_argument("--reproducibility-file", required=True)
    p_externality_pressure.add_argument("--second-operator-file", required=True)
    p_externality_pressure.add_argument("--operator-reading-file", required=True)
    p_externality_pressure.add_argument("--label", required=True)
    p_externality_pressure.add_argument("--output", required=True)
    p_externality_pressure.set_defaults(func=cmd_externality_pressure)

    p_repair_handoff = sub.add_parser("repair-handoff", help=argparse.SUPPRESS)
    p_repair_handoff.add_argument("--state-file", required=True)
    p_repair_handoff.add_argument("--output", required=True)
    p_repair_handoff.set_defaults(func=cmd_repair_handoff)

    p_repair_packet = sub.add_parser("repair-packet", help=argparse.SUPPRESS)
    p_repair_packet.add_argument("--state-file", required=True)
    p_repair_packet.add_argument("--artifact-root", required=True)
    p_repair_packet.add_argument("--output", required=True)
    p_repair_packet.add_argument("--previous-packet-file")
    p_repair_packet.add_argument("--repair-handoff-file")
    p_repair_packet.add_argument("--mode-selection-receipt")
    p_repair_packet.add_argument("--preparation-receipt-file")
    p_repair_packet.add_argument("--repair-receipt-file")
    p_repair_packet.add_argument("--report-file")
    p_repair_packet.add_argument("--doctor-run-id")
    p_repair_packet.add_argument("--doctor-level", choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_repair_packet.add_argument("--target-path")
    p_repair_packet.add_argument("--target-classification")
    p_repair_packet.add_argument("--baseline-identity")
    p_repair_packet.add_argument("--intended-run-class", choices=["core_probe", "support_run", "exact_retry"])
    p_repair_packet.add_argument("--execution-surface-identity")
    p_repair_packet.add_argument("--final-result", default="")
    p_repair_packet.add_argument("--prompt-identity", default="")
    p_repair_packet.add_argument("--task-identity", default="")
    p_repair_packet.add_argument("--prompt-identity-ok", action="store_true", default=None)
    p_repair_packet.add_argument("--readback")
    p_repair_packet.add_argument("--scenario-proof")
    p_repair_packet.add_argument("--target-identity-file")
    p_repair_packet.add_argument("--clean-surface", action="store_true", default=None)
    p_repair_packet.add_argument("--artifact-viable", action="store_true", default=None)
    p_repair_packet.add_argument("--helper-ok", action="store_true", default=None)
    p_repair_packet.add_argument("--credentials-ok", action="store_true", default=None)
    p_repair_packet.add_argument("--artifact-path")
    p_repair_packet.add_argument("--helper-path")
    p_repair_packet.add_argument("--coverage-profile-file")
    p_repair_packet.add_argument("--coverage-corpus-file")
    p_repair_packet.add_argument("--credential-env", action="append", default=[])
    p_repair_packet.add_argument("--refresh-output")
    p_repair_packet.add_argument("--refresh-event-type")
    p_repair_packet.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"], default="NOT_REQUIRED")
    p_repair_packet.add_argument("--refresh-reverification-complete", action="store_true", default=None)
    p_repair_packet.add_argument("--refresh-use-bundle", action="store_true", default=None)
    p_repair_packet.add_argument("--refresh-use-closure", action="store_true", default=None)
    p_repair_packet.set_defaults(func=cmd_repair_packet)

    p_orchestrate = sub.add_parser("orchestrate", help=argparse.SUPPRESS)
    add_orchestration_args(p_orchestrate, include_resume_from_state=True)
    p_orchestrate.set_defaults(func=cmd_orchestrate)

    p_resume = sub.add_parser("resume", aliases=["continue", "retry"], help=argparse.SUPPRESS)
    add_orchestration_args(p_resume, include_resume_from_state=False, relaxed_runtime=True)
    p_resume.add_argument("--mode", default="default", choices=["default", "dev"])
    p_resume.set_defaults(func=cmd_resume)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    parsed_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(parsed_argv)
    if not getattr(args, "cmd", None):
        dashboard_args = argparse.Namespace(
            cmd="status",
            artifact_root=DEFAULT_ALPHA_ARTIFACT_ROOT,
            state_file=None,
            json=False,
        )
        return cmd_status(dashboard_args)
    caught: Exception | None = None
    exit_code = 1
    try:
        exit_code = int(args.func(args))
    except Exception as exc:
        caught = exc
    root = alpha_root_from_args(args) if getattr(args, "cmd", None) else None
    if (
        caught is None
        and getattr(args, "cmd", None) in {"init", "start"}
        and getattr(args, "telemetry_opt_in", False)
        and exit_code == 0
        and root is not None
    ):
        enable_telemetry(root, getattr(args, "tester_id", "alpha_tester"))
    try:
        maybe_capture_alpha_telemetry(
            args,
            exit_code=exit_code,
            explicit_error_class=caught.__class__.__name__ if caught else "",
        )
    except Exception:
        pass
    if isinstance(caught, PathScopeValidationError):
        print(json.dumps(caught.as_payload(), ensure_ascii=True))
        return 2
    if caught is not None:
        raise caught
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
