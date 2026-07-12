#!/usr/bin/env python3
"""Smoke tests for repo-native agent adoption files."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_agent_adoption_v0 import render_claude_policy_block, render_claude_policy_markdown, render_gemini_policy_block, render_gemini_policy_markdown, render_local_workflow_policy
from synrail_cli_v0 import (
    cmd_check,
    cmd_init_agent,
    cmd_init_ci,
    cmd_install_agent_files,
    preferred_synrail_command,
    preferred_synrail_fallback_command,
    runtime_helper_text,
)
from synrail_commands_v0 import render_security_hygiene_workflow


class AgentAdoptionTests(unittest.TestCase):
    def run_alpha(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        repo_path = str(REPO_ROOT)
        env["PYTHONPATH"] = repo_path if not existing else repo_path + os.pathsep + existing
        return subprocess.run(
            [sys.executable, str(ALPHA_ENTRY), *args],
            cwd=cwd or REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def test_install_agent_files_writes_repo_native_guidance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_agent_adoption_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("Agent adoption files are ready.", result.stdout)
            self.assertIn("Synrail command: synrail", result.stdout)

            agents = (project_root / "AGENTS.md").read_text()
            gemini = (project_root / "GEMINI.md").read_text()
            claude = (project_root / "CLAUDE.md").read_text()

            self.assertIn("First Step On Every New Task", agents)
            self.assertIn("synrail", agents)
            self.assertIn('synrail start "Describe the bounded local change."', agents)
            self.assertIn("synrail check", agents)
            self.assertIn("cleanup_status` absent unless Synrail later asks for cleanup attestation", agents)
            self.assertIn("Only materialize readback or scenario proof if Synrail explicitly targets them", agents)
            self.assertIn("If `git` is unavailable on this host, do not invent `git_diff`", agents)
            self.assertIn("Treat `PATH_SCOPE_VIOLATION` as blocking for that command", agents)
            self.assertIn("never combine the blocked output with a later command's `Status: Accepted`", agents)
            self.assertIn("Do not skip Synrail", agents)
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", agents)
            self.assertIn("functionally complete, 100% done", agents)
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', agents)
            self.assertIn("# only stop on Status: Accepted", agents)
            self.assertIn("./.venv/bin/synrail", agents)
            self.assertIn("python3 alpha.py", agents)
            self.assertIn("approval or permission wall", agents)
            self.assertIn("Repo-Local Fallback", agents)
            self.assertIn('python3 alpha.py start "Describe the bounded local change."', agents)
            self.assertIn("python3 alpha.py check", agents)
            self.assertIn("Prefer these exact repo-local commands instead of probing wrapper paths with shell piping.", agents)
            self.assertNotIn('ARTIFACT_ROOT="$(pwd)/.synrail"', agents)
            self.assertIn("run `synrail` in this repo", result.stdout)

            self.assertIn("Use Synrail as the default local control path", gemini)
            self.assertIn("For every new user task, run Synrail first", gemini)
            self.assertIn("If the user asks what this project is, where work stopped, or what the current status is", gemini)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", gemini)
            self.assertIn("Do not inspect database schema, templates, or app internals for a simple orientation prompt", gemini)
            self.assertIn("Do not turn project recall into repo archaeology.", gemini)
            self.assertIn('synrail start "Describe the bounded local change."', gemini)
            self.assertIn("fix only what check tells you to fix", gemini)
            self.assertIn("cheapest honest order", gemini)
            self.assertIn("fallback-only surfaces", gemini)
            self.assertIn("do not touch them unless Synrail explicitly targets them", gemini)
            self.assertIn("If `git` is unavailable on this host, do not invent `git_diff`", gemini)
            self.assertIn("Treat `PATH_SCOPE_VIOLATION` as blocking for that command", gemini)
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", gemini)
            self.assertIn("functionally complete, 100% done", gemini)
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', gemini)
            self.assertIn("# only stop on Status: Accepted", gemini)
            self.assertIn("./.venv/bin/synrail", gemini)
            self.assertIn("python3 alpha.py", gemini)
            self.assertIn("approval or permission wall", gemini)
            self.assertIn("Repo-Local Fallback", gemini)
            self.assertIn("python3 alpha.py check", gemini)

            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("For every new user task, run Synrail first", claude)
            self.assertIn("If the user asks what this project is, where work stopped, or what the current status is", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)
            self.assertIn('synrail start "Describe the bounded local change."', claude)
            self.assertIn("fix only what check tells you to fix", claude)
            self.assertIn("cheapest honest order", claude)
            self.assertIn("fallback-only surfaces", claude)
            self.assertIn("do not touch them unless Synrail explicitly targets them", claude)
            self.assertIn("If `git` is unavailable on this host, do not invent `git_diff`", claude)
            self.assertIn("Treat `PATH_SCOPE_VIOLATION` as blocking for that command", claude)
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", claude)
            self.assertIn("functionally complete, 100% done", claude)
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', claude)
            self.assertIn("# only stop on Status: Accepted", claude)
            self.assertIn("./.venv/bin/synrail", claude)
            self.assertIn("python3 alpha.py", claude)
            self.assertIn("approval or permission wall", claude)
            self.assertIn("Repo-Local Fallback", claude)
            self.assertIn("python3 alpha.py check", claude)

    def test_init_agent_writes_only_requested_single_agent_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_agent_single_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "init-agent",
                "--agent",
                "claude",
                "--project-root",
                str(project_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("Agent onboarding is ready for claude.", result.stdout)
            self.assertIn("CLAUDE.md: written", result.stdout)
            self.assertNotIn("AGENTS.md:", result.stdout)
            self.assertNotIn("GEMINI.md:", result.stdout)
            self.assertFalse((project_root / "AGENTS.md").exists())
            self.assertFalse((project_root / "GEMINI.md").exists())
            self.assertTrue((project_root / "CLAUDE.md").exists())
            claude = (project_root / "CLAUDE.md").read_text()
            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("python3 alpha.py check", claude)
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", claude)
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', claude)
            self.assertIn("# only stop on Status: Accepted", claude)

    def test_init_agent_routes_codex_and_cursor_to_full_agent_wiring(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_agent_alias_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            codex = self.run_alpha(
                "init-agent",
                "--agent",
                "codex",
                "--project-root",
                str(project_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, codex.returncode, codex.stdout + codex.stderr)
            self.assertIn("Agent adoption files are ready.", codex.stdout)
            self.assertTrue((project_root / "AGENTS.md").exists())
            self.assertTrue((project_root / "GEMINI.md").exists())
            self.assertTrue((project_root / "CLAUDE.md").exists())

            cursor_root = Path(tmpdir) / "cursor_project"
            cursor_root.mkdir(parents=True, exist_ok=True)
            (cursor_root / "alpha.py").write_text("print('stub')\n")
            cursor = self.run_alpha(
                "init-agent",
                "--agent",
                "cursor",
                "--project-root",
                str(cursor_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, cursor.returncode, cursor.stdout + cursor.stderr)
            self.assertIn("Agent adoption files are ready.", cursor.stdout)
            self.assertTrue((cursor_root / "AGENTS.md").exists())
            self.assertTrue((cursor_root / "GEMINI.md").exists())
            self.assertTrue((cursor_root / "CLAUDE.md").exists())

    def test_generated_agent_policy_forbids_done_after_non_accepted_check(self) -> None:
        agents = render_local_workflow_policy(
            heading="# Agent Workflow",
            intro="This repo uses Synrail to keep one bounded local change inside one controlled run.",
            artifact_root=".synrail",
            command="synrail",
            fallback_command="./.venv/bin/synrail",
            repo_native_alpha_command="python3 alpha.py",
            workspace_isolation_note="",
            prefer_runtime_helper=False,
            first_command_heading="## First Step On Every New Task",
            first_command_intro="Run Synrail before deciding what to do next. It is a CLI control kernel, not a background daemon.",
            show_cli_kernel_note=False,
            start_intro="If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:",
        )
        self.assertEqual(1, agents.count("Only `Status: Accepted` means the task may be reported as complete."))
        self.assertIn("If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", agents)
        self.assertIn('synrail start "TASK" --artifact-root ./.synrail', agents)
        self.assertIn("synrail check --artifact-root ./.synrail", agents)
        self.assertIn("# only stop on Status: Accepted", agents)

    def test_init_agent_single_file_contains_non_accepted_rule(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_agent_single_rule_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "init-agent",
                "--agent",
                "claude",
                "--project-root",
                str(project_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            claude = (project_root / "CLAUDE.md").read_text()
            self.assertEqual(1, claude.count("Only `Status: Accepted` means the task may be reported as complete."))
            self.assertIn("If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", claude)
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', claude)
            self.assertIn("synrail check --artifact-root ./.synrail", claude)
            self.assertIn("# only stop on Status: Accepted", claude)

    def test_install_agent_files_contains_non_accepted_rule_for_all_agents(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_agent_rule_all_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            for name in ["AGENTS.md", "GEMINI.md", "CLAUDE.md"]:
                content = (project_root / name).read_text()
                self.assertEqual(1, content.count("Only `Status: Accepted` means the task may be reported as complete."), name)
                self.assertIn("If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", content)
                self.assertIn('synrail start "TASK" --artifact-root ./.synrail', content)
                self.assertIn("synrail check --artifact-root ./.synrail", content)
                self.assertIn("# only stop on Status: Accepted", content)

    def test_cmd_init_agent_can_append_existing_single_agent_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_agent_append_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")
            (project_root / "GEMINI.md").write_text("# Existing Gemini Context\n\nKeep this repo focused on product work.\n")

            stdout = StringIO()
            args = mock.Mock(
                agent="gemini",
                project_root=str(project_root),
                artifact_root=".synrail",
                force=False,
            )
            with redirect_stdout(stdout):
                rc = cmd_init_agent(args)
            self.assertEqual(0, rc)
            rendered = stdout.getvalue()
            self.assertIn("Agent onboarding is ready for gemini.", rendered)
            self.assertIn("GEMINI.md: appended", rendered)
            self.assertNotIn("AGENTS.md:", rendered)
            gemini = (project_root / "GEMINI.md").read_text()
            self.assertIn("# Existing Gemini Context", gemini)
            self.assertIn("<!-- SYNRAIL_GEMINI_START -->", gemini)
            self.assertIn("Use Synrail as the default local control path", gemini)

            agents = (project_root / "AGENTS.md")
            claude = (project_root / "CLAUDE.md")
            self.assertFalse(agents.exists())
            self.assertFalse(claude.exists())
            self.assertIn("run `synrail` in this repo", rendered)

    def test_init_ci_writes_bounded_github_action_adapter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_ci_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "init-ci",
                "--project-root",
                str(project_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("GitHub Action CI adapter is ready.", result.stdout)
            self.assertIn("Adapter scope: bounded check-only GitHub composite action", result.stdout)
            self.assertIn("Workflow call site: uses: ./.github/actions/synrail-check", result.stdout)
            self.assertIn("Invocation path: python3 alpha.py check --artifact-root \"${{ inputs.artifact-root }}\"", result.stdout)

            action_file = project_root / ".github" / "actions" / "synrail-check" / "action.yml"
            self.assertTrue(action_file.exists())
            action = action_file.read_text()
            self.assertIn("name: Synrail check", action)
            self.assertIn("using: composite", action)
            self.assertIn("python3 alpha.py check --artifact-root \"${{ inputs.artifact-root }}\"", action)
            self.assertNotIn("start", action)
            self.assertNotIn("restore", action)

    def test_cmd_init_ci_blocks_replacement_without_force(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_ci_block_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            action_dir = project_root / ".github" / "actions" / "synrail-check"
            action_dir.mkdir(parents=True, exist_ok=True)
            action_file = action_dir / "action.yml"
            action_file.write_text("name: Existing adapter\n")

            stdout = StringIO()
            args = mock.Mock(
                project_root=str(project_root),
                artifact_root=".synrail",
                workflow=False,
                force=False,
            )
            with redirect_stdout(stdout):
                rc = cmd_init_ci(args)
            self.assertEqual(2, rc)
            rendered = stdout.getvalue()
            self.assertIn("GitHub Action CI adapter already exists with different contents.", rendered)
            self.assertIn("rerun with --force", rendered)
            self.assertEqual("name: Existing adapter\n", action_file.read_text())

    def test_cmd_init_ci_force_replaces_existing_adapter_with_backup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_ci_force_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            action_dir = project_root / ".github" / "actions" / "synrail-check"
            action_dir.mkdir(parents=True, exist_ok=True)
            action_file = action_dir / "action.yml"
            action_file.write_text("name: Existing adapter\n")
            (project_root / "alpha.py").write_text("print('stub')\n")

            stdout = StringIO()
            args = mock.Mock(
                project_root=str(project_root),
                artifact_root=".synrail",
                workflow=False,
                force=True,
            )
            with redirect_stdout(stdout):
                rc = cmd_init_ci(args)
            self.assertEqual(0, rc)
            rendered = stdout.getvalue()
            self.assertIn("GitHub Action CI adapter is ready.", rendered)
            self.assertIn("Adapter backup:", rendered)
            self.assertIn("What to do next: commit the refreshed adapter", rendered)
            self.assertIn("python3 alpha.py check --artifact-root \"${{ inputs.artifact-root }}\"", action_file.read_text())
            backups = list(action_dir.glob("action.yml.synrail.bak.*"))
            self.assertEqual(1, len(backups))
            self.assertEqual("name: Existing adapter\n", backups[0].read_text())

    def test_init_ci_workflow_writes_composite_action_and_workflow(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_ci_workflow_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "init-ci",
                "--workflow",
                "--project-root",
                str(project_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("GitHub Action CI adapter is ready.", result.stdout)
            self.assertIn("GitHub Actions workflow is ready.", result.stdout)
            self.assertIn("Workflow triggers: push, pull_request, workflow_dispatch", result.stdout)
            action_file = project_root / ".github" / "actions" / "synrail-check" / "action.yml"
            workflow_file = project_root / ".github" / "workflows" / "synrail-check.yml"
            self.assertTrue(action_file.exists())
            self.assertTrue(workflow_file.exists())
            workflow = workflow_file.read_text()
            self.assertIn("push:", workflow)
            self.assertIn("pull_request:", workflow)
            self.assertIn("workflow_dispatch:", workflow)
            self.assertIn("uses: actions/checkout@v4", workflow)
            self.assertIn("uses: actions/setup-python@v5", workflow)
            self.assertIn("make install-dev", workflow)
            self.assertIn("make test", workflow)
            self.assertIn("make lint", workflow)
            self.assertIn("make coverage", workflow)
            self.assertIn("uses: ./.github/actions/synrail-check", workflow)
            self.assertIn("artifact-root: .synrail", workflow)

    def test_init_ci_default_says_adapter_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_ci_adapter_only_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "init-ci",
                "--project-root",
                str(project_root),
                "--artifact-root",
                ".synrail",
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("Adapter only: add a workflow that calls uses: ./.github/actions/synrail-check, or rerun with --workflow.", result.stdout)
            self.assertFalse((project_root / ".github" / "workflows" / "synrail-check.yml").exists())

    def test_init_ci_workflow_blocks_existing_different_file_without_force(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_ci_workflow_block_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            workflow_dir = project_root / ".github" / "workflows"
            workflow_dir.mkdir(parents=True, exist_ok=True)
            workflow_file = workflow_dir / "synrail-check.yml"
            workflow_file.write_text("name: Existing workflow\n")
            (project_root / "alpha.py").write_text("print('stub')\n")

            stdout = StringIO()
            args = mock.Mock(
                project_root=str(project_root),
                artifact_root=".synrail",
                workflow=True,
                force=False,
            )
            with redirect_stdout(stdout):
                rc = cmd_init_ci(args)
            self.assertEqual(2, rc)
            rendered = stdout.getvalue()
            self.assertIn("GitHub Actions workflow already exists with different contents.", rendered)
            self.assertIn("rerun with --force", rendered)
            self.assertEqual("name: Existing workflow\n", workflow_file.read_text())

    def test_init_ci_workflow_force_creates_backup(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_init_ci_workflow_force_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            workflow_dir = project_root / ".github" / "workflows"
            workflow_dir.mkdir(parents=True, exist_ok=True)
            workflow_file = workflow_dir / "synrail-check.yml"
            workflow_file.write_text("name: Existing workflow\n")
            (project_root / "alpha.py").write_text("print('stub')\n")

            stdout = StringIO()
            args = mock.Mock(
                project_root=str(project_root),
                artifact_root=".synrail",
                workflow=True,
                force=True,
            )
            with redirect_stdout(stdout):
                rc = cmd_init_ci(args)
            self.assertEqual(0, rc)
            rendered = stdout.getvalue()
            self.assertIn("GitHub Actions workflow is ready.", rendered)
            self.assertIn("Workflow backup:", rendered)
            self.assertIn("What to do next: commit the refreshed adapter and workflow", rendered)
            self.assertIn("uses: ./.github/actions/synrail-check", workflow_file.read_text())
            backups = list(workflow_dir.glob("synrail-check.yml.synrail.bak.*"))
            self.assertEqual(1, len(backups))
            self.assertEqual("name: Existing workflow\n", backups[0].read_text())

    def test_repo_security_hygiene_workflow_covers_dependency_audit_and_secret_patterns(self) -> None:
        workflow = (REPO_ROOT / ".github" / "workflows" / "security-hygiene.yml").read_text()

        self.assertIn("name: CI", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("uses: actions/checkout@v4", workflow)
        self.assertIn("uses: actions/setup-python@v5", workflow)
        self.assertIn('python-version: "3.11"', workflow)
        self.assertIn("make install-dev", workflow)
        self.assertIn("make test", workflow)
        self.assertIn("make compile", workflow)
        self.assertIn("make lint", workflow)
        self.assertIn("make coverage", workflow)
        self.assertIn("make audit", workflow)
        self.assertIn("Check repository text for common secret patterns", workflow)
        self.assertIn("python3 - <<'PY'", workflow)
        self.assertIn('excluded_dirs = {".git", ".venv", "__pycache__"}', workflow)
        self.assertIn('part.startswith(".tmp-")', workflow)
        self.assertIn("AKIA[0-9A-Z]{16}", workflow)
        self.assertIn("ghp_[A-Za-z0-9]{20,}", workflow)

    def test_observability_command_does_not_raise_missing_context_nameerror(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_observability_cli_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            result = self.run_alpha(
                "observability",
                "--help",
                cwd=project_root,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertNotIn("NameError", result.stdout + result.stderr)
            self.assertIn("usage: synrail observability", result.stdout)
            self.assertIn("--refresh-file", result.stdout)
            self.assertIn("--output", result.stdout)

    def test_init_ci_renderer_covers_security_hygiene_workflow(self) -> None:
        workflow = render_security_hygiene_workflow()
        self.assertIn("name: CI", workflow)
        self.assertIn("push:", workflow)
        self.assertIn("make install-dev", workflow)
        self.assertIn("make test", workflow)
        self.assertIn("make compile", workflow)
        self.assertIn("make lint", workflow)
        self.assertIn("make coverage", workflow)
        self.assertIn("make audit", workflow)
        self.assertIn("python3 - <<'PY'", workflow)
        self.assertIn("ghp_[A-Za-z0-9]{20,}", workflow)
        self.assertIn("AKIA[0-9A-Z]{16}", workflow)

    def test_prefers_repo_portable_command_when_path_points_elsewhere(self) -> None:
        with mock.patch("synrail_cli_v0.sys.argv", ["/opt/synrail/.venv/bin/synrail"]), mock.patch(
            "synrail_cli_v0.shutil.which",
            return_value="/usr/local/bin/synrail",
        ):
            self.assertEqual("synrail", preferred_synrail_command())
            self.assertEqual(
                "/opt/synrail/.venv/bin/synrail",
                preferred_synrail_fallback_command(),
            )

    def test_keeps_repo_portable_command_even_when_path_matches(self) -> None:
        with mock.patch("synrail_cli_v0.sys.argv", ["/opt/synrail/.venv/bin/synrail"]), mock.patch(
            "synrail_cli_v0.shutil.which",
            return_value="/opt/synrail/.venv/bin/synrail",
        ):
            self.assertEqual("synrail", preferred_synrail_command())
            self.assertEqual(
                "/opt/synrail/.venv/bin/synrail",
                preferred_synrail_fallback_command(),
            )

    def test_uses_sibling_synrail_as_local_fallback_when_console_wrapper_uses_python_dash_c(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_wrapper_probe_") as tmpdir:
            bin_dir = Path(tmpdir) / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            python_path = bin_dir / "python"
            synrail_path = bin_dir / "synrail"
            python_path.symlink_to(Path(sys.executable))
            synrail_path.write_text("")
            with mock.patch("synrail_cli_v0.sys.argv", ["-c"]), mock.patch(
                "synrail_cli_v0.sys.executable",
                str(python_path),
            ):
                self.assertEqual("synrail", preferred_synrail_command())
                self.assertEqual(
                    str(synrail_path.resolve()),
                    preferred_synrail_fallback_command(),
                )

    def test_no_machine_fallback_when_no_synrail_wrapper_is_available(self) -> None:
        with mock.patch("synrail_cli_v0.sys.argv", ["-c"]), mock.patch(
            "synrail_cli_v0.sys.executable",
            "/tmp/no-wrapper/python",
        ):
            self.assertEqual("synrail", preferred_synrail_command())
            self.assertIsNone(preferred_synrail_fallback_command())

    def test_install_agent_files_keeps_generic_checkout_fallbacks_without_machine_specific_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_agent_generic_fallback_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            stdout = StringIO()
            args = mock.Mock(
                project_root=str(project_root),
                artifact_root=".synrail",
                force=False,
            )
            with mock.patch("synrail_cli_v0.sys.argv", ["-c"]), mock.patch(
                "synrail_cli_v0.sys.executable",
                "/tmp/no-wrapper/python",
            ), redirect_stdout(stdout):
                rc = cmd_install_agent_files(args)
            self.assertEqual(0, rc)
            gemini = (project_root / "GEMINI.md").read_text()
            self.assertIn("./.venv/bin/synrail", gemini)
            self.assertIn("python3 alpha.py", gemini)
            self.assertNotIn("Synrail fallback for this machine:", stdout.getvalue())

    def test_install_agent_files_is_idempotent_and_merges_existing_gemini_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_agent_adoption_force_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            first = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
            )
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)

            second = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
            )
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertIn("AGENTS.md: unchanged", second.stdout)
            self.assertIn("GEMINI.md: unchanged", second.stdout)
            self.assertIn("CLAUDE.md: unchanged", second.stdout)

            (project_root / "GEMINI.md").write_text("# Existing Gemini Context\n\nKeep this repo focused on product work.\n")
            (project_root / "CLAUDE.md").write_text("# Existing Claude Context\n\nStay inside the repo.\n")

            merged = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
            )
            self.assertEqual(0, merged.returncode, merged.stdout + merged.stderr)
            self.assertIn("GEMINI.md: appended", merged.stdout)
            self.assertIn("CLAUDE.md: appended", merged.stdout)
            gemini = (project_root / "GEMINI.md").read_text()
            claude = (project_root / "CLAUDE.md").read_text()
            self.assertIn("# Existing Gemini Context", gemini)
            self.assertIn("<!-- SYNRAIL_GEMINI_START -->", gemini)
            self.assertIn("Use Synrail as the default local control path", gemini)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", gemini)
            self.assertIn("Do not turn project recall into repo archaeology.", gemini)
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", gemini)
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', gemini)
            self.assertIn("# only stop on Status: Accepted", gemini)
            self.assertIn("Keep repo instructions portable: prefer `synrail`", gemini)
            self.assertIn("approval or permission wall", gemini)
            self.assertIn("# Existing Claude Context", claude)
            self.assertIn("<!-- SYNRAIL_CLAUDE_START -->", claude)
            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", claude)
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', claude)
            self.assertIn("# only stop on Status: Accepted", claude)
            self.assertIn("approval or permission wall", claude)

            forced = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
                "--force",
            )
            self.assertEqual(0, forced.returncode, forced.stdout + forced.stderr)
            self.assertIn("GEMINI.md: written", forced.stdout)
            self.assertIn("GEMINI.md backup:", forced.stdout)
            self.assertIn("CLAUDE.md: written", forced.stdout)
            self.assertIn("CLAUDE.md backup:", forced.stdout)
            backups = list(project_root.glob("GEMINI.md.synrail.bak.*"))
            claude_backups = list(project_root.glob("CLAUDE.md.synrail.bak.*"))
            self.assertEqual(1, len(backups))
            self.assertEqual(1, len(claude_backups))
            self.assertIn("# Existing Gemini Context", backups[0].read_text())
            self.assertIn("# Existing Claude Context", claude_backups[0].read_text())
            self.assertNotIn("<!-- SYNRAIL_GEMINI_START -->", (project_root / "GEMINI.md").read_text())
            self.assertIn("Use Synrail as the default local control path", (project_root / "GEMINI.md").read_text())
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", (project_root / "GEMINI.md").read_text())
            self.assertIn("Do not turn project recall into repo archaeology.", (project_root / "GEMINI.md").read_text())
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", (project_root / "GEMINI.md").read_text())
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', (project_root / "GEMINI.md").read_text())
            self.assertNotIn("<!-- SYNRAIL_CLAUDE_START -->", (project_root / "CLAUDE.md").read_text())
            self.assertIn("Use Synrail as the default local control path", (project_root / "CLAUDE.md").read_text())
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", (project_root / "CLAUDE.md").read_text())
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete. If Synrail returns Proof Invalid, Rejected, Blocked, or any repair step, do not summarize the task as done; run the named repair step or report the exact Synrail blocker.", (project_root / "CLAUDE.md").read_text())
            self.assertIn('synrail start "TASK" --artifact-root ./.synrail', (project_root / "CLAUDE.md").read_text())

    def test_install_agent_files_adds_nested_git_and_runtime_notes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_agent_nested_git_") as tmpdir:
            parent_root = Path(tmpdir) / "parent"
            project_root = parent_root / "project"
            (parent_root / ".git").mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("Workspace note:", result.stdout)
            self.assertIn("Runtime note:", result.stdout)

            claude = (project_root / "CLAUDE.md").read_text()
            self.assertIn("Parent git repo detected above the project root", claude)
            self.assertIn("runtime-helper", claude)
            self.assertIn("python3 alpha.py runtime-helper", claude)
            self.assertIn("Keep repo instructions portable: prefer `synrail`", claude)

    def test_install_agent_files_surfaces_machine_fallback_without_committing_it_into_commands(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_agent_fallback_note_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            stdout = StringIO()
            args = mock.Mock(
                project_root=str(project_root),
                artifact_root=".synrail",
                force=False,
            )
            with mock.patch("synrail_cli_v0.sys.argv", ["/opt/synrail/.venv/bin/synrail"]), redirect_stdout(stdout):
                rc = cmd_install_agent_files(args)
            self.assertEqual(0, rc)
            rendered = stdout.getvalue()
            self.assertIn("Synrail command: synrail", rendered)
            self.assertIn(
                "Synrail fallback for this machine: /opt/synrail/.venv/bin/synrail",
                rendered,
            )

            gemini = (project_root / "GEMINI.md").read_text()
            self.assertIn("Keep repo instructions portable: prefer `synrail`", gemini)
            self.assertIn(
                "If this machine cannot resolve the right Synrail binary from PATH, use `/opt/synrail/.venv/bin/synrail` as the local fallback for this checkout.",
                gemini,
            )
            self.assertNotIn("/opt/synrail/.venv/bin/synrail start", gemini)

    def test_gemini_and_claude_policy_markdown_match_shared_local_workflow_renderer(self) -> None:
        common_kwargs = {
            "artifact_root": ".synrail",
            "command": "synrail",
            "fallback_command": "./.venv/bin/synrail",
            "repo_native_alpha_command": "python3 alpha.py",
            "workspace_isolation_note": "Parent git repo detected above the project root.",
            "prefer_runtime_helper": True,
        }

        self.assertEqual(
            render_local_workflow_policy(
                heading="# Gemini Workflow",
                intro="Use Synrail as the default local control path for this repo.",
                first_command_heading="## First Command",
                first_command_intro="For every new user task, run Synrail first so you can see the current governed state:",
                show_cli_kernel_note=True,
                start_intro="If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:",
                include_gemini_orientation_note=True,
                **common_kwargs,
            ),
            render_gemini_policy_markdown(**common_kwargs),
        )
        self.assertEqual(
            render_local_workflow_policy(
                heading="# Claude Workflow",
                intro="Use Synrail as the default local control path for this repo.",
                first_command_heading="## First Command",
                first_command_intro="For every new user task, run Synrail first so you can see the current governed state:",
                show_cli_kernel_note=True,
                start_intro="If Synrail shows that no controlled run is active and the task needs edits, start one controlled run:",
                **common_kwargs,
            ),
            render_claude_policy_markdown(**common_kwargs),
        )

    def test_gemini_and_claude_policy_blocks_use_dedicated_helpers_without_drift(self) -> None:
        common_kwargs = {
            "artifact_root": ".synrail",
            "command": "synrail",
            "fallback_command": "./.venv/bin/synrail",
            "repo_native_alpha_command": "python3 alpha.py",
            "workspace_isolation_note": "Parent git repo detected above the project root.",
            "prefer_runtime_helper": True,
        }

        self.assertEqual(
            render_local_workflow_policy(
                heading="## Synrail Local Workflow",
                intro="Use Synrail as the default local control path for this repo.",
                first_command_heading=None,
                first_command_intro="First command for every new task:",
                show_cli_kernel_note=False,
                start_intro="If Synrail shows that no controlled run is active, start one:",
                finish_intro="Before claiming success, run:",
                **common_kwargs,
            ),
            render_gemini_policy_block(**common_kwargs),
        )
        self.assertEqual(
            render_local_workflow_policy(
                heading="## Synrail Local Workflow",
                intro="Use Synrail as the default local control path for this repo.",
                first_command_heading=None,
                first_command_intro="First command for every new task:",
                show_cli_kernel_note=False,
                start_intro="If Synrail shows that no controlled run is active, start one:",
                finish_intro="Before claiming success, run:",
                **common_kwargs,
            ),
            render_claude_policy_block(**common_kwargs),
        )

    def test_check_guidance_surfaces_runtime_helper_for_runtime_evidence_projects(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_check_runtime_guidance_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            (artifact_root / "state.json").write_text(
                json.dumps(
                    {
                        "run_id": "RUN-123",
                        "task_class": "bounded_change",
                        "state": "CLAIMED_NOT_ACCEPTED",
                        "next_safe_step": "attest target surface",
                        "check_count": 0,
                        "proof_bundle": {
                            "status": "MISSING",
                            "missing_sections": [],
                            "structural_status": "MISSING",
                            "semantic_status": "MISSING",
                            "semantically_insufficient_sections": [],
                            "semantic_next_safe_step": "",
                            "artifact_integrity_warning": False,
                        },
                        "integrity": {
                            "status": "UNKNOWN",
                            "exact_task_identity_ok": True,
                            "bootstrap_provenance_ok": True,
                            "bootstrap_provenance_reason": "CONTROLLED_BOOTSTRAP_CONFIRMED",
                        },
                        "closure": {
                            "status": "CLAIMED_NOT_ACCEPTED",
                            "blocking_reason": "",
                            "next_allowed_transition": "CHECK",
                            "narrow_next_safe_step": "",
                            "missing_sections": [],
                        },
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )
            (artifact_root / "bootstrap.json").write_text(
                json.dumps(
                    {
                        "task_identity": "Guide the proof path instead of asking me to invent it.",
                        "prompt_identity": "prompt-123",
                        "target_path": "tests/test_agent_adoption.py",
                        "target_classification": "file",
                        "baseline_identity": "autodetected_python_baseline",
                        "execution_surface_identity": "autodetected_python_worktree",
                        "intended_run_class": "bounded_change",
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )
            (artifact_root / "proof_request.json").write_text(
                json.dumps(
                    {
                        "preferred_artifacts": {
                            "final_result": ".synrail/final_result.json",
                        }
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )
            (artifact_root / "task_identity.txt").write_text("Guide the proof path instead of asking me to invent it.\n")
            (artifact_root / "prompt_identity.txt").write_text("prompt-123\n")
            (artifact_root / "target_identity.txt").write_text("tests/test_agent_adoption.py\n")
            (artifact_root / "acceptance_criteria.json").write_text(json.dumps({"criteria_revision_id": "rev-1"}, ensure_ascii=True) + "\n")
            (artifact_root / "project_profile.json").write_text(
                json.dumps(
                    {
                        "project_root": str(project_root),
                        "prefers_runtime_evidence": True,
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )
            (artifact_root / "final_result.json").write_text('{"status":"starter"}\n')
            (artifact_root / "starter_hashes.json").write_text(
                json.dumps(
                    {
                        "final_result": "2f2fe4f1d7fc4322fd1f8bf5c22de7714f1f3f900c1e499f198ed28d2fd96199"
                    },
                    ensure_ascii=True,
                )
                + "\n"
            )

            stdout = StringIO()
            args = argparse.Namespace(
                artifact_root=str(artifact_root),
                state_file="",
                report_file="",
                output="",
                doctor_file="",
                repair_packet_file="",
                consistency_recovery_file="",
                checkpoint_record_file="",
                checkpoint_id="",
                acceptance_validation_output="",
                project_profile_file="",
                acceptance_criteria_file="",
                target_path="",
                target_classification="",
                baseline_identity="",
                execution_surface_identity="",
                final_result="",
                prompt_identity="",
                task_identity="",
                readback="",
                scenario_proof="",
                plan_output="",
                preparation_receipt_output="",
                preparation_artifact_root="",
                refresh_output="",
                observability_output="",
                artifact_consistency_output="",
                refresh_event_type="",
                refresh_doctor_status="",
                refresh_recovery_status="",
                refresh_reverification_complete=False,
                refresh_use_bundle=False,
                refresh_use_closure=False,
                baseline_file="",
                synrail_file="",
                comparison_output="",
                worked_artifact_output="",
                run_artifact_output="",
                clean_surface=False,
                artifact_viable=False,
                helper_ok=False,
                credentials_ok=False,
                prompt_identity_ok=False,
                artifact_path="",
                helper_path="",
                credential_env=[],
                prompt_identity_file="",
                target_identity_file="",
                coverage_profile_file="",
                coverage_corpus_file="",
                changed_file=[],
                allowed_scope_path=[],
                mode="default",
                final_answer_file="",
                doctor_run_id="",
                doctor_level="",
                bundle_output="",
                closure_output="",
                closure_certificate_output="",
                checkpoint_record_output="",
            )
            with mock.patch("synrail_cli_v0.validate_root_within_project", return_value=None), mock.patch(
                "synrail_cli_v0.validate_check_like_paths",
                return_value=None,
            ), mock.patch("synrail_cli_v0.discover_candidate_file_filtered", return_value=None), mock.patch(
                "synrail_cli_v0.apply_bootstrap_defaults",
                return_value={"status": "VALID", "reason": "CONTROLLED_BOOTSTRAP_CONFIRMED"},
            ), mock.patch("synrail_cli_v0.cmd_thin_output", return_value=0), mock.patch(
                "synrail_cli_v0.current_project_root", return_value=project_root
            ), mock.patch("synrail_cli_v0.Path.cwd", return_value=project_root), redirect_stdout(stdout):
                rc = cmd_check(args)
            self.assertEqual(2, rc)
            rendered = stdout.getvalue()
            self.assertIn("waiting for explicit proof artifacts and local verification evidence", rendered)
            self.assertIn("Need a canonical final_result shape? run synrail final-result-template", rendered)
            self.assertIn("Need a small UI/runtime verification path? run synrail runtime-helper", rendered)
            self.assertTrue(str(args.closure_certificate_output).endswith(".synrail/closure_certificate.json"))
            self.assertTrue(str(args.run_artifact_output).endswith(".synrail/run.json"))

    def test_runtime_helper_marks_examples_as_manual_runtime_evidence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_runtime_helper_text_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)

            with mock.patch("synrail_cli_v0.load_project_profile", return_value={"project_root": str(project_root), "prefers_runtime_evidence": True}):
                helper = runtime_helper_text(root=project_root)

        self.assertIn("manual runtime evidence", helper)
        self.assertIn("curl -s http://localhost:8000/  # then inspect the local response", helper)
        self.assertIn("python3 - <<'PY'", helper)
        self.assertIn("keep verification_command to the direct file-observation allowlist", helper)


if __name__ == "__main__":
    unittest.main()
