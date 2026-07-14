#!/usr/bin/env python3
"""Regression coverage for the privacy-bounded internal pilot capture."""

from __future__ import annotations

import hashlib
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.pilots.capture_cross_repo_run import (
    CLAIM_SCOPE,
    EVIDENCE_CLASS,
    PilotCaptureError,
    build_pilot_record,
    main,
)
from tools.reference.synrail_validate_v0 import validate_document


REPO_ROOT = Path(__file__).resolve().parents[1]
PILOT_FIXTURES = REPO_ROOT / "fixtures" / "internal_cross_repo_pilots"


def run(command: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)


class CrossRepoPilotTests(unittest.TestCase):
    def test_committed_pilots_are_bound_internal_evidence(self) -> None:
        schema = json.loads(
            (REPO_ROOT / "schemas" / "internal_cross_repo_pilot_v0.schema.json").read_text()
        )
        records = sorted(
            path
            for path in PILOT_FIXTURES.glob("*.json")
            if not path.name.endswith("-blocked-report.json")
        )
        self.assertEqual(3, len(records))

        for record_path in records:
            with self.subTest(record=record_path.name):
                record = json.loads(record_path.read_text())
                self.assertEqual([], validate_document(record, schema))
                self.assertEqual(EVIDENCE_CLASS, record["evidence_class"])
                self.assertEqual(CLAIM_SCOPE, record["claim_scope"])
                self.assertTrue(record["outcome"]["accepted"])
                self.assertEqual("yes", record["outcome"]["false_green_prevented"])
                self.assertEqual(
                    "VERIFICATION_FAILED",
                    record["outcome"]["first_blocker_reason"],
                )
                self.assertTrue(all(profile["green"] for profile in record["verification_profiles"]))

                blocked_path = record_path.with_name(
                    f"{record_path.stem}-blocked-report.json"
                )
                blocked_bytes = blocked_path.read_bytes()
                self.assertEqual(
                    hashlib.sha256(blocked_bytes).hexdigest(),
                    record["artifact_bindings"]["blocked_report_sha256"],
                )
                blocked = json.loads(blocked_bytes)
                self.assertEqual(record["run_id"], blocked["run_id"])
                self.assertEqual("BLOCKED", blocked["result"])
                self.assertEqual("VERIFICATION_FAILED", blocked["reason"])

                serialized = record_path.read_text() + blocked_path.read_text()
                self.assertNotIn("/Users/", serialized)
                self.assertNotIn("/tmp/", serialized)
                self.assertNotIn("stdout", serialized)
                self.assertNotIn("stderr", serialized)

    def seed(self, tmpdir: str) -> tuple[Path, Path]:
        project = Path(tmpdir) / "project"
        artifacts = Path(tmpdir) / "artifacts"
        project.mkdir()
        artifacts.mkdir()
        (project / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.assertEqual(0, run(["git", "init"], cwd=project).returncode)
        self.assertEqual(0, run(["git", "add", "app.py"], cwd=project).returncode)
        committed = run(
            [
                "git",
                "-c",
                "user.name=Pilot Tests",
                "-c",
                "user.email=pilot-tests@example.com",
                "commit",
                "-m",
                "seed",
            ],
            cwd=project,
        )
        self.assertEqual(0, committed.returncode, committed.stdout + committed.stderr)
        run_id = "ALPHA_RUN_PILOT_001"
        payloads = {
            "state.json": {
                "run_id": run_id,
                "start_timestamp_utc": "2026-07-14T10:00:00Z",
                "closure_timestamp_utc": "2026-07-14T10:02:03Z",
                "closure": {"status": "ACCEPTED"},
            },
            "project_profile.json": {
                "project_root": str(project.resolve()),
                "artifact_root": str(artifacts.resolve()),
                "project_type": "python",
                "verification_profiles": {
                    "config_sha256": "config-hash",
                    "profiles": {"unit": {"required": True}},
                },
            },
            "report.json": {
                "run_id": run_id,
                "result": "OK",
                "reason": "NONE",
                "closure_status": "ACCEPTED",
            },
            "final_result.json": {
                "request_id": run_id,
                "status": "PROVEN",
            },
            "verification_receipts.json": {
                "receipts": {
                    "unit": {
                        "run_id": run_id,
                        "config_sha256": "config-hash",
                        "duration_seconds": 1.25,
                        "exit_code": 0,
                        "timed_out": False,
                    }
                }
            },
        }
        for name, payload in payloads.items():
            (artifacts / name).write_text(json.dumps(payload), encoding="utf-8")
        (Path(tmpdir) / "blocked-report.json").write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "result": "BLOCKED",
                    "reason": "VERIFICATION_FAILED",
                    "closure_status": "CLAIMED_NOT_ACCEPTED",
                }
            ),
            encoding="utf-8",
        )
        return project, artifacts

    def build(self, project: Path, artifacts: Path) -> dict:
        return build_pilot_record(
            project_root=project,
            artifact_root=artifacts,
            repository_label="sample",
            task_summary="Fix the bounded behavior.",
            task_class="bounded-fix",
            ecosystem="python",
            setup_seconds=12.5,
            total_operator_seconds=130.0,
            time_to_first_blocker_seconds=40.0,
            false_green_prevented="yes",
            blocked_report_path=project.parent / "blocked-report.json",
            operator_interventions=["Reviewed profile."],
            confusion_moments=[],
            notes="Internal only.",
        )

    def test_capture_is_bound_redacted_and_explicitly_internal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_cross_repo_pilot_") as tmpdir:
            project, artifacts = self.seed(tmpdir)

            record = self.build(project, artifacts)

            self.assertEqual(EVIDENCE_CLASS, record["evidence_class"])
            self.assertEqual(CLAIM_SCOPE, record["claim_scope"])
            self.assertTrue(record["outcome"]["accepted"])
            self.assertEqual(123.0, record["timing"]["time_to_accepted_seconds"])
            self.assertEqual(1.25, record["timing"]["verification_seconds"])
            self.assertTrue(record["verification_profiles"][0]["green"])
            self.assertEqual("VERIFICATION_FAILED", record["outcome"]["first_blocker_reason"])
            self.assertTrue(record["artifact_bindings"]["blocked_report_sha256"])
            schema = json.loads(
                (REPO_ROOT / "schemas" / "internal_cross_repo_pilot_v0.schema.json").read_text()
            )
            self.assertEqual([], validate_document(record, schema))
            serialized = json.dumps(record)
            self.assertNotIn(str(project), serialized)
            self.assertNotIn(str(artifacts), serialized)
            self.assertNotIn("stdout", serialized)

    def test_capture_fails_closed_on_root_mismatch_and_symlinked_artifact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_cross_repo_pilot_") as tmpdir:
            project, artifacts = self.seed(tmpdir)
            other = Path(tmpdir) / "other"
            other.mkdir()
            with self.assertRaises(PilotCaptureError):
                self.build(other, artifacts)

            report = artifacts / "report.json"
            target = artifacts / "report-target.json"
            report.replace(target)
            try:
                report.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"symlink creation unavailable: {exc}")
            with self.assertRaises(PilotCaptureError):
                self.build(project, artifacts)

    def test_false_green_yes_requires_a_bound_blocked_report(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_cross_repo_pilot_") as tmpdir:
            project, artifacts = self.seed(tmpdir)
            with self.assertRaises(PilotCaptureError):
                build_pilot_record(
                    project_root=project,
                    artifact_root=artifacts,
                    repository_label="sample",
                    task_summary="Fix behavior.",
                    task_class="bounded-fix",
                    ecosystem="python",
                    setup_seconds=1,
                    total_operator_seconds=None,
                    time_to_first_blocker_seconds=None,
                    false_green_prevented="yes",
                    blocked_report_path=None,
                    operator_interventions=[],
                    confusion_moments=[],
                    notes="",
                )

    def test_cli_refuses_silent_output_replacement(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_cross_repo_pilot_") as tmpdir:
            project, artifacts = self.seed(tmpdir)
            output = Path(tmpdir) / "record.json"
            argv = [
                "--project-root",
                str(project),
                "--artifact-root",
                str(artifacts),
                "--output",
                str(output),
                "--repository-label",
                "sample",
                "--task-summary",
                "Fix behavior.",
                "--task-class",
                "bounded-fix",
                "--setup-seconds",
                "1",
                "--false-green-prevented",
                "unclear",
            ]

            self.assertEqual(0, main(argv))
            original = output.read_bytes()
            self.assertEqual(2, main(argv))
            self.assertEqual(original, output.read_bytes())


if __name__ == "__main__":
    unittest.main()
