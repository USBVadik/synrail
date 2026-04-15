#!/usr/bin/env python3
"""Install smoke for the supported Synrail tester path."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallSmokeTests(unittest.TestCase):
    def _assert_installed_start_path(self, python_bin: Path, synrail_bin: Path, project_root: Path) -> None:
        artifact_root = project_root / ".synrail"

        help_result = subprocess.run(
            [str(synrail_bin), "start", "--help"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("--project-root", help_result.stdout)
        self.assertIn("--task-identity", help_result.stdout)

        project_root.mkdir(parents=True, exist_ok=True)
        start_result = subprocess.run(
            [
                str(synrail_bin),
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
        self.assertIn(
            "Do this now: Edit only the starter proof files below in place. Leave every other surface unchanged.",
            start_result.stdout,
        )
        self.assertIn("Starter proof files are ready for this run.", start_result.stdout)
        self.assertIn("Artifact root: .synrail", start_result.stdout)
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

    def test_default_install_path_boots_synrail_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            subprocess.run(
                ["python3", "-m", "venv", str(venv_dir)],
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
                ],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self._assert_installed_start_path(
                venv_dir / "bin" / "python",
                venv_dir / "bin" / "synrail",
                project_root,
            )

    def test_editable_install_path_boots_synrail_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_editable_install_smoke_") as tmpdir:
            root = Path(tmpdir)
            venv_dir = root / "venv"
            project_root = root / "project"

            subprocess.run(
                ["python3", "-m", "venv", str(venv_dir)],
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
                    "-e",
                    str(REPO_ROOT),
                ],
                check=True,
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            self._assert_installed_start_path(
                venv_dir / "bin" / "python",
                venv_dir / "bin" / "synrail",
                project_root,
            )


if __name__ == "__main__":
    unittest.main()
