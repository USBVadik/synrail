#!/usr/bin/env python3
"""Regression coverage for the behavioral-claim gap closed by verification profiles.

Reproduced black-box on 82f3d71: a task required the unit tests to pass, the
real unittest run exited 1, the agent recorded a valid read-only grep as
proof, and `synrail check` returned `Status: Accepted`. The verification
recheck allowlist (grep/cat/head/tail/git) never re-ran tests, so a
behavioral claim could earn acceptance while the behavior was false.

Operator-owned verification profiles close that bypass: `synrail.toml`
locks the approved commands at start, `synrail verify` re-executes them and
writes signed receipts, and check refuses acceptance while any required
profile lacks a fresh green receipt.

Status assertions compare whole stdout lines because the final-answer guard
text legitimately contains the substring "Status: Accepted".
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"

BUGGY_APP = "def add(a, b):\n    return a - b\n"
WRONG_FIX_APP = (
    "def add(a, b):\n"
    "    # optimized fast path\n"
    "    return a - b\n"
)
REAL_FIX_APP = (
    "def add(a, b):\n"
    "    # optimized fast path\n"
    "    return a + b\n"
)
UNIT_TEST = (
    "import unittest\n"
    "\n"
    "from app import add\n"
    "\n"
    "\n"
    "class AddTests(unittest.TestCase):\n"
    "    def test_add(self):\n"
    "        self.assertEqual(5, add(2, 3))\n"
    "\n"
    "\n"
    'if __name__ == "__main__":\n'
    "    unittest.main()\n"
)
TASK_IDENTITY = "Fix add() in app.py so the unit tests in test_app.py pass."


def verification_profile_toml() -> str:
    # The operator approves an absolute interpreter path; json.dumps produces
    # a valid TOML basic string for it on every platform.
    # -B keeps bytecode caching out of the fixture: the wrong and the real
    # fix have identical size and can land within one mtime granule.
    return (
        "[verification.unit]\n"
        f'argv = [{json.dumps(sys.executable)}, "-B", "-m", "unittest", "test_app"]\n'
        "timeout_seconds = 300\n"
        "required = true\n"
    )


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def stdout_lines(completed: subprocess.CompletedProcess[str]) -> set[str]:
    return {line.strip() for line in completed.stdout.splitlines()}


class BehavioralClaimGapTests(unittest.TestCase):
    def run_alpha(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ALPHA_ENTRY), *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    def _start_bypass_scenario(self, tmpdir: str) -> Path:
        """Seed the repo, start a controlled run, apply a wrong fix, record grep proof."""
        project_root = Path(tmpdir) / "project"
        project_root.mkdir(parents=True, exist_ok=True)

        (project_root / "app.py").write_text(BUGGY_APP)
        (project_root / "test_app.py").write_text(UNIT_TEST)
        (project_root / "synrail.toml").write_text(verification_profile_toml())
        (project_root / ".gitignore").write_text("__pycache__/\n")

        git_init = run(["git", "init"], cwd=project_root)
        self.assertEqual(0, git_init.returncode, git_init.stdout + git_init.stderr)
        git_add = run(
            ["git", "add", "app.py", "test_app.py", "synrail.toml", ".gitignore"],
            cwd=project_root,
        )
        self.assertEqual(0, git_add.returncode, git_add.stdout + git_add.stderr)
        git_commit = run(
            [
                "git",
                "-c",
                "user.name=Synrail Tests",
                "-c",
                "user.email=synrail-tests@example.com",
                "commit",
                "-m",
                "seed",
            ],
            cwd=project_root,
        )
        self.assertEqual(0, git_commit.returncode, git_commit.stdout + git_commit.stderr)

        start = self.run_alpha(
            "start",
            "--artifact-root",
            ".synrail",
            "--project-root",
            str(project_root),
            "--task-identity",
            TASK_IDENTITY,
            cwd=project_root,
        )
        self.assertEqual(0, start.returncode, start.stdout + start.stderr)
        self.assertIn("Verification profiles locked for this run: unit", start.stdout)

        (project_root / "app.py").write_text(WRONG_FIX_APP)

        real_tests = run([sys.executable, "-B", "-m", "unittest", "test_app"], cwd=project_root)
        self.assertEqual(
            1,
            real_tests.returncode,
            "fixture must keep the real unit tests failing: "
            + real_tests.stdout
            + real_tests.stderr,
        )

        record = self.run_alpha(
            "record",
            "app.py",
            "--artifact-root",
            ".synrail",
            "--summary",
            "Fixed add() so the unit tests pass.",
            "--verify",
            "grep -n 'optimized fast path' app.py",
            cwd=project_root,
        )
        self.assertEqual(0, record.returncode, record.stdout + record.stderr)
        return project_root

    def test_failing_required_tests_cannot_reach_accepted_via_substituted_proof(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertNotIn("Status: Accepted", stdout_lines(check))
            self.assertIn("Status: Verification Required", stdout_lines(check))
            report = json.loads((project_root / ".synrail" / "report.json").read_text())
            self.assertEqual("BLOCKED", report["result"])
            self.assertEqual("VERIFICATION_RECEIPT_MISSING", report["reason"])

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("Verification unit: FAIL (exit 1)", verify.stdout)

            check_after_red_verify = self.run_alpha(
                "check", "--artifact-root", ".synrail", cwd=project_root
            )
            self.assertNotIn("Status: Accepted", stdout_lines(check_after_red_verify))
            self.assertIn("Status: Verification Failed", stdout_lines(check_after_red_verify))
            report = json.loads((project_root / ".synrail" / "report.json").read_text())
            self.assertEqual("VERIFICATION_FAILED", report["reason"])

    def test_honest_fix_with_green_verify_reaches_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            (project_root / "app.py").write_text(REAL_FIX_APP)
            record = self.run_alpha(
                "record",
                "app.py",
                "--artifact-root",
                ".synrail",
                "--summary",
                "Fixed add() so the unit tests pass.",
                "--verify",
                "grep -n 'optimized fast path' app.py",
                cwd=project_root,
            )
            self.assertEqual(0, record.returncode, record.stdout + record.stderr)

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("Verification unit: GREEN", verify.stdout)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertIn("Status: Accepted", stdout_lines(check))

    def test_editing_code_after_green_verify_goes_stale(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            (project_root / "app.py").write_text(REAL_FIX_APP)
            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)

            (project_root / "app.py").write_text(WRONG_FIX_APP)
            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertNotIn("Status: Accepted", stdout_lines(check))
            report = json.loads((project_root / ".synrail" / "report.json").read_text())
            self.assertEqual("VERIFICATION_RECEIPT_STALE", report["reason"])

    def test_config_change_mid_run_blocks_check_and_verify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            relaxed = verification_profile_toml().replace("required = true", "required = false")
            (project_root / "synrail.toml").write_text(relaxed)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertNotIn("Status: Accepted", stdout_lines(check))
            self.assertIn("Status: Verification Config Changed", stdout_lines(check))
            report = json.loads((project_root / ".synrail" / "report.json").read_text())
            self.assertEqual("VERIFICATION_CONFIG_CHANGED", report["reason"])

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("VERIFICATION_CONFIG_CHANGED", verify.stdout)

    def test_tampered_receipt_blocks_acceptance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)

            receipts_path = project_root / ".synrail" / "verification_receipts.json"
            payload = json.loads(receipts_path.read_text())
            payload["receipts"]["unit"]["exit_code"] = 0
            receipts_path.write_text(json.dumps(payload, indent=2) + "\n")

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertNotIn("Status: Accepted", stdout_lines(check))
            report = json.loads((project_root / ".synrail" / "report.json").read_text())
            self.assertEqual("VERIFICATION_RECEIPT_INVALID", report["reason"])


if __name__ == "__main__":
    unittest.main()
