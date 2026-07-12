#!/usr/bin/env python3
"""Regression coverage for the thin single-file proof recorder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_cli_v0 import ephemeral_artifact_root  # noqa: E402
from synrail_bundle_v0 import build_bundle  # noqa: E402
from synrail_proof_recorder_v0 import ProofRecordError, record_single_file_proof  # noqa: E402


class ThinRecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="synrail_thin_record_")
        self.addCleanup(self.tempdir.cleanup)
        self.project_root = Path(self.tempdir.name) / "project"
        self.project_root.mkdir(parents=True)
        self.git("init", "-q")
        self.git("config", "user.email", "tester@example.com")
        self.git("config", "user.name", "Tester")
        (self.project_root / "sample.txt").write_text(
            "Greeting:\nhello before\nEnd greeting.\n"
        )
        (self.project_root / "other.txt").write_text("other before\n")
        self.git("add", "sample.txt", "other.txt")
        self.git("commit", "-qm", "baseline")
        self.artifact_root = ephemeral_artifact_root(project_root=self.project_root)
        self.addCleanup(self.cleanup_ephemeral)

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(self.project_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )

    def run_alpha(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        existing = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = str(REPO_ROOT) if not existing else str(REPO_ROOT) + os.pathsep + existing
        return subprocess.run(
            [sys.executable, str(ALPHA_ENTRY), *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def cleanup_ephemeral(self) -> None:
        self.run_alpha(
            "cleanup",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
        )

    def start(self) -> subprocess.CompletedProcess[str]:
        return self.run_alpha(
            "start",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
            "Replace one greeting with a verified line.",
        )

    def record(self, *extra: str) -> subprocess.CompletedProcess[str]:
        return self.run_alpha(
            "record",
            "sample.txt",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
            "--summary",
            "Replaced the sample greeting with the requested verified line.",
            "--verify",
            "grep -n 'hello from thin record' sample.txt",
            *extra,
        )

    def starter_hash(self) -> str:
        return hashlib.sha256((self.artifact_root / "final_result.json").read_bytes()).hexdigest()

    def test_single_tracked_file_record_reaches_accepted_closure(self) -> None:
        started = self.start()
        self.assertEqual(0, started.returncode, started.stdout + started.stderr)
        self.assertIn("synrail check --ephemeral --project-root", started.stdout)
        self.assertIn("synrail final-result-template --ephemeral --project-root", started.stdout)

        status = self.run_alpha(
            "status",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
        )
        self.assertEqual(0, status.returncode, status.stdout + status.stderr)
        self.assertIn("controlled run in progress", status.stdout)

        (self.project_root / "sample.txt").write_text(
            "Greeting:\nhello from thin record\nEnd greeting.\n"
        )
        recorded = self.record()
        self.assertEqual(0, recorded.returncode, recorded.stdout + recorded.stderr)
        self.assertIn("Acceptance has not been evaluated yet.", recorded.stdout)
        self.assertIn("check --ephemeral --project-root", recorded.stdout)

        final_result = json.loads((self.artifact_root / "final_result.json").read_text())
        self.assertEqual("PROVEN", final_result["status"])
        self.assertEqual(["sample.txt"], final_result["modified_files"])
        self.assertIn("diff --git a/sample.txt b/sample.txt", final_result["git_diff"])
        self.assertEqual("git_patch_plus_recheck", final_result["diff_provenance"]["method"])
        self.assertEqual("hello from thin record", final_result["diff_provenance"]["verification_result"])
        self.assertFalse(final_result["_synrail"]["acceptance_evaluated"])

        checked = self.run_alpha(
            "check",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
        )
        self.assertEqual(0, checked.returncode, checked.stdout + checked.stderr)
        self.assertIn("Status: Accepted", checked.stdout)

    def test_record_rejects_a_second_dirty_file_without_overwriting_starter(self) -> None:
        self.assertEqual(0, self.start().returncode)
        before = self.starter_hash()
        (self.project_root / "sample.txt").write_text("hello from thin record\n")
        (self.project_root / "other.txt").write_text("other changed\n")

        recorded = self.record()
        self.assertEqual(2, recorded.returncode, recorded.stdout + recorded.stderr)
        self.assertIn("SINGLE_FILE_SCOPE_REQUIRED", recorded.stdout)
        self.assertEqual(before, self.starter_hash())

    def test_record_rejects_untracked_file(self) -> None:
        self.assertEqual(0, self.start().returncode)
        untracked = self.project_root / "new.txt"
        untracked.write_text("new evidence\n")
        recorded = self.run_alpha(
            "record",
            "new.txt",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
            "--summary",
            "Added a new file with concrete local evidence.",
            "--verify",
            "cat new.txt",
        )
        self.assertEqual(2, recorded.returncode, recorded.stdout + recorded.stderr)
        self.assertIn("TRACKED_PATCH_REQUIRED", recorded.stdout)

    def test_record_rejects_a_file_that_was_dirty_before_start(self) -> None:
        (self.project_root / "sample.txt").write_text("dirty before start\n")
        self.assertEqual(0, self.start().returncode)
        recorded = self.run_alpha(
            "record",
            "sample.txt",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
            "--summary",
            "Tried to claim work that existed before this controlled run.",
            "--verify",
            "cat sample.txt",
        )
        self.assertEqual(2, recorded.returncode, recorded.stdout + recorded.stderr)
        self.assertIn("CLEAN_START_REQUIRED", recorded.stdout)

    def test_record_rejects_head_change_after_start(self) -> None:
        self.assertEqual(0, self.start().returncode)
        (self.project_root / "other.txt").write_text("committed during run\n")
        self.git("add", "other.txt")
        self.git("commit", "-qm", "advance head")
        (self.project_root / "sample.txt").write_text("hello from thin record\n")
        recorded = self.record()
        self.assertEqual(2, recorded.returncode, recorded.stdout + recorded.stderr)
        self.assertIn("GIT_HEAD_CHANGED_DURING_RUN", recorded.stdout)

    def test_record_rejects_absolute_changed_file(self) -> None:
        self.assertEqual(0, self.start().returncode)
        (self.project_root / "sample.txt").write_text("hello from thin record\n")
        recorded = self.run_alpha(
            "record",
            str(self.project_root / "sample.txt"),
            "--ephemeral",
            "--project-root",
            str(self.project_root),
            "--summary",
            "Changed the sample greeting with concrete evidence.",
            "--verify",
            "cat sample.txt",
        )
        self.assertEqual(2, recorded.returncode, recorded.stdout + recorded.stderr)
        self.assertIn("CHANGED_FILE_MUST_BE_RELATIVE", recorded.stdout)

    def test_record_does_not_execute_disallowed_verification_command(self) -> None:
        self.assertEqual(0, self.start().returncode)
        before = self.starter_hash()
        (self.project_root / "sample.txt").write_text("hello from thin record\n")
        marker = self.project_root / "should-not-exist"
        malicious_command = (
            f'python3 -c "from pathlib import Path; Path({str(marker)!r}).touch()"'
        )
        recorded = self.run_alpha(
            "record",
            "sample.txt",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
            "--summary",
            "Changed the sample greeting with concrete evidence.",
            "--verify",
            malicious_command,
        )
        self.assertEqual(2, recorded.returncode, recorded.stdout + recorded.stderr)
        self.assertIn("VERIFICATION_COMMAND_NOT_RECHECKABLE", recorded.stdout)
        self.assertFalse(marker.exists())
        self.assertEqual(before, self.starter_hash())

    @unittest.skipIf(os.name == "nt", "repo-local executable attack harness is POSIX-only")
    def test_record_rejects_repo_local_recheck_executable(self) -> None:
        marker = self.project_root / "fake-grep-executed"
        fake_bin = self.project_root / "bin"
        fake_bin.mkdir()
        fake_grep = fake_bin / "grep"
        fake_grep.write_text(f"#!/bin/sh\ntouch {str(marker)!r}\necho forged\n")
        fake_grep.chmod(0o755)
        self.git("add", "bin/grep")
        self.git("commit", "-qm", "add hostile repo-local grep")
        self.assertEqual(0, self.start().returncode)
        before = self.starter_hash()
        (self.project_root / "sample.txt").write_text("hello from thin record\n")
        poisoned_path = str(fake_bin) + os.pathsep + os.environ.get("PATH", "")
        with mock.patch.dict(os.environ, {"PATH": poisoned_path}, clear=False):
            with self.assertRaises(ProofRecordError) as raised:
                record_single_file_proof(
                    artifact_root=self.artifact_root,
                    project_root=self.project_root,
                    changed_file="sample.txt",
                    summary="Changed the sample greeting with concrete local evidence.",
                    verification_command="grep -n 'hello from thin record' sample.txt",
                )
        self.assertEqual("VERIFICATION_COMMAND_NOT_RECHECKABLE", raised.exception.reason)
        self.assertFalse(marker.exists())
        self.assertEqual(before, self.starter_hash())

    def test_record_reports_corrupt_active_profile_without_traceback(self) -> None:
        self.assertEqual(0, self.start().returncode)
        (self.project_root / "sample.txt").write_text("hello from thin record\n")
        (self.artifact_root / "project_profile.json").write_text("{broken\n")
        recorded = self.record()
        self.assertEqual(2, recorded.returncode, recorded.stdout + recorded.stderr)
        self.assertIn("ACTIVE_RUN_ARTIFACT_UNREADABLE", recorded.stdout)
        self.assertNotIn("Traceback", recorded.stderr)

    def test_record_rejects_a_file_that_changes_during_capture(self) -> None:
        self.assertEqual(0, self.start().returncode)
        target = self.project_root / "sample.txt"
        target.write_text("Greeting:\nhello from thin record\nEnd greeting.\n")

        def mutate_during_capture(**_kwargs) -> str:
            target.write_text("Greeting:\nchanged during capture\nEnd greeting.\n")
            return "hello from thin record"

        with mock.patch(
            "synrail_proof_recorder_v0._capture_verification",
            side_effect=mutate_during_capture,
        ):
            with self.assertRaises(ProofRecordError) as raised:
                record_single_file_proof(
                    artifact_root=self.artifact_root,
                    project_root=self.project_root,
                    changed_file="sample.txt",
                    summary="Replaced the sample greeting with the requested verified line.",
                    verification_command="grep -n 'hello from thin record' sample.txt",
                )
        self.assertEqual("WORKTREE_CHANGED_DURING_RECORD", raised.exception.reason)

    def test_record_rejects_a_second_file_that_changes_during_capture(self) -> None:
        self.assertEqual(0, self.start().returncode)
        target = self.project_root / "sample.txt"
        target.write_text("Greeting:\nhello from thin record\nEnd greeting.\n")

        def mutate_second_file(**_kwargs) -> str:
            (self.project_root / "other.txt").write_text("changed during capture\n")
            return "hello from thin record"

        with mock.patch(
            "synrail_proof_recorder_v0._capture_verification",
            side_effect=mutate_second_file,
        ):
            with self.assertRaises(ProofRecordError) as raised:
                record_single_file_proof(
                    artifact_root=self.artifact_root,
                    project_root=self.project_root,
                    changed_file="sample.txt",
                    summary="Replaced the sample greeting with the requested verified line.",
                    verification_command="grep -n 'hello from thin record' sample.txt",
                )
        self.assertEqual("WORKTREE_CHANGED_DURING_RECORD", raised.exception.reason)

    def test_check_rejects_recorded_patch_after_target_changes_again(self) -> None:
        self.assertEqual(0, self.start().returncode)
        target = self.project_root / "sample.txt"
        target.write_text("Greeting:\nhello from thin record\nEnd greeting.\n")
        self.assertEqual(0, self.record().returncode)

        target.write_text(
            "Greeting:\nhello from thin record\nextra unrecorded edit\nEnd greeting.\n"
        )
        checked = self.run_alpha(
            "check",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
        )
        self.assertNotEqual("Status: Accepted", checked.stdout.splitlines()[0])
        self.assertIn("rerun synrail record", checked.stdout)
        bundle = json.loads((self.artifact_root / "bundle.json").read_text())
        self.assertTrue(bundle["recorded_patch_binding"]["required"])
        self.assertFalse(bundle["recorded_patch_binding"]["matched"])
        self.assertIn("recorded_patch_binding", bundle["semantically_insufficient_sections"])

        rerecorded = self.record()
        self.assertEqual(0, rerecorded.returncode, rerecorded.stdout + rerecorded.stderr)
        rechecked = self.run_alpha(
            "check",
            "--ephemeral",
            "--project-root",
            str(self.project_root),
        )
        self.assertEqual("Status: Accepted", rechecked.stdout.splitlines()[0])

    def test_live_patch_binding_runs_after_verification_recheck(self) -> None:
        self.assertEqual(0, self.start().returncode)
        target = self.project_root / "sample.txt"
        target.write_text("Greeting:\nhello from thin record\nEnd greeting.\n")
        self.assertEqual(0, self.record().returncode)

        def mutate_after_recheck(*_args, **_kwargs) -> dict:
            target.write_text(
                "Greeting:\nhello from thin record\nchanged after recheck\nEnd greeting.\n"
            )
            return {
                "required": True,
                "executed": True,
                "command_allowed": True,
                "matched": True,
                "stdout_snippet": "hello from thin record",
                "skip_reason": "",
            }

        args = argparse.Namespace(
            final_result=str(self.artifact_root / "final_result.json"),
            doctor_file="",
            readback="",
            scenario_proof="",
            state_file=str(self.artifact_root / "state.json"),
            task_class="small_template_text_fix",
            run_id="",
            baseline_identity="captured-clean-git-baseline",
            execution_surface_identity="single-tracked-file-worktree",
            prompt_identity="replace-one-greeting",
            task_identity="replace-one-greeting-with-verified-text",
        )
        with mock.patch(
            "synrail_bundle_v0.verification_recheck_results",
            side_effect=mutate_after_recheck,
        ):
            bundle = build_bundle(args)
        self.assertTrue(bundle["verification_recheck"]["matched"])
        self.assertFalse(bundle["recorded_patch_binding"]["matched"])

    def test_check_help_hides_internal_orchestration_flags(self) -> None:
        help_result = self.run_alpha("check", "--help")
        self.assertEqual(0, help_result.returncode, help_result.stdout + help_result.stderr)
        self.assertIn("--artifact-root", help_result.stdout)
        self.assertIn("--ephemeral", help_result.stdout)
        self.assertIn("--project-root", help_result.stdout)
        self.assertNotIn("--doctor-run-id", help_result.stdout)
        self.assertNotIn("--repair-packet-file", help_result.stdout)
        self.assertNotIn("--allowed-scope-path", help_result.stdout)


if __name__ == "__main__":
    unittest.main()
