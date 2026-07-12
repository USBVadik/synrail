#!/usr/bin/env python3
"""Regression anchor for the P0 behavioral-claim gap.

Reproduced black-box on 82f3d71: a task requires the unit tests to pass,
the real unittest run exits 1, the agent records a valid read-only grep as
proof, and `synrail check` returns `Status: Accepted`.

The verification recheck allowlist (grep/cat/head/tail/git) never re-runs
tests, and closure's VERIFICATION_RECHECK_NOT_EXECUTED repair step tells the
agent to substitute an allowed read-only command. So a behavioral claim
("tests pass") can earn acceptance while the behavior is false.

Two tests pin this gap from both sides:

- test_current_behavior_accepts_failing_tests_with_substituted_proof
  characterizes today's behavior. It passes now. It MUST start failing when
  operator-owned verification profiles land; delete it at that point.

- test_failing_required_tests_must_not_reach_accepted asserts the desired
  behavior and is marked expectedFailure. When verification profiles land it
  will unexpectedly pass; remove the expectedFailure marker at that point.

The fixture writes `synrail.toml` with the agreed Verification Profiles v1
shape ([verification.unit] argv/timeout_seconds/required). Today Synrail
ignores that file. If the implementation chooses a different config path or
schema, update the fixture here first, then implement against it.
"""

from __future__ import annotations

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
VERIFICATION_PROFILE = (
    "[verification.unit]\n"
    'argv = ["python", "-m", "unittest", "test_app"]\n'
    "timeout_seconds = 300\n"
    "required = true\n"
)
TASK_IDENTITY = "Fix add() in app.py so the unit tests in test_app.py pass."


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


class BehavioralClaimGapTests(unittest.TestCase):
    def run_alpha(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ALPHA_ENTRY), *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    def _run_substituted_proof_scenario(self, tmpdir: str) -> subprocess.CompletedProcess[str]:
        """Build the bypass scenario and return the final `synrail check` result.

        Every step before the final check is asserted loudly so fixture rot
        cannot hide inside the expectedFailure test.
        """
        project_root = Path(tmpdir) / "project"
        project_root.mkdir(parents=True, exist_ok=True)

        (project_root / "app.py").write_text(BUGGY_APP)
        (project_root / "test_app.py").write_text(UNIT_TEST)
        (project_root / "synrail.toml").write_text(VERIFICATION_PROFILE)
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

        (project_root / "app.py").write_text(WRONG_FIX_APP)

        real_tests = run([sys.executable, "-m", "unittest", "test_app"], cwd=project_root)
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

        return self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)

    def test_current_behavior_accepts_failing_tests_with_substituted_proof(self) -> None:
        """Characterization of the open P0 gap; delete once profiles land.

        This test passing is NOT an endorsement. It exists so the gap cannot
        silently change shape, and so fixture breakage shows up here instead
        of vanishing into the expectedFailure test below.
        """
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            check = self._run_substituted_proof_scenario(tmpdir)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertIn("Status: Accepted", check.stdout)

    @unittest.expectedFailure
    def test_failing_required_tests_must_not_reach_accepted(self) -> None:
        """Desired behavior: remove expectedFailure when profiles land.

        With a required verification profile whose command fails, check must
        not print `Status: Accepted` and must exit non-zero.
        """
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            check = self._run_substituted_proof_scenario(tmpdir)
            self.assertNotIn(
                "Status: Accepted",
                check.stdout,
                "failing required tests earned acceptance via substituted read-only proof",
            )
            self.assertNotEqual(
                0,
                check.returncode,
                "check must fail closed while the required verification profile is red",
            )


if __name__ == "__main__":
    unittest.main()
