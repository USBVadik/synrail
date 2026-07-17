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
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from tools.reference.synrail_verification_profile_v0 import (
    OUTPUT_EXCERPT_BYTES,
    SYNRAIL_PYTHON_ARGV0,
    _terminate_process_tree,
    fingerprints_match,
    workspace_fingerprint,
)

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
    # The operator approves Synrail's interpreter alias; controlled start still
    # locks the concrete interpreter realpath and content hash.
    # -B keeps bytecode caching out of the fixture: the wrong and the real
    # fix have identical size and can land within one mtime granule.
    return (
        "[verification.unit]\n"
        f'argv = [{json.dumps(SYNRAIL_PYTHON_ARGV0)}, "-B", "-m", "unittest", "test_app"]\n'
        "timeout_seconds = 300\n"
        "required = true\n"
    )


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def stdout_lines(completed: subprocess.CompletedProcess[str]) -> set[str]:
    return {line.strip() for line in completed.stdout.splitlines()}


class BehavioralClaimGapTests(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix", "process-group cleanup is POSIX-specific")
    def test_process_group_cleanup_treats_permission_error_as_best_effort(self) -> None:
        process = mock.Mock()
        process.pid = 12345
        process.poll.return_value = 0

        with (
            mock.patch(
                "tools.reference.synrail_verification_profile_v0.os.killpg",
                side_effect=[None, PermissionError(1, "operation not permitted")],
            ),
            mock.patch("tools.reference.synrail_verification_profile_v0.time.sleep"),
        ):
            _terminate_process_tree(process)

        process.kill.assert_not_called()

    def run_alpha(
        self,
        *args: str,
        cwd: Path,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ALPHA_ENTRY), *args],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def _seed_project(self, tmpdir: str, *, profile_toml: str | None = None) -> Path:
        project_root = Path(tmpdir) / "project"
        project_root.mkdir(parents=True, exist_ok=True)

        (project_root / "app.py").write_text(BUGGY_APP)
        (project_root / "test_app.py").write_text(UNIT_TEST)
        (project_root / "synrail.toml").write_text(profile_toml or verification_profile_toml())
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
        return project_root

    def _start_bypass_scenario(self, tmpdir: str) -> Path:
        """Seed the repo, start a controlled run, apply a wrong fix, record grep proof."""
        project_root = self._seed_project(tmpdir)

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

    def test_dirty_profile_cannot_be_locked_as_operator_owned(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._seed_project(tmpdir)
            (project_root / "synrail.toml").write_text(
                '[verification.unit]\nargv = ["/usr/bin/true"]\nrequired = true\n'
            )

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
            self.assertEqual(2, start.returncode, start.stdout + start.stderr)
            self.assertIn("verification profile config could not be locked", start.stdout)
            self.assertIn("must match HEAD", start.stdout)
            self.assertFalse((project_root / ".synrail" / "state.json").exists())

    @unittest.skipUnless(os.name == "posix", "executable-file hash regression uses POSIX mode bits")
    def test_binary_content_change_at_same_realpath_blocks_verify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            binary = project_root / "operator-check"
            profile = (
                "[verification.unit]\n"
                f"argv = [{json.dumps(str(binary))}]\n"
                "required = true\n"
            )
            project_root = self._seed_project(tmpdir, profile_toml=profile)
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o755)

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

            binary.write_text("#!/bin/sh\nexit 1\n")
            binary.chmod(0o755)
            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("VERIFICATION_BINARY_CHANGED", verify.stdout)

    def test_untracked_overflow_fails_closed_instead_of_skipping_content_hashes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._seed_project(tmpdir)
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
            for index in range(201):
                (project_root / f"untracked_{index:03}.txt").write_text("visible\n")

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("VERIFICATION_WORKSPACE_UNBOUND", verify.stdout)
            self.assertFalse((project_root / ".synrail" / "verification_receipts.json").exists())

    def test_tampered_profile_lock_blocks_verify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._seed_project(tmpdir)
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

            profile_path = project_root / ".synrail" / "project_profile.json"
            profile = json.loads(profile_path.read_text())
            profile["verification_profiles"]["profiles"]["unit"]["argv"] = ["/usr/bin/true"]
            profile_path.write_text(json.dumps(profile, indent=2) + "\n")

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("VERIFICATION_LOCK_INVALID", verify.stdout)
            self.assertIn(
                "What to do next: start a new controlled run so Synrail can rebuild the authenticated "
                "operator-approved verification lock.",
                verify.stdout,
            )

    def test_profile_lock_downgrade_cannot_disable_required_verification(self) -> None:
        for tamper_mode in ("unsigned_absent", "missing"):
            with self.subTest(tamper_mode=tamper_mode):
                with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
                    project_root = self._start_bypass_scenario(tmpdir)
                    profile_path = project_root / ".synrail" / "project_profile.json"
                    profile = json.loads(profile_path.read_text())
                    if tamper_mode == "unsigned_absent":
                        profile["verification_profiles"] = {
                            "schema_version": "verification_profile_lock_v0",
                            "present": False,
                        }
                    else:
                        del profile["verification_profiles"]
                    profile_path.write_text(json.dumps(profile, indent=2) + "\n")
                    (project_root / "synrail.toml").unlink()

                    check = self.run_alpha(
                        "check",
                        "--artifact-root",
                        ".synrail",
                        "--clean-surface",
                        cwd=project_root,
                    )
                    self.assertNotIn("Status: Accepted", stdout_lines(check))
                    self.assertIn("Status: Verification Lock Invalid", stdout_lines(check))
                    report = json.loads(
                        (project_root / ".synrail" / "report.json").read_text()
                    )
                    self.assertEqual("VERIFICATION_LOCK_INVALID", report["reason"])

    def test_project_root_substitution_cannot_reuse_a_signed_lock(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._seed_project(tmpdir)
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
            clone_root = Path(tmpdir) / "clone"
            clone = run(["git", "clone", "-q", str(project_root), str(clone_root)], cwd=Path(tmpdir))
            self.assertEqual(0, clone.returncode, clone.stdout + clone.stderr)
            (clone_root / "app.py").write_text(REAL_FIX_APP)

            profile_path = project_root / ".synrail" / "project_profile.json"
            profile = json.loads(profile_path.read_text())
            profile["project_root"] = str(clone_root)
            profile["target_path"] = str(clone_root)
            profile_path.write_text(json.dumps(profile, indent=2) + "\n")

            verify = self.run_alpha(
                "verify",
                "--artifact-root",
                str(project_root / ".synrail"),
                cwd=project_root,
            )
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("VERIFICATION_PROJECT_ROOT_CHANGED", verify.stdout)
            self.assertFalse(
                (project_root / ".synrail" / "verification_receipts.json").exists()
            )

    def test_verification_output_is_hashed_with_a_bounded_excerpt(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            output_bytes = 10 * OUTPUT_EXCERPT_BYTES
            code = f"import sys; sys.stdout.buffer.write(b'x' * {output_bytes})"
            profile = (
                "[verification.unit]\n"
                f"argv = [{json.dumps(sys.executable)}, \"-c\", {json.dumps(code)}]\n"
                "required = true\n"
            )
            project_root = self._seed_project(tmpdir, profile_toml=profile)
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

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            payload = json.loads(
                (project_root / ".synrail" / "verification_receipts.json").read_text()
            )
            receipt = payload["receipts"]["unit"]
            self.assertEqual(output_bytes, receipt["stdout_bytes"])
            self.assertIn("[...output truncated...]", receipt["stdout_excerpt"])
            self.assertLess(len(receipt["stdout_excerpt"]), 3 * OUTPUT_EXCERPT_BYTES)

    @unittest.skipUnless(os.name == "posix", "process-group cleanup regression is POSIX-specific")
    def test_verification_kills_lingering_background_processes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            checker = project_root / "background-check"
            profile = (
                "[verification.unit]\n"
                f"argv = [{json.dumps(str(checker))}]\n"
                "required = true\n"
            )
            project_root = self._seed_project(tmpdir, profile_toml=profile)
            checker.write_text(
                "#!/bin/sh\n"
                "(sleep 1; printf 'late mutation\\n' > app.py) >/dev/null 2>&1 &\n"
                "exit 0\n"
            )
            checker.chmod(0o755)
            self.assertEqual(0, run(["git", "add", "background-check"], cwd=project_root).returncode)
            commit = run(
                [
                    "git",
                    "-c",
                    "user.name=Synrail Tests",
                    "-c",
                    "user.email=synrail-tests@example.com",
                    "commit",
                    "-m",
                    "add checker",
                ],
                cwd=project_root,
            )
            self.assertEqual(0, commit.returncode, commit.stdout + commit.stderr)
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

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            time.sleep(1.2)
            self.assertEqual(BUGGY_APP, (project_root / "app.py").read_text())

    def test_unusual_untracked_filename_content_is_bound(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._seed_project(tmpdir)
            unusual = project_root / "odd\nname.txt"
            unusual.write_text("before\n")
            before = workspace_fingerprint(
                project_root,
                artifact_root=project_root / ".synrail",
            )
            unusual.write_text("after\n")
            after = workspace_fingerprint(
                project_root,
                artifact_root=project_root / ".synrail",
            )
            self.assertTrue(before["complete"])
            self.assertTrue(after["complete"])
            self.assertFalse(fingerprints_match(before, after))

    def test_untracked_symlink_fails_closed_instead_of_following_external_content(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._seed_project(tmpdir)
            external = Path(tmpdir) / "external.py"
            external.write_text("print('outside')\n")
            (project_root / "linked.py").symlink_to(external)

            fingerprint = workspace_fingerprint(
                project_root,
                artifact_root=project_root / ".synrail",
            )

            self.assertFalse(fingerprint["complete"])
            self.assertIn("symlink", fingerprint["reason"])

    @unittest.skipUnless(
        sys.platform.startswith("linux"),
        "non-UTF-8 git path regression requires a filesystem that accepts raw byte names",
    )
    def test_non_utf8_untracked_filename_does_not_crash_fingerprinting(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._seed_project(tmpdir)
            unusual = project_root / os.fsdecode(b"odd_\xff.txt")
            unusual.write_bytes(b"before\n")
            before = workspace_fingerprint(
                project_root,
                artifact_root=project_root / ".synrail",
            )
            unusual.write_bytes(b"after\n")
            after = workspace_fingerprint(
                project_root,
                artifact_root=project_root / ".synrail",
            )

            self.assertTrue(before["complete"])
            self.assertTrue(after["complete"])
            self.assertFalse(fingerprints_match(before, after))

    def test_known_environment_overrides_are_scrubbed_from_profile_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            code = (
                "import os,sys; "
                "sys.exit(9 if os.getenv('PYTEST_ADDOPTS') or os.getenv('NODE_OPTIONS') else 0)"
            )
            profile = (
                "[verification.unit]\n"
                f"argv = [{json.dumps(sys.executable)}, \"-c\", {json.dumps(code)}]\n"
                "required = true\n"
            )
            project_root = self._seed_project(tmpdir, profile_toml=profile)
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

            hostile_env = os.environ.copy()
            hostile_env["PYTEST_ADDOPTS"] = "--ignore=test_app.py"
            hostile_env["NODE_OPTIONS"] = "--require=./agent-shim.js"
            verify = self.run_alpha(
                "verify",
                "--artifact-root",
                ".synrail",
                cwd=project_root,
                env=hostile_env,
            )
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("Verification unit: GREEN", verify.stdout)

    def test_failing_required_tests_cannot_reach_accepted_via_substituted_proof(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
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
            self.assertEqual(
                2,
                check_after_red_verify.returncode,
                check_after_red_verify.stdout + check_after_red_verify.stderr,
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
            self.assertIn(
                "Assurance: Behavioral verification passed (1 locked, operator-approved required profile green).",
                stdout_lines(check),
            )

    def test_editing_code_after_green_verify_goes_stale(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            (project_root / "app.py").write_text(REAL_FIX_APP)
            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, verify.returncode, verify.stdout + verify.stderr)

            (project_root / "app.py").write_text(WRONG_FIX_APP)
            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertNotIn("Status: Accepted", stdout_lines(check))
            report = json.loads((project_root / ".synrail" / "report.json").read_text())
            self.assertEqual("VERIFICATION_RECEIPT_STALE", report["reason"])

    def test_config_change_mid_run_blocks_check_and_verify(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            relaxed = verification_profile_toml().replace("required = true", "required = false")
            (project_root / "synrail.toml").write_text(relaxed)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertNotIn("Status: Accepted", stdout_lines(check))
            self.assertIn("Status: Verification Config Changed", stdout_lines(check))
            report = json.loads((project_root / ".synrail" / "report.json").read_text())
            self.assertEqual("VERIFICATION_CONFIG_CHANGED", report["reason"])

            verify = self.run_alpha("verify", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("VERIFICATION_CONFIG_CHANGED", verify.stdout)
            self.assertIn(
                "What to do next: restore the locked synrail.toml or start a new controlled run to "
                "adopt the changed configuration.",
                verify.stdout,
            )

    def test_unknown_verify_profile_names_the_bounded_retry(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_behavioral_gap_") as tmpdir:
            project_root = self._start_bypass_scenario(tmpdir)

            verify = self.run_alpha(
                "verify",
                "--artifact-root",
                ".synrail",
                "--profile",
                "does-not-exist",
                cwd=project_root,
            )
            self.assertEqual(2, verify.returncode, verify.stdout + verify.stderr)
            self.assertIn("VERIFICATION_PROFILE_UNKNOWN", verify.stdout)
            self.assertIn(
                "What to do next: rerun synrail verify without the unknown --profile value, or select "
                "a profile locked at controlled start.",
                verify.stdout,
            )

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
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertNotIn("Status: Accepted", stdout_lines(check))
            report = json.loads((project_root / ".synrail" / "report.json").read_text())
            self.assertEqual("VERIFICATION_RECEIPT_INVALID", report["reason"])


if __name__ == "__main__":
    unittest.main()
