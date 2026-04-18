#!/usr/bin/env python3
"""Smoke tests for repo-native agent adoption files."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_cli_v0 import preferred_synrail_command


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
            self.assertIn("Do not skip Synrail", agents)
            self.assertNotIn('ARTIFACT_ROOT="$(pwd)/.synrail"', agents)
            self.assertIn("run `synrail` in this repo", result.stdout)

            self.assertIn("Use Synrail as the default local control path", gemini)
            self.assertIn("For every new user task, run Synrail first", gemini)
            self.assertIn("If the user asks what this project is, where work stopped, or what the current status is", gemini)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", gemini)
            self.assertIn('synrail start "Describe the bounded local change."', gemini)
            self.assertIn("fix only what check tells you to fix", gemini)

            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("For every new user task, run Synrail first", claude)
            self.assertIn("If the user asks what this project is, where work stopped, or what the current status is", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)
            self.assertIn('synrail start "Describe the bounded local change."', claude)
            self.assertIn("fix only what check tells you to fix", claude)

    def test_prefers_explicit_binary_when_path_points_elsewhere(self) -> None:
        with mock.patch("synrail_cli_v0.sys.argv", ["/opt/synrail/.venv/bin/synrail"]), mock.patch(
            "synrail_cli_v0.shutil.which",
            return_value="/usr/local/bin/synrail",
        ):
            self.assertEqual("/opt/synrail/.venv/bin/synrail", preferred_synrail_command())

    def test_prefers_explicit_binary_even_when_path_matches(self) -> None:
        with mock.patch("synrail_cli_v0.sys.argv", ["/opt/synrail/.venv/bin/synrail"]), mock.patch(
            "synrail_cli_v0.shutil.which",
            return_value="/opt/synrail/.venv/bin/synrail",
        ):
            self.assertEqual("/opt/synrail/.venv/bin/synrail", preferred_synrail_command())

    def test_prefers_sibling_synrail_when_console_wrapper_uses_python_dash_c(self) -> None:
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
                self.assertEqual(str(synrail_path.resolve()), preferred_synrail_command())

    def test_install_agent_files_is_idempotent_and_merges_existing_gemini_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_agent_adoption_force_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

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
            self.assertIn("# Existing Claude Context", claude)
            self.assertIn("<!-- SYNRAIL_CLAUDE_START -->", claude)
            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)

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
            self.assertNotIn("<!-- SYNRAIL_CLAUDE_START -->", (project_root / "CLAUDE.md").read_text())
            self.assertIn("Use Synrail as the default local control path", (project_root / "CLAUDE.md").read_text())
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", (project_root / "CLAUDE.md").read_text())

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


if __name__ == "__main__":
    unittest.main()
