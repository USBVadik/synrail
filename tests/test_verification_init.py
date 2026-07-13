#!/usr/bin/env python3
"""Regression coverage for the verification-profile scaffold command."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from tools.reference import synrail_verification_init_v0 as verification_init
from tools.reference.synrail_verification_init_v0 import (
    VerificationInitError,
    render_verification_scaffold,
    write_verification_scaffold,
)
from tools.reference.synrail_verification_profile_v0 import (
    MAX_ARG_CHARS,
    MAX_ARGV_ITEMS,
    MAX_CONFIG_BYTES,
    MAX_PROFILE_NAME_CHARS,
    MAX_TIMEOUT_SECONDS,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


class VerificationInitTests(unittest.TestCase):
    def run_alpha(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(ALPHA_ENTRY), *args], cwd=cwd)

    def seed_git_project(self, tmpdir: str) -> Path:
        project_root = Path(tmpdir) / "project"
        project_root.mkdir()
        (project_root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        (project_root / ".gitignore").write_text(".synrail-test/\n", encoding="utf-8")
        self.assertEqual(0, run(["git", "init"], cwd=project_root).returncode)
        self.assertEqual(0, run(["git", "add", "app.py", ".gitignore"], cwd=project_root).returncode)
        commit = run(
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
        self.assertEqual(0, commit.returncode, commit.stdout + commit.stderr)
        return project_root

    def test_rendered_profile_round_trips_as_toml_without_executing_argv(self) -> None:
        rendered = render_verification_scaffold(
            profile_name="integration-tests",
            argv=[sys.executable, "-c", 'print("quoted \\\\ path")', "zażółć"],
            timeout_seconds=45,
        )

        parsed = tomllib.loads(rendered)

        self.assertEqual(
            [sys.executable, "-c", 'print("quoted \\\\ path")', "zażółć"],
            parsed["verification"]["integration-tests"]["argv"],
        )
        self.assertEqual(45, parsed["verification"]["integration-tests"]["timeout_seconds"])
        self.assertTrue(parsed["verification"]["integration-tests"]["required"])
        self.assertIn("REVIEW REQUIRED", rendered)
        self.assertIn("did not execute", rendered)
        self.assertIn("Do not put secrets in argv", rendered)

    def test_write_is_idempotent_and_force_preserves_exact_existing_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_init_") as tmpdir:
            project_root = Path(tmpdir)
            first = write_verification_scaffold(
                project_root=project_root,
                profile_name="unit",
                argv=["python", "-m", "pytest", "-q"],
            )
            second = write_verification_scaffold(
                project_root=project_root,
                profile_name="unit",
                argv=["python", "-m", "pytest", "-q"],
            )

            self.assertEqual("written", first.state)
            self.assertEqual("unchanged", second.state)
            self.assertIsNone(second.backup_path)

            original = b"legacy\r\nbytes\xff"
            first.path.write_bytes(original)
            if os.name == "posix":
                first.path.chmod(0o600)
            with self.assertRaises(VerificationInitError) as blocked:
                write_verification_scaffold(
                    project_root=project_root,
                    profile_name="unit",
                    argv=["python", "-m", "unittest"],
                )
            self.assertEqual("VERIFICATION_CONFIG_EXISTS", blocked.exception.reason)
            self.assertEqual(original, first.path.read_bytes())

            forced = write_verification_scaffold(
                project_root=project_root,
                profile_name="unit",
                argv=["python", "-m", "unittest"],
                force=True,
            )
            self.assertEqual("updated", forced.state)
            self.assertIsNotNone(forced.backup_path)
            self.assertEqual(original, forced.backup_path.read_bytes())
            self.assertNotEqual(original, first.path.read_bytes())
            if os.name == "posix":
                self.assertEqual(0o600, stat.S_IMODE(first.path.stat().st_mode))
                self.assertEqual(0o600, stat.S_IMODE(forced.backup_path.stat().st_mode))

    def test_force_refuses_to_overwrite_a_concurrent_config_change(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_init_") as tmpdir:
            project_root = Path(tmpdir)
            config = project_root / "synrail.toml"
            config.write_text("original\n", encoding="utf-8")
            real_atomic_write = verification_init._atomic_write_bytes

            def write_then_mutate_source(path: Path, payload: bytes, *, mode: int = 0o644) -> None:
                real_atomic_write(path, payload, mode=mode)
                if ".synrail.bak." in path.name:
                    config.write_text("concurrent writer\n", encoding="utf-8")

            with mock.patch.object(
                verification_init,
                "_atomic_write_bytes",
                side_effect=write_then_mutate_source,
            ):
                with self.assertRaises(VerificationInitError) as changed:
                    write_verification_scaffold(
                        project_root=project_root,
                        profile_name="unit",
                        argv=["python", "-m", "pytest"],
                        force=True,
                    )

            self.assertEqual("VERIFICATION_CONFIG_CHANGED", changed.exception.reason)
            self.assertEqual("concurrent writer\n", config.read_text(encoding="utf-8"))

    def test_symlink_and_special_file_are_rejected_even_with_force(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_init_") as tmpdir:
            project_root = Path(tmpdir)
            target = project_root / "target.toml"
            target.write_text("do not replace\n", encoding="utf-8")
            config = project_root / "synrail.toml"
            try:
                config.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")

            with self.assertRaises(VerificationInitError) as symlink_error:
                write_verification_scaffold(
                    project_root=project_root,
                    profile_name="unit",
                    argv=["python", "-m", "pytest"],
                    force=True,
                )
            self.assertEqual("VERIFICATION_CONFIG_UNTRUSTED", symlink_error.exception.reason)
            self.assertEqual("do not replace\n", target.read_text(encoding="utf-8"))

            config.unlink()
            config.mkdir()
            with self.assertRaises(VerificationInitError) as special_error:
                write_verification_scaffold(
                    project_root=project_root,
                    profile_name="unit",
                    argv=["python", "-m", "pytest"],
                    force=True,
                )
            self.assertEqual("VERIFICATION_CONFIG_UNTRUSTED", special_error.exception.reason)

    def test_invalid_names_argv_timeouts_and_root_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_init_") as tmpdir:
            project_root = Path(tmpdir)
            invalid_cases = [
                {"profile_name": "", "argv": ["python"]},
                {"profile_name": "has space", "argv": ["python"]},
                {"profile_name": "has.dot", "argv": ["python"]},
                {"profile_name": "x" * (MAX_PROFILE_NAME_CHARS + 1), "argv": ["python"]},
                {"profile_name": "unit", "argv": []},
                {"profile_name": "unit", "argv": ["python", ""]},
                {"profile_name": "unit", "argv": ["python", "line\nbreak"]},
                {"profile_name": "unit", "argv": ["python"] * (MAX_ARGV_ITEMS + 1)},
                {"profile_name": "unit", "argv": ["x" * (MAX_ARG_CHARS + 1)]},
                {
                    "profile_name": "unit",
                    "argv": ["x" * ((MAX_CONFIG_BYTES // MAX_ARGV_ITEMS) + 100)] * MAX_ARGV_ITEMS,
                },
                {"profile_name": "unit", "argv": ["python"], "timeout_seconds": 0},
                {
                    "profile_name": "unit",
                    "argv": ["python"],
                    "timeout_seconds": MAX_TIMEOUT_SECONDS + 1,
                },
                {"profile_name": "unit", "argv": ["python"], "timeout_seconds": True},
            ]
            for case in invalid_cases:
                with self.subTest(case=case), self.assertRaises(VerificationInitError):
                    write_verification_scaffold(project_root=project_root, **case)

            missing = project_root / "missing"
            with self.assertRaises(VerificationInitError) as root_error:
                write_verification_scaffold(
                    project_root=missing,
                    profile_name="unit",
                    argv=["python"],
                )
            self.assertEqual("PROJECT_ROOT_INVALID", root_error.exception.reason)

    def test_cli_discovers_git_root_but_does_not_execute_or_trust_scaffold(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_init_cli_") as tmpdir:
            project_root = self.seed_git_project(tmpdir)
            subdirectory = project_root / "src" / "nested"
            subdirectory.mkdir(parents=True)
            marker = project_root / "init-command-executed.txt"
            command = [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('executed')",
            ]

            initialized = self.run_alpha(
                "init-verification",
                "--name",
                "unit",
                "--",
                *command,
                cwd=subdirectory,
            )
            self.assertEqual(0, initialized.returncode, initialized.stdout + initialized.stderr)
            self.assertTrue((project_root / "synrail.toml").is_file())
            self.assertFalse(marker.exists(), "init-verification must never execute the configured argv")
            self.assertIn("State: written", initialized.stdout)
            self.assertIn("Trust state: REVIEW REQUIRED", initialized.stdout)
            self.assertIn("did not execute or trust", initialized.stdout)
            argv_line = next(line for line in initialized.stdout.splitlines() if line.startswith("Argv: "))
            self.assertEqual(command, json.loads(argv_line.removeprefix("Argv: ")))

            untrusted_start = self.run_alpha(
                "start",
                "Scaffold a verification profile without auto-trusting it.",
                "--artifact-root",
                ".synrail-test",
                cwd=project_root,
            )
            self.assertEqual(2, untrusted_start.returncode, untrusted_start.stdout + untrusted_start.stderr)
            self.assertIn("must be tracked in git", untrusted_start.stdout)
            self.assertFalse(marker.exists())

            self.assertEqual(0, run(["git", "add", "synrail.toml"], cwd=project_root).returncode)
            commit = run(
                [
                    "git",
                    "-c",
                    "user.name=Synrail Tests",
                    "-c",
                    "user.email=synrail-tests@example.com",
                    "commit",
                    "-m",
                    "approve verification profile",
                ],
                cwd=project_root,
            )
            self.assertEqual(0, commit.returncode, commit.stdout + commit.stderr)

            trusted_start = self.run_alpha(
                "start",
                "Start only after operator review and commit.",
                "--artifact-root",
                ".synrail-test",
                cwd=project_root,
            )
            self.assertEqual(0, trusted_start.returncode, trusted_start.stdout + trusted_start.stderr)
            self.assertIn("Verification profiles locked for this run: unit", trusted_start.stdout)
            self.assertFalse(marker.exists(), "start locks profile identity but does not execute verification")

    def test_cli_blocks_overwrite_and_reports_exact_backup_on_force(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_init_cli_") as tmpdir:
            project_root = Path(tmpdir)
            config = project_root / "synrail.toml"
            original = b"existing\r\nconfig\xff"
            config.write_bytes(original)

            blocked = self.run_alpha(
                "init-verification",
                "--project-root",
                str(project_root),
                "--",
                "python",
                "-m",
                "pytest",
                cwd=project_root,
            )
            self.assertEqual(2, blocked.returncode, blocked.stdout + blocked.stderr)
            self.assertIn("VERIFICATION_CONFIG_EXISTS", blocked.stdout)
            self.assertEqual(original, config.read_bytes())

            forced = self.run_alpha(
                "init-verification",
                "--project-root",
                str(project_root),
                "--force",
                "--",
                "python",
                "-m",
                "pytest",
                cwd=project_root,
            )
            self.assertEqual(0, forced.returncode, forced.stdout + forced.stderr)
            backups = list(project_root.glob("synrail.toml.synrail.bak.*"))
            self.assertEqual(1, len(backups))
            self.assertEqual(original, backups[0].read_bytes())
            self.assertIn(f"Exact backup: {backups[0].resolve()}", forced.stdout)


if __name__ == "__main__":
    unittest.main()
