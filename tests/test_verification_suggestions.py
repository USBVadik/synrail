#!/usr/bin/env python3
"""Regression coverage for read-only verification profile suggestions."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.reference.synrail_verification_suggestions_v0 import (
    MAX_MARKER_BYTES,
    VerificationSuggestionError,
    discover_verification_suggestions,
)
from tools.reference.synrail_verification_profile_v0 import SYNRAIL_PYTHON_ARGV0


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


class VerificationSuggestionTests(unittest.TestCase):
    def run_alpha(self, *args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return run([sys.executable, str(ALPHA_ENTRY), *args], cwd=cwd)

    def seed_git_project(self, tmpdir: str) -> Path:
        project_root = Path(tmpdir) / "project"
        project_root.mkdir()
        (project_root / "README.md").write_text("# project\n", encoding="utf-8")
        self.assertEqual(0, run(["git", "init"], cwd=project_root).returncode)
        self.assertEqual(0, run(["git", "add", "README.md"], cwd=project_root).returncode)
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

    def test_python_pytest_candidate_is_review_required_and_copyable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_suggestions_") as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "pyproject.toml").write_text(
                '[project]\nname = "sample"\ndependencies = ["pytest>=8"]\n',
                encoding="utf-8",
            )

            report = discover_verification_suggestions(project_root)

            self.assertEqual("verification_suggestions_v0", report["schema_version"])
            self.assertEqual("SUGGESTIONS_FOUND", report["status"])
            self.assertTrue(report["discovery_only"])
            self.assertFalse(report["source_provenance_verified"])
            self.assertFalse(report["verification_commands_executed"])
            self.assertFalse(report["files_written"])
            self.assertEqual(1, report["candidate_count"])
            candidate = report["candidates"][0]
            self.assertEqual("python-pytest", candidate["candidate_id"])
            self.assertEqual("python-tests", candidate["profile_name"])
            self.assertEqual([SYNRAIL_PYTHON_ARGV0, "-m", "pytest", "-q"], candidate["argv"])
            self.assertEqual("REVIEW_REQUIRED", candidate["trust_state"])
            self.assertEqual("NOT_ATTESTED", candidate["source_trust"])
            self.assertEqual(
                [
                    "synrail",
                    "init-verification",
                    "--name",
                    "python-tests",
                    "--",
                    SYNRAIL_PYTHON_ARGV0,
                    "-m",
                    "pytest",
                    "-q",
                ],
                candidate["scaffold_argv"],
            )
            self.assertFalse((project_root / "synrail.toml").exists())
            self.assertFalse((project_root / ".synrail").exists())

    def test_cli_discovers_git_root_without_running_package_script_or_writing_files(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_suggestions_cli_") as tmpdir:
            project_root = self.seed_git_project(tmpdir)
            marker = project_root / "script-executed.txt"
            package = {
                "scripts": {
                    "test": f'node -e "require(\'fs\').writeFileSync(\'{marker}\', \'ran\')"',
                }
            }
            (project_root / "package.json").write_text(json.dumps(package), encoding="utf-8")
            (project_root / "pnpm-lock.yaml").write_text("lockfileVersion: 9\n", encoding="utf-8")
            nested = project_root / "src" / "nested"
            nested.mkdir(parents=True)

            completed = self.run_alpha("suggest-verification", cwd=nested)

            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertIn(f"Project root: {project_root.resolve()}", completed.stdout)
            self.assertIn("Candidate 1: node-pnpm-test", completed.stdout)
            self.assertIn('Argv: ["pnpm", "test"]', completed.stdout)
            self.assertIn(
                "Scaffold: synrail init-verification --name node-tests -- pnpm test",
                completed.stdout,
            )
            self.assertIn("no suggested verification command was executed", completed.stdout)
            self.assertFalse(marker.exists(), "suggest-verification must never execute package scripts")
            self.assertFalse((project_root / "synrail.toml").exists())
            self.assertFalse((project_root / ".synrail").exists())

    def test_json_candidates_are_deterministic_across_supported_ecosystems(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_suggestions_json_") as tmpdir:
            project_root = self.seed_git_project(tmpdir)
            (project_root / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            (project_root / "package.json").write_text(
                json.dumps({"scripts": {"test": "vitest run"}}),
                encoding="utf-8",
            )
            (project_root / "package-lock.json").write_bytes(b"x" * (MAX_MARKER_BYTES + 1))
            (project_root / "go.mod").write_text("module example.test/app\n", encoding="utf-8")
            (project_root / "Cargo.toml").write_text('[package]\nname = "sample"\n', encoding="utf-8")

            completed = self.run_alpha("suggest-verification", "--json", cwd=project_root)

            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual(
                ["python-pytest", "node-npm-test", "go-test", "rust-cargo-test"],
                [item["candidate_id"] for item in payload["candidates"]],
            )
            self.assertEqual(4, payload["candidate_count"])
            self.assertEqual([], payload["warnings"], "lock markers are type-checked, not read in full")

    def test_node_package_manager_field_wins_without_executing_or_reading_scripts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_suggestions_manager_") as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").write_text(
                json.dumps(
                    {
                        "packageManager": "yarn@4.3.1",
                        "scripts": {"test": "node ./dangerous-test-runner.js"},
                    }
                ),
                encoding="utf-8",
            )
            (project_root / "package-lock.json").write_text("{}\n", encoding="utf-8")

            report = discover_verification_suggestions(project_root)

            candidate = report["candidates"][0]
            self.assertEqual("node-yarn-test", candidate["candidate_id"])
            self.assertEqual(["yarn", "test"], candidate["argv"])
            self.assertEqual(["package.json"], candidate["detected_from"])

    def test_placeholder_node_script_and_unknown_project_return_no_suggestions(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_suggestions_empty_") as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "package.json").write_text(
                json.dumps({"scripts": {"test": "echo Error: no test specified && exit 1"}}),
                encoding="utf-8",
            )
            (project_root / "pyproject.toml").write_text(
                '[project]\nname = "sample"\ndescription = "pytest is not configured here"\n',
                encoding="utf-8",
            )

            report = discover_verification_suggestions(project_root)

            self.assertEqual("NO_SUGGESTIONS", report["status"])
            self.assertEqual(0, report["candidate_count"])
            self.assertEqual([], report["candidates"])
            self.assertIn("init-verification", report["next_step"])

    def test_symlink_and_malformed_markers_are_ignored_with_named_warnings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_suggestions_unsafe_") as tmpdir:
            workspace = Path(tmpdir)
            project_root = workspace / "project"
            project_root.mkdir()
            outside = workspace / "outside-package.json"
            outside.write_text(json.dumps({"scripts": {"test": "touch escaped"}}), encoding="utf-8")
            try:
                (project_root / "package.json").symlink_to(outside)
            except OSError as exc:
                self.skipTest(f"symlink creation is unavailable: {exc}")
            (project_root / "pyproject.toml").write_text("[broken\n", encoding="utf-8")

            report = discover_verification_suggestions(project_root)

            self.assertEqual("NO_SUGGESTIONS", report["status"])
            reasons = {(item["path"], item["reason"]) for item in report["warnings"]}
            self.assertIn(("package.json", "MARKER_UNTRUSTED"), reasons)
            self.assertIn(("pyproject.toml", "MARKER_PARSE_FAILED"), reasons)
            self.assertFalse((workspace / "escaped").exists())

    def test_oversized_content_marker_is_skipped_but_root_marker_detection_remains_bounded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_suggestions_large_") as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "requirements-dev.txt").write_bytes(b"pytest\n" + b"x" * MAX_MARKER_BYTES)
            (project_root / "go.mod").write_bytes(b"x" * (MAX_MARKER_BYTES + 1))

            report = discover_verification_suggestions(project_root)

            self.assertEqual(["go-test"], [item["candidate_id"] for item in report["candidates"]])
            self.assertIn(
                ("requirements-dev.txt", "MARKER_TOO_LARGE"),
                {(item["path"], item["reason"]) for item in report["warnings"]},
            )

    def test_invalid_project_root_fails_closed_in_api_and_json_cli(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_verification_suggestions_invalid_") as tmpdir:
            missing = Path(tmpdir) / "missing"
            with self.assertRaises(VerificationSuggestionError) as error:
                discover_verification_suggestions(missing)
            self.assertEqual("PROJECT_ROOT_INVALID", error.exception.reason)

            completed = self.run_alpha(
                "suggest-verification",
                "--project-root",
                str(missing),
                "--json",
                cwd=Path(tmpdir),
            )
            self.assertEqual(2, completed.returncode, completed.stdout + completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertEqual("BLOCKED", payload["status"])
            self.assertEqual("PROJECT_ROOT_INVALID", payload["reason"])


if __name__ == "__main__":
    unittest.main()
