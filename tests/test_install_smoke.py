#!/usr/bin/env python3
"""Install smoke for the supported Synrail tester path."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallSmokeTests(unittest.TestCase):
    def test_supported_install_path_boots_synrail_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"
            artifact_root = project_root / ".synrail"

            subprocess.run(
                ["python3", "-m", "venv", "--system-site-packages", str(venv_dir)],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    str(venv_dir / "bin" / "python"),
                    "-m",
                    "pip",
                    "install",
                    str(REPO_ROOT),
                    "--no-build-isolation",
                ],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )

            help_result = subprocess.run(
                [str(venv_dir / "bin" / "synrail"), "start", "--help"],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertIn("--project-root", help_result.stdout)
            self.assertIn("--task-identity", help_result.stdout)

            project_root.mkdir(parents=True, exist_ok=True)
            start_result = subprocess.run(
                [
                    str(venv_dir / "bin" / "synrail"),
                    "start",
                    "--artifact-root",
                    ".synrail",
                    "--project-root",
                    str(project_root),
                    "--task-identity",
                    "install smoke",
                ],
                check=True,
                cwd=project_root,
                capture_output=True,
                text=True,
            )

            self.assertIn("Controlled run started.", start_result.stdout)
            self.assertIn("Artifact root: .synrail", start_result.stdout)
            self.assertTrue((artifact_root / "state.json").exists())
            self.assertTrue((artifact_root / "acceptance_criteria.json").exists())
            self.assertTrue((artifact_root / "project_profile.json").exists())
            self.assertTrue((artifact_root / "bootstrap.json").exists())
            self.assertTrue((artifact_root / "proof_request.json").exists())
            self.assertTrue((artifact_root / "target_identity.txt").exists())
            self.assertTrue((artifact_root / "task_identity.txt").exists())
            self.assertTrue((artifact_root / "prompt_identity.txt").exists())


if __name__ == "__main__":
    unittest.main()
