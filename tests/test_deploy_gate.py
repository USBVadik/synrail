#!/usr/bin/env python3
"""Tests for the deploy gate — synrail deploy and synrail deploy-check."""

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
DEPLOY_GUARD = REPO_ROOT / "tools" / "reference" / "synrail_deploy_guard.sh"
GUARDED_SIDE_EFFECT = REPO_ROOT / "tools" / "reference" / "synrail_guarded_side_effect_v0.sh"
DEPLOY_EXAMPLES = REPO_ROOT / "examples" / "deploy_guard"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


class DeployGateTests(unittest.TestCase):
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

    def _start_run(self, project_root: Path) -> None:
        result = self.run_alpha(
            "start",
            "--artifact-root", ".synrail",
            "--project-root", str(project_root),
            "--task-identity", "Test deploy gate task.",
            cwd=project_root,
        )
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def run_guard(self, artifact_root: str, *, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(DEPLOY_GUARD), "--artifact-root", artifact_root],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    def run_guarded_side_effect(self, artifact_root: str, *, cwd: Path, command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["bash", str(GUARDED_SIDE_EFFECT), "--artifact-root", artifact_root, "--", *command],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_deploy_blocks_before_acceptance(self) -> None:
        """Deploy must be blocked when run is not CLOSURE_ACCEPTED."""
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_block_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(2, deploy.returncode)
            self.assertIn("deploy blocked", deploy.stdout.lower())
            self.assertIn("CLOSURE_ACCEPTED", deploy.stdout)

    def test_deploy_succeeds_after_acceptance(self) -> None:
        """Deploy must succeed when state is CLOSURE_ACCEPTED."""
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_accept_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            # Set state to CLOSURE_ACCEPTED
            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, deploy.returncode)
            self.assertIn("deploy authorized", deploy.stdout.lower())

            # Verify receipt was written
            receipt = load_json(artifact_root / "deploy_receipt.json")
            self.assertEqual("DEPLOY_AUTHORIZED", receipt["result"])
            self.assertEqual(state["run_id"], receipt["run_id"])
            self.assertEqual((artifact_root / "target_identity.txt").read_text().strip(), receipt["target_identity"])

    def test_deploy_blocks_on_rejected(self) -> None:
        """Deploy must be blocked when state is CLOSURE_REJECTED."""
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_reject_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_REJECTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(2, deploy.returncode)
            self.assertIn("deploy blocked", deploy.stdout.lower())

    def test_deploy_blocks_on_run_id_mismatch(self) -> None:
        """Deploy must be blocked when deploy-run-id doesn't match state."""
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_runid_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                "--deploy-run-id", "WRONG_RUN_ID",
                cwd=project_root,
            )
            self.assertEqual(2, deploy.returncode)
            self.assertIn("deploy blocked", deploy.stdout.lower())

    def test_deploy_dev_mode_returns_json(self) -> None:
        """In dev mode, deploy gate returns structured JSON."""
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_dev_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            # Blocked case
            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                "--mode", "dev",
                cwd=project_root,
            )
            self.assertEqual(2, deploy.returncode)
            result = json.loads(deploy.stdout.strip())
            self.assertEqual("BLOCKED", result["result"])
            self.assertEqual("DEPLOY_REQUIRES_ACCEPTED_CLOSURE", result["reason"])

    def test_deploy_blocks_on_target_identity_mismatch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_target_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                "--deploy-target", "WRONG_TARGET_IDENTITY",
                cwd=project_root,
            )
            self.assertEqual(2, deploy.returncode)
            self.assertIn("deploy blocked", deploy.stdout.lower())

    def test_deploy_check_without_receipt_blocks(self) -> None:
        """deploy-check must block when no deploy receipt exists."""
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_check_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            check = self.run_alpha(
                "deploy-check", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(2, check.returncode)
            result = json.loads(check.stdout.strip())
            self.assertEqual("BLOCKED", result["result"])
            self.assertEqual("NO_DEPLOY_RECEIPT", result["reason"])

    def test_deploy_check_with_valid_receipt_passes(self) -> None:
        """deploy-check must pass when a valid deploy receipt exists for the current run."""
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_check_ok_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            # First deploy to create receipt
            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, deploy.returncode)

            # Then check
            check = self.run_alpha(
                "deploy-check", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, check.returncode)
            result = json.loads(check.stdout.strip())
            self.assertEqual("OK", result["result"])

    def test_deploy_check_blocks_when_current_state_regresses(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_check_regress_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, deploy.returncode)

            state["state"] = "CLOSURE_REJECTED"
            write_json(artifact_root / "state.json", state)

            check = self.run_alpha(
                "deploy-check", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(2, check.returncode)
            result = json.loads(check.stdout.strip())
            self.assertEqual("BLOCKED", result["result"])
            self.assertEqual("DEPLOY_CURRENT_STATE_NOT_ACCEPTED", result["reason"])

    def test_deploy_check_blocks_stale_receipt(self) -> None:
        """deploy-check must block when receipt run_id doesn't match current state."""
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_check_stale_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            # Create receipt for this run
            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, deploy.returncode)

            # Now change the state run_id to simulate a new run
            state["run_id"] = "DIFFERENT_RUN"
            write_json(artifact_root / "state.json", state)

            check = self.run_alpha(
                "deploy-check", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(2, check.returncode)
            result = json.loads(check.stdout.strip())
            self.assertEqual("BLOCKED", result["result"])
            self.assertEqual("DEPLOY_RECEIPT_RUN_ID_STALE", result["reason"])

    def test_deploy_check_blocks_stale_target_identity(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_check_target_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, deploy.returncode)

            (artifact_root / "target_identity.txt").write_text("DIFFERENT_TARGET\n")

            check = self.run_alpha(
                "deploy-check", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(2, check.returncode)
            result = json.loads(check.stdout.strip())
            self.assertEqual("BLOCKED", result["result"])
            self.assertEqual("DEPLOY_RECEIPT_TARGET_IDENTITY_STALE", result["reason"])

    def test_deploy_guard_blocks_when_current_state_regresses(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_guard_regress_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, deploy.returncode)

            state["state"] = "CLOSURE_REJECTED"
            write_json(artifact_root / "state.json", state)

            guard = self.run_guard(".synrail", cwd=project_root)
            self.assertEqual(1, guard.returncode)
            self.assertIn("not 'CLOSURE_ACCEPTED'", guard.stdout)

    def test_deploy_guard_blocks_on_corrupted_deploy_receipt_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_guard_receipt_json_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)
            (artifact_root / "deploy_receipt.json").write_text("{not valid json\n")

            guard = self.run_guard(".synrail", cwd=project_root)
            self.assertEqual(1, guard.returncode)
            self.assertIn("could not parse deploy receipt JSON", guard.stdout)

    def test_deploy_guard_blocks_on_corrupted_state_json(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_deploy_guard_state_json_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, deploy.returncode)
            (artifact_root / "state.json").write_text("{not valid json\n")

            guard = self.run_guard(".synrail", cwd=project_root)
            self.assertEqual(1, guard.returncode)
            self.assertIn("could not parse run state JSON", guard.stdout)

    def test_guarded_side_effect_blocks_without_authorization(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_guarded_side_effect_block_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            guarded = self.run_guarded_side_effect(
                ".synrail",
                cwd=project_root,
                command=["python3", "-c", "print('SIDE_EFFECT_RAN')"],
            )
            self.assertEqual(1, guarded.returncode)
            self.assertIn("DEPLOY BLOCKED", guarded.stdout)
            self.assertNotIn("SIDE_EFFECT_RAN", guarded.stdout)

    def test_guarded_side_effect_runs_after_authorization(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_guarded_side_effect_ok_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            self._start_run(project_root)

            state = load_json(artifact_root / "state.json")
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)

            deploy = self.run_alpha(
                "deploy", "--artifact-root", ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, deploy.returncode)

            guarded = self.run_guarded_side_effect(
                ".synrail",
                cwd=project_root,
                command=["python3", "-c", "print('SIDE_EFFECT_RAN')"],
            )
            self.assertEqual(0, guarded.returncode)
            self.assertIn("SIDE_EFFECT_RAN", guarded.stdout)

    def test_deploy_guard_examples_parse_and_reference_guard_helpers(self) -> None:
        scripts = [
            DEPLOY_EXAMPLES / "deploy_with_synrail_guard.sh",
            DEPLOY_EXAMPLES / "deploy_with_synrail_wrapper.sh",
            DEPLOY_EXAMPLES / "pm2_pre_restart_with_synrail.sh",
            DEPLOY_EXAMPLES / "systemd_restart_with_synrail.sh",
        ]
        for script in scripts:
            self.assertTrue(script.exists(), f"missing example script: {script}")
            parsed = subprocess.run(
                ["bash", "-n", str(script)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, parsed.returncode, parsed.stderr)
            text = script.read_text()
            self.assertTrue(
                "synrail_deploy_guard.sh" in text or "synrail_guarded_side_effect_v0.sh" in text,
                f"example script does not reference a Synrail guard helper: {script}",
            )

        override = DEPLOY_EXAMPLES / "systemd_service_override.conf"
        self.assertTrue(override.exists(), f"missing systemd override example: {override}")
        override_text = override.read_text()
        self.assertIn("ExecStartPre=", override_text)
        self.assertIn("synrail_deploy_guard.sh", override_text)


if __name__ == "__main__":
    unittest.main()
