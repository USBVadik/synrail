#!/usr/bin/env python3
"""Extracted CLI command handlers for Synrail v0."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class TelemetryContext:
    alpha_root_from_args: Callable[..., Path | None]
    enable_telemetry: Callable[[Path, str], dict]
    default_session_replay_file: Callable[[Path], Path]
    default_issue_body_file: Callable[[Path], Path]
    export_session_replay: Callable[[Path, Path, Path | None], dict]



def cmd_telemetry_enable(
    args: argparse.Namespace,
    *,
    context: TelemetryContext,
) -> int:
    root = context.alpha_root_from_args(args, ensure=True)
    config = context.enable_telemetry(root, args.tester_id)
    print(json.dumps({"result": "OK", "telemetry_session_id": config["telemetry_session_id"]}, ensure_ascii=True))
    return 0




PolicyWriter = Callable[[Path, str, str, bool], tuple[bool, str, Path | None]]


@dataclass(frozen=True)
class AgentAdoptionContext:
    relative_artifact_root_for_project: Callable[..., str]
    preferred_synrail_command: Callable[[], str]
    preferred_synrail_fallback_command: Callable[[], str | None]
    preferred_repo_native_alpha_command: Callable[..., str | None]
    workspace_git_context: Callable[[Path], dict]
    project_prefers_runtime_evidence: Callable[[Path], bool]
    render_agent_policy_markdown: Callable[..., str]
    render_gemini_policy_markdown: Callable[..., str]
    render_claude_policy_markdown: Callable[..., str]
    render_agents_policy_block: Callable[..., str]
    render_gemini_policy_block: Callable[..., str]
    render_claude_policy_block: Callable[..., str]
    write_agent_policy_file: PolicyWriter


def emit_completed_capture(completed: object) -> None:
    stderr = getattr(completed, "stderr", "")
    stdout = getattr(completed, "stdout", "")
    if stderr and stderr.strip():
        print(stderr.strip(), file=sys.stderr)
    if stdout and stdout.strip():
        print(stdout.strip())


def build_agent_policy_context(
    args: argparse.Namespace,
    *,
    context: AgentAdoptionContext,
) -> dict[str, object]:
    project_root = Path(args.project_root or ".").resolve()
    artifact_root = context.relative_artifact_root_for_project(
        project_root=project_root,
        artifact_root=args.artifact_root,
    )
    command = context.preferred_synrail_command()
    fallback_command = context.preferred_synrail_fallback_command()
    repo_native_alpha_command = context.preferred_repo_native_alpha_command(project_root=project_root)
    git_context = context.workspace_git_context(project_root)
    workspace_isolation_note = git_context.get("workspace_isolation_note", "")
    prefer_runtime_helper = context.project_prefers_runtime_evidence(project_root)
    return {
        "project_root": project_root,
        "artifact_root": artifact_root,
        "command": command,
        "fallback_command": fallback_command,
        "repo_native_alpha_command": repo_native_alpha_command,
        "workspace_isolation_note": workspace_isolation_note,
        "prefer_runtime_helper": prefer_runtime_helper,
    }


def run_install_agent_files_command(
    args: argparse.Namespace,
    *,
    context: AgentAdoptionContext,
) -> int:
    policy_context = build_agent_policy_context(
        args,
        context=context,
    )
    project_root = policy_context["project_root"]
    artifact_root = policy_context["artifact_root"]
    command = policy_context["command"]
    fallback_command = policy_context["fallback_command"]
    repo_native_alpha_command = policy_context["repo_native_alpha_command"]
    workspace_isolation_note = policy_context["workspace_isolation_note"]
    prefer_runtime_helper = policy_context["prefer_runtime_helper"]
    agents_path = project_root / "AGENTS.md"
    gemini_path = project_root / "GEMINI.md"
    claude_path = project_root / "CLAUDE.md"

    agents_content = context.render_agent_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    gemini_content = context.render_gemini_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    claude_content = context.render_claude_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    agents_block = context.render_agents_policy_block(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    gemini_block = context.render_gemini_policy_block(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    claude_block = context.render_claude_policy_block(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )

    agents_written, agents_state, agents_backup = context.write_agent_policy_file(
        agents_path,
        agents_content,
        managed_block=agents_block,
        force=args.force,
    )
    gemini_written, gemini_state, gemini_backup = context.write_agent_policy_file(
        gemini_path,
        gemini_content,
        managed_block=gemini_block,
        force=args.force,
    )
    claude_written, claude_state, claude_backup = context.write_agent_policy_file(
        claude_path,
        claude_content,
        managed_block=claude_block,
        force=args.force,
    )

    print("Agent adoption files are ready.")
    print(f"Project root: {project_root}")
    print(f"Artifact root hint: {artifact_root}")
    print(f"Synrail command: {command}")
    if fallback_command:
        print(f"Synrail fallback for this machine: {fallback_command}")
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


def cmd_install_agent_files(
    args: argparse.Namespace,
    *,
    context: AgentAdoptionContext,
) -> int:
    return run_install_agent_files_command(
        args,
        context=context,
    )


def cmd_init_agent(
    args: argparse.Namespace,
    *,
    context: AgentAdoptionContext,
) -> int:
    agent = (getattr(args, "agent", "") or "").strip().lower()
    if agent in {"codex", "cursor"}:
        return run_install_agent_files_command(
            args,
            context=context,
        )

    policy_context = build_agent_policy_context(
        args,
        context=context,
    )
    project_root = policy_context["project_root"]
    artifact_root = policy_context["artifact_root"]
    command = policy_context["command"]
    fallback_command = policy_context["fallback_command"]
    repo_native_alpha_command = policy_context["repo_native_alpha_command"]
    workspace_isolation_note = policy_context["workspace_isolation_note"]
    prefer_runtime_helper = policy_context["prefer_runtime_helper"]

    file_name = "CLAUDE.md" if agent == "claude" else "GEMINI.md"
    path = project_root / file_name
    if agent == "claude":
        full_content = context.render_claude_policy_markdown(
            artifact_root=artifact_root,
            command=command,
            fallback_command=fallback_command,
            repo_native_alpha_command=repo_native_alpha_command,
            workspace_isolation_note=workspace_isolation_note,
            prefer_runtime_helper=prefer_runtime_helper,
        )
        managed_block = context.render_claude_policy_block(
            artifact_root=artifact_root,
            command=command,
            fallback_command=fallback_command,
            repo_native_alpha_command=repo_native_alpha_command,
            workspace_isolation_note=workspace_isolation_note,
            prefer_runtime_helper=prefer_runtime_helper,
        )
    else:
        full_content = context.render_gemini_policy_markdown(
            artifact_root=artifact_root,
            command=command,
            fallback_command=fallback_command,
            repo_native_alpha_command=repo_native_alpha_command,
            workspace_isolation_note=workspace_isolation_note,
            prefer_runtime_helper=prefer_runtime_helper,
        )
        managed_block = context.render_gemini_policy_block(
            artifact_root=artifact_root,
            command=command,
            fallback_command=fallback_command,
            repo_native_alpha_command=repo_native_alpha_command,
            workspace_isolation_note=workspace_isolation_note,
            prefer_runtime_helper=prefer_runtime_helper,
        )

    written, state, backup = context.write_agent_policy_file(
        path,
        full_content,
        managed_block=managed_block,
        force=args.force,
    )

    print(f"Agent onboarding is ready for {agent}.")
    print(f"Project root: {project_root}")
    print(f"Artifact root hint: {artifact_root}")
    print(f"Synrail command: {command}")
    if fallback_command:
        print(f"Synrail fallback for this machine: {fallback_command}")
    if workspace_isolation_note:
        print(f"Workspace note: {workspace_isolation_note}")
    if prefer_runtime_helper:
        print(f"Runtime note: use `{command} runtime-helper` for a small curl or template-render verification path.")
    print(f"{file_name}: {state}")
    if backup:
        print(f"{file_name} backup: {backup}")
    if state in {"appended", "updated"}:
        print(f"What to do next: run `synrail` in this repo so the dashboard can show the current state, then review and commit the managed Synrail block in {file_name} if the wording fits the repo.")
    elif written:
        print(f"What to do next: run `synrail` in this repo. Commit {file_name} if you want local {agent} runs to keep discovering Synrail before editing.")
    else:
        print(f"What to do next: run `synrail` in this repo. Keep {file_name} committed so local {agent} runs continue discovering the same Synrail entrypoint.")
    return 0


def render_github_action_ci_adapter(*, artifact_root: str, invocation_command: str) -> str:
    return "\n".join(
        [
            "name: Synrail check",
            "description: Run Synrail check through a bounded repo-local adapter path",
            "inputs:",
            "  artifact-root:",
            "    description: Artifact root passed to Synrail check",
            "    required: false",
            f"    default: {artifact_root}",
            "runs:",
            "  using: composite",
            "  steps:",
            "    - name: Run Synrail check",
            "      shell: bash",
            "      run: |",
            f"        {invocation_command} check --artifact-root \"${{{{ inputs.artifact-root }}}}\"",
        ]
    ) + "\n"


def render_github_action_ci_workflow(*, artifact_root: str) -> str:
    return "\n".join(
        [
            "name: Synrail check",
            "on:",
            "  push:",
            "  pull_request:",
            "  workflow_dispatch:",
            "permissions:",
            "  contents: read",
            "jobs:",
            "  synrail-check:",
            "    runs-on: ubuntu-latest",
            "    steps:",
            "      - name: Checkout repo",
            "        uses: actions/checkout@v4",
            "      - name: Set up Python",
            "        uses: actions/setup-python@v5",
            "        with:",
            "          python-version: \"3.11\"",
            "      - name: Upgrade pip",
            "        run: python3 -m pip install --upgrade pip",
            "      - name: Install Synrail dev dependencies",
            "        run: make install-dev",
            "      - name: Run unit tests",
            "        run: make test",
            "      - name: Compile Python files",
            "        run: make compile",
            "      - name: Run Ruff",
            "        run: make lint",
            "      - name: Run coverage",
            "        run: make coverage",
            "      - name: Run Synrail composite action",
            "        uses: ./.github/actions/synrail-check",
            "        with:",
            f"          artifact-root: {artifact_root}",
        ]
    ) + "\n"


def render_security_hygiene_workflow() -> str:
    return "\n".join(
        [
            "name: Security hygiene",
            "on:",
            "  push:",
            "  pull_request:",
            "  workflow_dispatch:",
            "permissions:",
            "  contents: read",
            "jobs:",
            "  security-hygiene:",
            "    runs-on: ubuntu-latest",
            "    steps:",
            "      - name: Checkout repo",
            "        uses: actions/checkout@v4",
            "      - name: Set up Python",
            "        uses: actions/setup-python@v5",
            "        with:",
            "          python-version: \"3.11\"",
            "      - name: Upgrade pip",
            "        run: python3 -m pip install --upgrade pip",
            "      - name: Install Synrail dev dependencies",
            "        run: make install-dev",
            "      - name: Run unit tests",
            "        run: make test",
            "      - name: Compile Python files",
            "        run: make compile",
            "      - name: Run Ruff",
            "        run: make lint",
            "      - name: Run coverage",
            "        run: make coverage",
            "      - name: Audit Python dependencies",
            "        run: make audit",
            "      - name: Check repository text for common secret patterns",
            "        shell: bash",
            "        run: |",
            "          python3 - <<'PY'",
            "          from pathlib import Path",
            "          import re",
            "          import sys",
            "",
            "          patterns = [",
            "              re.compile(r\"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY\"),",
            "              re.compile(r\"ghp_[A-Za-z0-9]{20,}\"),",
            "              re.compile(r\"github_pat_[A-Za-z0-9_]{20,}\"),",
            "              re.compile(r\"AKIA[0-9A-Z]{16}\"),",
            "              re.compile(r\"AIza[A-Za-z0-9_-]{20,}\"),",
            "              re.compile(r\"xox[baprs]-[A-Za-z0-9-]{10,}\"),",
            "          ]",
            "          excluded_dirs = {\".git\", \".venv\", \"__pycache__\"}",
            "          excluded_suffixes = {\".pyc\"}",
            "",
            "          for path in Path('.').rglob('*'):",
            "              if not path.is_file():",
            "                  continue",
            "              if any(part in excluded_dirs or part.startswith(\".tmp-\") for part in path.parts):",
            "                  continue",
            "              if path.suffix in excluded_suffixes:",
            "                  continue",
            "              try:",
            "                  text = path.read_text(errors='ignore')",
            "              except OSError:",
            "                  continue",
            "              for pattern in patterns:",
            "                  if pattern.search(text):",
            "                      print(f'Potential secret pattern detected: {path}')",
            "                      sys.exit(1)",
            "          PY",
        ]
    ) + "\n"


def inspect_ci_file(path: Path, content: str) -> str:
    if not path.exists():
        return "missing"
    return "unchanged" if path.read_text() == content else "different"


def write_ci_file(path: Path, content: str, *, force: bool) -> tuple[bool, str, Path | None]:
    if path.exists():
        current = path.read_text()
        if current == content:
            return False, "unchanged", None
        if not force:
            return False, "blocked", None
        timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = path.with_name(f"{path.name}.synrail.bak.{timestamp}")
        backup_path.write_text(current)
        path.write_text(content)
        return True, "updated", backup_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return True, "written", None


@dataclass(frozen=True)
class CiPreflightContext:
    relative_artifact_root_for_project: Callable[..., str]
    preferred_repo_native_alpha_command: Callable[..., str | None]
    current_project_root: Callable[[], Path]
    preferred_synrail_command: Callable[[], str]
    preferred_synrail_fallback_command: Callable[[], str | None]
    workspace_git_context: Callable[[Path], dict]


def cmd_init_ci(
    args: argparse.Namespace,
    *,
    context: CiPreflightContext,
) -> int:
    project_root = Path(args.project_root or ".").resolve()
    artifact_root = context.relative_artifact_root_for_project(
        project_root=project_root,
        artifact_root=args.artifact_root,
    )
    invocation_command = context.preferred_repo_native_alpha_command(project_root=project_root) or "synrail"
    adapter_path = project_root / ".github" / "actions" / "synrail-check" / "action.yml"
    adapter_content = render_github_action_ci_adapter(
        artifact_root=artifact_root,
        invocation_command=invocation_command,
    )
    workflow_enabled = bool(getattr(args, "workflow", False))
    workflow_path = project_root / ".github" / "workflows" / "synrail-check.yml"
    workflow_content = render_github_action_ci_workflow(artifact_root=artifact_root)

    adapter_inspection = inspect_ci_file(adapter_path, adapter_content)
    if adapter_inspection == "different" and not args.force:
        print("GitHub Action CI adapter already exists with different contents.")
        print(f"Adapter path: {adapter_path}")
        print("What to do next: review the existing adapter and rerun with --force if you want Synrail to replace it with the bounded check adapter.")
        return 2
    if workflow_enabled:
        workflow_inspection = inspect_ci_file(workflow_path, workflow_content)
        if workflow_inspection == "different" and not args.force:
            print("GitHub Actions workflow already exists with different contents.")
            print(f"Workflow path: {workflow_path}")
            print("What to do next: review the existing workflow and rerun with --force if you want Synrail to replace it with the bounded workflow scaffold.")
            return 2

    adapter_written, adapter_state, adapter_backup = write_ci_file(adapter_path, adapter_content, force=args.force)
    workflow_written = False
    workflow_state = ""
    workflow_backup: Path | None = None
    if workflow_enabled:
        workflow_written, workflow_state, workflow_backup = write_ci_file(workflow_path, workflow_content, force=args.force)

    print("GitHub Action CI adapter is ready.")
    print(f"Project root: {project_root}")
    print(f"Adapter path: {adapter_path}")
    print("Adapter scope: bounded check-only GitHub composite action")
    print(f"Artifact root default: {artifact_root}")
    print(f"Invocation path: {invocation_command} check --artifact-root \"${{{{ inputs.artifact-root }}}}\"")
    print("Workflow call site: uses: ./.github/actions/synrail-check")
    if adapter_backup:
        print(f"Adapter backup: {adapter_backup}")
    if workflow_enabled:
        print("GitHub Actions workflow is ready.")
        print(f"Workflow path: {workflow_path}")
        print("Workflow triggers: push, pull_request, workflow_dispatch")
        print("Workflow behavior: checks out the repo and runs the local composite action without mutating proof artifacts by default.")
        if workflow_backup:
            print(f"Workflow backup: {workflow_backup}")
        if adapter_state == "updated" or workflow_state == "updated":
            print("What to do next: commit the refreshed adapter and workflow so GitHub Actions can run the bounded Synrail lane.")
        elif adapter_written or workflow_written:
            print("What to do next: commit the adapter and workflow so GitHub Actions can run the bounded Synrail lane.")
        else:
            print("What to do next: keep the existing adapter and workflow committed so GitHub Actions continues using the bounded Synrail lane.")
        return 0

    print("Adapter only: add a workflow that calls uses: ./.github/actions/synrail-check, or rerun with --workflow.")
    if adapter_state == "updated":
        print("What to do next: commit the refreshed adapter and add a workflow with `uses: ./.github/actions/synrail-check`, or rerun with `--workflow`.")
    elif adapter_written:
        print("What to do next: commit the adapter and add a workflow with `uses: ./.github/actions/synrail-check`, or rerun with `--workflow`.")
    else:
        print("What to do next: call the existing adapter from a workflow with `uses: ./.github/actions/synrail-check`, or rerun with `--workflow`.")
    return 0


def cmd_telemetry_export(
    args: argparse.Namespace,
    *,
    context: TelemetryContext,
) -> int:
    root = context.alpha_root_from_args(args)
    if not root:
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2
    if not getattr(args, "output", None):
        args.output = str(context.default_session_replay_file(root))
    if not getattr(args, "issue_output", None):
        args.issue_output = str(context.default_issue_body_file(root))
    try:
        record = context.export_session_replay(root, Path(args.output), Path(args.issue_output))
    except ValueError:
        print("Synrail could not export feedback yet.")
        print("What happened: telemetry is not enabled for this artifact root.")
        print("What to do next: rerun synrail start with --telemetry-opt-in or use synrail telemetry enable before exporting feedback.")
        return 2
    print("Feedback export ready.")
    print("What it includes: one session replay and one issue-ready summary.")
    print(f"Command count captured: {record['command_count']}")
    print("Use this when you want to send back a non-green run without hand-assembling artifacts.")
    return 0


@dataclass(frozen=True)
class SessionExportBugPacketContext:
    alpha_root_from_args: Callable[..., Path | None]
    maybe_existing_alpha_file: Callable[[Path | None, str], str | None]
    alpha_file: Callable[[Path, str], Path]
    cmd_observability: Callable[[argparse.Namespace], int]
    run_python: Callable[[Path, list[str]], int]
    bug_packet_script: Path


@dataclass(frozen=True)
class ReproducibilityOperatorBriefContext:
    run_python: Callable[[Path, list[str]], int]
    reproducibility_script: Path
    second_operator_script: Path
    operator_brief_script: Path


@dataclass(frozen=True)
class OperatorBriefRenderReadingContext:
    run_python: Callable[[Path, list[str]], int]
    operator_brief_chain_script: Path
    operator_render_script: Path
    operator_reading_script: Path


@dataclass(frozen=True)
class OperatorRenderAdoptionPressureContext:
    run_python: Callable[[Path, list[str]], int]
    operator_render_adoption_script: Path
    operator_render_adoption_delta_script: Path
    externality_pressure_script: Path


@dataclass(frozen=True)
class RepairBundleClosureContext:
    run_python: Callable[[Path, list[str]], int]
    repair_handoff_script: Path
    bundle_script: Path
    closure_script: Path


@dataclass(frozen=True)
class ApplyRefreshValidateContext:
    run_python: Callable[[Path, list[str]], int]
    spine_script: Path
    refresh_script: Path
    validate_script: Path


@dataclass(frozen=True)
class DoctorCompareSubstituteContext:
    alpha_root_from_args: Callable[..., Path | None]
    current_project_root: Callable[[], Path]
    validate_root_within_project: Callable[..., None]
    validate_doctor_paths: Callable[..., None]
    load_json: Callable[[Path], dict]
    comparison_harness_for_inputs: Callable[[str, str], Path]
    run_python: Callable[[Path, list[str]], int]
    doctor_script: Path
    substitute_pressure_script: Path


@dataclass(frozen=True)
class HybridModeContext:
    run_python: Callable[[Path, list[str]], int]
    hybrid_status_script: Path
    mode_selector_script: Path
    mode_receipt_script: Path


@dataclass(frozen=True)
class ProofPreparationCostContext:
    run_python: Callable[[Path, list[str]], int]
    proof_plan_script: Path
    preparation_receipt_script: Path
    governed_cost_script: Path


@dataclass(frozen=True)
class CheckpointCreateSaveVerifyContext:
    alpha_root_from_args: Callable[..., Path | None]
    checkpoint_record_file: Callable[[Path, str], Path]
    checkpoint_root: Callable[[Path, str], Path]
    alpha_file: Callable[[Path, str], Path]
    maybe_existing_alpha_file: Callable[[Path | None, str], str | None]
    checkpoint_verify_file: Callable[[Path, str], Path]
    discover_checkpoint_record: Callable[[Path | None, str | None], str | None]
    run_python: Callable[[Path, list[str]], int]
    run_python_capture: Callable[[Path, list[str]], object]
    print_checkpoint_summary: Callable[[Path, str, Path | None], None]
    print_save_summary: Callable[[Path, Path, Path | None], None]
    shell_command: Callable[[Path, str], str]
    checkpoint_script: Path


@dataclass(frozen=True)
class RestoreConsistencyThinContext:
    alpha_root_from_args: Callable[..., Path | None]
    discover_checkpoint_record: Callable[[Path | None, str | None], str | None]
    alpha_file: Callable[[Path, str], Path]
    load_json: Callable[[Path], dict]
    maybe_existing_alpha_file: Callable[[Path | None, str], str | None]
    run_python: Callable[[Path, list[str]], int]
    run_python_capture: Callable[[Path, list[str]], object]
    print_checkpoint_summary: Callable[[Path, str, Path | None], None]
    shell_command: Callable[[Path, str], str]
    sync_restored_checkpoint_artifacts: Callable[[Path], None]
    print_thin_output_summary: Callable[[Path], None]
    checkpoint_script: Path
    artifact_consistency_script: Path
    thin_output_script: Path


@dataclass(frozen=True)
class PromptReadingFollowupContext:
    alpha_root_from_args: Callable[..., Path | None]
    alpha_file: Callable[[Path, str], Path]
    maybe_existing_alpha_file: Callable[[Path | None, str], str | None]
    discover_checkpoint_record: Callable[[Path | None, str | None], str | None]
    load_json: Callable[[Path], dict]
    apply_resume_output_defaults: Callable[..., None]
    ensure_repair_packet_synthesis_defaults: Callable[[argparse.Namespace], None]
    synthesize_repair_packet: Callable[[argparse.Namespace, dict], None]
    run_python: Callable[[Path, list[str]], int]
    run_python_capture: Callable[[Path, list[str]], object]
    maybe_materialize_requested_fallback_surface: Callable[..., str | None]
    print_prompt_summary: Callable[[Path], None]
    load_project_profile: Callable[[Path | None], dict | None]
    plain_shell_command: Callable[..., str]
    prompt_bridge_script: Path
    thin_output_reading_script: Path
    prompt_followup_script: Path


@dataclass(frozen=True)
class RetryRecoveryReadingContext:
    run_python: Callable[[Path, list[str]], int]
    prompt_retry_guard_script: Path
    consistency_recovery_script: Path
    checkpoint_operator_reading_script: Path


@dataclass(frozen=True)
class RecoveryPromptObservabilityContext:
    run_python: Callable[[Path, list[str]], int]
    consistency_recovery_prompt_script: Path
    consistency_recovery_prompt_reading_script: Path
    observability_script: Path


def cmd_session_export(
    args: argparse.Namespace,
    *,
    context: SessionExportBugPacketContext,
) -> int:
    root = context.alpha_root_from_args(args)
    if root:
        if not getattr(args, "state_file", None):
            args.state_file = context.maybe_existing_alpha_file(root, "state")
        if not getattr(args, "report_file", None):
            args.report_file = context.maybe_existing_alpha_file(root, "report")
        if not getattr(args, "repair_packet_file", None):
            args.repair_packet_file = context.maybe_existing_alpha_file(root, "repair_packet")
        if not getattr(args, "repair_receipt_file", None):
            args.repair_receipt_file = context.maybe_existing_alpha_file(root, "repair_receipt")
        if not getattr(args, "refresh_file", None):
            args.refresh_file = context.maybe_existing_alpha_file(root, "refresh")
        if not getattr(args, "output", None):
            args.output = str(context.alpha_file(root, "session_export"))
    if not getattr(args, "state_file", None) or not getattr(args, "report_file", None):
        print(json.dumps({"result": "ERROR", "reason": "STATE_AND_REPORT_REQUIRED"}, ensure_ascii=True))
        return 2
    return context.cmd_observability(args)


def cmd_bug_packet(
    args: argparse.Namespace,
    *,
    context: SessionExportBugPacketContext,
) -> int:
    root = context.alpha_root_from_args(args)
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
                value = context.maybe_existing_alpha_file(root, file_id)
                if value:
                    setattr(args, attr, value)
        if not getattr(args, "observability_file", None):
            session_export = context.maybe_existing_alpha_file(root, "session_export")
            if session_export:
                args.observability_file = session_export
        if not getattr(args, "output", None):
            args.output = str(context.alpha_file(root, "bug_packet"))
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
    code = context.run_python(context.bug_packet_script, forwarded)
    if code == 0:
        print("Bug packet ready.")
        print("What it includes: one compact runtime summary and one issue-ready markdown body.")
        print("Use this only when telemetry export is not enough for the bug report.")
    return code



def cmd_reproducibility(
    args: argparse.Namespace,
    *,
    context: ReproducibilityOperatorBriefContext,
) -> int:
    return context.run_python(
        context.reproducibility_script,
        [
            "--run-a", args.run_a,
            "--run-b", args.run_b,
            "--output", args.output,
        ],
    )



def cmd_second_operator(
    args: argparse.Namespace,
    *,
    context: ReproducibilityOperatorBriefContext,
) -> int:
    return context.run_python(
        context.second_operator_script,
        [
            "--state-file", args.state_file,
            "--repair-packet-file", args.repair_packet_file,
            "--run-file", args.run_file,
            "--output", args.output,
        ],
    )



def cmd_operator_brief(
    args: argparse.Namespace,
    *,
    context: ReproducibilityOperatorBriefContext,
) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--repair-packet-file", args.repair_packet_file,
        "--output", args.output,
    ]
    if args.doctor_file:
        forwarded.extend(["--doctor-file", args.doctor_file])
    return context.run_python(context.operator_brief_script, forwarded)



def cmd_operator_brief_chain(
    args: argparse.Namespace,
    *,
    context: OperatorBriefRenderReadingContext,
) -> int:
    forwarded: list[str] = []
    for brief in args.brief:
        forwarded.extend(["--brief", brief])
    forwarded.extend(["--output", args.output])
    return context.run_python(context.operator_brief_chain_script, forwarded)



def cmd_operator_render(
    args: argparse.Namespace,
    *,
    context: OperatorBriefRenderReadingContext,
) -> int:
    forwarded = ["--output", args.output]
    if args.brief_file:
        forwarded.extend(["--brief-file", args.brief_file])
    if args.chain_file:
        forwarded.extend(["--chain-file", args.chain_file])
    return context.run_python(context.operator_render_script, forwarded)



def cmd_operator_render_adoption(
    args: argparse.Namespace,
    *,
    context: OperatorRenderAdoptionPressureContext,
) -> int:
    return context.run_python(
        context.operator_render_adoption_script,
        [
            "--source", args.source,
            "--render", args.render,
            "--label", args.label,
            "--output", args.output,
        ],
    )



def cmd_operator_render_adoption_delta(
    args: argparse.Namespace,
    *,
    context: OperatorRenderAdoptionPressureContext,
) -> int:
    forwarded: list[str] = []
    for record in args.record:
        forwarded.extend(["--record", record])
    forwarded.extend(["--output", args.output])
    return context.run_python(context.operator_render_adoption_delta_script, forwarded)



def cmd_operator_reading(
    args: argparse.Namespace,
    *,
    context: OperatorBriefRenderReadingContext,
) -> int:
    return context.run_python(
        context.operator_reading_script,
        [
            "--second-operator-file", args.second_operator_file,
            "--brief-file", args.brief_file,
            "--render-file", args.render_file,
            "--label", args.label,
            "--output", args.output,
        ],
    )



def cmd_externality_pressure(
    args: argparse.Namespace,
    *,
    context: OperatorRenderAdoptionPressureContext,
) -> int:
    return context.run_python(
        context.externality_pressure_script,
        [
            "--reproducibility-file", args.reproducibility_file,
            "--second-operator-file", args.second_operator_file,
            "--operator-reading-file", args.operator_reading_file,
            "--label", args.label,
            "--output", args.output,
        ],
    )



def cmd_repair_handoff(
    args: argparse.Namespace,
    *,
    context: RepairBundleClosureContext,
) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    return context.run_python(context.repair_handoff_script, forwarded)


def cmd_bundle_check(
    args: argparse.Namespace,
    *,
    context: RepairBundleClosureContext,
) -> int:
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
        ("--doctor-file", args.doctor_file),
        ("--state-file", getattr(args, "state_file", None)),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    return context.run_python(context.bundle_script, forwarded)


def cmd_apply_bundle(
    args: argparse.Namespace,
    *,
    run_python: Callable[[Path, list[str]], int],
    spine_script: Path,
) -> int:
    return run_python(spine_script, ["apply-bundle", args.state_file, args.bundle_file])


def cmd_closure(
    args: argparse.Namespace,
    *,
    context: RepairBundleClosureContext,
) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--bundle-file", args.bundle_file,
        "--output", args.output,
    ]
    if args.update_state:
        forwarded.append("--update-state")
    return context.run_python(context.closure_script, forwarded)


def cmd_apply_closure(
    args: argparse.Namespace,
    *,
    context: ApplyRefreshValidateContext,
) -> int:
    return context.run_python(context.spine_script, ["apply-closure", args.state_file, args.closure_file])


def cmd_refresh(
    args: argparse.Namespace,
    *,
    context: ApplyRefreshValidateContext,
) -> int:
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
    return context.run_python(context.refresh_script, forwarded)


def cmd_validate(
    args: argparse.Namespace,
    *,
    context: ApplyRefreshValidateContext,
) -> int:
    return context.run_python(context.validate_script, ["--schema", args.schema, "--document", args.document])


def cmd_doctor(
    args: argparse.Namespace,
    *,
    context: DoctorCompareSubstituteContext,
) -> int:
    artifact_root = context.alpha_root_from_args(args) or Path(args.output).expanduser().resolve().parent
    project_root = context.current_project_root()
    context.validate_root_within_project(
        "artifact_root" if getattr(args, "artifact_root", None) else "output",
        getattr(args, "artifact_root", None) or args.output,
        root=artifact_root,
        project_root=project_root,
        artifact_root=artifact_root,
    )
    artifact_root.mkdir(parents=True, exist_ok=True)
    context.validate_doctor_paths(args, artifact_root=artifact_root, project_root=project_root)
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
        ("--coverage-profile-file", getattr(args, "coverage_profile_file", None)),
        ("--coverage-corpus-file", getattr(args, "coverage_corpus_file", None)),
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
    return context.run_python(context.doctor_script, forwarded)


GIT_MISSING_MESSAGE = (
    "Git is not installed. Synrail can still use structured diff_provenance, but git_diff and restore coverage will be weaker. Install git for the normal path."
)


def _preflight_wrapper_available(project_root: Path) -> bool:
    for candidate in [project_root / ".venv" / "bin" / "synrail"]:
        if candidate.exists() and candidate.is_file():
            return True
    return shutil.which("synrail") is not None


def _artifact_root_writable(artifact_root: Path) -> bool:
    try:
        artifact_root.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=artifact_root, delete=True):
            pass
        return True
    except OSError:
        return False


def _parent_git_repo_above(project_root: Path, current_dir: Path, workspace_git_context: Callable[[Path], dict]) -> str:
    current_context = workspace_git_context(current_dir)
    project_context = workspace_git_context(project_root)
    for context in [current_context, project_context]:
        parent_root = (context.get("parent_git_root", "") or "").strip()
        if parent_root:
            return parent_root
    return ""


def build_preflight_report(
    *,
    project_root: Path,
    current_dir: Path,
    artifact_root: Path,
    preferred_synrail_command: Callable[[], str],
    preferred_synrail_fallback_command: Callable[[], str | None],
    preferred_repo_native_alpha_command: Callable[..., str | None],
    workspace_git_context: Callable[[Path], dict],
) -> dict[str, object]:
    git_path = shutil.which("git")
    git_available = git_path is not None
    current_git_context = workspace_git_context(current_dir)
    current_directory_is_git_repo = current_git_context.get("workspace_git_mode", "") in {"workspace_git_root", "nested_parent_git"}
    parent_git_root = _parent_git_repo_above(project_root, current_dir, workspace_git_context)
    repo_native_alpha_command = preferred_repo_native_alpha_command(project_root=project_root)
    wrapper_command = preferred_synrail_command()
    fallback_command = preferred_synrail_fallback_command()
    wrapper_available = _preflight_wrapper_available(project_root)
    artifact_root_writable = _artifact_root_writable(artifact_root)
    report = {
        "status": "PASS",
        "project_root": str(project_root),
        "current_directory": str(current_dir),
        "python_version": sys.version.split()[0],
        "git": {
            "available": git_available,
            "path": git_path or "",
            "message": "" if git_available else GIT_MISSING_MESSAGE,
        },
        "current_directory_git_repo": current_directory_is_git_repo,
        "parent_git_repo_above_project_root": bool(parent_git_root),
        "parent_git_root": parent_git_root,
        "artifact_root": str(artifact_root),
        "artifact_root_writable": artifact_root_writable,
        "synrail_wrapper": {
            "available": wrapper_available,
            "command": wrapper_command,
            "fallback_command": fallback_command or "",
        },
        "repo_native_alpha_fallback": {
            "available": repo_native_alpha_command is not None,
            "command": repo_native_alpha_command or "",
        },
    }
    if not artifact_root_writable:
        report["status"] = "FAIL"
    return report


def _print_preflight_human(report: dict[str, object]) -> None:
    git = report["git"]
    wrapper = report["synrail_wrapper"]
    alpha_fallback = report["repo_native_alpha_fallback"]
    print("Synrail preflight")
    print(f"Python version: {report['python_version']}")
    if git["available"]:
        print(f"Git: available ({git['path']})")
    else:
        print(GIT_MISSING_MESSAGE)
    print(f"Current directory is a git repo: {'yes' if report['current_directory_git_repo'] else 'no'}")
    print(
        "Parent git repo above project root: "
        + (str(report["parent_git_root"]) if report["parent_git_repo_above_project_root"] else "no")
    )
    print(f"Artifact root: {report['artifact_root']}")
    print(f"Artifact root writable: {'yes' if report['artifact_root_writable'] else 'no'}")
    print(f"Synrail wrapper available: {'yes' if wrapper['available'] else 'no'}")
    print(f"Synrail command: {wrapper['command']}")
    if wrapper["fallback_command"]:
        print(f"Synrail fallback command: {wrapper['fallback_command']}")
    print(f"Repo-native alpha fallback available: {'yes' if alpha_fallback['available'] else 'no'}")
    if alpha_fallback["command"]:
        print(f"Repo-native alpha command: {alpha_fallback['command']}")
    if report["status"] != "PASS":
        print("What to do next: fix the failing local preflight surface before relying on the normal install path.")


def cmd_preflight(
    args: argparse.Namespace,
    *,
    context: CiPreflightContext,
) -> int:
    current_dir = context.current_project_root()
    project_root = Path(getattr(args, "project_root", "") or current_dir).expanduser().resolve()
    artifact_root = Path(getattr(args, "artifact_root", "") or (project_root / ".synrail")).expanduser().resolve()
    report = build_preflight_report(
        project_root=project_root,
        current_dir=current_dir,
        artifact_root=artifact_root,
        preferred_synrail_command=context.preferred_synrail_command,
        preferred_synrail_fallback_command=context.preferred_synrail_fallback_command,
        preferred_repo_native_alpha_command=context.preferred_repo_native_alpha_command,
        workspace_git_context=context.workspace_git_context,
    )
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        _print_preflight_human(report)
    return 0 if report["status"] == "PASS" else 2


def cmd_compare(
    args: argparse.Namespace,
    *,
    context: DoctorCompareSubstituteContext,
) -> int:
    try:
        baseline = context.load_json(Path(args.baseline_file))
        harness = context.comparison_harness_for_inputs(args.baseline_file, args.synrail_file)
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
    return context.run_python(harness, forwarded)


def cmd_substitute_pressure(
    args: argparse.Namespace,
    *,
    context: DoctorCompareSubstituteContext,
) -> int:
    forwarded: list[str] = []
    for record in args.record:
        forwarded.extend(["--record", record])
    forwarded.extend(["--output", args.output])
    return context.run_python(context.substitute_pressure_script, forwarded)


def cmd_hybrid_status(
    args: argparse.Namespace,
    *,
    context: HybridModeContext,
) -> int:
    forwarded = [
        "--cost-record", args.cost_record,
        "--output", args.output,
    ]
    for hybrid_record in args.hybrid_record:
        forwarded.extend(["--hybrid-record", hybrid_record])
    return context.run_python(context.hybrid_status_script, forwarded)


def cmd_recommend_mode(
    args: argparse.Namespace,
    *,
    context: HybridModeContext,
) -> int:
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
    return context.run_python(context.mode_selector_script, forwarded)


def cmd_select_mode(
    args: argparse.Namespace,
    *,
    context: HybridModeContext,
) -> int:
    forwarded = [
        "--recommendation-file", args.recommendation_file,
        "--output", args.output,
    ]
    if args.selected_mode:
        forwarded.extend(["--selected-mode", args.selected_mode])
    if args.selected_with_preparation:
        forwarded.append("--selected-with-preparation")
    return context.run_python(context.mode_receipt_script, forwarded)


def cmd_plan_proof(
    args: argparse.Namespace,
    *,
    context: ProofPreparationCostContext,
) -> int:
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
    return context.run_python(context.proof_plan_script, forwarded)


def cmd_preparation_receipt(
    args: argparse.Namespace,
    *,
    context: ProofPreparationCostContext,
) -> int:
    return context.run_python(
        context.preparation_receipt_script,
        ["--plan-file", args.plan_file, "--bundle-file", args.bundle_file, "--output", args.output],
    )


def cmd_governed_cost(
    args: argparse.Namespace,
    *,
    context: ProofPreparationCostContext,
) -> int:
    return context.run_python(
        context.governed_cost_script,
        ["--unprepared-file", args.unprepared_file, "--prepared-file", args.prepared_file, "--output", args.output],
    )


def cmd_create_checkpoint(
    args: argparse.Namespace,
    *,
    context: CheckpointCreateSaveVerifyContext,
) -> int:
    root = context.alpha_root_from_args(args, ensure=True)
    if root and not getattr(args, "checkpoint_id", None):
        args.checkpoint_id = "working"
    if root and not getattr(args, "checkpoint_root", None):
        args.checkpoint_root = str(context.checkpoint_root(root, args.checkpoint_id))
    if root and not getattr(args, "state_file", None):
        args.state_file = str(context.alpha_file(root, "state"))
    if root and not getattr(args, "output", None):
        args.output = str(context.checkpoint_record_file(root, args.checkpoint_id))
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
                existing = context.maybe_existing_alpha_file(root, file_id)
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
        return context.run_python(context.checkpoint_script, forwarded)
    completed = context.run_python_capture(context.checkpoint_script, forwarded)
    if completed.returncode != 0:
        emit_completed_capture(completed)
        return completed.returncode
    context.print_checkpoint_summary(Path(args.output), action="create", root=root)
    return 0


def cmd_save(
    args: argparse.Namespace,
    *,
    context: CheckpointCreateSaveVerifyContext,
) -> int:
    root = context.alpha_root_from_args(args, ensure=True)
    checkpoint_id = getattr(args, "checkpoint_id", None) or "working"
    record_output = Path(getattr(args, "output", "") or context.checkpoint_record_file(root, checkpoint_id))
    record_root = Path(getattr(args, "checkpoint_root", "") or context.checkpoint_root(root, checkpoint_id))
    state_file = Path(getattr(args, "state_file", "") or context.alpha_file(root, "state"))
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
            value = context.maybe_existing_alpha_file(root, file_id)
        if value:
            create_forwarded.extend([flag, value])
    created = context.run_python_capture(context.checkpoint_script, create_forwarded)
    if created.returncode != 0:
        emit_completed_capture(created)
        return created.returncode
    verify_output = Path(context.checkpoint_verify_file(root, checkpoint_id))
    verified = context.run_python_capture(
        context.checkpoint_script,
        [
            "verify",
            "--checkpoint-record-file", str(record_output),
            "--output", str(verify_output),
        ],
    )
    if verified.returncode != 0:
        emit_completed_capture(verified)
        context.print_checkpoint_summary(record_output, action="create", root=root)
        return verified.returncode
    context.print_save_summary(record_output, verify_output, root=root)
    return 0


def cmd_verify_checkpoint(
    args: argparse.Namespace,
    *,
    context: CheckpointCreateSaveVerifyContext,
) -> int:
    root = context.alpha_root_from_args(args)
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = context.discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if root and not getattr(args, "output", None):
        checkpoint_id = getattr(args, "checkpoint_id", None) or (Path(args.checkpoint_record_file).parent.name if getattr(args, "checkpoint_record_file", None) else "working")
        args.output = str(context.checkpoint_verify_file(root, checkpoint_id))
    if not getattr(args, "checkpoint_record_file", None):
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_RECORD_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not find a restore point to confirm.")
            if root:
                print("What to do next: create one while the project is in a verified working state.")
                print("Next command: " + context.shell_command(root, "save"))
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
        return context.run_python(context.checkpoint_script, forwarded)
    completed = context.run_python_capture(context.checkpoint_script, forwarded)
    if completed.returncode != 0:
        emit_completed_capture(completed)
        return completed.returncode
    context.print_checkpoint_summary(Path(args.output), action="verify", root=root)
    return 0


def cmd_restore_checkpoint(
    args: argparse.Namespace,
    *,
    context: RestoreConsistencyThinContext,
) -> int:
    root = context.alpha_root_from_args(args, ensure=True)
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = context.discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if root and not getattr(args, "target_root", None):
        args.target_root = str(root)
    if root and not getattr(args, "output", None):
        output_file_id = "checkpoint_restore_preview" if getattr(args, "preview", False) else "checkpoint_restore"
        args.output = str(context.alpha_file(root, output_file_id))
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
                    print("Next command: " + context.shell_command(root, "save"))
            return 2
        forwarded = [
            "preview",
            "--checkpoint-record-file", args.checkpoint_record_file,
            "--target-root", args.target_root,
            "--output", args.output,
        ]
        if args.mode == "dev":
            return context.run_python(context.checkpoint_script, forwarded)
        completed = context.run_python_capture(context.checkpoint_script, forwarded)
        if completed.returncode != 0:
            emit_completed_capture(completed)
            return completed.returncode
        context.print_checkpoint_summary(Path(args.output), action="preview", root=root)
        return 0
    if not getattr(args, "checkpoint_record_file", None):
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_RECORD_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not find a verified restore point to restore.")
            if root:
                print("What to do next: create one while the project is in a verified working state.")
                print("Next command: " + context.shell_command(root, "save"))
        return 2
    if not getattr(args, "confirm", False):
        preview_output = Path(args.output).with_name("checkpoint_restore_preview.json")
        forwarded = [
            "preview",
            "--checkpoint-record-file", args.checkpoint_record_file,
            "--target-root", args.target_root,
            "--output", str(preview_output),
        ]
        completed = context.run_python_capture(context.checkpoint_script, forwarded)
        if completed.returncode != 0:
            emit_completed_capture(completed)
            return completed.returncode
        preview_payload = context.load_json(preview_output)
        if preview_payload.get("workspace_restore_destructive", False):
            if args.mode == "dev":
                print(json.dumps({"result": "ERROR", "reason": "RESTORE_CONFIRM_REQUIRED"}, ensure_ascii=True))
            else:
                print("Synrail will not run this destructive restore without explicit confirmation.")
                print("What happened: this restore would modify project workspace files on the saved project root.")
                print("What to do next: preview the restore carefully, then rerun with --confirm if you want to proceed.")
                print("Preview command: " + context.shell_command(root, "restore") + " --preview")
                print("Next command: " + context.shell_command(root, "restore") + " --confirm")
            return 2
    forwarded = [
        "restore",
        "--checkpoint-record-file", args.checkpoint_record_file,
        "--target-root", args.target_root,
        "--output", args.output,
    ]
    if args.mode == "dev":
        code = context.run_python(context.checkpoint_script, forwarded)
    else:
        completed = context.run_python_capture(context.checkpoint_script, forwarded)
        if completed.returncode != 0:
            emit_completed_capture(completed)
            return completed.returncode
        code = 0
    if code == 0:
        context.sync_restored_checkpoint_artifacts(Path(args.target_root))
        if args.mode != "dev":
            context.print_checkpoint_summary(Path(args.output), action="restore", root=root)
    return code


def cmd_artifact_consistency(
    args: argparse.Namespace,
    *,
    context: RestoreConsistencyThinContext,
) -> int:
    root = context.alpha_root_from_args(args)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(context.alpha_file(root, "state"))
    if root and not getattr(args, "output", None):
        args.output = str(context.alpha_file(root, "artifact_consistency"))
    if root and not getattr(args, "bundle_file", None):
        args.bundle_file = str(context.alpha_file(root, "bundle"))
    if root:
        for attr, file_id in [
            ("report_file", "report"),
            ("orchestration_file", "orchestration"),
            ("run_file", "run"),
            ("closure_certificate_file", "closure_certificate"),
            ("repair_packet_file", "repair_packet"),
            ("repair_handoff_file", "repair_handoff"),
            ("repair_receipt_file", "repair_receipt"),
        ]:
            if not getattr(args, attr, None):
                existing = context.maybe_existing_alpha_file(root, file_id)
                if existing:
                    setattr(args, attr, existing)
    forwarded = [
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    if getattr(args, "bundle_file", None):
        forwarded.extend(["--bundle-file", args.bundle_file])
    for flag, value in [
        ("--report-file", args.report_file),
        ("--orchestration-file", args.orchestration_file),
        ("--run-file", args.run_file),
        ("--closure-certificate-file", args.closure_certificate_file),
        ("--repair-packet-file", args.repair_packet_file),
        ("--repair-handoff-file", args.repair_handoff_file),
        ("--repair-receipt-file", args.repair_receipt_file),
    ]:
        if value:
            forwarded.extend([flag, value])
    return context.run_python(context.artifact_consistency_script, forwarded)


def cmd_thin_output(
    args: argparse.Namespace,
    *,
    context: RestoreConsistencyThinContext,
) -> int:
    root = context.alpha_root_from_args(args)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(context.alpha_file(root, "state"))
    if root and not getattr(args, "report_file", None):
        args.report_file = str(context.alpha_file(root, "report"))
    if root and not getattr(args, "output", None):
        args.output = str(context.alpha_file(root, "thin_output"))
    if root and not getattr(args, "repair_packet_file", None):
        existing = context.maybe_existing_alpha_file(root, "repair_packet")
        if existing:
            args.repair_packet_file = existing
    if root and not getattr(args, "doctor_file", None):
        existing = context.maybe_existing_alpha_file(root, "doctor")
        if existing:
            args.doctor_file = existing
    if root and not getattr(args, "consistency_recovery_file", None):
        existing = context.maybe_existing_alpha_file(root, "consistency_recovery")
        if existing:
            args.consistency_recovery_file = existing
    if root and not getattr(args, "refresh_file", None):
        existing = context.maybe_existing_alpha_file(root, "refresh")
        if existing:
            args.refresh_file = existing
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = context.discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
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
        ("--refresh-file", getattr(args, "refresh_file", None)),
    ]:
        if value:
            forwarded.extend([flag, value])
    if args.mode == "dev":
        return context.run_python(context.thin_output_script, forwarded)
    completed = context.run_python_capture(context.thin_output_script, forwarded)
    if completed.returncode != 0:
        emit_completed_capture(completed)
    elif not getattr(args, "_suppress_summary", False):
        context.print_thin_output_summary(Path(args.output))
    return completed.returncode


def cmd_generate_prompt(
    args: argparse.Namespace,
    *,
    context: PromptReadingFollowupContext,
) -> int:
    root = context.alpha_root_from_args(args)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(context.alpha_file(root, "state"))
    if root and not getattr(args, "report_file", None):
        existing = context.maybe_existing_alpha_file(root, "report")
        if existing:
            args.report_file = existing
    if root and not getattr(args, "repair_packet_file", None):
        args.repair_packet_file = str(context.alpha_file(root, "repair_packet"))
    if root and not getattr(args, "doctor_file", None):
        existing = context.maybe_existing_alpha_file(root, "doctor")
        if existing:
            args.doctor_file = existing
    if root and not getattr(args, "output", None):
        args.output = str(context.alpha_file(root, "prompt"))
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = context.discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if not args.repair_packet_file or not Path(args.repair_packet_file).exists():
        state_file = getattr(args, "state_file", None)
        if root and state_file and Path(state_file).expanduser().resolve().exists():
            state = context.load_json(Path(state_file).expanduser().resolve())
            context.apply_resume_output_defaults(args, state)
            context.ensure_repair_packet_synthesis_defaults(args)
            context.synthesize_repair_packet(args, state)
        if not args.repair_packet_file or not Path(args.repair_packet_file).exists():
            if args.mode == "dev":
                print(json.dumps({"result": "ERROR", "reason": "REPAIR_PACKET_REQUIRED"}, ensure_ascii=True))
                return 2
            print("Synrail does not have the next bounded repair instruction yet.")
            if root:
                print("What to do next: run one check first so Synrail can build the bounded next step.")
                print("Next command: " + context.plain_shell_command("check"))
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
        return context.run_python(context.prompt_bridge_script, forwarded)
    completed = context.run_python_capture(context.prompt_bridge_script, forwarded)
    if completed.returncode != 0:
        emit_completed_capture(completed)
        return completed.returncode
    created_fallback = context.maybe_materialize_requested_fallback_surface(root=root, prompt_file=Path(args.output))
    if created_fallback:
        print(f"Prepared fallback surface: {created_fallback}")
    context.print_prompt_summary(Path(args.output))
    return 0


def cmd_thin_output_reading(
    args: argparse.Namespace,
    *,
    context: PromptReadingFollowupContext,
) -> int:
    return context.run_python(
        context.thin_output_reading_script,
        [
            "--thin-output-file", args.thin_output_file,
            "--prompt-bridge-file", args.prompt_bridge_file,
            "--report-file", args.report_file,
            "--repair-packet-file", args.repair_packet_file,
            "--output", args.output,
        ],
    )


def cmd_prompt_followup(
    args: argparse.Namespace,
    *,
    context: PromptReadingFollowupContext,
) -> int:
    forwarded = [
        "--repair-packet-file", args.repair_packet_file,
        "--prompt-bridge-file", args.prompt_bridge_file,
        "--output", args.output,
    ]
    if args.thin_output_file:
        forwarded.extend(["--thin-output-file", args.thin_output_file])
    return context.run_python(context.prompt_followup_script, forwarded)


def cmd_prompt_retry_guard(
    args: argparse.Namespace,
    *,
    context: RetryRecoveryReadingContext,
) -> int:
    return context.run_python(
        context.prompt_retry_guard_script,
        [
            "--packet-a-file", args.packet_a_file,
            "--prompt-a-file", args.prompt_a_file,
            "--packet-b-file", args.packet_b_file,
            "--prompt-b-file", args.prompt_b_file,
            "--output", args.output,
        ],
    )


def cmd_consistency_recovery(
    args: argparse.Namespace,
    *,
    context: RetryRecoveryReadingContext,
) -> int:
    forwarded = [
        "--consistency-file", args.consistency_file,
        "--output", args.output,
    ]
    if args.checkpoint_record_file:
        forwarded.extend(["--checkpoint-record-file", args.checkpoint_record_file])
    return context.run_python(context.consistency_recovery_script, forwarded)


def cmd_checkpoint_operator_reading(
    args: argparse.Namespace,
    *,
    context: RetryRecoveryReadingContext,
) -> int:
    return context.run_python(
        context.checkpoint_operator_reading_script,
        [
            "--second-operator-file", args.second_operator_file,
            "--thin-output-file", args.thin_output_file,
            "--repair-packet-file", args.repair_packet_file,
            "--output", args.output,
        ],
    )


def cmd_consistency_recovery_prompt(
    args: argparse.Namespace,
    *,
    context: RecoveryPromptObservabilityContext,
) -> int:
    forwarded = [
        "--consistency-recovery-file", args.consistency_recovery_file,
        "--output", args.output,
    ]
    if args.thin_output_file:
        forwarded.extend(["--thin-output-file", args.thin_output_file])
    return context.run_python(context.consistency_recovery_prompt_script, forwarded)


def cmd_consistency_recovery_prompt_reading(
    args: argparse.Namespace,
    *,
    context: RecoveryPromptObservabilityContext,
) -> int:
    return context.run_python(
        context.consistency_recovery_prompt_reading_script,
        [
            "--consistency-recovery-file", args.consistency_recovery_file,
            "--prompt-file", args.prompt_file,
            "--output", args.output,
        ],
    )


def cmd_observability(
    args: argparse.Namespace,
    *,
    context: RecoveryPromptObservabilityContext,
) -> int:
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
    return context.run_python(context.observability_script, forwarded)


def cmd_deploy(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    alpha_file: Callable[[Path, str], Path],
    load_json: Callable[[Path], dict],
    expected_target_identity_for_root: Callable[[Path], str],
    save_json: Callable[[Path, dict], None],
    display_path: Callable[[Path], str],
) -> int:
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


def cmd_deploy_check(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    alpha_file: Callable[[Path, str], Path],
    load_json: Callable[[Path], dict],
    expected_target_identity_for_root: Callable[[Path], str],
) -> int:
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


def cmd_repair_packet(
    args: argparse.Namespace,
    *,
    current_project_root: Callable[[], Path],
    validate_root_within_project: Callable[..., None],
    validate_repair_packet_paths: Callable[..., None],
    run_python: Callable[[Path, list[str]], int],
    repair_packet_script: Path,
) -> int:
    artifact_root = Path(args.artifact_root).expanduser().resolve()
    project_root = current_project_root()
    validate_root_within_project(
        "artifact_root",
        args.artifact_root,
        root=artifact_root,
        project_root=project_root,
        artifact_root=artifact_root,
    )
    validate_repair_packet_paths(args, artifact_root=artifact_root, project_root=project_root)
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
        ("--coverage-profile-file", getattr(args, "coverage_profile_file", None)),
        ("--coverage-corpus-file", getattr(args, "coverage_corpus_file", None)),
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
    return run_python(repair_packet_script, forwarded)


def cmd_orchestrate(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    current_project_root: Callable[[], Path],
    validate_root_within_project: Callable[..., None],
    apply_alpha_runtime_file_defaults: Callable[[argparse.Namespace], None],
    project_root_from_profile: Callable[[Path | None], Path | None],
    validate_check_like_paths: Callable[..., None],
    run_python: Callable[[Path, list[str]], int],
    run_python_capture: Callable[[Path, list[str]], object],
    spine_script: Path,
) -> int:
    root = alpha_root_from_args(args) or (Path(args.state_file).expanduser().resolve().parent if getattr(args, "state_file", None) else None)
    project_root = current_project_root()
    if root:
        validate_root_within_project(
            "artifact_root" if getattr(args, "artifact_root", None) else "state_file",
            getattr(args, "artifact_root", None) or getattr(args, "state_file", ""),
            root=root,
            project_root=project_root,
            artifact_root=root,
        )
        root.mkdir(parents=True, exist_ok=True)
    apply_alpha_runtime_file_defaults(args)
    project_root = project_root_from_profile(root) or project_root
    validate_check_like_paths(args, artifact_root=root, project_root=project_root)
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
        "--closure-certificate-output", args.closure_certificate_output,
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
        ("--coverage-profile-file", getattr(args, "coverage_profile_file", None)),
        ("--coverage-corpus-file", getattr(args, "coverage_corpus_file", None)),
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
    for changed_file in getattr(args, "changed_file", []):
        forwarded.extend(["--changed-file", changed_file])
    for allowed_scope_path in getattr(args, "allowed_scope_path", []):
        forwarded.extend(["--allowed-scope-path", allowed_scope_path])
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    if getattr(args, "_capture_output", False):
        completed = run_python_capture(spine_script, ["orchestrate", *forwarded])
        if completed.returncode != 0:
            emit_completed_capture(completed)
        return completed.returncode
    return run_python(spine_script, ["orchestrate", *forwarded])


def cmd_resume(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    current_project_root: Callable[[], Path],
    validate_root_within_project: Callable[..., None],
    apply_alpha_runtime_file_defaults: Callable[[argparse.Namespace], None],
    project_root_from_profile: Callable[[Path | None], Path | None],
    validate_check_like_paths: Callable[..., None],
    load_json: Callable[[Path], dict],
    ensure_run_state_extensions: Callable[[dict], dict],
    apply_bootstrap_defaults: Callable[..., dict | None],
    apply_resume_output_defaults: Callable[[argparse.Namespace, dict], None],
    maybe_apply_repair_packet: Callable[[argparse.Namespace, dict], list[str]],
    cmd_orchestrate: Callable[[argparse.Namespace], int],
    cmd_thin_output: Callable[[argparse.Namespace], int],
    print_thin_output_summary: Callable[[Path], None],
    alpha_file: Callable[[Path, str], Path],
) -> int:
    root = alpha_root_from_args(args) or (Path(args.state_file).expanduser().resolve().parent if getattr(args, "state_file", None) else None)
    project_root = current_project_root()
    if root:
        validate_root_within_project(
            "artifact_root" if getattr(args, "artifact_root", None) else "state_file",
            getattr(args, "artifact_root", None) or getattr(args, "state_file", ""),
            root=root,
            project_root=project_root,
            artifact_root=root,
        )
        root.mkdir(parents=True, exist_ok=True)
    apply_alpha_runtime_file_defaults(args)
    project_root = project_root_from_profile(root) or project_root
    validate_check_like_paths(args, artifact_root=root, project_root=project_root)
    if not getattr(args, "state_file", None):
        print(json.dumps({"result": "ERROR", "reason": "STATE_FILE_REQUIRED"}, ensure_ascii=True))
        return 2
    state_path = Path(args.state_file)
    state = ensure_run_state_extensions(load_json(state_path))
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


def cmd_thin_output_reading_cluster(
    args: argparse.Namespace,
    *,
    run_python: Callable[[Path, list[str]], int],
    thin_output_reading_script: Path,
    prompt_followup_script: Path,
    prompt_retry_guard_script: Path,
    consistency_recovery_script: Path,
    checkpoint_operator_reading_script: Path,
    consistency_recovery_prompt_script: Path,
    consistency_recovery_prompt_reading_script: Path,
    observability_script: Path,
) -> dict[str, Callable[[], int]]:
    retry_recovery_reading_context = RetryRecoveryReadingContext(
        run_python=run_python,
        prompt_retry_guard_script=prompt_retry_guard_script,
        consistency_recovery_script=consistency_recovery_script,
        checkpoint_operator_reading_script=checkpoint_operator_reading_script,
    )
    recovery_prompt_observability_context = RecoveryPromptObservabilityContext(
        run_python=run_python,
        consistency_recovery_prompt_script=consistency_recovery_prompt_script,
        consistency_recovery_prompt_reading_script=consistency_recovery_prompt_reading_script,
        observability_script=observability_script,
    )
    return {
        "thin_output_reading": lambda: cmd_thin_output_reading(args, run_python=run_python, thin_output_reading_script=thin_output_reading_script),
        "prompt_followup": lambda: cmd_prompt_followup(args, run_python=run_python, prompt_followup_script=prompt_followup_script),
        "prompt_retry_guard": lambda: cmd_prompt_retry_guard(args, context=retry_recovery_reading_context),
        "consistency_recovery": lambda: cmd_consistency_recovery(args, context=retry_recovery_reading_context),
        "checkpoint_operator_reading": lambda: cmd_checkpoint_operator_reading(args, context=retry_recovery_reading_context),
        "consistency_recovery_prompt": lambda: cmd_consistency_recovery_prompt(args, context=recovery_prompt_observability_context),
        "consistency_recovery_prompt_reading": lambda: cmd_consistency_recovery_prompt_reading(args, context=recovery_prompt_observability_context),
        "observability": lambda: cmd_observability(args, context=recovery_prompt_observability_context),
    }
