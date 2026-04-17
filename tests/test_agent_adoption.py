#!/usr/bin/env python3
"""Smoke tests for repo-native agent adoption files."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"


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

            agents = (project_root / "AGENTS.md").read_text()
            gemini = (project_root / "GEMINI.md").read_text()

            self.assertIn("First Step On Every New Task", agents)
            self.assertIn("synrail", agents)
            self.assertIn('synrail start "Describe the bounded local change."', agents)
            self.assertIn("synrail check", agents)
            self.assertIn("Do not skip Synrail", agents)
            self.assertNotIn('ARTIFACT_ROOT="$(pwd)/.synrail"', agents)

            self.assertIn("Use Synrail as the default local control path", gemini)
            self.assertIn("For every new user task, run Synrail first", gemini)
            self.assertIn('synrail start "Describe the bounded local change."', gemini)
            self.assertIn("synrail repair-step", gemini)

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

            (project_root / "GEMINI.md").write_text("# Existing Gemini Context\n\nKeep this repo focused on product work.\n")

            merged = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
            )
            self.assertEqual(0, merged.returncode, merged.stdout + merged.stderr)
            self.assertIn("GEMINI.md: appended", merged.stdout)
            gemini = (project_root / "GEMINI.md").read_text()
            self.assertIn("# Existing Gemini Context", gemini)
            self.assertIn("<!-- SYNRAIL_GEMINI_START -->", gemini)
            self.assertIn("Use Synrail as the default local control path", gemini)

            forced = self.run_alpha(
                "install-agent-files",
                "--project-root",
                str(project_root),
                "--force",
            )
            self.assertEqual(0, forced.returncode, forced.stdout + forced.stderr)
            self.assertIn("GEMINI.md: written", forced.stdout)
            self.assertIn("GEMINI.md backup:", forced.stdout)
            backups = list(project_root.glob("GEMINI.md.synrail.bak.*"))
            self.assertEqual(1, len(backups))
            self.assertIn("# Existing Gemini Context", backups[0].read_text())
            self.assertNotIn("<!-- SYNRAIL_GEMINI_START -->", (project_root / "GEMINI.md").read_text())
            self.assertIn("Use Synrail as the default local control path", (project_root / "GEMINI.md").read_text())


if __name__ == "__main__":
    unittest.main()
