#!/usr/bin/env python3
"""Minimal terminal-first CLI facade for Synrail v0."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

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
    return subprocess.run(cmd, check=False).returncode


def run_python_capture(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    if __package__:
        cmd = [sys.executable, "-m", REFERENCE_RUNNER_MODULE, script.stem, *args]
    else:
        cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


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


def relative_artifact_root_for_project(*, project_root: Path, artifact_root: str) -> str:
    artifact_path = Path(artifact_root)
    if artifact_path.is_absolute():
        try:
            return str(artifact_path.relative_to(project_root))
        except ValueError:
            return str(artifact_path)
    return str(artifact_path)


def policy_command_examples(*, artifact_root: str) -> dict[str, str]:
    return policy_command_examples_for_binary(artifact_root=artifact_root, command="synrail")


def preferred_synrail_command() -> str:
    argv0 = Path(sys.argv[0]).expanduser()
    if argv0.name != "synrail":
        sibling = Path(sys.executable).expanduser().with_name("synrail")
        if sibling.exists():
            return shlex.quote(str(sibling.resolve()))
        return "synrail"
    # When install-agent-files is invoked via the real synrail entrypoint, pin
    # that exact binary in agent policy files. This avoids agent-specific PATH
    # drift where Claude/Gemini resolve a different synrail binary than the one
    # that authored the repo instructions.
    return shlex.quote(str(argv0.resolve()))


def policy_command_examples_for_binary(*, artifact_root: str, command: str) -> dict[str, str]:
    quoted_root = shlex.quote(artifact_root)
    if artifact_root == DEFAULT_ALPHA_ARTIFACT_ROOT:
        return {
            "status": command,
            "start": f'{command} start "Describe the bounded local change."',
            "check": f"{command} check",
            "repair": f"{command} repair-step",
        }
    return {
        "status": f"{command} status --artifact-root {quoted_root}",
        "start": f'{command} start --artifact-root {quoted_root} "Describe the bounded local change."',
        "check": f"{command} check --artifact-root {quoted_root}",
        "repair": f"{command} repair-step --artifact-root {quoted_root}",
    }


def policy_workspace_note_lines(*, workspace_isolation_note: str, prefer_runtime_helper: bool, command: str) -> list[str]:
    lines: list[str] = []
    if workspace_isolation_note:
        lines.append(f"- {workspace_isolation_note}")
    if prefer_runtime_helper:
        lines.append(
            f"- For UI or rendered-output tasks, prefer `{command} runtime-helper` and a simple curl or template-render check before browser automation."
        )
    return lines


def render_agent_policy_markdown(
    *,
    artifact_root: str,
    command: str = "synrail",
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    commands = policy_command_examples_for_binary(artifact_root=artifact_root, command=command)
    note_lines = policy_workspace_note_lines(
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
        command=command,
    )
    orientation_lines = policy_orientation_lines(commands["status"])
    lines = [
        "# Agent Workflow",
        "",
        "This repo uses Synrail to keep one bounded local change inside one controlled run.",
        "",
        "## First Step On Every New Task",
        "",
        "Run Synrail before deciding what to do next. It is a CLI control kernel, not a background daemon.",
        "```bash",
        commands["status"],
        "```",
        "",
    ]
    lines.extend(orientation_lines)
    lines.extend([
        "## Before You Edit",
        "",
        "1. If Synrail shows that no controlled run is active, start one before mutating code:",
        "```bash",
        commands["start"],
        "```",
        "",
        "2. Keep the change local and bounded to the stated task.",
        f"3. Edit the starter proof files under `{artifact_root}/` in place as the work becomes real.",
        "4. Run the local commands needed to verify the change honestly.",
        "",
        "## Before You Claim Success",
        "",
        "```bash",
        commands["check"],
        "```",
        "",
        "If Synrail is non-green, fix only what check tells you to fix, then rerun:",
        "",
        "```bash",
        commands["check"],
        "```",
        "",
        "## Important",
        "",
        "- Do not skip Synrail and try to legalize edits afterward.",
        "- Do not claim success without real local verification.",
        "- If `synrail` is unavailable on this machine, stop and report that the control tool is missing instead of bypassing it.",
        "",
    ])
    lines.extend(note_lines)
    if note_lines:
        lines.append("")
    return "\n".join(lines)


def render_gemini_policy_markdown(
    *,
    artifact_root: str,
    command: str = "synrail",
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    commands = policy_command_examples_for_binary(artifact_root=artifact_root, command=command)
    note_lines = policy_workspace_note_lines(
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
        command=command,
    )
    orientation_lines = policy_orientation_lines(commands["status"])
    gemini_orientation_lines = policy_gemini_orientation_lines()
    lines = [
        "# Gemini Workflow",
        "",
        "Use Synrail as the default local control path for this repo.",
        "",
        "## First Command",
        "",
        "For every new user task, run Synrail first so you can see the current governed state:",
        "",
        "```bash",
        commands["status"],
        "```",
        "",
        "Synrail is a CLI control kernel, not a background daemon.",
        "",
    ]
    lines.extend(orientation_lines)
    lines.extend(gemini_orientation_lines)
    lines.extend([
        "## Start",
        "",
        "If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:",
        "",
        "```bash",
        commands["start"],
        "```",
        "",
        "## Work",
        "",
        f"- Keep edits bounded and local to this repo.",
        f"- Update the starter proof files in `{artifact_root}/` as the change becomes real.",
        "- Run the local verification commands needed for the task.",
        "",
        "## Finish",
        "",
        "```bash",
        commands["check"],
        "```",
        "",
        f"If non-green, fix only what check tells you to fix, then rerun `{commands['check']}`.",
        "",
        "Do not bypass Synrail and do not claim success without real local verification.",
        "",
    ])
    lines.extend(note_lines)
    if note_lines:
        lines.append("")
    return "\n".join(lines)


def render_claude_policy_markdown(
    *,
    artifact_root: str,
    command: str = "synrail",
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    commands = policy_command_examples_for_binary(artifact_root=artifact_root, command=command)
    note_lines = policy_workspace_note_lines(
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
        command=command,
    )
    orientation_lines = policy_orientation_lines(commands["status"])
    lines = [
        "# Claude Workflow",
        "",
        "Use Synrail as the default local control path for this repo.",
        "",
        "## First Command",
        "",
        "For every new user task, run Synrail first so you can see the current governed state:",
        "",
        "```bash",
        commands["status"],
        "```",
        "",
        "Synrail is a CLI control kernel, not a background daemon.",
        "",
    ]
    lines.extend(orientation_lines)
    lines.extend([
        "## Start",
        "",
        "If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:",
        "",
        "```bash",
        commands["start"],
        "```",
        "",
        "## Work",
        "",
        f"- Keep edits bounded and local to this repo.",
        f"- Update the starter proof files in `{artifact_root}/` as the change becomes real.",
        "- Run the local verification commands needed for the task.",
        "",
        "## Finish",
        "",
        "```bash",
        commands["check"],
        "```",
        "",
        f"If non-green, fix only what check tells you to fix, then rerun `{commands['check']}`.",
        "",
        "Do not bypass Synrail and do not claim success without real local verification.",
        "",
    ])
    lines.extend(note_lines)
    if note_lines:
        lines.append("")
    return "\n".join(lines)


def render_agent_policy_block(
    *,
    title: str,
    intro: str,
    artifact_root: str,
    command: str = "synrail",
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    commands = policy_command_examples_for_binary(artifact_root=artifact_root, command=command)
    note_lines = policy_workspace_note_lines(
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
        command=command,
    )
    orientation_lines = policy_orientation_lines(commands["status"])
    lines = [
        f"## {title}",
        "",
        intro,
        "",
        "First command for every new task:",
        "",
        "```bash",
        commands["status"],
        "```",
        "",
    ]
    lines.extend(orientation_lines)
    lines.extend([
        "If Synrail shows that no controlled run is active, start one:",
        "",
        "```bash",
        commands["start"],
        "```",
        "",
        "Before claiming success, run:",
        "",
        "```bash",
        commands["check"],
        "```",
        "",
        f"If non-green, run `{commands['repair']}` and repair only the named gap before re-checking.",
        "",
        "Do not bypass Synrail and do not claim success without real local verification.",
    ])
    lines.extend(note_lines)
    return "\n".join(lines)


def policy_orientation_lines(status_command: str) -> list[str]:
    return [
        "## Project Orientation",
        "",
        "If the user asks what this project is, where work stopped, or what the current status is, treat that as a Synrail-guided orientation task too.",
        "",
        f"- Start with `{status_command}` before broader repo search.",
        "- Stay inside this project root and prefer read-only inspection first.",
        "- Summarize the governed state before exploring older files, sibling probes, or unrelated surfaces.",
        "- Do not turn project recall into repo archaeology.",
        "- Do not create helper scripts or make edits for an orientation-only question.",
        "",
    ]


def policy_gemini_orientation_lines() -> list[str]:
    return [
        "### Gemini Orientation Rule",
        "",
        "- After Synrail shows the current state, answer from the governed state first and stop once you can answer the user's question.",
        "- Do not inspect database schema, templates, or app internals for a simple orientation prompt unless Synrail state is genuinely insufficient.",
        "- Do not turn project recall into repo archaeology.",
        "",
    ]


def managed_policy_markers(path: Path) -> tuple[str, str]:
    stem = path.stem.upper().replace(".", "_")
    return (f"<!-- SYNRAIL_{stem}_START -->", f"<!-- SYNRAIL_{stem}_END -->")


def wrap_managed_policy_block(path: Path, body: str) -> str:
    start_marker, end_marker = managed_policy_markers(path)
    return f"{start_marker}\n{body.rstrip()}\n{end_marker}\n"


def upsert_managed_policy_block(current: str, *, path: Path, block: str) -> tuple[str, str]:
    start_marker, end_marker = managed_policy_markers(path)
    current_text = current or ""
    managed_block = wrap_managed_policy_block(path, block)
    if start_marker in current_text and end_marker in current_text:
        prefix, rest = current_text.split(start_marker, 1)
        _, suffix = rest.split(end_marker, 1)
        updated = prefix.rstrip() + "\n\n" + managed_block + suffix.lstrip("\n")
        state = "updated"
    elif current_text.strip():
        updated = current_text.rstrip() + "\n\n" + managed_block
        state = "appended"
    else:
        updated = managed_block
        state = "written"
    if updated == current_text:
        return current_text, "unchanged"
    return updated, state


def backup_existing_policy_file(path: Path) -> Path:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_name(f"{path.name}.synrail.bak.{timestamp}")
    backup_path.write_text(path.read_text())
    return backup_path


def write_agent_policy_file(
    path: Path,
    full_content: str,
    *,
    managed_block: str,
    force: bool,
) -> tuple[bool, str, Path | None]:
    if path.exists():
        current = path.read_text()
        if current == full_content:
            return False, "unchanged", None
        if force:
            backup_path = backup_existing_policy_file(path)
            path.write_text(full_content)
            return True, "written", backup_path
        updated, state = upsert_managed_policy_block(current, path=path, block=managed_block)
        if state == "unchanged":
            return False, state, None
        path.write_text(updated)
        return True, state, None
    path.write_text(full_content)
    return True, "written", None


def cmd_install_agent_files(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root or ".").resolve()
    artifact_root = relative_artifact_root_for_project(
        project_root=project_root,
        artifact_root=args.artifact_root,
    )
    command = preferred_synrail_command()
    git_context = workspace_git_context(project_root)
    workspace_isolation_note = git_context.get("workspace_isolation_note", "")
    prefer_runtime_helper = project_prefers_runtime_evidence(project_root)
    agents_path = project_root / "AGENTS.md"
    gemini_path = project_root / "GEMINI.md"
    claude_path = project_root / "CLAUDE.md"

    agents_content = render_agent_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    gemini_content = render_gemini_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    claude_content = render_claude_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    agents_block = render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="This repo uses Synrail to keep one bounded local change inside one controlled run.",
        artifact_root=artifact_root,
        command=command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    gemini_block = render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
        command=command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    claude_block = render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
        command=command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )

    agents_written, agents_state, agents_backup = write_agent_policy_file(
        agents_path,
        agents_content,
        managed_block=agents_block,
        force=args.force,
    )
    gemini_written, gemini_state, gemini_backup = write_agent_policy_file(
        gemini_path,
        gemini_content,
        managed_block=gemini_block,
        force=args.force,
    )
    claude_written, claude_state, claude_backup = write_agent_policy_file(
        claude_path,
        claude_content,
        managed_block=claude_block,
        force=args.force,
    )

    print("Agent adoption files are ready.")
    print(f"Project root: {project_root}")
    print(f"Artifact root hint: {artifact_root}")
    print(f"Synrail command: {command}")
    if workspace_isolation_note:
        print(f"Workspace note: {workspace_isolation_note}")
    if prefer_runtime_helper:
        print(f"Runtime note: use `{command} runtime-helper` for a small curl or template-render verification path.")
    print(f"AGENTS.md: {agents_state}")
    print(f"GEMINI.md: {gemini_state}")
    print(f"CLAUDE.md: {claude_state}")
    if agents_backup:
        print(f"AGENTS.md backup: {agents_backup}")
    if gemini_backup:
        print(f"GEMINI.md backup: {gemini_backup}")
    if claude_backup:
        print(f"CLAUDE.md backup: {claude_backup}")
    if (
        agents_state in {"appended", "updated"}
        or gemini_state in {"appended", "updated"}
        or claude_state in {"appended", "updated"}
    ):
        print("What to do next: run `synrail` in this repo so the dashboard can show the current state, then review and commit the managed Synrail block if the wording fits the repo.")
    elif agents_written or gemini_written or claude_written:
        print("What to do next: run `synrail` in this repo. Commit these files if you want local agents to keep discovering Synrail before editing.")
    else:
        print("What to do next: run `synrail` in this repo. Keep these files committed so local agents continue discovering the same Synrail entrypoint.")
    return 0


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


def is_default_workspace_artifact_root(root: Path, *, project_root: Path | None = None) -> bool:
    return root.resolve() == default_workspace_artifact_root(project_root=project_root)


def shell_command(root: Path | None, *parts: str, project_root: Path | None = None) -> str:
    command = ["synrail", *parts]
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


def untouched_preferred_proof_paths(root: Path | None) -> set[Path]:
    if not root:
        return set()
    proof_request_file = alpha_file(root, "proof_request")
    if not proof_request_file.exists():
        return set()
    proof_request = load_bootstrap_json(proof_request_file)
    starter_hashes = proof_request.get("starter_hashes", {})
    if not isinstance(starter_hashes, dict):
        return set()
    untouched: set[Path] = set()
    for artifact_id, path in preferred_proof_artifact_paths(root).items():
        expected_hash = starter_hashes.get(artifact_id, "")
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
    return path[0] in {"init", "start", "check", "refresh-acceptance", "generate-prompt", "next-step", "repair-step", "restore", "resume", "continue", "checkpoint", "session-export", "bug-packet"}


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


def alpha_root_from_args(args: argparse.Namespace, *, ensure: bool = False) -> Path | None:
    value = getattr(args, "artifact_root", None)
    if not value:
        return None
    root = Path(value).expanduser().resolve()
    if ensure:
        root.mkdir(parents=True, exist_ok=True)
    return root


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
    state = load_json(state_path)
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
    state = load_json(state_path)
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
    lines.extend([
        f"What happened: {payload.get('what_happened', payload.get('summary', ''))}",
        f"What it means: {payload.get('what_it_means', payload.get('diagnosis', ''))}",
        f"What to do next: {payload.get('what_to_do_next', payload.get('next_step', ''))}",
    ])
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
        lines.append("Runtime helper: synrail runtime-helper")
    print("\n".join(lines))


def print_start_summary(*, root: Path, state_file: Path, project_root: Path) -> None:
    state = load_json(state_file)
    proof_request = load_bootstrap_json(alpha_file(root, "proof_request"))
    preferred = proof_request.get("preferred_artifacts", {})
    profile = load_project_profile(root) or {}
    lines = [
        "Controlled run started.",
        "Do this now: Edit only the starter proof files below in place. Leave every other surface unchanged.",
        f"Artifact root: {display_path(root)}",
        f"Run id: {state.get('run_id', '')}",
        "Starter proof files are ready for this run.",
        f"- final result: {preferred.get('final_result', display_path_from_base(root / 'final_result.json', base=project_root))}",
        f"- readback: {preferred.get('readback', display_path_from_base(root / 'readback.txt', base=project_root))}",
        f"- scenario proof: {preferred.get('scenario_proof', display_path_from_base(root / 'scenario_proof.txt', base=project_root))}",
        "Then run: " + shell_command(root, "check", project_root=project_root),
    ]
    if profile.get("workspace_isolation_note", ""):
        lines.append("Workspace note: " + profile["workspace_isolation_note"])
    if profile.get("prefers_runtime_evidence", False):
        lines.append("Runtime helper: synrail runtime-helper")
    print("\n".join(lines))


def print_existing_run_summary(*, root: Path, state_file: Path, project_root: Path) -> None:
    state = load_json(state_file)
    proof_request = load_bootstrap_json(alpha_file(root, "proof_request")) if alpha_file(root, "proof_request").exists() else {}
    preferred = proof_request.get("preferred_artifacts", {})
    lines = [
        "Synrail already has a controlled run in progress.",
        "What happened: this artifact root still points at the current untouched run, so Synrail did not start a second one.",
        f"Artifact root: {display_path(root)}",
        f"Run id: {state.get('run_id', '')}",
        "Continue this run by editing only the starter proof files below in place.",
        f"- final result: {preferred.get('final_result', display_path_from_base(root / 'final_result.json', base=project_root))}",
        f"- readback: {preferred.get('readback', display_path_from_base(root / 'readback.txt', base=project_root))}",
        f"- scenario proof: {preferred.get('scenario_proof', display_path_from_base(root / 'scenario_proof.txt', base=project_root))}",
        "Next command: " + shell_command(root, "check", project_root=project_root),
    ]
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
        "help_command": "synrail --help",
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
        "Replace the sample changed file path with the actual file paths for this run.",
        "Set change_disposition to already_satisfied only when the requested state was already present before any edit.",
        "Keep the scope tight: do not smuggle adjacent spacing, class, or layout tweaks into a task that only asked you to add or insert a small surface change.",
        "If the task only asked for a simple subtitle or label, keep the new line visually plain and avoid extra emphasis styling unless the task explicitly asked for it.",
        "Keep git_diff as a real patch with diff --git, ---, +++, and @@ markers when you can produce one.",
        "If git_diff is unavailable, keep diff_provenance explicit with changed_file, changed lines, and verification command plus result.",
        "For an already_satisfied no-op, keep modified_files empty, keep git_diff empty, and use diff_provenance.changed_file plus observed_line, verification command/result, and provenance_note.",
        "artifact_identity can mirror the current run identities so low-level bundle-check stays reproducible too.",
        "Use synrail explain-proof after a check to see exact semantic gaps and reasons.",
    ]
    if profile.get("workspace_isolation_note", ""):
        notes.append(profile["workspace_isolation_note"])
    return {
        "request_id": state.get("run_id", "RUN_ID_FOR_THIS_CONTROLLED_RUN"),
        "task_class": state.get("task_class", DEFAULT_ALPHA_TASK_CLASS),
        "status": "success",
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
            "added_line": "describe one concrete inserted line from the changed file",
            "observed_line": "if no edit was required because the requested state was already present, record that existing line here instead of inventing a patch",
            "context_before": "describe the stable line immediately before the change",
            "context_after": "describe the stable line immediately after the change",
            "verification_command": f"grep -n 'needle' {changed_file}",
            "verification_result": "12:+ describe the concrete inserted or changed line",
            "provenance_note": "Use this when git_diff is unavailable or the file is not tracked by git.",
        },
        "artifact_identity": {
            "baseline_identity": baseline_identity or "autodetected_generic_baseline",
            "execution_surface_identity": execution_surface_identity or "autodetected_generic_worktree",
            "prompt_identity": prompt_identity or task_identity or "TASK_PROMPT_IDENTITY_FOR_THIS_RUN",
            "task_identity": task_identity or "TASK_IDENTITY_FOR_THIS_RUN",
        },
        "cleanup_status": {
            "success": True,
            "summary": f"workspace clean after updating only {changed_file} with no unintended changes",
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
                "If you still need UI or rendered-output evidence, prefer curl or direct template render before browser automation.",
            ]
        )
        return "\n".join(lines) + "\n"

    lines.extend(
        [
            "For UI, route, or rendered-output tasks, prefer a small local response/render check before browser automation.",
            "Try one of these paths first:",
            "1. HTTP path (if the local app is already running):",
            "   curl -s http://localhost:8000/ | grep -C 2 'needle'",
        ]
    )
    template_root = project_root / "templates"
    if template_root.exists() or any((child / "templates").exists() for child in project_root.iterdir() if child.is_dir()):
        lines.extend(
            [
                "2. Template/render path (no browser required):",
                "   python3 -c \"from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('templates')); html = env.get_template('index.html').render(); print('needle' in html)\"",
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
        "Scenario: describe the exact runtime context on the attested target surface",
        "Command: paste the local command, request, or test that verified the change",
        "Observed: paste the concrete output, rendered fragment, or behavior that was seen",
    ]
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
        "Observed: describe what this changed surface now contains, returns, or renders",
    ]
    if profile.get("prefers_runtime_evidence", False):
        lines.append("Runtime hint: for UI, route, or rendered output changes, prefer a local response or rendered fragment over source-only grep when possible; run `synrail runtime-helper` for a small curl or template-render path before browser automation")
    lines.append("")
    return "\n".join(lines)


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
    if any(section["section"] in {"final_result", "modified_files", "diff_provenance", "verification_corroboration", "cleanup_status"} for section in structural_gaps + semantic_gaps):
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
                lines.append("  Concrete fix: keep git_diff patch-shaped with diff --git, ---, +++, @@, and the named changed files, or add diff_provenance with changed_file, changed lines, and verification command plus result.")
                lines.append("  No-op fix: if the requested state was already present before any edit, set change_disposition to already_satisfied, keep modified_files empty, keep git_diff empty, and use diff_provenance.changed_file plus observed_line, verification command/result, and provenance_note.")
            if gap["section"] == "artifact_identity":
                lines.append("  Concrete fix: ensure baseline_identity, execution_surface_identity, prompt_identity, and task_identity are all non-empty for this run.")
            if gap["section"] == "modified_files":
                lines.append("  No-op fix: if no file had to change because the requested state already existed, set change_disposition to already_satisfied and keep modified_files empty instead of inventing a changed file list.")
            if gap["section"] == "scope_alignment":
                lines.append("  Concrete fix: keep only the requested additive change. Remove adjacent spacing, class, or layout rewrites unless the task explicitly asked for them.")
            if gap["section"] == "presentation_alignment":
                lines.append("  Concrete fix: keep the newly added line visually plain. Remove extra emphasis styling like italic, opacity, uppercase, or tracking unless the task explicitly asked for it.")
            if gap["section"] == "verification_corroboration":
                lines.append("  Concrete fix: keep acceptance tied to explicit local verification. Either add structured diff_provenance with verification command and result in final_result.json, or record a labeled scenario proof with Command and Observed or Result lines instead of prose-only proof text.")
    if semantic_gaps:
        lines.append("Semantic gaps:")
        for gap in semantic_gaps:
            lines.append(f"- {gap['section']}")
            if gap["why"]:
                lines.append(f"  Why: {gap['why']}")
            if gap["recommended_action"]:
                lines.append(f"  What to do: {gap['recommended_action']}")
            if gap["section"] == "diff_provenance":
                lines.append("  Concrete fix: keep git_diff patch-shaped with diff --git, ---, +++, @@, and the named changed files, or add diff_provenance with changed_file, changed lines, and verification command plus result.")
                lines.append("  No-op fix: if the requested state was already present before any edit, set change_disposition to already_satisfied, keep modified_files empty, keep git_diff empty, and use diff_provenance.changed_file plus observed_line, verification command/result, and provenance_note.")
            if gap["section"] == "artifact_identity":
                lines.append("  Concrete fix: ensure baseline_identity, execution_surface_identity, prompt_identity, and task_identity are all non-empty for this run.")
            if gap["section"] == "modified_files":
                lines.append("  No-op fix: if no file had to change because the requested state already existed, set change_disposition to already_satisfied and keep modified_files empty instead of inventing a changed file list.")
            if gap["section"] == "scope_alignment":
                lines.append("  Concrete fix: keep only the requested additive change. Remove adjacent spacing, class, or layout rewrites unless the task explicitly asked for them.")
            if gap["section"] == "presentation_alignment":
                lines.append("  Concrete fix: keep the newly added line visually plain. Remove extra emphasis styling like italic, opacity, uppercase, or tracking unless the task explicitly asked for it.")
            if gap["section"] == "verification_corroboration":
                lines.append("  Concrete fix: keep acceptance tied to explicit local verification. Either add structured diff_provenance with verification command and result in final_result.json, or record a labeled scenario proof with Command and Observed or Result lines instead of prose-only proof text.")
    if not structural_gaps and not semantic_gaps:
        lines.append("Synrail did not find structural or semantic proof gaps in the current bundle.")
    if any(gap["section"] in {"final_result", "modified_files", "diff_provenance", "verification_corroboration", "artifact_identity", "cleanup_status"} for gap in structural_gaps + semantic_gaps):
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
            lines.append("Next command: " + shell_command(root, "restore"))
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
            lines.append("Restore command: " + shell_command(root, "restore"))
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


def cmd_status(args: argparse.Namespace) -> int:
    project_root = Path.cwd().resolve()
    root = alpha_root_from_args(args) or default_workspace_artifact_root(project_root=project_root)
    state_path: Path | None = None
    if getattr(args, "state_file", None):
        state_path = Path(args.state_file).expanduser().resolve()
        default_state_path = alpha_file(root, "state")
        if state_path != default_state_path.resolve():
            root = state_path.parent
    summary = build_workspace_status(root, project_root=project_root, state_path=state_path)
    state_path = (state_path or alpha_file(root, "state")).resolve()
    if state_path.exists():
        state = load_json(state_path)
        summary.update(
            {
                "run_id": state.get("run_id", ""),
                "task_class": state.get("task_class", ""),
                "state": state.get("state", ""),
                "target_surface": state.get("target_surface", {}).get("status", ""),
                "doctor": state.get("doctor", {}).get("status", ""),
                "proof_bundle": state.get("proof_bundle", {}).get("status", ""),
                "closure": state.get("closure", {}).get("status", ""),
                "next_safe_step": state.get("next_safe_step", ""),
            }
        )
    if getattr(args, "json", False):
        print(json.dumps(summary, indent=2, ensure_ascii=True))
    else:
        print_workspace_dashboard(summary)
    return 0


def cmd_explain_proof(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args) or default_workspace_artifact_root(project_root=Path.cwd().resolve())
    bundle_file = Path(getattr(args, "bundle_file", "") or alpha_file(root, "bundle")).expanduser().resolve()
    if not bundle_file.exists():
        if getattr(args, "json", False):
            print(json.dumps({"result": "ERROR", "reason": "BUNDLE_FILE_REQUIRED", "next_command": "synrail check"}, ensure_ascii=True))
        else:
            print("Synrail does not have a proof explanation yet.")
            print("What is missing: bundle.json has not been generated for this run.")
            print("What to do next: run synrail check first so Synrail can evaluate the current proof bundle.")
        return 2
    bundle = load_json(bundle_file)
    explanation = build_proof_explanation(bundle, root=root)
    if getattr(args, "json", False):
        print(json.dumps(explanation, indent=2, ensure_ascii=True))
    else:
        print_proof_explanation(explanation, root=root)
    return 0


def cmd_final_result_template(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args) or default_workspace_artifact_root(project_root=Path.cwd().resolve())
    payload = final_result_template_payload(root=root if root.exists() else None)
    text = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    if getattr(args, "output", None):
        target = Path(args.output).expanduser().resolve()
        target.write_text(text)
        print(f"Wrote canonical final_result template to {display_path(target)}")
    else:
        print(text, end="")
    return 0


def cmd_scenario_proof_template(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args) or default_workspace_artifact_root(project_root=Path.cwd().resolve())
    text = scenario_proof_template_text(root=root if root.exists() else None)
    if getattr(args, "output", None):
        target = Path(args.output).expanduser().resolve()
        target.write_text(text)
        print(f"Wrote canonical scenario_proof template to {display_path(target)}")
    else:
        print(text, end="")
    return 0


def cmd_readback_template(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args) or default_workspace_artifact_root(project_root=Path.cwd().resolve())
    text = readback_template_text(root=root if root.exists() else None)
    if getattr(args, "output", None):
        target = Path(args.output).expanduser().resolve()
        target.write_text(text)
        print(f"Wrote canonical readback template to {display_path(target)}")
    else:
        print(text, end="")
    return 0


def cmd_runtime_helper(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args) or default_workspace_artifact_root(project_root=Path.cwd().resolve())
    text = runtime_helper_text(root=root if root.exists() else None)
    if getattr(args, "output", None):
        target = Path(args.output).expanduser().resolve()
        target.write_text(text)
        print(f"Wrote runtime helper guidance to {display_path(target)}")
    else:
        print(text, end="")
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    project_root = Path(getattr(args, "project_root", "") or Path.cwd()).resolve()
    if not getattr(args, "run_id", None):
        args.run_id = default_alpha_run_id()
    if not getattr(args, "task_class", None):
        args.task_class = DEFAULT_ALPHA_TASK_CLASS
    if not getattr(args, "output", None):
        if not root:
            raise ValueError("output or artifact root is required")
        args.output = str(alpha_file(root, "state"))
    forwarded = [
        "init",
        "--run-id", args.run_id,
        "--task-class", args.task_class,
        "--output", args.output,
    ]
    if args.mode == "dev":
        code = run_python(SPINE, forwarded)
        if code == 0 and root:
            save_project_profile(root, build_project_profile(project_root=project_root, root=root, task_class=args.task_class))
            save_alpha_identity_files(
                root,
                task_identity=getattr(args, "task_identity", ""),
                prompt_identity=getattr(args, "prompt_identity", ""),
            )
            criteria_completed = write_acceptance_criteria(root, generated_by="synrail init")
            if criteria_completed.returncode != 0:
                return criteria_completed.returncode
        return code
    completed = run_python_capture(SPINE, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    if root:
        save_project_profile(root, build_project_profile(project_root=project_root, root=root, task_class=args.task_class))
        save_alpha_identity_files(
            root,
            task_identity=getattr(args, "task_identity", ""),
            prompt_identity=getattr(args, "prompt_identity", ""),
        )
        criteria_completed = write_acceptance_criteria(root, generated_by="synrail init")
        if criteria_completed.returncode != 0:
            if criteria_completed.stderr.strip():
                print(criteria_completed.stderr.strip(), file=sys.stderr)
            if criteria_completed.stdout.strip():
                print(criteria_completed.stdout.strip())
            return criteria_completed.returncode
        print_init_summary(root=root, state_file=Path(args.output))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    project_root = Path(getattr(args, "project_root", "") or Path.cwd()).resolve()
    if not getattr(args, "output", None):
        if not root:
            raise ValueError("output or artifact root is required")
        args.output = str(alpha_file(root, "state"))

    existing_state_path = Path(args.output)
    existing_state = load_json(existing_state_path) if existing_state_path.exists() else None
    if not getattr(args, "run_id", None):
        args.run_id = default_alpha_run_id()
    if not getattr(args, "task_class", None):
        args.task_class = existing_state.get("task_class", DEFAULT_ALPHA_TASK_CLASS) if existing_state else DEFAULT_ALPHA_TASK_CLASS

    task_identity, prompt_identity = resolve_start_identities(args, root=root)
    if not task_identity:
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "TASK_IDENTITY_REQUIRED_FOR_CONTROLLED_START"}, ensure_ascii=True))
        else:
            print("Synrail could not start a controlled run yet.")
            print("What is missing: the original task request for this run.")
            print('What to do next: run `synrail start "Describe the bounded local change."` or pass --task-identity, then retry.')
        return 2

    existing_proof = existing_preferred_proof_artifacts(root)
    previous_state = existing_state.get("state", "") if existing_state else ""
    active_bootstrap = alpha_file(root, "bootstrap").exists()
    if existing_state and active_bootstrap and previous_state and previous_state not in TERMINAL_RUN_STATES and not existing_proof:
        if args.mode == "dev":
            print(
                json.dumps(
                    {
                        "result": "OK",
                        "reason": "CONTROLLED_RUN_ALREADY_ACTIVE",
                        "reused_existing_run": True,
                        "run_id": existing_state.get("run_id", ""),
                        "next_command": shell_command(root, "check", project_root=project_root),
                    },
                    ensure_ascii=True,
                )
            )
        else:
            print_existing_run_summary(root=root, state_file=existing_state_path, project_root=project_root)
        return 0
    if existing_proof:
        if previous_state in ("CLOSURE_ACCEPTED", "CLOSURE_REJECTED"):
            for _aid, path in preferred_proof_artifact_paths(root).items():
                path.unlink(missing_ok=True)
            proof_request_path = alpha_file(root, "proof_request")
            proof_request_path.unlink(missing_ok=True)
            existing_proof = []
        if existing_proof:
            if args.mode == "dev":
                print(json.dumps({"result": "ERROR", "reason": "CONTROLLED_START_REQUIRES_CLEAN_PROOF_SURFACE", "existing_proof_artifacts": existing_proof}, ensure_ascii=True))
            else:
                print("Synrail could not start this run in controlled mode yet.")
                print("What happened: proof artifacts already exist, so this looks like a post-hoc run instead of a controlled start.")
                print("What to do next: clear those proof artifacts or begin a fresh run before trusting Synrail acceptance.")
            return 2

    forwarded = [
        "init",
        "--run-id", args.run_id,
        "--task-class", args.task_class,
        "--output", args.output,
    ]
    completed = run_python_capture(SPINE, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode

    profile = build_project_profile(project_root=project_root, root=root, task_class=args.task_class)
    save_project_profile(root, profile)
    clear_runtime_artifacts_for_start(root)
    save_alpha_identity_files(root, task_identity=task_identity, prompt_identity=prompt_identity)
    write_controlled_start_artifacts(
        root,
        project_root=project_root,
        run_id=args.run_id,
        task_class=args.task_class,
        task_identity=task_identity,
        prompt_identity=prompt_identity,
        profile=profile,
        started_via="synrail start",
    )
    criteria_completed = write_acceptance_criteria(root, generated_by="synrail start")
    if criteria_completed.returncode != 0:
        if criteria_completed.stderr.strip():
            print(criteria_completed.stderr.strip(), file=sys.stderr)
        if criteria_completed.stdout.strip():
            print(criteria_completed.stdout.strip())
        return criteria_completed.returncode
    validation = apply_bootstrap_defaults(args, root=root)
    if validation:
        save_bootstrap_json(alpha_file(root, "bootstrap_validation"), validation)
    print_start_summary(root=root, state_file=Path(args.output), project_root=project_root)
    return 0


def cmd_refresh_acceptance(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if not root:
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2
    profile = project_profile_file(root)
    if not profile.exists():
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "PROJECT_PROFILE_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not refresh the acceptance rules yet.")
            print("What to do next: run synrail start first so Synrail can capture the controlled project profile.")
        return 2
    completed = write_acceptance_criteria(root, generated_by="synrail refresh-acceptance")
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    state_file = alpha_file(root, "state")
    if state_file.exists():
        validation_completed = write_acceptance_validation(root, criteria_file=alpha_file(root, "acceptance_criteria"), state_file=state_file)
        if validation_completed.returncode != 0:
            if validation_completed.stderr.strip():
                print(validation_completed.stderr.strip(), file=sys.stderr)
            if validation_completed.stdout.strip():
                print(validation_completed.stdout.strip())
            return validation_completed.returncode
    if args.mode == "dev":
        print(json.dumps(
            {
                "criteria": load_json(alpha_file(root, "acceptance_criteria")),
                "validation": load_json(alpha_file(root, "acceptance_validation")) if alpha_file(root, "acceptance_validation").exists() else None,
            },
            indent=2,
            ensure_ascii=True,
        ))
    else:
        print_acceptance_refresh_summary(root=root)
    return 0


def cmd_telemetry_enable(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    config = enable_telemetry(root, args.tester_id)
    print(json.dumps({"result": "OK", "telemetry_session_id": config["telemetry_session_id"]}, ensure_ascii=True))
    return 0


def cmd_telemetry_export(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if not root:
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2
    if not getattr(args, "output", None):
        args.output = str(default_session_replay_file(root))
    if not getattr(args, "issue_output", None):
        args.issue_output = str(default_issue_body_file(root))
    try:
        record = export_session_replay(root, Path(args.output), Path(args.issue_output))
    except ValueError as exc:
        print("Synrail could not export feedback yet.")
        print("What happened: telemetry is not enabled for this artifact root.")
        print("What to do next: rerun synrail start with --telemetry-opt-in or use synrail telemetry enable before exporting feedback.")
        return 2
    print("Feedback export ready.")
    print("What it includes: one session replay and one issue-ready summary.")
    print(f"Command count captured: {record['command_count']}")
    print("Use this when you want to send back a non-green run without hand-assembling artifacts.")
    return 0


def cmd_bundle_check(args: argparse.Namespace) -> int:
    forwarded = [
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--output", args.output,
    ]
    optional_pairs = [
        ("--run-id", args.run_id),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--baseline-identity", args.baseline_identity),
        ("--execution-surface-identity", args.execution_surface_identity),
        ("--prompt-identity", args.prompt_identity),
        ("--task-identity", args.task_identity),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    return run_python(BUNDLE, forwarded)


def cmd_apply_bundle(args: argparse.Namespace) -> int:
    return run_python(SPINE, ["apply-bundle", args.state_file, args.bundle_file])


def cmd_closure(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--bundle-file", args.bundle_file,
        "--output", args.output,
    ]
    if args.update_state:
        forwarded.append("--update-state")
    return run_python(CLOSURE, forwarded)


def cmd_apply_closure(args: argparse.Namespace) -> int:
    return run_python(SPINE, ["apply-closure", args.state_file, args.closure_file])


def cmd_refresh(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--event-type", args.event_type,
        "--output", args.output,
    ]
    optional_pairs = [
        ("--doctor-status", args.doctor_status),
        ("--bundle-file", args.bundle_file),
        ("--closure-file", args.closure_file),
        ("--recovery-status", args.recovery_status),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    if args.reverification_complete:
        forwarded.append("--reverification-complete")
    if args.update_state:
        forwarded.append("--update-state")
    return run_python(REFRESH, forwarded)


def cmd_validate(args: argparse.Namespace) -> int:
    forwarded = [
        "--schema", args.schema,
        "--document", args.document,
    ]
    return run_python(VALIDATE, forwarded)


def cmd_doctor(args: argparse.Namespace) -> int:
    forwarded = [
        "--doctor-run-id", args.doctor_run_id,
        "--doctor-level", args.doctor_level,
        "--target-path", args.target_path,
        "--target-classification", args.target_classification,
        "--baseline-identity", args.baseline_identity,
        "--intended-run-class", args.intended_run_class,
        "--output", args.output,
    ]
    if args.state_file:
        forwarded.extend(["--state-file", args.state_file])
    if args.update_state:
        forwarded.append("--update-state")
    if args.clean_surface:
        forwarded.append("--clean-surface")
    if args.artifact_viable:
        forwarded.append("--artifact-viable")
    if args.helper_ok:
        forwarded.append("--helper-ok")
    if args.credentials_ok:
        forwarded.append("--credentials-ok")
    if args.prompt_identity_ok:
        forwarded.append("--prompt-identity-ok")
    optional_pairs = [
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--prompt-identity-file", args.prompt_identity_file),
        ("--expected-task-identity", args.expected_task_identity),
        ("--target-identity-file", args.target_identity_file),
        ("--expected-target-identity", args.expected_target_identity),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    for changed_file in args.changed_file:
        forwarded.extend(["--changed-file", changed_file])
    for allowed_scope_path in args.allowed_scope_path:
        forwarded.extend(["--allowed-scope-path", allowed_scope_path])
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    return run_python(DOCTOR, forwarded)


def cmd_compare(args: argparse.Namespace) -> int:
    try:
        baseline = load_json(Path(args.baseline_file))
        harness = comparison_harness_for_inputs(args.baseline_file, args.synrail_file)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": "COMPARISON_INPUT_SCHEMA_MISMATCH", "detail": str(exc)}, ensure_ascii=True))
        return 2
    if baseline.get("schema_version") == "comparison_input_v2":
        forwarded = [
            "--substitute-file", args.baseline_file,
            "--synrail-file", args.synrail_file,
            "--output", args.output,
        ]
    else:
        forwarded = [
            "--baseline-file", args.baseline_file,
            "--synrail-file", args.synrail_file,
            "--output", args.output,
        ]
    return run_python(harness, forwarded)


def cmd_substitute_pressure(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    for record in args.record:
        forwarded.extend(["--record", record])
    forwarded.extend(["--output", args.output])
    return run_python(SUBSTITUTE_PRESSURE, forwarded)


def cmd_hybrid_status(args: argparse.Namespace) -> int:
    forwarded = [
        "--cost-record", args.cost_record,
        "--output", args.output,
    ]
    for hybrid_record in args.hybrid_record:
        forwarded.extend(["--hybrid-record", hybrid_record])
    return run_python(HYBRID_STATUS, forwarded)


def cmd_recommend_mode(args: argparse.Namespace) -> int:
    forwarded = [
        "--cost-record", args.cost_record,
        "--scenario-class", args.scenario_class,
        "--task-class", args.task_class,
        "--false-success-risk", args.false_success_risk,
        "--recovery-cost", args.recovery_cost,
        "--output", args.output,
    ]
    if args.hybrid_status:
        forwarded.extend(["--hybrid-status", args.hybrid_status])
    if args.governed_cost_delta:
        forwarded.extend(["--governed-cost-delta", args.governed_cost_delta])
    if args.execution_surface_ambiguous:
        forwarded.append("--execution-surface-ambiguous")
    if args.artifact_truth_nontrivial:
        forwarded.append("--artifact-truth-nontrivial")
    if args.explicit_hybrid_ambiguity:
        forwarded.extend(["--explicit-hybrid-ambiguity", args.explicit_hybrid_ambiguity])
    return run_python(MODE_SELECTOR, forwarded)


def cmd_select_mode(args: argparse.Namespace) -> int:
    forwarded = [
        "--recommendation-file", args.recommendation_file,
        "--output", args.output,
    ]
    if args.selected_mode:
        forwarded.extend(["--selected-mode", args.selected_mode])
    if args.selected_with_preparation:
        forwarded.append("--selected-with-preparation")
    return run_python(MODE_RECEIPT, forwarded)


def cmd_plan_proof(args: argparse.Namespace) -> int:
    forwarded = [
        "--run-id", args.run_id,
        "--task-class", args.task_class,
        "--artifact-root", args.artifact_root,
        "--baseline-identity", args.baseline_identity,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
        "--output", args.output,
    ]
    return run_python(PROOF_PLAN, forwarded)


def cmd_preparation_receipt(args: argparse.Namespace) -> int:
    forwarded = [
        "--plan-file", args.plan_file,
        "--bundle-file", args.bundle_file,
        "--output", args.output,
    ]
    return run_python(PREPARATION_RECEIPT, forwarded)


def cmd_governed_cost(args: argparse.Namespace) -> int:
    forwarded = [
        "--unprepared-file", args.unprepared_file,
        "--prepared-file", args.prepared_file,
        "--output", args.output,
    ]
    return run_python(GOVERNED_COST, forwarded)


def cmd_create_checkpoint(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if root and not getattr(args, "checkpoint_id", None):
        args.checkpoint_id = "working"
    if root and not getattr(args, "checkpoint_root", None):
        args.checkpoint_root = str(checkpoint_root(root, args.checkpoint_id))
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and not getattr(args, "output", None):
        args.output = str(checkpoint_record_file(root, args.checkpoint_id))
    if root:
        for attr, file_id in [
            ("report_file", "report"),
            ("orchestration_file", "orchestration"),
            ("bundle_file", "bundle"),
            ("closure_file", "closure"),
            ("refresh_file", "refresh"),
            ("selection_file", "selection_receipt"),
            ("preparation_file", "preparation_receipt"),
            ("repair_packet_file", "repair_packet"),
            ("repair_handoff_file", "repair_handoff"),
            ("repair_receipt_file", "repair_receipt"),
        ]:
            if not getattr(args, attr, None):
                existing = maybe_existing_alpha_file(root, file_id)
                if existing:
                    setattr(args, attr, existing)
    forwarded = [
        "create",
        "--checkpoint-id", args.checkpoint_id,
        "--checkpoint-root", args.checkpoint_root,
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    optional_pairs = [
        ("--report-file", args.report_file),
        ("--orchestration-file", args.orchestration_file),
        ("--bundle-file", args.bundle_file),
        ("--closure-file", args.closure_file),
        ("--refresh-file", args.refresh_file),
        ("--selection-file", args.selection_file),
        ("--preparation-file", args.preparation_file),
        ("--repair-packet-file", args.repair_packet_file),
        ("--repair-handoff-file", args.repair_handoff_file),
        ("--repair-receipt-file", args.repair_receipt_file),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    if args.mode == "dev":
        return run_python(CHECKPOINT, forwarded)
    completed = run_python_capture(CHECKPOINT, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    print_checkpoint_summary(Path(args.output), action="create", root=root)
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if args.mode == "dev":
        return cmd_create_checkpoint(args)
    checkpoint_id = getattr(args, "checkpoint_id", None) or "working"
    record_output = Path(getattr(args, "output", "") or checkpoint_record_file(root, checkpoint_id))
    record_root = Path(getattr(args, "checkpoint_root", "") or checkpoint_root(root, checkpoint_id))
    state_file = Path(getattr(args, "state_file", "") or alpha_file(root, "state"))
    project_root = Path(getattr(args, "project_root", "") or ".").resolve()
    create_forwarded = [
        "create",
        "--checkpoint-id", checkpoint_id,
        "--checkpoint-root", str(record_root),
        "--state-file", str(state_file),
        "--project-root", str(project_root),
        "--output", str(record_output),
    ]
    for attr, flag in [
        ("report_file", "--report-file"),
        ("orchestration_file", "--orchestration-file"),
        ("bundle_file", "--bundle-file"),
        ("closure_file", "--closure-file"),
        ("refresh_file", "--refresh-file"),
        ("selection_file", "--selection-file"),
        ("preparation_file", "--preparation-file"),
        ("repair_packet_file", "--repair-packet-file"),
        ("repair_handoff_file", "--repair-handoff-file"),
        ("repair_receipt_file", "--repair-receipt-file"),
    ]:
        value = getattr(args, attr, None)
        if not value and root:
            file_id = {
                "report_file": "report",
                "orchestration_file": "orchestration",
                "bundle_file": "bundle",
                "closure_file": "closure",
                "refresh_file": "refresh",
                "selection_file": "selection_receipt",
                "preparation_file": "preparation_receipt",
                "repair_packet_file": "repair_packet",
                "repair_handoff_file": "repair_handoff",
                "repair_receipt_file": "repair_receipt",
            }[attr]
            value = maybe_existing_alpha_file(root, file_id)
        if value:
            create_forwarded.extend([flag, value])
    created = run_python_capture(CHECKPOINT, create_forwarded)
    if created.returncode != 0:
        if created.stderr.strip():
            print(created.stderr.strip(), file=sys.stderr)
        if created.stdout.strip():
            print(created.stdout.strip())
        return created.returncode
    verify_output = Path(checkpoint_verify_file(root, checkpoint_id))
    verified = run_python_capture(
        CHECKPOINT,
        [
            "verify",
            "--checkpoint-record-file", str(record_output),
            "--output", str(verify_output),
        ],
    )
    if verified.returncode != 0:
        if verified.stderr.strip():
            print(verified.stderr.strip(), file=sys.stderr)
        if verified.stdout.strip():
            print(verified.stdout.strip())
        print_checkpoint_summary(record_output, action="create", root=root)
        return verified.returncode
    print_save_summary(record_output, verify_output, root=root)
    return 0


def cmd_verify_checkpoint(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if root and not getattr(args, "output", None):
        checkpoint_id = getattr(args, "checkpoint_id", None) or (Path(args.checkpoint_record_file).parent.name if getattr(args, "checkpoint_record_file", None) else "working")
        args.output = str(checkpoint_verify_file(root, checkpoint_id))
    if not getattr(args, "checkpoint_record_file", None):
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_RECORD_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not find a restore point to confirm.")
            if root:
                print("What to do next: create one while the project is in a verified working state.")
                print("Next command: " + shell_command(root, "save"))
        return 2
    if not getattr(args, "output", None):
        print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_VERIFY_OUTPUT_REQUIRED"}, ensure_ascii=True))
        return 2
    forwarded = [
        "verify",
        "--checkpoint-record-file", args.checkpoint_record_file,
        "--output", args.output,
    ]
    if args.mode == "dev":
        return run_python(CHECKPOINT, forwarded)
    completed = run_python_capture(CHECKPOINT, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    print_checkpoint_summary(Path(args.output), action="verify", root=root)
    return 0


def cmd_restore_checkpoint(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if root and not getattr(args, "target_root", None):
        args.target_root = str(root)
    if root and not getattr(args, "output", None):
        output_file_id = "checkpoint_restore_preview" if getattr(args, "preview", False) else "checkpoint_restore"
        args.output = str(alpha_file(root, output_file_id))
    if not root and not getattr(args, "output", None):
        print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_OUTPUT_REQUIRED"}, ensure_ascii=True))
        return 2
    if getattr(args, "preview", False):
        if not getattr(args, "checkpoint_record_file", None):
            if args.mode == "dev":
                print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_RECORD_REQUIRED"}, ensure_ascii=True))
            else:
                print("Synrail could not find a restore point to preview.")
                if root:
                    print("What to do next: create one before relying on restore semantics.")
                    print("Next command: " + shell_command(root, "save"))
            return 2
        forwarded = [
            "preview",
            "--checkpoint-record-file", args.checkpoint_record_file,
            "--target-root", args.target_root,
            "--output", args.output,
        ]
        if args.mode == "dev":
            return run_python(CHECKPOINT, forwarded)
        completed = run_python_capture(CHECKPOINT, forwarded)
        if completed.returncode != 0:
            if completed.stderr.strip():
                print(completed.stderr.strip(), file=sys.stderr)
            if completed.stdout.strip():
                print(completed.stdout.strip())
            return completed.returncode
        print_checkpoint_summary(Path(args.output), action="preview", root=root)
        return 0
    if not getattr(args, "checkpoint_record_file", None):
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_RECORD_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not find a verified restore point to restore.")
            if root:
                print("What to do next: create one while the project is in a verified working state.")
                print("Next command: " + shell_command(root, "save"))
        return 2
    forwarded = [
        "restore",
        "--checkpoint-record-file", args.checkpoint_record_file,
        "--target-root", args.target_root,
        "--output", args.output,
    ]
    if args.mode == "dev":
        code = run_python(CHECKPOINT, forwarded)
    else:
        completed = run_python_capture(CHECKPOINT, forwarded)
        if completed.returncode != 0:
            if completed.stderr.strip():
                print(completed.stderr.strip(), file=sys.stderr)
            if completed.stdout.strip():
                print(completed.stdout.strip())
            return completed.returncode
        code = 0
    if code == 0:
        sync_restored_checkpoint_artifacts(Path(args.target_root))
        if args.mode != "dev":
            print_checkpoint_summary(Path(args.output), action="restore", root=root)
    return code


def cmd_restore(args: argparse.Namespace) -> int:
    return cmd_restore_checkpoint(args)


def cmd_artifact_consistency(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "artifact_consistency"))
    if root:
        for attr, file_id in [
            ("report_file", "report"),
            ("orchestration_file", "orchestration"),
            ("run_file", "run"),
            ("repair_packet_file", "repair_packet"),
            ("repair_handoff_file", "repair_handoff"),
            ("repair_receipt_file", "repair_receipt"),
        ]:
            if not getattr(args, attr, None):
                existing = maybe_existing_alpha_file(root, file_id)
                if existing:
                    setattr(args, attr, existing)
    forwarded = [
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    for flag, value in [
        ("--report-file", args.report_file),
        ("--orchestration-file", args.orchestration_file),
        ("--run-file", args.run_file),
        ("--repair-packet-file", args.repair_packet_file),
        ("--repair-handoff-file", args.repair_handoff_file),
        ("--repair-receipt-file", args.repair_receipt_file),
    ]:
        if value:
            forwarded.extend([flag, value])
    return run_python(ARTIFACT_CONSISTENCY, forwarded)


def cmd_thin_output(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and not getattr(args, "report_file", None):
        args.report_file = str(alpha_file(root, "report"))
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "thin_output"))
    if root and not getattr(args, "repair_packet_file", None):
        existing = maybe_existing_alpha_file(root, "repair_packet")
        if existing:
            args.repair_packet_file = existing
    if root and not getattr(args, "doctor_file", None):
        existing = maybe_existing_alpha_file(root, "doctor")
        if existing:
            args.doctor_file = existing
    if root and not getattr(args, "consistency_recovery_file", None):
        existing = maybe_existing_alpha_file(root, "consistency_recovery")
        if existing:
            args.consistency_recovery_file = existing
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--mode", args.mode,
        "--output", args.output,
    ]
    for flag, value in [
        ("--repair-packet-file", args.repair_packet_file),
        ("--doctor-file", args.doctor_file),
        ("--checkpoint-record-file", args.checkpoint_record_file),
        ("--consistency-recovery-file", args.consistency_recovery_file),
    ]:
        if value:
            forwarded.extend([flag, value])
    if args.mode == "dev":
        return run_python(THIN_OUTPUT, forwarded)
    completed = run_python_capture(THIN_OUTPUT, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
    elif not getattr(args, "_suppress_summary", False):
        print_thin_output_summary(Path(args.output))
    return completed.returncode


def cmd_generate_prompt(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and not getattr(args, "report_file", None):
        existing = maybe_existing_alpha_file(root, "report")
        if existing:
            args.report_file = existing
    if root and not getattr(args, "repair_packet_file", None):
        args.repair_packet_file = str(alpha_file(root, "repair_packet"))
    if root and not getattr(args, "doctor_file", None):
        existing = maybe_existing_alpha_file(root, "doctor")
        if existing:
            args.doctor_file = existing
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "prompt"))
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if not args.repair_packet_file or not Path(args.repair_packet_file).exists():
        state_file = getattr(args, "state_file", None)
        if root and state_file and Path(state_file).expanduser().resolve().exists():
            state = load_json(Path(state_file).expanduser().resolve())
            apply_resume_output_defaults(args, state)
            ensure_repair_packet_synthesis_defaults(args)
            synthesize_repair_packet(args, state)
        if not args.repair_packet_file or not Path(args.repair_packet_file).exists():
            if args.mode == "dev":
                print(json.dumps({"result": "ERROR", "reason": "REPAIR_PACKET_REQUIRED"}, ensure_ascii=True))
                return 2
            else:
                print("Synrail does not have the next bounded repair instruction yet.")
                if root:
                    print("What to do next: run one check first so Synrail can build the bounded next step.")
                    print("Next command: " + shell_command(root, "check"))
                return 2
    forwarded = [
        "--repair-packet-file", args.repair_packet_file,
        "--output", args.output,
    ]
    if args.checkpoint_record_file:
        forwarded.extend(["--checkpoint-record-file", args.checkpoint_record_file])
    if getattr(args, "doctor_file", None):
        forwarded.extend(["--doctor-file", args.doctor_file])
    if args.mode == "dev":
        return run_python(PROMPT_BRIDGE, forwarded)
    completed = run_python_capture(PROMPT_BRIDGE, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    print_prompt_summary(Path(args.output))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
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
    bootstrap_validation = apply_bootstrap_defaults(args, root=root) if root else None
    if root and project_profile_file(root).exists():
        args.acceptance_validation_output = str(alpha_file(root, "acceptance_validation"))
        args.project_profile_file = str(project_profile_file(root))
        existing_criteria = maybe_existing_alpha_file(root, "acceptance_criteria")
        if existing_criteria:
            args.acceptance_criteria_file = existing_criteria

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
        state = load_json(Path(args.state_file))
        # Auto-detect clean_surface: during an active controlled run,
        # the workspace is expected to have uncommitted changes.
        if not getattr(args, "clean_surface", False):
            current_state = state.get("state", "")
            if current_state and current_state not in {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}:
                args.clean_surface = True
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
                    print("What is missing: Synrail is still waiting for the proof artifacts for this controlled run.")
                    print("What to do next: edit the starter proof files already placed at these paths, then rerun synrail check.")
                    for label in ["final_result", "readback", "scenario_proof"]:
                        if preferred.get(label, ""):
                            print(f"- {label}: {preferred[label]}")
                    print("Need a canonical readback shape? run synrail readback-template")
                    print("Need a canonical final_result shape? run synrail final-result-template")
                    print("Need a canonical scenario_proof shape? run synrail scenario-proof-template")
                    profile = load_project_profile(root) or {}
                    if profile.get("prefers_runtime_evidence", False):
                        print("Need a small UI/runtime verification path? run synrail runtime-helper")
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
                print("")
                print("What to fix:")
                print_prompt_summary_compact(Path(prompt_output), include_prompt=False)
    return thin_code


def cmd_thin_output_reading(args: argparse.Namespace) -> int:
    return run_python(
        THIN_OUTPUT_READING,
        [
            "--thin-output-file", args.thin_output_file,
            "--prompt-bridge-file", args.prompt_bridge_file,
            "--report-file", args.report_file,
            "--repair-packet-file", args.repair_packet_file,
            "--output", args.output,
        ],
    )


def cmd_prompt_followup(args: argparse.Namespace) -> int:
    forwarded = [
        "--repair-packet-file", args.repair_packet_file,
        "--prompt-bridge-file", args.prompt_bridge_file,
        "--output", args.output,
    ]
    if args.thin_output_file:
        forwarded.extend(["--thin-output-file", args.thin_output_file])
    return run_python(PROMPT_FOLLOWUP, forwarded)


def cmd_prompt_retry_guard(args: argparse.Namespace) -> int:
    return run_python(
        PROMPT_RETRY_GUARD,
        [
            "--packet-a-file", args.packet_a_file,
            "--prompt-a-file", args.prompt_a_file,
            "--packet-b-file", args.packet_b_file,
            "--prompt-b-file", args.prompt_b_file,
            "--output", args.output,
        ],
    )


def cmd_consistency_recovery(args: argparse.Namespace) -> int:
    forwarded = [
        "--consistency-file", args.consistency_file,
        "--output", args.output,
    ]
    if args.checkpoint_record_file:
        forwarded.extend(["--checkpoint-record-file", args.checkpoint_record_file])
    return run_python(CONSISTENCY_RECOVERY, forwarded)


def cmd_checkpoint_operator_reading(args: argparse.Namespace) -> int:
    return run_python(
        CHECKPOINT_OPERATOR_READING,
        [
            "--second-operator-file", args.second_operator_file,
            "--thin-output-file", args.thin_output_file,
            "--repair-packet-file", args.repair_packet_file,
            "--output", args.output,
        ],
    )


def cmd_consistency_recovery_prompt(args: argparse.Namespace) -> int:
    forwarded = [
        "--consistency-recovery-file", args.consistency_recovery_file,
        "--output", args.output,
    ]
    if args.thin_output_file:
        forwarded.extend(["--thin-output-file", args.thin_output_file])
    return run_python(CONSISTENCY_RECOVERY_PROMPT, forwarded)


def cmd_consistency_recovery_prompt_reading(args: argparse.Namespace) -> int:
    return run_python(
        CONSISTENCY_RECOVERY_PROMPT_READING,
        [
            "--consistency-recovery-file", args.consistency_recovery_file,
            "--prompt-file", args.prompt_file,
            "--output", args.output,
        ],
    )


def cmd_observability(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--output", args.output,
    ]
    for flag, value in [
        ("--repair-packet-file", args.repair_packet_file),
        ("--repair-receipt-file", args.repair_receipt_file),
        ("--refresh-file", args.refresh_file),
    ]:
        if value:
            forwarded.extend([flag, value])
    return run_python(OBSERVABILITY, forwarded)


def cmd_session_export(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root:
        if not getattr(args, "state_file", None):
            args.state_file = maybe_existing_alpha_file(root, "state")
        if not getattr(args, "report_file", None):
            args.report_file = maybe_existing_alpha_file(root, "report")
        if not getattr(args, "repair_packet_file", None):
            args.repair_packet_file = maybe_existing_alpha_file(root, "repair_packet")
        if not getattr(args, "repair_receipt_file", None):
            args.repair_receipt_file = maybe_existing_alpha_file(root, "repair_receipt")
        if not getattr(args, "refresh_file", None):
            args.refresh_file = maybe_existing_alpha_file(root, "refresh")
        if not getattr(args, "output", None):
            args.output = str(alpha_file(root, "session_export"))
    if not getattr(args, "state_file", None) or not getattr(args, "report_file", None):
        print(json.dumps({"result": "ERROR", "reason": "STATE_AND_REPORT_REQUIRED"}, ensure_ascii=True))
        return 2
    return cmd_observability(args)


def cmd_deploy(args: argparse.Namespace) -> int:
    """Gate deployment side effects behind accepted closure."""
    root = alpha_root_from_args(args)
    if not root:
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2

    state_file = Path(getattr(args, "state_file", "") or str(alpha_file(root, "state")))
    if not state_file.exists():
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({"result": "ERROR", "reason": "NO_STATE_FILE"}, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print("What happened: no run state found. Start a controlled run first.")
            print("What to do next: synrail start")
        return 2

    state = load_json(state_file)
    run_id = state.get("run_id", "")
    current_state = state.get("state", "")

    # Gate 1: state must be CLOSURE_ACCEPTED
    if current_state != "CLOSURE_ACCEPTED":
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({
                "result": "BLOCKED",
                "reason": "DEPLOY_REQUIRES_ACCEPTED_CLOSURE",
                "current_state": current_state,
                "run_id": run_id,
            }, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print(f"What happened: the current run is in state '{current_state}', not 'CLOSURE_ACCEPTED'.")
            print("Deployment is only allowed after Synrail has accepted the proof bundle.")
            if current_state in ("CLOSURE_REJECTED",):
                print("What to do next: fix the issues identified in the proof bundle, then rerun synrail check.")
            else:
                print("What to do next: complete the proof cycle (synrail check) until the run is accepted.")
        return 2

    # Gate 2: verify run_id matches if provided
    deploy_run_id = getattr(args, "deploy_run_id", "") or ""
    if deploy_run_id and deploy_run_id != run_id:
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({
                "result": "BLOCKED",
                "reason": "DEPLOY_RUN_ID_MISMATCH",
                "expected_run_id": deploy_run_id,
                "actual_run_id": run_id,
            }, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print(f"What happened: deploy requested for run '{deploy_run_id}' but accepted run is '{run_id}'.")
            print("What to do next: verify you are deploying the correct run.")
        return 2

    # Gate 3: verify stable target identity binding
    expected_target_identity = expected_target_identity_for_root(root)
    if not expected_target_identity:
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({
                "result": "BLOCKED",
                "reason": "DEPLOY_TARGET_IDENTITY_MISSING",
                "run_id": run_id,
            }, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print("What happened: this run does not have a stable target identity record.")
            print("What to do next: restart the controlled run and keep the target identity attested before deployment.")
        return 2

    deploy_target = (getattr(args, "deploy_target", "") or "").strip()
    if deploy_target and deploy_target != expected_target_identity:
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({
                "result": "BLOCKED",
                "reason": "DEPLOY_TARGET_MISMATCH",
                "deploy_target": deploy_target,
                "expected_target_identity": expected_target_identity,
            }, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print(f"What happened: deploy target '{deploy_target}' does not match the attested target identity '{expected_target_identity}'.")
            print("What to do next: verify you are deploying to the correct target.")
        return 2

    # All gates passed — record the deploy receipt
    deploy_receipt = {
        "schema_version": "deploy_receipt_v0",
        "result": "DEPLOY_AUTHORIZED",
        "run_id": run_id,
        "task_class": state.get("task_class", ""),
        "closure_state": current_state,
        "target_identity": expected_target_identity,
        "deploy_target": deploy_target,
        "deploy_time_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deploy_authorized_by": "synrail deploy gate",
    }

    receipt_path = alpha_file(root, "deploy_receipt")
    save_json(receipt_path, deploy_receipt)

    if getattr(args, "mode", "default") == "dev":
        print(json.dumps(deploy_receipt, ensure_ascii=True))
    else:
        print("Synrail deploy authorized.")
        print(f"Run: {run_id}")
        print(f"State: {current_state}")
        print(f"Target identity: {expected_target_identity}")
        print(f"Receipt: {display_path(receipt_path)}")
        print("You may now proceed with the deployment side effect.")

    return 0


def cmd_deploy_check(args: argparse.Namespace) -> int:
    """Check whether a valid deploy receipt exists (for use by external guards)."""
    root = alpha_root_from_args(args)
    if not root:
        print(json.dumps({"result": "BLOCKED", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2

    receipt_path = alpha_file(root, "deploy_receipt")
    if not receipt_path.exists():
        print(json.dumps({"result": "BLOCKED", "reason": "NO_DEPLOY_RECEIPT"}, ensure_ascii=True))
        return 2

    receipt = load_json(receipt_path)
    if receipt.get("result") != "DEPLOY_AUTHORIZED":
        print(json.dumps({"result": "BLOCKED", "reason": "DEPLOY_NOT_AUTHORIZED", "receipt": receipt}, ensure_ascii=True))
        return 2

    # Cross-check against current state
    state_file = Path(getattr(args, "state_file", "") or str(alpha_file(root, "state")))
    if not state_file.exists():
        print(json.dumps({"result": "BLOCKED", "reason": "NO_STATE_FILE"}, ensure_ascii=True))
        return 2

    state = load_json(state_file)
    if state.get("state", "") != "CLOSURE_ACCEPTED":
        print(json.dumps({
            "result": "BLOCKED",
            "reason": "DEPLOY_CURRENT_STATE_NOT_ACCEPTED",
            "current_state": state.get("state", ""),
        }, ensure_ascii=True))
        return 2
    if state.get("run_id", "") != receipt.get("run_id", ""):
        print(json.dumps({
            "result": "BLOCKED",
            "reason": "DEPLOY_RECEIPT_RUN_ID_STALE",
            "receipt_run_id": receipt.get("run_id", ""),
            "current_run_id": state.get("run_id", ""),
        }, ensure_ascii=True))
        return 2

    expected_target_identity = expected_target_identity_for_root(root)
    receipt_target_identity = (receipt.get("target_identity", "") or "").strip()
    if not receipt_target_identity:
        print(json.dumps({"result": "BLOCKED", "reason": "DEPLOY_RECEIPT_TARGET_IDENTITY_MISSING"}, ensure_ascii=True))
        return 2
    if not expected_target_identity:
        print(json.dumps({"result": "BLOCKED", "reason": "DEPLOY_TARGET_IDENTITY_MISSING"}, ensure_ascii=True))
        return 2
    if receipt_target_identity != expected_target_identity:
        print(json.dumps({
            "result": "BLOCKED",
            "reason": "DEPLOY_RECEIPT_TARGET_IDENTITY_STALE",
            "receipt_target_identity": receipt_target_identity,
            "current_target_identity": expected_target_identity,
        }, ensure_ascii=True))
        return 2

    print(json.dumps({"result": "OK", "deploy_receipt": receipt}, ensure_ascii=True))
    return 0


def cmd_bug_packet(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root:
        for attr, file_id in [
            ("state_file", "state"),
            ("report_file", "report"),
            ("doctor_file", "doctor"),
            ("acceptance_validation_file", "acceptance_validation"),
            ("repair_packet_file", "repair_packet"),
            ("observability_file", "observability"),
            ("thin_output_file", "thin_output"),
        ]:
            if not getattr(args, attr, None):
                value = maybe_existing_alpha_file(root, file_id)
                if value:
                    setattr(args, attr, value)
        if not getattr(args, "observability_file", None):
            session_export = maybe_existing_alpha_file(root, "session_export")
            if session_export:
                args.observability_file = session_export
        if not getattr(args, "output", None):
            args.output = str(alpha_file(root, "bug_packet"))
        if not getattr(args, "issue_output", None):
            args.issue_output = str(root / "bug_packet_issue.md")
    if not getattr(args, "state_file", None) or not getattr(args, "report_file", None):
        print("Synrail could not build the bug packet yet.")
        print("What is missing: state and report are both required.")
        return 2
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--output", args.output,
    ]
    for flag, value in [
        ("--doctor-file", args.doctor_file),
        ("--acceptance-validation-file", args.acceptance_validation_file),
        ("--repair-packet-file", args.repair_packet_file),
        ("--observability-file", args.observability_file),
        ("--thin-output-file", args.thin_output_file),
        ("--issue-output", args.issue_output),
    ]:
        if value:
            forwarded.extend([flag, value])
    code = run_python(BUG_PACKET, forwarded)
    if code == 0:
        print("Bug packet ready.")
        print("What it includes: one compact runtime summary and one issue-ready markdown body.")
        print("Use this only when telemetry export is not enough for the bug report.")
    return code


def cmd_reproducibility(args: argparse.Namespace) -> int:
    return run_python(
        REPRODUCIBILITY,
        [
            "--run-a", args.run_a,
            "--run-b", args.run_b,
            "--output", args.output,
        ],
    )


def cmd_second_operator(args: argparse.Namespace) -> int:
    return run_python(
        SECOND_OPERATOR,
        [
            "--state-file", args.state_file,
            "--repair-packet-file", args.repair_packet_file,
            "--run-file", args.run_file,
            "--output", args.output,
        ],
    )


def cmd_operator_brief(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--repair-packet-file", args.repair_packet_file,
        "--output", args.output,
    ]
    if args.doctor_file:
        forwarded.extend(["--doctor-file", args.doctor_file])
    return run_python(OPERATOR_BRIEF, forwarded)


def cmd_operator_brief_chain(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    for brief in args.brief:
        forwarded.extend(["--brief", brief])
    forwarded.extend(["--output", args.output])
    return run_python(OPERATOR_BRIEF_CHAIN, forwarded)


def cmd_operator_render(args: argparse.Namespace) -> int:
    forwarded = ["--output", args.output]
    if args.brief_file:
        forwarded.extend(["--brief-file", args.brief_file])
    if args.chain_file:
        forwarded.extend(["--chain-file", args.chain_file])
    return run_python(OPERATOR_RENDER, forwarded)


def cmd_operator_render_adoption(args: argparse.Namespace) -> int:
    return run_python(
        OPERATOR_RENDER_ADOPTION,
        [
            "--source", args.source,
            "--render", args.render,
            "--label", args.label,
            "--output", args.output,
        ],
    )


def cmd_operator_render_adoption_delta(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    for record in args.record:
        forwarded.extend(["--record", record])
    forwarded.extend(["--output", args.output])
    return run_python(OPERATOR_RENDER_ADOPTION_DELTA, forwarded)


def cmd_operator_reading(args: argparse.Namespace) -> int:
    return run_python(
        OPERATOR_READING,
        [
            "--second-operator-file", args.second_operator_file,
            "--brief-file", args.brief_file,
            "--render-file", args.render_file,
            "--label", args.label,
            "--output", args.output,
        ],
    )


def cmd_externality_pressure(args: argparse.Namespace) -> int:
    return run_python(
        EXTERNALITY_PRESSURE,
        [
            "--reproducibility-file", args.reproducibility_file,
            "--second-operator-file", args.second_operator_file,
            "--operator-reading-file", args.operator_reading_file,
            "--label", args.label,
            "--output", args.output,
        ],
    )


def cmd_repair_handoff(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    return run_python(REPAIR_HANDOFF, forwarded)


def cmd_repair_packet(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--artifact-root", args.artifact_root,
        "--output", args.output,
    ]
    for flag, value in [
        ("--doctor-run-id", getattr(args, "doctor_run_id", None)),
        ("--doctor-level", getattr(args, "doctor_level", None)),
        ("--target-path", getattr(args, "target_path", None)),
        ("--target-classification", getattr(args, "target_classification", None)),
        ("--baseline-identity", getattr(args, "baseline_identity", None)),
        ("--intended-run-class", getattr(args, "intended_run_class", None)),
        ("--execution-surface-identity", getattr(args, "execution_surface_identity", None)),
        ("--final-result", getattr(args, "final_result", None)),
        ("--prompt-identity", getattr(args, "prompt_identity", None)),
        ("--task-identity", getattr(args, "task_identity", None)),
        ("--previous-packet-file", getattr(args, "previous_packet_file", None)),
        ("--repair-handoff-file", args.repair_handoff_file),
        ("--mode-selection-receipt", args.mode_selection_receipt),
        ("--preparation-receipt-file", args.preparation_receipt_file),
        ("--repair-receipt-file", getattr(args, "repair_receipt_file", None)),
        ("--report-file", getattr(args, "report_file", None)),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--target-identity-file", args.target_identity_file),
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--refresh-output", args.refresh_output),
        ("--refresh-event-type", args.refresh_event_type),
        ("--refresh-recovery-status", args.refresh_recovery_status),
    ]:
        if value:
            forwarded.extend([flag, value])
    for enabled, flag in [
        (args.prompt_identity_ok, "--prompt-identity-ok"),
        (args.clean_surface, "--clean-surface"),
        (args.artifact_viable, "--artifact-viable"),
        (args.helper_ok, "--helper-ok"),
        (args.credentials_ok, "--credentials-ok"),
        (args.refresh_reverification_complete, "--refresh-reverification-complete"),
        (args.refresh_use_bundle, "--refresh-use-bundle"),
        (args.refresh_use_closure, "--refresh-use-closure"),
    ]:
        if enabled:
            forwarded.append(flag)
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    return run_python(REPAIR_PACKET, forwarded)


def load_repair_packet(path: Path) -> dict:
    packet = load_json(path)
    if packet.get("schema_version") != "repair_packet_v0":
        raise ValueError("repair packet must use repair_packet_v0")
    return packet


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


def cmd_orchestrate(args: argparse.Namespace) -> int:
    apply_alpha_runtime_file_defaults(args)
    if not getattr(args, "state_file", None):
        print(json.dumps({"result": "ERROR", "reason": "STATE_FILE_REQUIRED"}, ensure_ascii=True))
        return 2
    forwarded = [
        "--state-file", args.state_file,
        "--doctor-run-id", args.doctor_run_id,
        "--doctor-level", args.doctor_level,
        "--target-path", args.target_path,
        "--target-classification", args.target_classification,
        "--baseline-identity", args.baseline_identity,
        "--intended-run-class", args.intended_run_class,
        "--doctor-output", args.doctor_output,
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--bundle-output", args.bundle_output,
        "--closure-output", args.closure_output,
        "--report-output", args.report_output,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
    ]
    if getattr(args, "resume_from_state", None):
        forwarded.extend(["--resume-from-state", args.resume_from_state])
    if args.repair_handoff_file:
        forwarded.extend(["--repair-handoff-file", args.repair_handoff_file])
    if args.repair_packet_file:
        forwarded.extend(["--repair-packet-file", args.repair_packet_file])
    if args.mode_selection_receipt:
        forwarded.extend(["--mode-selection-receipt", args.mode_selection_receipt])
    for flag, value in [
        ("--repair-handoff-output", args.repair_handoff_output),
        ("--repair-packet-output", args.repair_packet_output),
        ("--repair-receipt-output", args.repair_receipt_output),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--plan-output", args.plan_output),
        ("--preparation-receipt-output", args.preparation_receipt_output),
        ("--preparation-artifact-root", args.preparation_artifact_root),
        ("--refresh-output", args.refresh_output),
        ("--observability-output", args.observability_output),
        ("--artifact-consistency-output", args.artifact_consistency_output),
        ("--refresh-event-type", args.refresh_event_type),
        ("--refresh-doctor-status", args.refresh_doctor_status),
        ("--refresh-recovery-status", args.refresh_recovery_status),
        ("--baseline-file", args.baseline_file),
        ("--synrail-file", args.synrail_file),
        ("--comparison-output", args.comparison_output),
        ("--worked-artifact-output", args.worked_artifact_output),
        ("--run-artifact-output", args.run_artifact_output),
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--prompt-identity-file", args.prompt_identity_file),
        ("--target-identity-file", args.target_identity_file),
        ("--expected-target-identity", args.execution_surface_identity),
        ("--acceptance-criteria-file", getattr(args, "acceptance_criteria_file", None)),
        ("--acceptance-validation-output", getattr(args, "acceptance_validation_output", None)),
        ("--project-profile-file", getattr(args, "project_profile_file", None)),
        ("--bootstrap-provenance-reason", getattr(args, "bootstrap_provenance_reason", None)),
    ]:
        if value:
            forwarded.extend([flag, value])
    for enabled, flag in [
        (getattr(args, "bootstrap_provenance_ok", False), "--bootstrap-provenance-ok"),
        (args.refresh_reverification_complete, "--refresh-reverification-complete"),
        (args.refresh_use_bundle, "--refresh-use-bundle"),
        (args.refresh_use_closure, "--refresh-use-closure"),
        (args.clean_surface, "--clean-surface"),
        (args.artifact_viable, "--artifact-viable"),
        (args.helper_ok, "--helper-ok"),
        (args.credentials_ok, "--credentials-ok"),
        (args.prompt_identity_ok, "--prompt-identity-ok"),
    ]:
        if enabled:
            forwarded.append(flag)
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    if getattr(args, "_capture_output", False):
        completed = run_python_capture(SPINE, ["orchestrate", *forwarded])
        if completed.returncode != 0:
            if completed.stderr.strip():
                print(completed.stderr.strip(), file=sys.stderr)
            if completed.stdout.strip():
                print(completed.stdout.strip())
        return completed.returncode
    return run_python(SPINE, ["orchestrate", *forwarded])


def cmd_resume(args: argparse.Namespace) -> int:
    apply_alpha_runtime_file_defaults(args)
    if not getattr(args, "state_file", None):
        print(json.dumps({"result": "ERROR", "reason": "STATE_FILE_REQUIRED"}, ensure_ascii=True))
        return 2
    state_path = Path(args.state_file)
    state = load_json(state_path)
    apply_bootstrap_defaults(args, root=state_path.parent)
    args.resume_from_state = state["state"]
    apply_resume_output_defaults(args, state)
    temp_runtime_files: list[str] = []
    try:
        temp_runtime_files = maybe_apply_repair_packet(args, state)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": "INVALID_REPAIR_PACKET", "detail": str(exc)}, ensure_ascii=True))
        return 2

    for attr in [
        "doctor_run_id",
        "doctor_level",
        "target_path",
        "target_classification",
        "baseline_identity",
        "intended_run_class",
        "doctor_output",
        "task_class",
        "bundle_output",
        "closure_output",
        "report_output",
        "execution_surface_identity",
    ]:
        if not getattr(args, attr, None):
            print(json.dumps({"result": "ERROR", "reason": "RESUME_CONTEXT_INCOMPLETE", "missing_field": attr}, ensure_ascii=True))
            return 2

    try:
        args._capture_output = args.mode == "default"
        code = cmd_orchestrate(args)
        if code == 0 and args.mode == "default":
            root = alpha_root_from_args(args)
            if getattr(args, "output", None):
                thin_output_path = str(Path(args.output))
            elif root:
                thin_output_path = str(alpha_file(root, "thin_output"))
            else:
                thin_output_path = str(Path(args.report_output).with_name("thin_output.json"))
            thin_args = argparse.Namespace(
                artifact_root=args.artifact_root,
                state_file=args.state_file,
                report_file=args.report_output,
                mode="default",
                output=thin_output_path,
                repair_packet_file=getattr(args, "repair_packet_file", None),
                doctor_file=getattr(args, "doctor_output", None),
                checkpoint_id=getattr(args, "checkpoint_id", None),
                checkpoint_record_file=getattr(args, "checkpoint_record_file", None),
                consistency_recovery_file=getattr(args, "consistency_recovery_file", None),
                _suppress_summary=True,
            )
            thin_code = cmd_thin_output(thin_args)
            if thin_code == 0:
                print_thin_output_summary(Path(thin_args.output))
            return thin_code
        return code
    finally:
        for temp_path in temp_runtime_files:
            Path(temp_path).unlink(missing_ok=True)


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
    parser.add_argument("--prompt-identity-file")
    parser.add_argument("--target-identity-file")
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
    p_start.add_argument("--project-root")
    p_start.add_argument("--task-identity")
    p_start.add_argument("--prompt-identity")
    p_start.add_argument("--telemetry-opt-in", action="store_true")
    p_start.add_argument("--tester-id", default="alpha_tester")
    p_start.add_argument("--mode", default="default", choices=["default", "dev"])
    p_start.add_argument("--output")
    p_start.add_argument("task_request", nargs="?")
    p_start.set_defaults(func=cmd_start)

    p_install_agent_files = sub.add_parser("install-agent-files", help="Write CLAUDE.md/GEMINI.md/AGENTS.md for agent discovery")
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
    p_check.add_argument("--prompt-identity-file")
    p_check.add_argument("--target-identity-file")
    p_check.set_defaults(func=cmd_check)

    p_status = sub.add_parser("status", aliases=["dashboard"], help="Show current run state")
    p_status.add_argument("state_file", nargs="?")
    p_status.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_status.add_argument("--json", action="store_true")
    p_status.set_defaults(func=cmd_status)

    p_explain_proof = sub.add_parser("explain-proof", aliases=["proof-explain"], help="Show what proof files are needed and why")
    p_explain_proof.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_explain_proof.add_argument("--bundle-file")
    p_explain_proof.add_argument("--json", action="store_true")
    p_explain_proof.set_defaults(func=cmd_explain_proof)

    p_final_result_template = sub.add_parser("final-result-template", help="Show template for final_result.json")
    p_final_result_template.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_final_result_template.add_argument("--output")
    p_final_result_template.set_defaults(func=cmd_final_result_template)

    p_readback_template = sub.add_parser("readback-template", help="Show template for readback.txt")
    p_readback_template.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_readback_template.add_argument("--output")
    p_readback_template.set_defaults(func=cmd_readback_template)

    p_scenario_proof_template = sub.add_parser("scenario-proof-template", help="Show template for scenario_proof.txt")
    p_scenario_proof_template.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_scenario_proof_template.add_argument("--output")
    p_scenario_proof_template.set_defaults(func=cmd_scenario_proof_template)

    p_runtime_helper = sub.add_parser("runtime-helper", help="Generate a runtime verification helper script")
    p_runtime_helper.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
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
    p_checkpoint_nested_restore.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_nested_restore.add_argument("--output")
    p_checkpoint_nested_restore.set_defaults(func=cmd_restore_checkpoint)

    p_restore = sub.add_parser("restore", help="Restore workspace from a saved checkpoint")
    p_restore.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_restore.add_argument("--checkpoint-id")
    p_restore.add_argument("--checkpoint-record-file")
    p_restore.add_argument("--target-root")
    p_restore.add_argument("--preview", action="store_true")
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
    p_artifact_consistency.add_argument("--output")
    p_artifact_consistency.add_argument("--report-file")
    p_artifact_consistency.add_argument("--orchestration-file")
    p_artifact_consistency.add_argument("--run-file")
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

    p_session_export = sub.add_parser("session-export", help="Export session replay for review")
    p_session_export.add_argument("--artifact-root")
    p_session_export.add_argument("--state-file")
    p_session_export.add_argument("--report-file")
    p_session_export.add_argument("--output")
    p_session_export.add_argument("--repair-packet-file")
    p_session_export.add_argument("--repair-receipt-file")
    p_session_export.add_argument("--refresh-file")
    p_session_export.set_defaults(func=cmd_session_export)

    p_deploy = sub.add_parser("deploy", help="Deploy with acceptance guard")
    p_deploy.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_deploy.add_argument("--state-file")
    p_deploy.add_argument("--deploy-run-id")
    p_deploy.add_argument("--deploy-target")
    p_deploy.add_argument("--mode", default="default", choices=["default", "dev"])
    p_deploy.set_defaults(func=cmd_deploy)

    p_deploy_check = sub.add_parser("deploy-check", help="Check if deployment is allowed")
    p_deploy_check.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_deploy_check.add_argument("--state-file")
    p_deploy_check.set_defaults(func=cmd_deploy_check)

    p_bug_packet = sub.add_parser("bug-packet", help="Export a bug report packet")
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
    p_thin_output.add_argument("--checkpoint-id")
    p_thin_output.add_argument("--checkpoint-record-file")
    p_thin_output.add_argument("--consistency-recovery-file")
    p_thin_output.set_defaults(func=cmd_thin_output)

    p_generate_prompt = sub.add_parser("generate-prompt", aliases=["next-step", "repair-step"], help="Show what to fix next")
    p_generate_prompt.add_argument("--artifact-root")
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
    if caught is not None:
        raise caught
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
