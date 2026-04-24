#!/usr/bin/env python3
"""Extracted CLI command handlers for Synrail v0."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Callable


PolicyWriter = Callable[[Path, str, str, bool], tuple[bool, str, Path | None]]


def run_install_agent_files_command(
    args: argparse.Namespace,
    *,
    relative_artifact_root_for_project: Callable[..., str],
    preferred_synrail_command: Callable[[], str],
    preferred_synrail_fallback_command: Callable[[], str | None],
    preferred_repo_native_alpha_command: Callable[..., str | None],
    workspace_git_context: Callable[[Path], dict],
    project_prefers_runtime_evidence: Callable[[Path], bool],
    render_agent_policy_markdown: Callable[..., str],
    render_gemini_policy_markdown: Callable[..., str],
    render_claude_policy_markdown: Callable[..., str],
    render_agent_policy_block: Callable[..., str],
    write_agent_policy_file: PolicyWriter,
) -> int:
    project_root = Path(args.project_root or ".").resolve()
    artifact_root = relative_artifact_root_for_project(
        project_root=project_root,
        artifact_root=args.artifact_root,
    )
    command = preferred_synrail_command()
    fallback_command = preferred_synrail_fallback_command()
    repo_native_alpha_command = preferred_repo_native_alpha_command(project_root=project_root)
    git_context = workspace_git_context(project_root)
    workspace_isolation_note = git_context.get("workspace_isolation_note", "")
    prefer_runtime_helper = project_prefers_runtime_evidence(project_root)
    agents_path = project_root / "AGENTS.md"
    gemini_path = project_root / "GEMINI.md"
    claude_path = project_root / "CLAUDE.md"

    agents_content = render_agent_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    gemini_content = render_gemini_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    claude_content = render_claude_policy_markdown(
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    agents_block = render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="This repo uses Synrail to keep one bounded local change inside one controlled run.",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    gemini_block = render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )
    claude_block = render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
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


def run_telemetry_export_command(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    default_session_replay_file: Callable[[Path], Path],
    default_issue_body_file: Callable[[Path], Path],
    export_session_replay: Callable[[Path, Path, Path | None], dict],
) -> int:
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


def run_session_export_command(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    maybe_existing_alpha_file: Callable[[Path | None, str], str | None],
    alpha_file: Callable[[Path, str], Path],
    cmd_observability: Callable[[argparse.Namespace], int],
) -> int:
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


def run_bug_packet_command(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    maybe_existing_alpha_file: Callable[[Path | None, str], str | None],
    alpha_file: Callable[[Path, str], Path],
    run_python: Callable[[Path, list[str]], int],
    bug_packet_script: Path,
) -> int:
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
    code = run_python(bug_packet_script, forwarded)
    if code == 0:
        print("Bug packet ready.")
        print("What it includes: one compact runtime summary and one issue-ready markdown body.")
        print("Use this only when telemetry export is not enough for the bug report.")
    return code
