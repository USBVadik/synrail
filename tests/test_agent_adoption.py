#!/usr/bin/env python3
"""Smoke tests for repo-native agent adoption files."""

from __future__ import annotations

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

from synrail_cli_v0 import (
    cmd_install_agent_files,
    preferred_synrail_command,
    preferred_synrail_fallback_command,
)


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
            self.assertIn("Do not skip Synrail", agents)
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", agents)
            self.assertIn("do not send a final success/completion answer", agents)
            self.assertIn("functionally complete, 100% done", agents)
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
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", gemini)
            self.assertIn("do not send a final success/completion answer", gemini)
            self.assertIn("functionally complete, 100% done", gemini)
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
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", claude)
            self.assertIn("do not send a final success/completion answer", claude)
            self.assertIn("functionally complete, 100% done", claude)
            self.assertIn("./.venv/bin/synrail", claude)
            self.assertIn("python3 alpha.py", claude)
            self.assertIn("approval or permission wall", claude)
            self.assertIn("Repo-Local Fallback", claude)
            self.assertIn("python3 alpha.py check", claude)

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
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", gemini)
            self.assertIn("do not send a final success/completion answer", gemini)
            self.assertIn("Keep repo instructions portable: prefer `synrail`", gemini)
            self.assertIn("approval or permission wall", gemini)
            self.assertIn("# Existing Claude Context", claude)
            self.assertIn("<!-- SYNRAIL_CLAUDE_START -->", claude)
            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", claude)
            self.assertIn("do not send a final success/completion answer", claude)
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
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", (project_root / "GEMINI.md").read_text())
            self.assertNotIn("<!-- SYNRAIL_CLAUDE_START -->", (project_root / "CLAUDE.md").read_text())
            self.assertIn("Use Synrail as the default local control path", (project_root / "CLAUDE.md").read_text())
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", (project_root / "CLAUDE.md").read_text())
            self.assertIn("Only `Status: Accepted` means the task may be reported as complete.", (project_root / "CLAUDE.md").read_text())

    def test_install_agent_files_adds_nested_git_and_runtime_notes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_agent_nested_git_") as tmpdir:
            parent_root = Path(tmpdir) / "parent"
            project_root = parent_root / "project"
            (parent_root / ".git").mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)

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


if __name__ == "__main__":
    unittest.main()
