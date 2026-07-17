#!/usr/bin/env python3
"""Extracted agent-adoption and policy rendering helpers for Synrail CLI."""

from __future__ import annotations

import datetime as dt
import shlex
from pathlib import Path
from typing import Literal


DEFAULT_ALPHA_ARTIFACT_ROOT = ".synrail"


def relative_artifact_root_for_project(*, project_root: Path, artifact_root: str) -> str:
    artifact_path = Path(artifact_root)
    if artifact_path.is_absolute():
        try:
            return str(artifact_path.relative_to(project_root))
        except ValueError:
            return str(artifact_path)
    return str(artifact_path)


def preferred_synrail_command() -> str:
    return "synrail"


def preferred_synrail_fallback_command(*, argv0: str, python_executable: str) -> str | None:
    argv0_path = Path(argv0).expanduser()
    if argv0_path.name != "synrail":
        sibling = Path(python_executable).expanduser().with_name("synrail")
        if sibling.exists():
            return shlex.quote(str(sibling.resolve()))
        return None
    return shlex.quote(str(argv0_path.resolve()))


def preferred_repo_native_alpha_command(*, project_root: Path) -> str | None:
    alpha_entry = project_root / "alpha.py"
    if not alpha_entry.exists():
        return None
    return "python3 alpha.py"


def policy_command_examples(*, artifact_root: str) -> dict[str, str]:
    return policy_command_examples_for_binary(artifact_root=artifact_root, command="synrail")


def policy_command_examples_for_binary(*, artifact_root: str, command: str) -> dict[str, str]:
    quoted_root = shlex.quote(artifact_root)
    if artifact_root == DEFAULT_ALPHA_ARTIFACT_ROOT:
        return {
            "status": command,
            "preflight": f"{command} preflight",
            "suggest_verification": f"{command} suggest-verification",
            "start": f'{command} start "Describe the bounded local change."',
            "record": (
                f'{command} record path/to/file --summary "Describe the concrete bounded result." '
                '--verify "grep -n \'expected text\' path/to/file"'
            ),
            "verify": f"{command} verify",
            "check": f"{command} check",
            "repair": f"{command} repair-step",
        }
    return {
        "status": f"{command} status --artifact-root {quoted_root}",
        "preflight": f"{command} preflight --artifact-root {quoted_root}",
        "suggest_verification": f"{command} suggest-verification",
        "start": f'{command} start --artifact-root {quoted_root} "Describe the bounded local change."',
        "record": (
            f'{command} record path/to/file --summary "Describe the concrete bounded result." '
            f'--verify "grep -n \'expected text\' path/to/file" --artifact-root {quoted_root}'
        ),
        "verify": f"{command} verify --artifact-root {quoted_root}",
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


def policy_portability_note_lines(
    *,
    fallback_command: str | None,
    repo_native_alpha_command: str | None,
) -> list[str]:
    lines = [
        "- Keep repo instructions portable: prefer `synrail` in commands and committed docs.",
    ]
    lines.extend(
        [
            "- If `synrail` from PATH is unavailable in this checkout, try a local wrapper like `./.venv/bin/synrail` before assuming the control tool is missing.",
        ]
    )
    if repo_native_alpha_command:
        lines.extend(
            [
                f"- If this repo exposes a local alpha entrypoint at `alpha.py`, prefer `{repo_native_alpha_command}` as the repo-local fallback instead of reverse-engineering the entrypoint from setup metadata.",
                f"- If a checkout-local wrapper path itself triggers an agent approval or permission wall, switch immediately to the exact repo-local commands below before concluding Synrail cannot run on this host.",
            ]
        )
    if fallback_command:
        lines.append(
            f"- If this machine cannot resolve the right Synrail binary from PATH, use `{fallback_command}` as the local fallback for this checkout."
        )
    return lines


def policy_explicit_artifact_root(artifact_root: str) -> str:
    artifact_path = Path(artifact_root)
    if artifact_path.is_absolute():
        return shlex.quote(str(artifact_path))
    artifact_text = str(artifact_path)
    if artifact_text.startswith("./"):
        return shlex.quote(artifact_text)
    return shlex.quote(f"./{artifact_text}")


def policy_run_loop_lines(*, artifact_root: str, command: str) -> list[str]:
    explicit_root = policy_explicit_artifact_root(artifact_root)
    commands = policy_command_examples_for_binary(artifact_root=artifact_root, command=command)
    return [
        "## Run Loop",
        "",
        "```bash",
        f"{command} preflight --artifact-root {explicit_root}",
        "# continue on READY; NOT_CONFIGURED only for non-behavioral tasks",
        f'{command} start "TASK" --artifact-root {explicit_root}',
        "# make one bounded change and run the real local verification",
        commands["record"],
        f"# READY only: {command} verify --artifact-root {explicit_root}",
        f"{command} check --artifact-root {explicit_root}",
        "# only stop on Status: Accepted",
        "```",
        "",
        "Use `record` only when the run started with a clean git worktree, `HEAD` did not change, and exactly one tracked regular file changed. For multi-file, untracked, deleted, no-op, no-git, pre-dirty, or revision-changing work, update `final_result.json` with complete structured proof instead. `record` never accepts the task; behavioral `verify` and final `check` remain separate gates.",
        "",
    ]


def policy_non_accepted_status_lines(check_command: str) -> list[str]:
    return [
        "## Non-Accepted Status Rule",
        "",
        "Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.",
        "Do not say the task is functionally complete, 100% done, fully done, or all requirements met while Synrail is non-green.",
        f"If `{check_command}` prints any other non-green status, report the exact Synrail status, follow only the named next command or repair target, and rerun Synrail until `Status: Accepted` appears.",
        "",
    ]


def policy_no_git_proof_line(artifact_root: str) -> str:
    return (
        f"If `git` is unavailable on this host, do not invent `git_diff`; leave it empty in `{artifact_root}/final_result.json` "
        "and use structured provenance: `diff_provenance` for a single-file change, or `diff_provenance_records` / `per_file_diff_provenance` with one `changed_file`-backed record per modified file for a multi-file change. "
        "Each record should include one exact changed or observed line, a stable context anchor, `verification_command`, and `verification_result`."
    )


def policy_recheck_command_line() -> str:
    return (
        "Keep `diff_provenance.verification_command` recheckable: use one repo-relative read-only command such as `grep -n`, `cat`, `head`, `tail`, `git diff -- <path>`, `git show -- <path>`, or `git log -- <path>`. "
        "Git recheck commands must use exactly `git diff/show/log -- <path>` with no `git -c`, `--ext-diff`, `--textconv`, or other options before `--`. "
        "Do not use pipes, `&&`, `sed`, `awk`, `perl`, subshells, or multi-command snippets there."
    )


def policy_path_scope_block_line() -> str:
    return (
        "Treat `PATH_SCOPE_VIOLATION` as blocking for that command: Synrail stopped before closure and did not accept the task. "
        "Fix the named path or `--project-root`, rerun `check` as a separate command, and never combine the blocked output with a later command's `Status: Accepted`."
    )


def policy_behavioral_verification_lines(commands: dict[str, str]) -> list[str]:
    return [
        "## Behavioral Verification Gate",
        "",
        "Before starting any mutation run, inspect the operator-owned verification policy:",
        "",
        "```bash",
        commands["preflight"],
        "```",
        "",
        "Interpret the behavioral-verification status exactly:",
        "",
        f"- `READY`: start the run, then run the required profiles with `{commands['verify']}` after the change and before `{commands['check']}`.",
        f"- `NOT_CONFIGURED`: only a task that does not require behavioral acceptance may continue. Claims such as tests passing are not Synrail-gated; do not make or attribute them to Synrail. If behavior matters, report the missing gate and suggest that the operator run `{commands['suggest_verification']}` outside the controlled run.",
        "- `REVIEW_REQUIRED` or `BLOCKED`: do not start a mutation run. Follow only the named safe setup step or report the blocker.",
        "- Any missing, malformed, or unrecognized status is blocking: do not start.",
        "",
        "Treat `synrail.toml` as operator-owned policy. Do not create, edit, commit, weaken, or replace it unless the user explicitly asks to configure verification and no controlled run is active. Never change it during an active run to evade a failed profile.",
        "",
        "When preflight reported `READY`, run behavioral verification before closure:",
        "",
        "```bash",
        commands["verify"],
        "```",
        "",
        f"If verification fails, repair the behavior and rerun `{commands['verify']}`. Do not replace a failing behavioral profile with `grep`, narrative proof, or another convenient read-only check. Any later code or config change makes prior verification stale, so rerun it before `{commands['check']}`.",
        "",
    ]


def render_local_workflow_policy(
    *,
    heading: str,
    intro: str,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
    first_command_heading: str | None,
    first_command_intro: str,
    show_cli_kernel_note: bool,
    start_intro: str,
    finish_intro: str | None = None,
    include_gemini_orientation_note: bool = False,
) -> str:
    commands = policy_command_examples_for_binary(artifact_root=artifact_root, command=command)
    note_lines = policy_workspace_note_lines(
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
        command=command,
    )
    portability_lines = policy_portability_note_lines(
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
    )
    orientation_lines = policy_orientation_lines(commands["status"])
    repo_native_commands = (
        policy_command_examples_for_binary(artifact_root=artifact_root, command=repo_native_alpha_command)
        if repo_native_alpha_command
        else None
    )

    lines = [heading, "", intro, ""]
    if first_command_heading:
        lines.extend([first_command_heading, ""])
    lines.extend([
        first_command_intro,
        "",
        "```bash",
        commands["status"],
        "```",
        "",
    ])
    if show_cli_kernel_note:
        lines.extend([
            "Synrail is a CLI control kernel, not a background daemon.",
            "",
        ])
    lines.extend(orientation_lines)
    if include_gemini_orientation_note:
        lines.extend(policy_gemini_orientation_lines())
    lines.extend(policy_behavioral_verification_lines(commands))
    if repo_native_commands:
        lines.extend(
            [
                "## Repo-Local Fallback",
                "",
                "If this host blocks checkout-local wrappers behind approval or permission gates, use the repo-local alpha entrypoint directly:",
                "",
                "```bash",
                repo_native_commands["status"],
                repo_native_commands["preflight"],
                repo_native_commands["start"],
                repo_native_commands["verify"],
                repo_native_commands["check"],
                f"{repo_native_alpha_command} runtime-helper",
                "```",
                "",
                "Prefer these exact repo-local commands instead of probing wrapper paths with shell piping.",
                "",
            ]
        )
    lines.extend([
        "## Start",
        "",
        start_intro,
        "",
        "```bash",
        commands["start"],
        "```",
        "",
        *policy_run_loop_lines(artifact_root=artifact_root, command=command),
        "## Work",
        "",
        "- Keep edits bounded and local to this repo.",
        f"- For a clean-start change to exactly one tracked regular file, run the real local verification and use `{commands['record']}` to record recheckable proof without hand-authoring JSON.",
        f"- For every other contour, run the local verification commands needed for the task before updating `{artifact_root}/final_result.json`. Only materialize fallback prose surfaces later if Synrail explicitly targets them, and leave `cleanup_status` absent unless Synrail later asks for cleanup attestation.",
        "- Keep proof explicit in the cheapest honest order: make final_result carry trust-bearing status plus patch or structured diff provenance first; treat readback and scenario proof as fallback-only surfaces and do not touch them unless Synrail explicitly targets them or final_result cannot yet carry strong structured verification.",
        f"- {policy_no_git_proof_line(artifact_root)}",
        f"- {policy_recheck_command_line()}",
        f"- {policy_path_scope_block_line()}",
        "",
        "## Finish",
        "",
    ])
    if finish_intro:
        lines.extend([finish_intro, ""])
    lines.extend([
        "```bash",
        commands["check"],
        "```",
        "",
        f"If non-green, fix only what check tells you to fix, then rerun `{commands['check']}`.",
        "",
        "Do not bypass Synrail and do not claim success without real local verification.",
        "",
        *policy_non_accepted_status_lines(commands["check"]),
    ])
    lines.extend(portability_lines)
    lines.extend(note_lines)
    if portability_lines or note_lines:
        lines.append("")
    return "\n".join(lines)


def render_policy_markdown(
    agent_type: Literal["agents", "gemini", "claude"],
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    if agent_type == "gemini":
        return render_local_workflow_policy(
            heading="# Gemini Workflow",
            intro="Use Synrail as the default local control path for this repo.",
            artifact_root=artifact_root,
            command=command,
            fallback_command=fallback_command,
            repo_native_alpha_command=repo_native_alpha_command,
            workspace_isolation_note=workspace_isolation_note,
            prefer_runtime_helper=prefer_runtime_helper,
            first_command_heading="## First Command",
            first_command_intro="For every new user task, run Synrail first so you can see the current governed state:",
            show_cli_kernel_note=True,
            start_intro="If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:",
            include_gemini_orientation_note=True,
        )
    if agent_type == "claude":
        return render_local_workflow_policy(
            heading="# Claude Workflow",
            intro="Use Synrail as the default local control path for this repo.",
            artifact_root=artifact_root,
            command=command,
            fallback_command=fallback_command,
            repo_native_alpha_command=repo_native_alpha_command,
            workspace_isolation_note=workspace_isolation_note,
            prefer_runtime_helper=prefer_runtime_helper,
            first_command_heading="## First Command",
            first_command_intro="For every new user task, run Synrail first so you can see the current governed state:",
            show_cli_kernel_note=True,
            start_intro="If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:",
        )

    commands = policy_command_examples_for_binary(artifact_root=artifact_root, command=command)
    note_lines = policy_workspace_note_lines(
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
        command=command,
    )
    portability_lines = policy_portability_note_lines(
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
    )
    orientation_lines = policy_orientation_lines(commands["status"])
    repo_native_commands = (
        policy_command_examples_for_binary(artifact_root=artifact_root, command=repo_native_alpha_command)
        if repo_native_alpha_command
        else None
    )

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
    lines.extend(policy_behavioral_verification_lines(commands))
    if repo_native_commands:
        lines.extend(
            [
                "## Repo-Local Fallback",
                "",
                "If this host blocks checkout-local wrappers behind approval or permission gates, use the repo-local alpha entrypoint directly:",
                "",
                "```bash",
                repo_native_commands["status"],
                repo_native_commands["preflight"],
                repo_native_commands["start"],
                repo_native_commands["verify"],
                repo_native_commands["check"],
                f"{repo_native_alpha_command} runtime-helper",
                "```",
                "",
                "Prefer these exact repo-local commands instead of probing wrapper paths with shell piping.",
                "",
            ]
        )
    lines.extend([
        "## Before You Edit",
        "",
        "1. If Synrail shows that no controlled run is active, start one before mutating code:",
        "```bash",
        commands["start"],
        "```",
        "",
        "2. Keep the change local and bounded to the stated task.",
        f"3. For a clean-start change to exactly one tracked regular file, run the real local verification and use `{commands['record']}`. `record` writes proof only; it does not accept the task.",
        f"4. For every other contour, run the local commands needed to verify the change honestly, then edit `{artifact_root}/final_result.json` in place as the work becomes real. Only materialize readback or scenario proof if Synrail explicitly targets them, and leave `cleanup_status` absent unless Synrail later asks for cleanup attestation.",
        "5. Keep proof explicit in the cheapest honest order: make final_result carry trust-bearing status plus patch or structured diff provenance first; treat readback and scenario proof as fallback-only surfaces and do not touch them unless Synrail explicitly targets them or final_result cannot yet carry strong structured verification.",
        f"6. {policy_no_git_proof_line(artifact_root)}",
        f"7. {policy_recheck_command_line()}",
        f"8. {policy_path_scope_block_line()}",
        "",
        *policy_run_loop_lines(artifact_root=artifact_root, command=command),
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
        *policy_non_accepted_status_lines(commands["check"]),
        "## Important",
        "",
        "- Do not skip Synrail and try to legalize edits afterward.",
        "- Do not claim success without real local verification.",
        "- If `synrail` is unavailable from PATH here, try the checkout-local fallbacks first instead of reverse-engineering the entrypoint.",
        "- Only report the control tool missing after the local checkout fallbacks fail too.",
        "",
    ])

    lines.extend(portability_lines)
    lines.extend(note_lines)
    if portability_lines or note_lines:
        lines.append("")
    return "\n".join(lines)


def render_agent_policy_markdown(
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    return render_policy_markdown(
        "agents",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )


def render_gemini_policy_markdown(
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    return render_policy_markdown(
        "gemini",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )


def render_claude_policy_markdown(
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    return render_policy_markdown(
        "claude",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )


def render_kiro_policy_markdown(
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    """Render a Kiro workspace-steering file with valid front matter."""
    policy = render_local_workflow_policy(
        heading="# Synrail Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
        first_command_heading="## First Command",
        first_command_intro="For every new task that changes code or needs acceptance, run Synrail first:",
        show_cli_kernel_note=True,
        start_intro="If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:",
    )
    return "\n".join(
        [
            "---",
            "inclusion: auto",
            "name: synrail-workflow",
            'description: "Use for bounded code changes, verification, and proof-gated acceptance tasks."',
            "---",
            "",
            policy.rstrip(),
            "",
        ]
    )


def render_agent_policy_block(
    *,
    title: str,
    intro: str,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    return render_local_workflow_policy(
        heading=f"## {title}",
        intro=intro,
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
        first_command_heading=None,
        first_command_intro="First command for every new task:",
        show_cli_kernel_note=False,
        start_intro="If Synrail shows that no controlled run is active, start one:",
        finish_intro="Before claiming success, run:",
    )


def render_agents_policy_block(
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    return render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="This repo uses Synrail to keep one bounded local change inside one controlled run.",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )


def render_gemini_policy_block(
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    return render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )


def render_claude_policy_block(
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    return render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )


def render_kiro_policy_block(
    *,
    artifact_root: str,
    command: str = "synrail",
    fallback_command: str | None = None,
    repo_native_alpha_command: str | None = None,
    workspace_isolation_note: str = "",
    prefer_runtime_helper: bool = False,
) -> str:
    return render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
        command=command,
        fallback_command=fallback_command,
        repo_native_alpha_command=repo_native_alpha_command,
        workspace_isolation_note=workspace_isolation_note,
        prefer_runtime_helper=prefer_runtime_helper,
    )


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
    path.parent.mkdir(parents=True, exist_ok=True)
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
