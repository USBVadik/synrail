#!/usr/bin/env python3
"""Smoke tests for controlled start, bootstrap gating, and proof guidance."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


class ControlledStartSmokeTests(unittest.TestCase):
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

    def test_start_creates_bootstrap_and_proof_request(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_controlled_start_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Keep this run controlled from the first action.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            self.assertIn("Controlled run started.", start.stdout)
            self.assertIn(
                "Do this now: Edit only the starter proof files below in place. Leave every other surface unchanged.",
                start.stdout,
            )
            self.assertIn("Starter proof files are ready for this run.", start.stdout)
            self.assertTrue((artifact_root / "bootstrap.json").exists())
            self.assertTrue((artifact_root / "bootstrap_validation.json").exists())
            self.assertTrue((artifact_root / "proof_request.json").exists())
            self.assertTrue((artifact_root / "target_identity.txt").exists())
            self.assertTrue((artifact_root / "final_result.json").exists())
            self.assertTrue((artifact_root / "readback.txt").exists())
            self.assertTrue((artifact_root / "scenario_proof.txt").exists())

            bootstrap = load_json(artifact_root / "bootstrap.json")
            validation = load_json(artifact_root / "bootstrap_validation.json")
            proof_request = load_json(artifact_root / "proof_request.json")

            self.assertTrue(bootstrap["controlled_mode"])
            self.assertEqual("VALID", validation["status"])
            self.assertEqual("edit_in_place", proof_request["starter_mode"])
            self.assertEqual(".synrail/final_result.json", proof_request["preferred_artifacts"]["final_result"])
            self.assertEqual(64, len(proof_request["starter_hashes"]["final_result"]))

    def test_check_after_plain_init_requires_controlled_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_bootstrap_block_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            init = self.run_alpha(
                "init",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Do not allow post-hoc legalization.",
                cwd=project_root,
            )
            self.assertEqual(0, init.returncode, init.stdout + init.stderr)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertIn("Controlled Run Required", check.stdout)
            self.assertIn("Next command: synrail start", check.stdout)

            thin_output = load_json(artifact_root / "thin_output.json")
            state = load_json(artifact_root / "state.json")

            self.assertEqual("NON_GREEN", thin_output["outcome_class"])
            self.assertEqual("synrail start", thin_output["next_command"])
            self.assertFalse(state["integrity"]["bootstrap_provenance_ok"])
            self.assertEqual("CONTROLLED_BOOTSTRAP_NOT_CONFIRMED", state["closure"]["blocking_reason"])

    def test_check_without_final_result_uses_proof_request_guidance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_proof_request_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Guide the proof path instead of asking me to invent it.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("waiting for the proof artifacts", check.stdout)
            self.assertIn("edit the starter proof files already placed", check.stdout)
            self.assertIn("final_result: .synrail/final_result.json", check.stdout)
            self.assertIn("readback: .synrail/readback.txt", check.stdout)
            self.assertIn("scenario_proof: .synrail/scenario_proof.txt", check.stdout)

    def test_check_blocks_remote_target_as_unsupported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_remote_unsupported_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Do not pretend that a remote target lane is supported.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            (artifact_root / "final_result.txt").write_text("Implemented the change and confirmed it locally.\n")

            check = self.run_alpha(
                "check",
                "--artifact-root",
                ".synrail",
                "--target-path",
                "ssh://remote-host/example-repo",
                "--target-classification",
                "remote_target",
                cwd=project_root,
            )
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertIn("Remote Target Not Supported Yet", check.stdout)

            report = load_json(artifact_root / "report.json")
            thin_output = load_json(artifact_root / "thin_output.json")

            self.assertEqual("REMOTE_TARGET_UNSUPPORTED", report["reason"])
            self.assertEqual("NON_GREEN", thin_output["outcome_class"])
            self.assertEqual("", thin_output["next_command"])
            self.assertFalse((artifact_root / "prompt.json").exists())

    def test_repair_step_names_readback_starter_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_readback_focus_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Point the next repair at the exact starter proof file that is still missing.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "DONE",
                    "summary": "Implemented the bounded change.",
                    "modified_files": ["app.py"],
                    "git_diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@\n+patched\n",
                    "cleanup_status": {
                        "success": True,
                        "summary": "workspace is clean after the bounded change",
                    },
                },
            )
            (artifact_root / "scenario_proof.txt").write_text(
                "Scenario passed on the attested surface and confirmed the expected behavior.\n"
            )

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)

            repair_step = self.run_alpha("repair-step", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, repair_step.returncode, repair_step.stdout + repair_step.stderr)
            self.assertIn(".synrail/readback.txt", repair_step.stdout)
            self.assertIn("Repair target: record readback in .synrail/readback.txt", repair_step.stdout)
            self.assertIn(
                "Do this now: Record readback in .synrail/readback.txt. Leave every other proof surface unchanged.",
                repair_step.stdout,
            )

            prompt = load_json(artifact_root / "prompt.json")
            self.assertEqual("complete_missing_proof_sections", prompt["current_step_id"])
            self.assertEqual("readback_record", prompt["current_step_subsurface_id"])
            self.assertEqual(".synrail/readback.txt", prompt["current_step_target_path"])
            self.assertEqual("record readback in .synrail/readback.txt", prompt["current_step_focus_summary"])
            self.assertEqual(
                "Record readback in .synrail/readback.txt. Leave every other proof surface unchanged.",
                prompt["current_step_action_instruction"],
            )
            self.assertIn("readback", prompt["current_step_label"])


    def test_start_after_terminal_state_auto_clears_proof(self) -> None:
        """After CLOSURE_ACCEPTED, next synrail start should work without manual cleanup."""
        with tempfile.TemporaryDirectory(prefix="synrail_restart_after_terminal_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            # First run: synrail start
            start1 = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "First task for terminal state test.",
                cwd=project_root,
            )
            self.assertEqual(0, start1.returncode, start1.stdout + start1.stderr)

            # Simulate completed run: modify proof files and set terminal state
            state = load_json(artifact_root / "state.json")
            first_run_id = state["run_id"]
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)
            (artifact_root / "final_result.json").write_text(
                json.dumps({"status": "DONE", "summary": "completed"}) + "\n"
            )
            (artifact_root / "readback.txt").write_text("Confirmed change in source.\n")
            (artifact_root / "scenario_proof.txt").write_text("Scenario passed.\n")

            # Second run: synrail start should auto-clear and succeed
            start2 = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "Second task after terminal state.",
                cwd=project_root,
            )
            self.assertEqual(0, start2.returncode, start2.stdout + start2.stderr)
            self.assertIn("Controlled run started.", start2.stdout)
            next_state = load_json(artifact_root / "state.json")
            self.assertNotEqual(first_run_id, next_state["run_id"])

    def test_start_after_active_run_still_blocks(self) -> None:
        """Mid-run proof artifacts should still block a new start."""
        with tempfile.TemporaryDirectory(prefix="synrail_restart_blocks_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start1 = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "Active run that should not be overwritten.",
                cwd=project_root,
            )
            self.assertEqual(0, start1.returncode, start1.stdout + start1.stderr)

            # Simulate active run: modify proof but state is NOT terminal
            state = load_json(artifact_root / "state.json")
            self.assertNotIn(state["state"], ("CLOSURE_ACCEPTED", "CLOSURE_REJECTED"))
            (artifact_root / "final_result.json").write_text(
                json.dumps({"status": "DONE", "summary": "in progress"}) + "\n"
            )

            # Second start should be blocked
            start2 = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "Should not overwrite active run.",
                cwd=project_root,
            )
            self.assertEqual(2, start2.returncode)
            self.assertIn("proof artifacts already exist", start2.stdout)


if __name__ == "__main__":
    unittest.main()
