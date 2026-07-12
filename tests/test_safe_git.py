#!/usr/bin/env python3
"""Adversarial tests for Git execution from untrusted local worktrees."""

from __future__ import annotations

import os
import argparse
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_bundle_v0 import verification_recheck_result  # noqa: E402
from synrail_checkpoint_v0 import _git_has_uncommitted  # noqa: E402
from synrail_cli_v0 import git_status_changed_paths  # noqa: E402
from synrail_doctor_v1 import probe_clean_execution_surface  # noqa: E402
from synrail_safe_git_v0 import SafeGitError, run_safe_git  # noqa: E402


@unittest.skipIf(os.name == "nt", "execution-marker attack harness is POSIX-only")
class SafeGitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="synrail_safe_git_")
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name) / "project"
        self.project_root.mkdir()
        self.git("init", "-q")
        self.git("config", "user.email", "tester@example.com")
        self.git("config", "user.name", "Tester")
        (self.project_root / ".gitattributes").write_text("sample.txt filter=evil\n")
        (self.project_root / "sample.txt").write_text("before\n")
        self.git("add", ".gitattributes", "sample.txt")
        self.git("commit", "-qm", "baseline")

        self.markers: dict[str, Path] = {}
        for name in ("diff", "fsmonitor", "filter", "env"):
            marker = self.project_root / f"{name}.executed"
            script = self.project_root / f"{name}.sh"
            script.write_text(f"#!/bin/sh\ntouch {str(marker)!r}\ncat\n")
            script.chmod(0o755)
            self.markers[name] = marker

        self.git("config", "diff.external", str(self.project_root / "diff.sh"))
        self.git("config", "core.fsmonitor", str(self.project_root / "fsmonitor.sh"))
        self.git("config", "filter.evil.clean", str(self.project_root / "filter.sh"))
        self.clear_markers()
        (self.project_root / "sample.txt").write_text("after\n")

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.project_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def clear_markers(self) -> None:
        for marker in self.markers.values():
            marker.unlink(missing_ok=True)

    def assert_no_marker_executed(self) -> None:
        self.assertEqual([], [name for name, marker in self.markers.items() if marker.exists()])

    def test_safe_diff_neutralizes_local_execution_surfaces(self) -> None:
        result = run_safe_git(self.project_root, ["diff", "HEAD", "--", "sample.txt"])
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn("diff --git a/sample.txt b/sample.txt", result.stdout)
        self.assert_no_marker_executed()

    def test_bundle_git_recheck_uses_hardened_execution(self) -> None:
        expected = run_safe_git(
            self.project_root,
            ["diff", "HEAD", "--", "sample.txt"],
        ).stdout.rstrip("\n")
        self.clear_markers()
        result = verification_recheck_result(
            {
                "changed_file": "sample.txt",
                "verification_command": "git diff -- sample.txt",
                "verification_result": expected,
            },
            project_root=self.project_root,
        )
        self.assertTrue(result["command_allowed"])
        self.assertTrue(result["executed"])
        self.assertTrue(result["matched"], result)
        self.assert_no_marker_executed()

    def test_inherited_git_config_injection_is_removed(self) -> None:
        injected = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "core.fsmonitor",
            "GIT_CONFIG_VALUE_0": str(self.project_root / "env.sh"),
            "GIT_DIR": str(self.project_root / "not-the-repository"),
            "GIT_WORK_TREE": str(self.project_root / "not-the-worktree"),
            "GIT_INDEX_FILE": str(self.project_root / "not-the-index"),
            "GIT_OBJECT_DIRECTORY": str(self.project_root / "not-the-objects"),
        }
        with mock.patch.dict(os.environ, injected, clear=False):
            result = run_safe_git(self.project_root, ["status", "--porcelain"])
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assert_no_marker_executed()

    def test_workspace_mutation_fails_closed_when_filters_are_configured(self) -> None:
        with self.assertRaises(SafeGitError) as raised:
            run_safe_git(
                self.project_root,
                ["checkout", "HEAD", "--force"],
                reject_configured_filters=True,
            )
        self.assertEqual("GIT_FILTERED_MUTATION_UNSUPPORTED", raised.exception.reason)
        self.assert_no_marker_executed()

    def test_repo_local_git_binary_is_rejected(self) -> None:
        fake_bin = self.project_root / "bin"
        fake_bin.mkdir()
        fake_git = fake_bin / "git"
        fake_git.write_text(
            f"#!/bin/sh\ntouch {str(self.markers['env'])!r}\nexit 0\n"
        )
        fake_git.chmod(0o755)
        poisoned_path = str(fake_bin) + os.pathsep + os.environ.get("PATH", "")
        with mock.patch.dict(os.environ, {"PATH": poisoned_path}, clear=False):
            with self.assertRaises(SafeGitError) as raised:
                run_safe_git(self.project_root, ["status", "--porcelain"])
        self.assertEqual("UNTRUSTED_COMMAND_EXECUTABLE", raised.exception.reason)
        self.assert_no_marker_executed()

    def test_cli_doctor_and_checkpoint_git_status_do_not_execute_local_helpers(self) -> None:
        self.assertIn("sample.txt", git_status_changed_paths(self.project_root) or [])
        self.assertTrue(_git_has_uncommitted(self.project_root))
        doctor_gate = probe_clean_execution_surface(
            argparse.Namespace(
                changed_file=[],
                allowed_scope_path=[],
                clean_surface=False,
                target_path=str(self.project_root),
                artifact_path=str(self.project_root / ".synrail" / "final_result.json"),
            )
        )
        self.assertEqual("FAIL", doctor_gate["status"])
        self.assert_no_marker_executed()


if __name__ == "__main__":
    unittest.main()
