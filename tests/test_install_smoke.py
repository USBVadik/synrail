#!/usr/bin/env python3
"""Install smoke for the supported Synrail tester path."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
INSTALLER = REPO_ROOT / "tools" / "reference" / "synrail_install_v0.py"


class InstallSmokeTests(unittest.TestCase):
    def _assert_installed_start_path(self, synrail_bin: Path, project_root: Path) -> None:
        artifact_root = project_root / ".synrail"

        help_result = subprocess.run(
            [str(synrail_bin), "start", "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--project-root", help_result.stdout)
        self.assertIn("--task-identity", help_result.stdout)
        self.assertIn("task_request", help_result.stdout)

        project_root.mkdir(parents=True, exist_ok=True)
        start_result = subprocess.run(
            [
                str(synrail_bin),
                "start",
                "install smoke",
            ],
            check=True,
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        self.assertIn("Controlled run started.", start_result.stdout)
        self.assertIn(
            "Do this now: make the bounded change, run local verification, then edit only the starter proof files below in place. Leave every other surface unchanged.",
            start_result.stdout,
        )
        self.assertIn("Starter proof files are ready for this run.", start_result.stdout)
        self.assertIn("Artifact root: .synrail", start_result.stdout)
        self.assertIn("Then run: synrail check", start_result.stdout)
        self.assertTrue((artifact_root / "state.json").exists())
        self.assertTrue((artifact_root / "acceptance_criteria.json").exists())
        self.assertTrue((artifact_root / "project_profile.json").exists())
        self.assertTrue((artifact_root / "bootstrap.json").exists())
        self.assertTrue((artifact_root / "proof_request.json").exists())
        self.assertTrue((artifact_root / "final_result.json").exists())
        self.assertTrue((artifact_root / "readback.txt").exists())
        self.assertTrue((artifact_root / "scenario_proof.txt").exists())
        self.assertTrue((artifact_root / "target_identity.txt").exists())
        self.assertTrue((artifact_root / "task_identity.txt").exists())
        self.assertTrue((artifact_root / "prompt_identity.txt").exists())

    def test_supported_installer_boots_synrail_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self._assert_installed_start_path(
                venv_dir / "bin" / "synrail",
                project_root,
            )

    def test_supported_installer_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_editable_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                ["python3", str(INSTALLER), "--venv", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self._assert_installed_start_path(
                venv_dir / "bin" / "synrail",
                project_root,
            )

    def test_supported_installer_can_install_agent_files_into_project(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_agent_files_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "GEMINI.md").write_text("# Existing Gemini Context\n\nKeep this repo focused.\n")

            result = subprocess.run(
                [
                    "python3",
                    str(INSTALLER),
                    "--venv",
                    str(venv_dir),
                    "--project-root",
                    str(project_root),
                ],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            self.assertIn("Agent adoption files are ready.", result.stdout)
            self.assertIn("Agent files installed into:", result.stdout)
            self.assertIn("Quick status: run `synrail` inside your project.", result.stdout)
            self.assertIn('Start a run: `synrail start "Describe the bounded local change."`', result.stdout)
            self.assertTrue((project_root / "AGENTS.md").exists())
            self.assertTrue((project_root / "CLAUDE.md").exists())
            gemini = (project_root / "GEMINI.md").read_text()
            claude = (project_root / "CLAUDE.md").read_text()
            self.assertIn("# Existing Gemini Context", gemini)
            self.assertIn("<!-- SYNRAIL_GEMINI_START -->", gemini)
            self.assertIn("Use Synrail as the default local control path", gemini)
            self.assertIn("cheapest honest order", gemini)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", gemini)
            self.assertIn("Do not turn project recall into repo archaeology.", gemini)
            self.assertIn("Use Synrail as the default local control path", claude)
            self.assertIn("cheapest honest order", claude)
            self.assertIn("Do not create helper scripts or make edits for an orientation-only question.", claude)


if __name__ == "__main__":
    unittest.main()
