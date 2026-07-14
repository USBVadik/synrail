#!/usr/bin/env python3
"""Regression coverage for verification-aware preflight readiness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.reference.synrail_verification_profile_v0 import (
    SYNRAIL_PYTHON_ARGV0,
    inspect_verification_readiness,
    lock_verification_profiles,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def profile_toml(*argv: str) -> str:
    encoded = ", ".join(json.dumps(item) for item in argv)
    return (
        "[verification.unit]\n"
        f"argv = [{encoded}]\n"
        "timeout_seconds = 60\n"
        "required = true\n"
    )


class VerificationPreflightTests(unittest.TestCase):
    def run_alpha(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(ALPHA_ENTRY), *args], cwd=cwd)

    def seed_git_project(self, tmpdir: str, *, config: str | None = None) -> Path:
        project_root = Path(tmpdir) / "project"
        project_root.mkdir()
        (project_root / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.assertEqual(0, run(["git", "init"], cwd=project_root).returncode)
        self.assertEqual(0, run(["git", "add", "app.py"], cwd=project_root).returncode)
        if config is not None:
            (project_root / "synrail.toml").write_text(config, encoding="utf-8")
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
                "seed",
            ],
            cwd=project_root,
        )
        self.assertEqual(0, commit.returncode, commit.stdout + commit.stderr)
        return project_root

    def test_absent_config_is_explicit_but_does_not_fail_install_preflight(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            project_root = self.seed_git_project(tmpdir)

            readiness = inspect_verification_readiness(project_root)
            preflight = self.run_alpha("preflight", "--json", cwd=project_root)

            self.assertEqual("NOT_CONFIGURED", readiness["status"])
            self.assertFalse(readiness["configured"])
            self.assertEqual(0, preflight.returncode, preflight.stdout + preflight.stderr)
            payload = json.loads(preflight.stdout)
            self.assertEqual("PASS", payload["status"])
            self.assertEqual("NOT_CONFIGURED", payload["behavioral_verification"]["status"])
            self.assertIn("suggest-verification", payload["behavioral_verification"]["next_step"])
            self.assertIn("init-verification", payload["behavioral_verification"]["next_step"])
            self.assertFalse((project_root / ".synrail").exists(), "preflight must not leave an artifact directory behind")

    def test_untracked_and_dirty_profiles_require_review_before_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            project_root = self.seed_git_project(tmpdir)
            config = project_root / "synrail.toml"
            config.write_text(profile_toml(sys.executable, "-m", "unittest"), encoding="utf-8")

            untracked = inspect_verification_readiness(project_root)
            self.assertEqual("REVIEW_REQUIRED", untracked["status"])
            self.assertEqual("REVIEW_AND_COMMIT", untracked["next_action"])

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
                    "approve verification",
                ],
                cwd=project_root,
            )
            self.assertEqual(0, commit.returncode, commit.stdout + commit.stderr)
            self.assertEqual("READY", inspect_verification_readiness(project_root)["status"])

            config.write_text(profile_toml(sys.executable, "-m", "pytest"), encoding="utf-8")
            dirty = self.run_alpha("preflight", "--json", cwd=project_root)
            self.assertEqual(2, dirty.returncode, dirty.stdout + dirty.stderr)
            payload = json.loads(dirty.stdout)
            self.assertEqual("FAIL", payload["status"])
            self.assertEqual("REVIEW_REQUIRED", payload["behavioral_verification"]["status"])
            self.assertIn("commit", payload["behavioral_verification"]["next_step"])

    def test_invalid_unsafe_and_unresolved_profiles_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            invalid_root = self.seed_git_project(tmpdir, config="[verification.unit\n")
            invalid = inspect_verification_readiness(invalid_root)
            self.assertEqual("BLOCKED", invalid["status"])
            self.assertEqual("FIX_CONFIG", invalid["next_action"])
            self.assertEqual("VERIFICATION_CONFIG_PARSE_ERROR", invalid["reason"])

        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            missing_root = self.seed_git_project(
                tmpdir,
                config=profile_toml("synrail-command-that-does-not-exist"),
            )
            missing = inspect_verification_readiness(missing_root)
            self.assertEqual("BLOCKED", missing["status"])
            self.assertEqual("FIX_EXECUTABLE", missing["next_action"])
            self.assertEqual("VERIFICATION_BINARY_UNRESOLVED", missing["reason"])

        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            no_git_root = Path(tmpdir)
            (no_git_root / "synrail.toml").write_text(
                profile_toml(sys.executable),
                encoding="utf-8",
            )
            no_git = inspect_verification_readiness(no_git_root)
            self.assertEqual("REVIEW_REQUIRED", no_git["status"])
            self.assertEqual("INITIALIZE_AND_COMMIT", no_git["next_action"])

        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            project_root = self.seed_git_project(tmpdir)
            target = project_root / "outside.toml"
            target.write_text(profile_toml(sys.executable), encoding="utf-8")
            config = project_root / "synrail.toml"
            try:
                config.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            unsafe = inspect_verification_readiness(project_root)
            self.assertEqual("BLOCKED", unsafe["status"])
            self.assertEqual("VERIFICATION_CONFIG_UNTRUSTED", unsafe["reason"])

    def test_optional_only_and_special_file_profiles_do_not_report_ready(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            optional_root = self.seed_git_project(
                tmpdir,
                config=profile_toml(sys.executable).replace("required = true", "required = false"),
            )
            optional = inspect_verification_readiness(optional_root)
            self.assertEqual("REVIEW_REQUIRED", optional["status"])
            self.assertEqual("VERIFICATION_NO_REQUIRED_PROFILES", optional["reason"])
            self.assertEqual("MAKE_PROFILE_REQUIRED", optional["next_action"])

        if not hasattr(os, "mkfifo"):
            return
        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            project_root = self.seed_git_project(tmpdir)
            fifo = project_root / "verification-fifo"
            os.mkfifo(fifo, mode=0o700)
            config = project_root / "synrail.toml"
            config.write_text(profile_toml(str(fifo)), encoding="utf-8")
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
                    "approve special executable path",
                ],
                cwd=project_root,
            )
            self.assertEqual(0, commit.returncode, commit.stdout + commit.stderr)

            probe = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    (
                        "import json, sys; from pathlib import Path; "
                        "from tools.reference.synrail_verification_profile_v0 import inspect_verification_readiness; "
                        "print(json.dumps(inspect_verification_readiness(Path(sys.argv[1]))))"
                    ),
                    str(project_root),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=3,
            )
            self.assertEqual(0, probe.returncode, probe.stdout + probe.stderr)
            special = json.loads(probe.stdout)
            self.assertEqual("BLOCKED", special["status"])
            self.assertEqual("VERIFICATION_BINARY_UNRESOLVED", special["reason"])
            self.assertIn("not a regular file", special["detail"])

    def test_ready_preflight_matches_start_lock_without_executing_profile(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            marker = project_root / "preflight-executed.txt"
            command = [
                sys.executable,
                "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('executed')",
            ]
            project_root = self.seed_git_project(tmpdir, config=profile_toml(*command))
            nested = project_root / "src" / "nested"
            nested.mkdir(parents=True)

            preflight = self.run_alpha("preflight", "--json", cwd=nested)

            self.assertEqual(0, preflight.returncode, preflight.stdout + preflight.stderr)
            self.assertFalse(marker.exists(), "preflight must never execute a configured verification command")
            payload = json.loads(preflight.stdout)
            verification = payload["behavioral_verification"]
            self.assertEqual("PASS", payload["status"])
            self.assertEqual(str(project_root.resolve()), payload["project_root"])
            self.assertEqual(str(nested.resolve()), payload["current_directory"])
            self.assertEqual(str((project_root / ".synrail").resolve()), payload["artifact_root"])
            self.assertEqual("READY", verification["status"])
            self.assertEqual(1, verification["profile_count"])
            self.assertEqual(1, verification["required_profile_count"])
            self.assertEqual("unit", verification["profiles"][0]["name"])
            self.assertEqual(str(Path(sys.executable).resolve()), verification["profiles"][0]["argv0_realpath"])

            locked = lock_verification_profiles(project_root)
            self.assertTrue(locked["present"])
            self.assertNotEqual("ERROR", locked.get("status"))
            self.assertEqual(
                verification["config_git_head"],
                locked["config_git_head"],
                "preflight and start must agree on trusted git provenance",
            )
            self.assertEqual(
                verification["profiles"][0]["argv0_realpath"],
                locked["profiles"]["unit"]["argv0_realpath"],
                "preflight and start must agree on executable resolution",
            )

    def test_synrail_python_alias_locks_the_current_interpreter(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_alias_") as tmpdir:
            project_root = self.seed_git_project(
                tmpdir,
                config=profile_toml(SYNRAIL_PYTHON_ARGV0, "-c", "print('green')"),
            )

            readiness = inspect_verification_readiness(project_root)
            locked = lock_verification_profiles(project_root)

            expected = str(Path(sys.executable).resolve())
            self.assertEqual("READY", readiness["status"])
            self.assertEqual(SYNRAIL_PYTHON_ARGV0, readiness["profiles"][0]["argv0"])
            self.assertEqual(expected, readiness["profiles"][0]["argv0_realpath"])
            self.assertEqual(expected, locked["profiles"]["unit"]["argv0_realpath"])
            self.assertTrue(locked["profiles"]["unit"]["argv0_sha256"])

    def test_relative_artifact_root_resolves_from_discovered_project_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_preflight_") as tmpdir:
            project_root = self.seed_git_project(tmpdir)
            nested = project_root / "src" / "nested"
            nested.mkdir(parents=True)

            preflight = self.run_alpha(
                "preflight",
                "--artifact-root",
                ".checks/synrail",
                "--json",
                cwd=nested,
            )

            self.assertEqual(0, preflight.returncode, preflight.stdout + preflight.stderr)
            payload = json.loads(preflight.stdout)
            self.assertEqual(str((project_root / ".checks" / "synrail").resolve()), payload["artifact_root"])
            self.assertFalse((nested / ".checks").exists())
            self.assertFalse((project_root / ".checks").exists())


if __name__ == "__main__":
    unittest.main()
