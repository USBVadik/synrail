#!/usr/bin/env python3
"""Smoke test for the current external alpha tester pack contour."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


class AlphaTestPackSmokeTests(unittest.TestCase):
    def run_alpha(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ALPHA_ENTRY), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_current_external_alpha_pack_non_green_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_alpha_pack_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = Path(tmpdir) / "lane"
            project_root.mkdir(parents=True, exist_ok=True)

            init = self.run_alpha(
                "init",
                "--artifact-root",
                str(artifact_root),
                "--project-root",
                str(project_root),
                "--task-identity",
                "Reject a plain-text final result and keep the repair bounded.",
                "--telemetry-opt-in",
                "--tester-id",
                "alpha_pack_smoke",
            )
            self.assertEqual(0, init.returncode, init.stdout + init.stderr)
            self.assertTrue((artifact_root / "state.json").exists())
            self.assertTrue((artifact_root / "acceptance_criteria.json").exists())
            self.assertTrue((artifact_root / "telemetry" / "config.json").exists())

            (artifact_root / "final_result.txt").write_text(
                "Implemented the change and confirmed it locally.\n"
            )

            check = self.run_alpha("check", "--artifact-root", str(artifact_root))
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)

            thin_output = load_json(artifact_root / "thin_output.json")
            self.assertEqual("PROOF_INVALID", thin_output["outcome_class"])

            repair_step = self.run_alpha("repair-step", "--artifact-root", str(artifact_root))
            self.assertEqual(0, repair_step.returncode, repair_step.stdout + repair_step.stderr)
            self.assertIn("repair the final result artifact", repair_step.stdout)

            prompt = load_json(artifact_root / "prompt.json")
            self.assertEqual("repair_final_result_artifact", prompt["current_step_id"])
            self.assertIn("final_result_payload", prompt["allowed_scope"])

            telemetry_export = self.run_alpha("telemetry", "export", "--artifact-root", str(artifact_root))
            self.assertEqual(0, telemetry_export.returncode, telemetry_export.stdout + telemetry_export.stderr)

            session_replay = load_json(artifact_root / "telemetry" / "session_replay.json")
            issue_body = (artifact_root / "telemetry" / "github_issue.md").read_text()

            self.assertEqual("PROOF_INVALID", session_replay["latest_result"])
            self.assertIn("repair the final result artifact", session_replay["next_safe_step"])
            self.assertIn("# Synrail Alpha Telemetry", issue_body)
            self.assertIn("INVALID_PROOF_BUNDLE", issue_body)


if __name__ == "__main__":
    unittest.main()
