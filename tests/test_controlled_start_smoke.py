#!/usr/bin/env python3
"""Smoke tests for controlled start, bootstrap gating, and proof guidance."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock


def run(cmd: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"


if str(REPO_ROOT / "tools" / "reference") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "tools" / "reference"))

from synrail_io_v0 import load_json  # noqa: E402
import synrail_cli_v0  # noqa: E402


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


class ControlledStartSmokeTests(unittest.TestCase):
    def run_alpha(
        self,
        *args: str,
        cwd: Path | None = None,
        env_overrides: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        repo_path = str(REPO_ROOT)
        env["PYTHONPATH"] = repo_path if not existing else repo_path + os.pathsep + existing
        if env_overrides:
            env.update(env_overrides)
        return subprocess.run(
            [sys.executable, str(ALPHA_ENTRY), *args],
            cwd=cwd or REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

    def _create_accepted_greeting_run(self, project_root: Path) -> Path:
        artifact_root = project_root / ".synrail"
        start = self.run_alpha(
            "start",
            "--artifact-root",
            ".synrail",
            "--project-root",
            str(project_root),
            "--task-identity",
            "Create accepted state before a path failure.",
            cwd=project_root,
        )
        self.assertEqual(0, start.returncode, start.stdout + start.stderr)

        target = project_root / "greeting.txt"
        target.write_text("Greeting:\nhello from Synrail\nEnd greeting.\n")
        verification_result = "2:hello from Synrail"
        state = load_json(artifact_root / "state.json")
        write_json(
            artifact_root / "final_result.json",
            {
                "request_id": state["run_id"],
                "task_class": state["task_class"],
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "Created and verified the bounded greeting.",
                "modified_files": ["greeting.txt"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "greeting.txt",
                    "added_line": "hello from Synrail",
                    "context_before": "Greeting:",
                    "context_after": "End greeting.",
                    "verification_command": "grep -n 'hello from Synrail' greeting.txt",
                    "verification_result": verification_result,
                },
            },
        )
        accepted = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
        self.assertEqual(0, accepted.returncode, accepted.stdout + accepted.stderr)
        self.assertIn("Status: Accepted", accepted.stdout)
        return artifact_root

    def test_no_args_prints_dashboard_instead_of_help(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_dashboard_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            dashboard = self.run_alpha(cwd=project_root)
            self.assertEqual(0, dashboard.returncode, dashboard.stdout + dashboard.stderr)
            self.assertIn("Synrail: local governance dashboard", dashboard.stdout)
            self.assertIn("CLI control kernel (not a background daemon)", dashboard.stdout)
            self.assertIn("Active run: none", dashboard.stdout)
            self.assertIn("Start new run: synrail start", dashboard.stdout)
            self.assertNotIn("usage: synrail", dashboard.stdout)

    def test_help_shows_compact_primary_surface(self) -> None:
        help_result = self.run_alpha("--help")
        self.assertEqual(0, help_result.returncode, help_result.stdout + help_result.stderr)
        self.assertIn("start", help_result.stdout)
        self.assertIn("record", help_result.stdout)
        self.assertIn("check", help_result.stdout)
        self.assertIn("status (dashboard)", help_result.stdout)
        self.assertIn("explain-proof (proof-explain)", help_result.stdout)
        self.assertIn("save", help_result.stdout)
        self.assertIn("restore", help_result.stdout)
        self.assertIn("init-agent", help_result.stdout)
        self.assertIn("init-ci", help_result.stdout)
        self.assertIn("init-verification", help_result.stdout)
        self.assertIn("preflight", help_result.stdout)
        self.assertNotIn("install-agent-files", help_result.stdout)
        self.assertNotIn("session-export", help_result.stdout)
        self.assertNotIn("bug-packet", help_result.stdout)
        self.assertNotIn("final-result-template", help_result.stdout)
        self.assertNotIn("readback-template", help_result.stdout)
        self.assertNotIn("scenario-proof-template", help_result.stdout)
        self.assertNotIn("runtime-helper", help_result.stdout)
        self.assertNotIn("deploy-check", help_result.stdout)
        self.assertNotIn("generate-prompt", help_result.stdout)
        self.assertNotIn("init\n", help_result.stdout)
        self.assertNotIn("init ", help_result.stdout)
        self.assertNotIn("init\t", help_result.stdout)
        self.assertNotIn("usage: synrail init", help_result.stdout)
        self.assertNotIn("usage: synrail install-agent-files", help_result.stdout)
        self.assertNotIn("usage: synrail init-ci", help_result.stderr)
        self.assertNotIn("usage: synrail init-agent", help_result.stderr)
        self.assertNotIn("usage: synrail install-agent-files", help_result.stderr)
        self.assertNotIn("session-export", help_result.stdout)
        self.assertNotIn("bug-packet", help_result.stdout)
        self.assertNotIn("final-result-template", help_result.stdout)
        self.assertNotIn("readback-template", help_result.stdout)
        self.assertNotIn("scenario-proof-template", help_result.stdout)
        self.assertNotIn("runtime-helper", help_result.stdout)
        self.assertNotIn("deploy-check", help_result.stdout)
        self.assertNotIn("generate-prompt", help_result.stdout)
        self.assertNotIn("deploy-check", help_result.stdout)
        self.assertNotIn("generate-prompt", help_result.stdout)

    def test_dashboard_shows_active_run_after_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_dashboard_active_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "Keep this run visible from the dashboard.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            dashboard = self.run_alpha(cwd=project_root)
            self.assertEqual(0, dashboard.returncode, dashboard.stdout + dashboard.stderr)
            self.assertIn("Workspace: controlled run in progress", dashboard.stdout)
            self.assertIn("Active run: ALPHA_RUN_", dashboard.stdout)
            self.assertIn("Next step: confirm that this repo/worktree is the intended place for the run", dashboard.stdout)
            self.assertNotIn("Next step: attest target surface", dashboard.stdout)

    def test_dashboard_prefers_local_wrapper_when_synrail_not_on_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_dashboard_wrapper_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            wrapper = project_root / ".venv" / "bin" / "synrail"
            wrapper.parent.mkdir(parents=True, exist_ok=True)
            wrapper.write_text("#!/bin/sh\nexit 0\n")
            wrapper.chmod(0o755)

            dashboard = self.run_alpha(cwd=project_root, env_overrides={"PATH": ""})
            self.assertEqual(0, dashboard.returncode, dashboard.stdout + dashboard.stderr)
            self.assertIn("Start new run: .venv/bin/synrail start", dashboard.stdout)
            self.assertIn("Full help: .venv/bin/synrail --help", dashboard.stdout)

    def test_start_and_check_hints_prefer_local_wrapper_when_synrail_not_on_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_start_wrapper_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            wrapper = project_root / ".venv" / "bin" / "synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            wrapper.parent.mkdir(parents=True, exist_ok=True)
            wrapper.write_text("#!/bin/sh\nexit 0\n")
            wrapper.chmod(0o755)

            start = self.run_alpha(
                "start",
                "Keep wrapper-aware hints honest.",
                cwd=project_root,
                env_overrides={"PATH": ""},
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            self.assertIn("Need a canonical final_result shape? run .venv/bin/synrail final-result-template", start.stdout)
            self.assertIn("Then run: .venv/bin/synrail check", start.stdout)

            check = self.run_alpha("check", cwd=project_root, env_overrides={"PATH": ""})
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("rerun .venv/bin/synrail check.", check.stdout)
            self.assertIn("Need a canonical final_result shape? run .venv/bin/synrail final-result-template", check.stdout)

    def test_preflight_reports_git_missing_without_crashing(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_preflight_no_git_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            result = self.run_alpha(
                "preflight",
                cwd=project_root,
                env_overrides={"PATH": ""},
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn(
                "Git is not installed. Synrail can still use structured diff_provenance, but git_diff and restore coverage will be weaker. Install git for the normal path.",
                result.stdout,
            )

    def test_preflight_reports_repo_native_alpha_fallback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_preflight_alpha_fallback_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "alpha.py").write_text("print('stub')\n")

            result = self.run_alpha(
                "preflight",
                cwd=project_root,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertIn("Repo-native alpha fallback available: yes", result.stdout)
            self.assertIn("Repo-native alpha command: python3 alpha.py", result.stdout)

    def test_preflight_json_shape_is_machine_readable(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_preflight_json_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root = project_root / ".artifacts"

            result = self.run_alpha(
                "preflight",
                "--artifact-root",
                str(artifact_root),
                "--json",
                cwd=project_root,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PASS", payload["status"])
            self.assertEqual(str(project_root.resolve()), payload["project_root"])
            self.assertEqual(str(project_root.resolve()), payload["current_directory"])
            self.assertEqual(str(artifact_root.resolve()), payload["artifact_root"])
            self.assertIn("python_version", payload)
            self.assertIn("available", payload["git"])
            self.assertIn("message", payload["git"])
            self.assertIn("available", payload["synrail_wrapper"])
            self.assertIn("command", payload["synrail_wrapper"])
            self.assertIn("available", payload["repo_native_alpha_fallback"])
            self.assertIn("command", payload["repo_native_alpha_fallback"])

    def test_restore_preview_surfaces_file_copy_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_restore_preview_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "hello.py").write_text('print("hello")\n')

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Preview restore before using it on a live workspace.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            save = self.run_alpha(
                "save",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                cwd=project_root,
            )
            self.assertEqual(0, save.returncode, save.stdout + save.stderr)
            self.assertIn("Preview command: synrail restore --preview", save.stdout)

            preview = self.run_alpha(
                "restore",
                "--artifact-root",
                ".synrail",
                "--preview",
                cwd=project_root,
            )
            self.assertEqual(0, preview.returncode, preview.stdout + preview.stderr)
            self.assertIn("Restore preview: Ready", preview.stdout)
            self.assertIn("Workspace restore mode: File-copy workspace snapshot", preview.stdout)
            self.assertIn("Caution: this restore will modify project workspace files", preview.stdout)
            self.assertIn("Next command: synrail restore --confirm", preview.stdout)
            self.assertTrue((artifact_root / "checkpoint_restore_preview.json").exists())

    def test_restore_requires_confirm_for_destructive_workspace_restore(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_restore_confirm_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "hello.py").write_text('print("hello")\n')

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Require explicit confirm before destructive restore.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            save = self.run_alpha(
                "save",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                cwd=project_root,
            )
            self.assertEqual(0, save.returncode, save.stdout + save.stderr)

            restore = self.run_alpha(
                "restore",
                "--artifact-root",
                ".synrail",
                cwd=project_root,
            )
            self.assertEqual(2, restore.returncode, restore.stdout + restore.stderr)
            self.assertIn("without explicit confirmation", restore.stdout)
            self.assertIn("Next command: synrail restore --confirm", restore.stdout)

    def test_start_creates_bootstrap_and_proof_request(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_controlled_start_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Keep this run controlled from the first action.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            self.assertIn("Controlled run started.", start.stdout)
            self.assertIn(
                "Do this now: make the bounded change and run local verification; then use synrail record for one tracked file, synrail record --all-modified for a small tracked batch, or strengthen final_result.json for other contours.",
                start.stdout,
            )
            self.assertIn("fallback note: readback.txt and scenario_proof.txt stay hidden by default unless a later synrail check names one.", start.stdout)
            self.assertIn("Need a canonical final_result shape? run synrail final-result-template", start.stdout)
            self.assertIn("Starter proof surface is ready for this run.", start.stdout)
            self.assertIn("Runtime helper: synrail runtime-helper", start.stdout)
            self.assertTrue((artifact_root / "bootstrap.json").exists())
            self.assertTrue((artifact_root / "bootstrap_validation.json").exists())
            self.assertTrue((artifact_root / "proof_request.json").exists())
            self.assertTrue((artifact_root / "target_identity.txt").exists())
            self.assertTrue((artifact_root / "final_result.json").exists())
            self.assertFalse((artifact_root / "readback.txt").exists())
            self.assertFalse((artifact_root / "scenario_proof.txt").exists())

            state = load_json(artifact_root / "state.json")
            bootstrap = load_json(artifact_root / "bootstrap.json")
            validation = load_json(artifact_root / "bootstrap_validation.json")
            proof_request = load_json(artifact_root / "proof_request.json")
            final_result = load_json(artifact_root / "final_result.json")

            self.assertTrue(bootstrap["controlled_mode"])
            self.assertTrue(state["start_timestamp_utc"])
            self.assertEqual("", state["closure_timestamp_utc"])
            self.assertEqual(0, state["check_count"])
            self.assertEqual(
                hashlib.sha256((artifact_root / "final_result.json").read_bytes()).hexdigest(),
                state["last_known_final_result_hash"],
            )
            self.assertEqual("VALID", validation["status"])
            self.assertEqual("edit_in_place", proof_request["starter_mode"])
            self.assertEqual(".synrail/final_result.json", proof_request["preferred_artifacts"]["final_result"])
            self.assertEqual(64, len(proof_request["starter_hashes"]["final_result"]))
            self.assertEqual(
                ["final_result", "modified_files", "diff_provenance"],
                proof_request["required_sections"],
            )
            self.assertIn("strong final_result.json plus local verification evidence", proof_request["summary"])
            self.assertIn("make final_result.json strong first", proof_request["next_safe_step"])
            self.assertIn("leave cleanup_status absent unless Synrail later asks for it", proof_request["next_safe_step"])
            self.assertIn("keep readback.txt and scenario_proof.txt untouched unless Synrail later names them", proof_request["next_safe_step"])
            self.assertNotIn("cleanup_status", final_result)
            self.assertEqual("direct_file_observation", final_result["diff_provenance"]["method"])
            self.assertIn("changed or observed line", final_result["diff_provenance"]["context_before"])
            self.assertIn("exact changed or observed line", final_result["diff_provenance"]["verification_result"])
            self.assertIn(
                "leave cleanup_status absent unless Synrail later asks for explicit cleanup attestation",
                final_result["_synrail"]["starter_guidance"]["cleanup_hint"],
            )
            self.assertIn(
                "Treat readback.txt and scenario_proof.txt as fallback-only surfaces",
                final_result["_synrail"]["starter_guidance"]["explanatory_surface_hint"],
            )
            self.assertIn(
                "unless Synrail explicitly targets one as blocker-specific fallback evidence",
                final_result["_synrail"]["starter_guidance"]["explanatory_surface_hint"],
            )

    def test_check_after_plain_init_requires_controlled_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_bootstrap_block_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)

            init = self.run_alpha(
                "init",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Do not allow post-hoc legalization.",
                cwd=project_root,
            )
            self.assertEqual(0, init.returncode, init.stdout + init.stderr)
            self.assertIn("Synrail setup is ready.", init.stdout)
            self.assertIn("This setup is not a controlled run yet.", init.stdout)
            self.assertIn("Runtime helper: synrail runtime-helper", init.stdout)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("Controlled Run Required", check.stdout)
            self.assertIn("Next command: synrail start", check.stdout)

    def test_refresh_acceptance_reports_validation_after_controlled_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_refresh_acceptance_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "Refresh acceptance from a controlled run.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            refresh = self.run_alpha("refresh-acceptance", cwd=project_root)
            self.assertEqual(0, refresh.returncode, refresh.stdout + refresh.stderr)
            self.assertIn("Acceptance rules refreshed.", refresh.stdout)
            self.assertIn("Validation: VALID", refresh.stdout)
            self.assertIn("Next command: synrail check", refresh.stdout)
            self.assertTrue((artifact_root / "acceptance_validation.json").exists())

            validation = load_json(artifact_root / "acceptance_validation.json")
            self.assertEqual("acceptance_criteria_validation_record_v0", validation["schema_version"])
            self.assertEqual("VALID", validation["status"])
            self.assertEqual("CRITERIA_VALID", validation["reason"])
            self.assertTrue(validation["task_class_matches"])
            self.assertTrue(validation["project_type_matches"])
            self.assertTrue(validation["target_classification_matches"])
            self.assertTrue(validation["intended_run_class_matches"])
            self.assertTrue(validation["required_gate_ids_match"])
            self.assertTrue(validation["required_bundle_sections_match"])
            self.assertTrue(validation["criteria_standard_matches"])
            self.assertTrue(validation["criteria_owner_matches"])
            self.assertTrue(validation["project_profile_fingerprint_matches"])
            self.assertTrue(validation["criteria_revision_matches"])
            self.assertTrue(validation["provenance_complete"])
            self.assertTrue(validation["provenance_profile_fingerprint_matches"])
            self.assertEqual("synrail refresh-acceptance", load_json(artifact_root / "acceptance_criteria.json")["criteria_provenance"]["generated_by"])

            state = load_json(artifact_root / "state.json")
            self.assertEqual(0, state["check_count"])
            self.assertEqual("INITIALIZED", state["state"])
            self.assertEqual("", state["closure_timestamp_utc"])
            self.assertEqual("UNKNOWN", state["doctor"]["status"])
            self.assertEqual("MISSING", state["proof_bundle"]["status"])
            self.assertEqual("OPEN", state["closure"]["status"])
            self.assertEqual("attest target surface", state["next_safe_step"])
            self.assertTrue((artifact_root / "bootstrap_validation.json").exists())
            self.assertTrue((artifact_root / "proof_request.json").exists())
            self.assertTrue((artifact_root / "acceptance_criteria.json").exists())
            self.assertTrue((artifact_root / "final_result.json").exists())
            self.assertFalse((artifact_root / "thin_output.json").exists())
            self.assertFalse((artifact_root / "report.json").exists())

    def test_thin_output_surfaces_refresh_change_impact(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_refresh_change_impact_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Surface only stale obligations after refresh invalidation.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            state = load_json(artifact_root / "state.json")
            state["state"] = "DOCTOR_BLOCKED"
            state["doctor"]["status"] = "FAIL"
            state["proof_bundle"]["status"] = "COMPLETE"
            state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
            state["closure"]["blocking_reason"] = "DOCTOR_NOT_GREEN"
            state["next_safe_step"] = "repair readiness"
            write_json(artifact_root / "state.json", state)
            write_json(
                artifact_root / "report.json",
                {
                    "reason": "DOCTOR_NOT_GREEN",
                    "result": "NON_GREEN",
                    "next_safe_step": "repair readiness",
                },
            )
            write_json(
                artifact_root / "refresh.json",
                {
                    "schema_version": "refresh_report_v0",
                    "run_id": state["run_id"],
                    "event_type": "DOCTOR_EVENT",
                    "steps_applied": ["doctor_status_refreshed"],
                    "invalidations": ["closure_invalidated_by_doctor"],
                    "dominant_invalidation": "closure_invalidated_by_doctor",
                    "resulting_state": "DOCTOR_BLOCKED",
                    "resulting_closure_status": "CLAIMED_NOT_ACCEPTED",
                    "next_safe_step": "run doctor and clear blocking failure classes",
                },
            )

            thin_output_result = self.run_alpha("thin-output", "--artifact-root", ".synrail", "--mode", "default", cwd=project_root)
            self.assertEqual(0, thin_output_result.returncode, thin_output_result.stdout + thin_output_result.stderr)
            self.assertIn("Do this now: Repair only readiness, then rerun synrail check.", thin_output_result.stdout)
            self.assertIn("Refresh change impact: closure invalidated by doctor", thin_output_result.stdout)
            self.assertIn("Applicable invalidations: closure invalidated by doctor", thin_output_result.stdout)

            thin_output = load_json(artifact_root / "thin_output.json")
            self.assertEqual("refresh change impact: closure invalidated by doctor", thin_output["change_impact_focus"])
            self.assertEqual("applicable invalidations: closure invalidated by doctor", thin_output["change_impact_scope"])

    def test_proof_plan_keeps_prose_surfaces_fallback_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_proof_plan_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            artifact_root.mkdir(parents=True, exist_ok=True)
            plan_output = artifact_root / "plan.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_proof_plan_v0.py"),
                    "--run-id",
                    "R1",
                    "--task-class",
                    "bounded_change",
                    "--artifact-root",
                    ".synrail",
                    "--baseline-identity",
                    "baseline",
                    "--execution-surface-identity",
                    "surface",
                    "--prompt-identity",
                    "prompt",
                    "--task-identity",
                    "Keep fallback prose off the happy path.",
                    "--output",
                    str(plan_output),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            plan = load_json(plan_output)
            self.assertEqual(
                ["final_result", "modified_files", "diff_provenance", "artifact_identity", "cleanup_status"],
                plan["required_sections"],
            )
            self.assertNotIn("readback", plan["required_sections"])
            self.assertNotIn("scenario_proof", plan["required_sections"])
            self.assertEqual(".synrail/readback.txt", plan["recommended_artifacts"]["readback"])
            self.assertEqual(".synrail/scenario.txt", plan["recommended_artifacts"]["scenario_proof"])

    def test_check_without_final_result_uses_proof_request_guidance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_proof_request_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Guide the proof path instead of asking me to invent it.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("waiting for explicit proof artifacts and local verification evidence", check.stdout)
            self.assertIn("run local verification", check.stdout)
            self.assertIn("use synrail record for one tracked file or strengthen final_result.json for other contours", check.stdout)
            self.assertIn("final_result: .synrail/final_result.json", check.stdout)
            self.assertIn("fallback note: readback.txt and scenario_proof.txt stay hidden by default unless a later synrail check names one.", check.stdout)
            self.assertIn("synrail final-result-template", check.stdout)

    def test_final_result_template_uses_current_run_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_final_result_template_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "Show the canonical final_result shape for this run.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            state = load_json(artifact_root / "state.json")

            template = self.run_alpha("final-result-template", cwd=project_root)
            self.assertEqual(0, template.returncode, template.stdout + template.stderr)
            self.assertIn(state["run_id"], template.stdout)
            self.assertIn('"status": "PROVEN"', template.stdout)
            self.assertIn('"change_disposition": "modified"', template.stdout)
            self.assertIn('"git_diff": "diff --git', template.stdout)
            self.assertIn('"diff_provenance": {', template.stdout)
            self.assertIn("If git is not installed, do not invent git_diff", template.stdout)
            self.assertIn("diff_provenance_records/per_file_diff_provenance", template.stdout)
            self.assertIn('"artifact_identity": {', template.stdout)
            self.assertIn("ALREADY_SATISFIED", template.stdout)
            self.assertIn("already_satisfied", template.stdout)
            self.assertNotIn('"cleanup_status": {', template.stdout)

    def test_final_result_template_can_write_output_file(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_final_result_template_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "Write the canonical final_result template to a file.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            output_path = project_root / "template.json"
            template = self.run_alpha("final-result-template", "--output", str(output_path), cwd=project_root)
            self.assertEqual(0, template.returncode, template.stdout + template.stderr)
            self.assertIn("Wrote canonical final_result template to template.json", template.stdout)
            self.assertTrue(output_path.exists())
            self.assertIn('"status": "PROVEN"', output_path.read_text())

    def test_readback_template_uses_current_run_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_readback_template_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "Show the canonical readback shape for this run.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            state = load_json(artifact_root / "state.json")

            template = self.run_alpha("readback-template", cwd=project_root)
            self.assertEqual(0, template.returncode, template.stdout + template.stderr)
            self.assertIn(state["run_id"], template.stdout)
            self.assertIn("Changed surface:", template.stdout)
            self.assertIn("Observed:", template.stdout)
            self.assertIn("record only the concrete property needed for the blocker Synrail explicitly targeted", template.stdout)
            self.assertIn("Fallback-only note", template.stdout)
            self.assertIn("leave this readback untouched unless Synrail explicitly targets this file", template.stdout)
            self.assertIn("keep it minimal and concrete; do not add extra narrative beyond the named blocker", template.stdout)
            self.assertIn("Runtime hint:", template.stdout)
            self.assertIn("for UI, route, or rendered output changes", template.stdout)
            self.assertIn("synrail runtime-helper", template.stdout)

    def test_scenario_proof_template_uses_current_run_context(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_scenario_proof_template_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "Show the canonical scenario_proof shape for this run.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "project_profile.json",
                {
                    "prefers_runtime_evidence": True,
                },
            )

            template = self.run_alpha("scenario-proof-template", cwd=project_root)
            self.assertEqual(0, template.returncode, template.stdout + template.stderr)
            self.assertIn(state["run_id"], template.stdout)
            self.assertIn("Scenario:", template.stdout)
            self.assertIn("Observed:", template.stdout)
            self.assertIn("paste only the concrete output, rendered fragment, or behavior needed to unblock it", template.stdout)
            self.assertIn("Fallback-only note", template.stdout)
            self.assertIn("leave this scenario proof untouched unless Synrail explicitly targets this file", template.stdout)
            self.assertIn("keep it minimal and concrete; do not add extra narrative beyond the named blocker", template.stdout)
            self.assertIn("Runtime hint:", template.stdout)
            self.assertIn("synrail runtime-helper", template.stdout)
            self.assertIn("Status: PASSED", template.stdout)

    def test_runtime_helper_offers_small_ui_paths(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_runtime_helper_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)
            (project_root / "app.py").write_text("print('stub')\n")

            init = self.run_alpha("init", cwd=project_root)
            self.assertEqual(0, init.returncode, init.stdout + init.stderr)

            helper = self.run_alpha("runtime-helper", cwd=project_root)
            self.assertEqual(0, helper.returncode, helper.stdout + helper.stderr)
            self.assertIn("manual runtime evidence", helper.stdout)
            self.assertIn("curl -s http://localhost:8000/  # then inspect the local response", helper.stdout)
            self.assertIn("python3 - <<'PY'", helper.stdout)
            self.assertIn("keep verification_command to the direct file-observation allowlist", helper.stdout)
            self.assertIn("browser automation", helper.stdout)

    def test_status_surfaces_nested_parent_git_warning(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_nested_status_") as tmpdir:
            parent_root = Path(tmpdir) / "parent"
            project_root = parent_root / "project"
            (parent_root / ".git").mkdir(parents=True, exist_ok=True)
            project_root.mkdir(parents=True, exist_ok=True)

            init = self.run_alpha("init", cwd=project_root)
            self.assertEqual(0, init.returncode, init.stdout + init.stderr)

            status = self.run_alpha("status", cwd=project_root)
            self.assertEqual(0, status.returncode, status.stdout + status.stderr)
            self.assertIn("Parent git repo detected above the project root", status.stdout)

    def test_explain_proof_guides_user_before_first_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_missing_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "Need proof explanation after the bundle exists.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(2, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("bundle.json has not been generated", explain.stdout)
            self.assertIn("run synrail check first", explain.stdout)

    def test_explain_proof_surfaces_semantic_reason(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_bundle_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "bundle.json",
                {
                    "status": "STRUCTURALLY_COMPLETE",
                    "structural_status": "COMPLETE",
                    "semantic_status": "INSUFFICIENT",
                    "semantic_next_safe_step": "capture non-empty diff or provenance evidence for the changed files",
                    "semantic_decision_trace": [
                        {
                            "section": "diff_provenance",
                            "evaluated": True,
                            "semantically_sufficient": False,
                            "why": "diff or provenance evidence is present but does not yet prove a concrete patch on the named files",
                            "recommended_action": "capture non-empty diff or provenance evidence for the changed files",
                        }
                    ],
                    "structural_decision_trace": [],
                    "missing_sections": [],
                    "semantically_insufficient_sections": ["diff_provenance"],
                },
            )

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(0, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("Semantic gaps:", explain.stdout)
            self.assertIn("diff_provenance", explain.stdout)
            self.assertIn("does not yet prove a concrete patch on the named files", explain.stdout)
            self.assertIn("Concrete fix: keep git_diff patch-shaped", explain.stdout)
            self.assertIn("synrail final-result-template", explain.stdout)

    def test_explain_proof_surfaces_artifact_identity_hints(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_identity_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "project_profile.json",
                {
                    "baseline_identity": "autodetected_generic_baseline",
                    "execution_surface_identity": "autodetected_generic_worktree",
                },
            )
            (artifact_root / "prompt_identity.txt").write_text("prompt-123\n")
            (artifact_root / "task_identity.txt").write_text("task-123\n")
            write_json(
                artifact_root / "bundle.json",
                {
                    "status": "STRUCTURALLY_COMPLETE",
                    "structural_status": "COMPLETE",
                    "semantic_status": "INSUFFICIENT",
                    "semantic_next_safe_step": "restore baseline, execution surface, prompt, and task identity values for this run",
                    "semantic_decision_trace": [
                        {
                            "section": "artifact_identity",
                            "evaluated": True,
                            "semantically_sufficient": False,
                            "why": "identity fields are incomplete or empty in the current run context and final result artifact",
                            "recommended_action": "restore baseline, execution surface, prompt, and task identity values for this run",
                        }
                    ],
                    "structural_decision_trace": [],
                    "missing_sections": [],
                    "semantically_insufficient_sections": ["artifact_identity"],
                },
            )

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(0, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("artifact_identity", explain.stdout)
            self.assertIn("Current run identity hints:", explain.stdout)
            self.assertIn("baseline_identity: autodetected_generic_baseline", explain.stdout)
            self.assertIn("prompt_identity: prompt-123", explain.stdout)

    def test_explain_proof_surfaces_readback_helper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_readback_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "project_profile.json",
                {
                    "prefers_runtime_evidence": True,
                },
            )
            write_json(
                artifact_root / "bundle.json",
                {
                    "status": "STRUCTURALLY_COMPLETE",
                    "structural_status": "COMPLETE",
                    "semantic_status": "INSUFFICIENT",
                    "semantic_next_safe_step": "record substantive readback from the changed sections on the attested surface",
                    "semantic_decision_trace": [
                        {
                            "section": "readback",
                            "evaluated": True,
                            "semantically_sufficient": False,
                            "why": "readback evidence does not yet name the changed surface with a concrete observed property",
                            "recommended_action": "record substantive readback from the changed sections on the attested surface",
                        }
                    ],
                    "structural_decision_trace": [],
                    "missing_sections": [],
                    "semantically_insufficient_sections": ["readback"],
                },
            )

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(0, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("readback", explain.stdout)
            self.assertIn("readback target: .synrail/readback.txt", explain.stdout)
            self.assertIn("readback evidence does not yet name the changed surface with a concrete observed property", explain.stdout)
            self.assertIn("synrail readback-template", explain.stdout)
            self.assertIn("synrail runtime-helper", explain.stdout)
            self.assertNotIn("observed readback", explain.stdout)

    def test_explain_proof_surfaces_scope_alignment_fix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_scope_alignment_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "bundle.json",
                {
                    "status": "STRUCTURALLY_COMPLETE",
                    "structural_status": "COMPLETE",
                    "semantic_status": "INSUFFICIENT",
                    "semantic_next_safe_step": "keep the implementation inside the requested additive scope and remove unrelated adjacent rewrites or spacing tweaks",
                    "semantic_decision_trace": [
                        {
                            "section": "scope_alignment",
                            "evaluated": True,
                            "semantically_sufficient": False,
                            "why": "the task reads like an add-only request, but the proof shows adjacent rewrites or removals beyond the requested insertion",
                            "recommended_action": "keep the implementation inside the requested additive scope and remove unrelated adjacent rewrites or spacing tweaks",
                        }
                    ],
                    "structural_decision_trace": [],
                    "missing_sections": [],
                    "semantically_insufficient_sections": ["scope_alignment"],
                },
            )

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(0, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("scope_alignment", explain.stdout)
            self.assertIn("requested additive change", explain.stdout)
            self.assertIn("spacing, class, or layout rewrites", explain.stdout)

    def test_explain_proof_surfaces_scenario_helper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_scenario_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "project_profile.json",
                {
                    "prefers_runtime_evidence": True,
                },
            )
            write_json(
                artifact_root / "bundle.json",
                {
                    "status": "STRUCTURALLY_COMPLETE",
                    "structural_status": "COMPLETE",
                    "semantic_status": "INSUFFICIENT",
                    "semantic_next_safe_step": "record an explicit scenario-proof result for the attested target surface",
                    "semantic_decision_trace": [
                        {
                            "section": "scenario_proof",
                            "evaluated": True,
                            "semantically_sufficient": False,
                            "why": "scenario-proof evidence does not yet record a concrete scenario context and outcome",
                            "recommended_action": "record an explicit scenario-proof result for the attested target surface",
                        }
                    ],
                    "structural_decision_trace": [],
                    "missing_sections": [],
                    "semantically_insufficient_sections": ["scenario_proof"],
                },
            )

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(0, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("scenario_proof", explain.stdout)
            self.assertIn("scenario_proof target: .synrail/scenario_proof.txt", explain.stdout)
            self.assertIn("scenario-proof evidence does not yet record a concrete scenario context and outcome", explain.stdout)
            self.assertIn("Runtime nudge:", explain.stdout)
            self.assertIn("synrail runtime-helper", explain.stdout)
            self.assertIn("synrail scenario-proof-template", explain.stdout)

    def test_explain_proof_surfaces_verification_corroboration_fix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_verification_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "bundle.json",
                {
                    "status": "STRUCTURALLY_COMPLETE",
                    "structural_status": "COMPLETE",
                    "semantic_status": "INSUFFICIENT",
                    "semantic_next_safe_step": "tie acceptance to explicit local verification evidence inside the current proof surfaces instead of prose-only readback and scenario text",
                    "semantic_decision_trace": [
                        {
                            "section": "verification_corroboration",
                            "evaluated": True,
                            "semantically_sufficient": False,
                            "why": "the proof still leans on authored text without an explicit structured verification record or a labeled scenario command/result pair",
                            "recommended_action": "tie acceptance to explicit local verification evidence inside the current proof surfaces instead of prose-only readback and scenario text",
                        }
                    ],
                    "structural_decision_trace": [],
                    "missing_sections": [],
                    "semantically_insufficient_sections": ["verification_corroboration"],
                },
            )

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(0, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("verification_corroboration", explain.stdout)
            self.assertIn("final_result target: .synrail/final_result.json", explain.stdout)
            self.assertIn("scenario_proof target: .synrail/scenario_proof.txt", explain.stdout)
            self.assertIn("prose-only proof", explain.stdout)
            self.assertIn("synrail final-result-template", explain.stdout)
            self.assertIn("synrail scenario-proof-template", explain.stdout)

    def test_explain_proof_surfaces_final_result_status_fix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_final_status_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "bundle.json",
                {
                    "status": "STRUCTURALLY_COMPLETE",
                    "structural_status": "COMPLETE",
                    "semantic_status": "INSUFFICIENT",
                    "semantic_next_safe_step": "state a trust-bearing final_result.status: use PROVEN for an evidenced modification run, or ALREADY_SATISFIED for a truthful no-op attestation",
                    "semantic_decision_trace": [
                        {
                            "section": "final_result_status",
                            "evaluated": True,
                            "semantically_sufficient": False,
                            "why": "final_result.status uses generic execution language (SUCCESS) instead of the trust-bearing closure claim PROVEN",
                            "recommended_action": "state a trust-bearing final_result.status: use PROVEN for an evidenced modification run, or ALREADY_SATISFIED for a truthful no-op attestation",
                        }
                    ],
                    "structural_decision_trace": [],
                    "missing_sections": [],
                    "semantically_insufficient_sections": ["final_result_status"],
                },
            )

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(0, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("final_result_status", explain.stdout)
            self.assertIn("final_result target: .synrail/final_result.json", explain.stdout)
            self.assertIn("PROVEN", explain.stdout)
            self.assertIn("ALREADY_SATISFIED", explain.stdout)
            self.assertIn("SUCCESS", explain.stdout)
            self.assertIn("synrail final-result-template", explain.stdout)

    def test_explain_proof_surfaces_presentation_alignment_fix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_presentation_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "bundle.json",
                {
                    "status": "STRUCTURALLY_COMPLETE",
                    "structural_status": "COMPLETE",
                    "semantic_status": "INSUFFICIENT",
                    "semantic_next_safe_step": "keep the newly added surface visually plain and remove extra emphasis styling unless the task asked for it",
                    "semantic_decision_trace": [
                        {
                            "section": "presentation_alignment",
                            "evaluated": True,
                            "semantically_sufficient": False,
                            "why": "the task reads like a plain add-only request, but the newly added surface adds extra emphasis styling: italic, opacity-75",
                            "recommended_action": "keep the newly added surface visually plain and remove extra emphasis styling unless the task asked for it",
                        }
                    ],
                    "structural_decision_trace": [],
                    "missing_sections": [],
                    "semantically_insufficient_sections": ["presentation_alignment"],
                },
            )

            explain = self.run_alpha("explain-proof", cwd=project_root)
            self.assertEqual(0, explain.returncode, explain.stdout + explain.stderr)
            self.assertIn("presentation_alignment", explain.stdout)
            self.assertIn("visually plain", explain.stdout)
            self.assertIn("italic, opacity", explain.stdout)

    def test_check_blocks_remote_target_as_unsupported(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_remote_unsupported_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Do not pretend that a remote target lane is supported.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            (artifact_root / "final_result.txt").write_text("Implemented the change and confirmed it locally.\n")

            check = self.run_alpha(
                "check",
                "--artifact-root",
                ".synrail",
                "--target-path",
                "ssh://remote-host/example-repo",
                "--target-classification",
                "remote_target",
                cwd=project_root,
            )
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("Remote Target Not Supported Yet", check.stdout)

            report = load_json(artifact_root / "report.json")
            thin_output = load_json(artifact_root / "thin_output.json")

            self.assertEqual("REMOTE_TARGET_UNSUPPORTED", report["reason"])
            self.assertEqual("NON_GREEN", thin_output["outcome_class"])
            self.assertEqual("", thin_output["next_command"])
            self.assertFalse((artifact_root / "prompt.json").exists())

    def test_repair_step_prefers_final_result_before_readback_starter_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_readback_focus_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Point the next repair at the exact starter proof file that is still missing.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "DONE",
                    "summary": "Implemented the bounded change.",
                    "modified_files": ["app.py"],
                    "git_diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@\n+patched\n",
                    "cleanup_status": {
                        "success": True,
                        "summary": "workspace is clean after the bounded change",
                    },
                },
            )
            (artifact_root / "scenario_proof.txt").write_text(
                "Scenario passed on the attested surface and confirmed the expected behavior.\n"
            )

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertFalse((artifact_root / "readback.txt").exists())
            self.assertNotIn("Prepared fallback surface: .synrail/readback.txt", check.stdout)
            self.assertIn(".synrail/final_result.json", check.stdout)
            self.assertNotIn("record readback in .synrail/readback.txt", check.stdout)

            repair_step = self.run_alpha("repair-step", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, repair_step.returncode, repair_step.stdout + repair_step.stderr)
            self.assertIn(".synrail/final_result.json", repair_step.stdout)
            self.assertIn("Repair target:", repair_step.stdout)
            self.assertNotIn("Repair target: record readback in .synrail/readback.txt", repair_step.stdout)

            prompt = load_json(artifact_root / "prompt.json")
            self.assertEqual("repair_final_result_artifact", prompt["current_step_id"])
            self.assertIn(
                prompt["current_step_subsurface_id"],
                {"final_result_payload", "final_result_status_record", "diff_provenance_record", "artifact_identity_record"},
            )
            self.assertEqual(".synrail/final_result.json", prompt["current_step_target_path"])
            self.assertIn("final_result.json", prompt["current_step_focus_summary"])
            self.assertIn("final_result.json", prompt["current_step_action_instruction"])
            self.assertIn("final_result.status", prompt["current_step_label"])

    def test_retry_preserves_controlled_bootstrap_after_proof_thin_check(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_retry_bootstrap_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Stay in the same controlled run while strengthening thin proof.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "COMPLETED",
                    "summary": "Implemented a bounded local change.",
                    "modified_files": ["app.py"],
                    "git_diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@\n+patched\n",
                    "cleanup_status": {
                        "success": True,
                        "summary": "workspace is stable after the bounded change",
                    },
                },
            )
            (artifact_root / "readback.txt").write_text("Updated app.py.\n")
            (artifact_root / "scenario_proof.txt").write_text("Scenario passed.\n")

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("Proof Too Thin To Trust", check.stdout)

            retry = self.run_alpha("retry", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, retry.returncode, retry.stdout + retry.stderr)
            self.assertIn("Proof Too Thin To Trust", retry.stdout)
            self.assertNotIn("Controlled Run Required", retry.stdout)
            self.assertNotIn("Not Ready For The Next Attempt", retry.stdout)

            retried_state = load_json(artifact_root / "state.json")
            self.assertTrue(retried_state["integrity"]["bootstrap_provenance_ok"])
            self.assertEqual(
                "CONTROLLED_BOOTSTRAP_CONFIRMED",
                retried_state["integrity"]["bootstrap_provenance_reason"],
            )

    def test_check_does_not_treat_first_starter_replacement_as_integrity_drift(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_first_starter_replacement_check_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Allow the first sanctioned final_result replacement without artifact drift.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            tracked_file = project_root / "src" / "app.py"
            tracked_file.parent.mkdir(parents=True, exist_ok=True)
            tracked_file.write_text('def main():\n    print("patched")\n    return 0\n')
            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "Implemented the bounded change and verified it locally.",
                    "modified_files": ["src/app.py"],
                    "git_diff": "",
                    "diff_provenance": {
                        "method": "direct_file_observation",
                        "changed_file": "src/app.py",
                        "added_line": 'print("patched")',
                        "context_before": "def main():",
                        "context_after": "    return 0",
                        "verification_command": "grep -n 'print(\"patched\")' src/app.py",
                        "verification_result": '    print("patched")',
                    },
                    "artifact_identity": {
                        "baseline_identity": "autodetected_generic_baseline",
                        "execution_surface_identity": "autodetected_generic_worktree",
                        "prompt_identity": "Allow the first sanctioned final_result replacement without artifact drift.",
                        "task_identity": "Allow the first sanctioned final_result replacement without artifact drift.",
                    },
                },
            )

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertNotIn("artifact integrity failed", check.stdout.lower())

            bundle = load_json(artifact_root / "bundle.json")
            report = load_json(artifact_root / "report.json")
            checked_state = load_json(artifact_root / "state.json")
            self.assertFalse(bundle["artifact_integrity_warning"])
            self.assertNotEqual("ARTIFACT_INTEGRITY_FAILED", report.get("reason", ""))
            self.assertFalse(checked_state["proof_bundle"]["artifact_integrity_warning"])
            self.assertIn(report.get("reason", ""), {"", "NONE"})

    def test_named_final_result_repair_can_reach_accepted_on_same_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_named_proof_repair_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Add a verified greeting.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            started_state = load_json(artifact_root / "state.json")
            starter_hash = started_state["last_known_final_result_hash"]

            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": started_state["run_id"],
                    "task_class": started_state["task_class"],
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "Done. Tests passed.",
                    "modified_files": ["greeting.txt"],
                    "git_diff": "",
                    "diff_provenance": "Done. Tests passed.",
                },
            )

            weak_check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, weak_check.returncode, weak_check.stdout + weak_check.stderr)
            self.assertIn("Status: Proof Incomplete", weak_check.stdout)
            repairable_state = load_json(artifact_root / "state.json")
            self.assertEqual("PROOF_BUNDLE_PARTIAL", repairable_state["state"])
            self.assertEqual(starter_hash, repairable_state["last_known_final_result_hash"])

            (project_root / "greeting.txt").write_text(
                "Greeting:\nhello from Synrail\nEnd greeting.\n"
            )
            verification_result = "2:hello from Synrail"
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": started_state["run_id"],
                    "task_class": started_state["task_class"],
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "Added the bounded greeting and verified the exact line locally.",
                    "modified_files": ["greeting.txt"],
                    "git_diff": "",
                    "diff_provenance": {
                        "method": "direct_file_observation",
                        "changed_file": "greeting.txt",
                        "added_line": "hello from Synrail",
                        "context_before": "Greeting:",
                        "context_after": "End greeting.",
                        "verification_command": "grep -n 'hello from Synrail' greeting.txt",
                        "verification_result": verification_result,
                    },
                },
            )

            accepted_check = self.run_alpha(
                "check",
                "--artifact-root",
                ".synrail",
                cwd=project_root,
            )
            self.assertEqual(0, accepted_check.returncode, accepted_check.stdout + accepted_check.stderr)
            self.assertIn("Status: Accepted", accepted_check.stdout)
            accepted_state = load_json(artifact_root / "state.json")
            self.assertEqual("CLOSURE_ACCEPTED", accepted_state["state"])
            self.assertEqual(
                hashlib.sha256((artifact_root / "final_result.json").read_bytes()).hexdigest(),
                accepted_state["last_known_final_result_hash"],
            )

    def test_repair_step_synthesizes_missing_packet_with_final_result_first_before_scenario_gap(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_repair_step_scenario_packet_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Guide the operator directly to scenario proof when that is the only gap.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "DONE",
                    "summary": "Implemented the bounded change.",
                    "modified_files": ["app.py"],
                    "git_diff": "diff --git a/app.py b/app.py\n--- a/app.py\n+++ b/app.py\n@@\n+patched\n",
                    "cleanup_status": {
                        "success": True,
                        "summary": "workspace is clean after the bounded change",
                    },
                },
            )
            (artifact_root / "readback.txt").write_text("Confirmed the changed section in app.py.\n")

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("set a trust-bearing final_result.status in .synrail/final_result.json", check.stdout)
            self.assertFalse((artifact_root / "scenario_proof.txt").exists())
            self.assertNotIn("Prepared fallback surface: .synrail/scenario_proof.txt", check.stdout)

            (artifact_root / "repair_packet.json").unlink(missing_ok=True)
            (artifact_root / "prompt.json").unlink(missing_ok=True)

            repair_step = self.run_alpha("repair-step", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, repair_step.returncode, repair_step.stdout + repair_step.stderr)
            self.assertNotIn("does not have the next bounded repair instruction yet", repair_step.stdout.lower())
            self.assertIn(".synrail/final_result.json", repair_step.stdout)
            self.assertIn("Repair target: set a trust-bearing final_result.status in .synrail/final_result.json", repair_step.stdout)
            self.assertIn("Do not touch fallback proof surfaces like .synrail/readback.txt or .synrail/scenario_proof.txt unless Synrail explicitly targets them.", load_json(artifact_root / "prompt.json")["prompt"])


    def test_doctor_surfaces_override_warning_and_preserves_json_stdout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_override_warning_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            doctor_output = project_root / ".synrail" / "doctor.json"
            artifact_path = project_root / ".synrail" / "final_result.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{}\n")
            project_root.mkdir(parents=True, exist_ok=True)

            doctor = self.run_alpha(
                "doctor",
                "--doctor-run-id", "DOCTOR_OVERRIDE_001",
                "--doctor-level", "CORE_DOCTOR",
                "--target-path", str(project_root),
                "--target-classification", "core_surface",
                "--baseline-identity", "TRUSTED_BASELINE_001",
                "--intended-run-class", "core_probe",
                "--artifact-path", str(artifact_path),
                "--output", str(doctor_output),
                "--clean-surface",
                cwd=project_root,
            )
            self.assertEqual(0, doctor.returncode, doctor.stdout + doctor.stderr)
            self.assertEqual("OK", json.loads(doctor.stdout.strip())["result"])
            self.assertIn("doctor override present", doctor.stderr.lower())
            self.assertIn("clean_execution_surface", doctor.stderr)

            record = load_json(doctor_output)
            self.assertEqual(["clean_execution_surface"], record["override_gates"])
            self.assertEqual("doctor override present: clean_execution_surface", record["override_summary"])
            self.assertEqual(["clean_execution_surface: operator bypass via --clean-surface"], record["override_warnings"])

    def test_check_surfaces_doctor_override_warning_before_status_summary(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_override_warning_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            tracked_file = project_root / "app.py"
            tracked_file.write_text("def main():\n    return 0\n")

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Surface doctor override warnings before closure.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            tracked_file.write_text('def main():\n    print("patched")\n    return 0\n')
            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "Implemented the bounded change and verified it locally.",
                    "modified_files": ["app.py"],
                    "git_diff": "",
                    "diff_provenance": {
                        "method": "direct_file_observation",
                        "changed_file": "app.py",
                        "added_line": '    print("patched")',
                        "context_before": "def main():",
                        "context_after": "    return 0",
                        "verification_command": "grep -n 'patched' app.py",
                        "verification_result": '    print("patched")',
                    },
                    "artifact_identity": {
                        "baseline_identity": "autodetected_generic_baseline",
                        "execution_surface_identity": "autodetected_generic_worktree",
                        "prompt_identity": "Surface doctor override warnings before closure.",
                        "task_identity": "Surface doctor override warnings before closure.",
                    },
                },
            )

            check = self.run_alpha(
                "check",
                "--artifact-root",
                ".synrail",
                "--clean-surface",
                cwd=project_root,
            )
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertIn("warning: doctor override present", check.stdout.lower())
            self.assertIn("clean_execution_surface: operator bypass via --clean-surface", check.stdout)
            self.assertLess(
                check.stdout.lower().index("warning: doctor override present"),
                check.stdout.index("Status:"),
            )

            doctor = load_json(artifact_root / "doctor.json")
            self.assertEqual("doctor override present: clean_execution_surface", doctor["override_summary"])
            self.assertEqual(["clean_execution_surface: operator bypass via --clean-surface"], doctor["override_warnings"])

    def test_check_prefers_explicit_clean_surface_override_over_observed_scope_defaults(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_clean_surface_override_precedence_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)

            git_init = run(["git", "init"], cwd=project_root)
            self.assertEqual(0, git_init.returncode, git_init.stdout + git_init.stderr)
            tracked_file = project_root / "src" / "app.py"
            tracked_file.parent.mkdir(parents=True, exist_ok=True)
            tracked_file.write_text("def main():\n    return 0\n")
            git_add = run(["git", "add", "src/app.py"], cwd=project_root)
            self.assertEqual(0, git_add.returncode, git_add.stdout + git_add.stderr)
            configure_identity = subprocess.run(
                [
                    "git",
                    "-c", "user.name=Test",
                    "-c", "user.email=test@example.com",
                    "commit",
                    "-m",
                    "seed",
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, configure_identity.returncode, configure_identity.stdout + configure_identity.stderr)

            (project_root / "docs").mkdir(parents=True, exist_ok=True)
            (project_root / "docs" / "out_of_scope.md").write_text("changed\n")

            start = self.run_alpha(
                "start",
                "Prefer explicit clean-surface repair input over observed dirty scope defaults.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": "RUN1",
                    "task_class": "bounded_change",
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "Bound one in-scope file only.",
                    "modified_files": ["src/app.py"],
                    "git_diff": "",
                    "diff_provenance": {
                        "method": "direct_file_observation",
                        "changed_file": "src/app.py",
                        "added_line": "    return 0",
                        "context_before": "def main():",
                        "context_after": "",
                        "verification_command": "grep -n 'return 0' src/app.py",
                        "verification_result": "2:    return 0",
                    },
                    "artifact_identity": {
                        "baseline_identity": "autodetected_generic_baseline",
                        "execution_surface_identity": "autodetected_generic_worktree",
                        "prompt_identity": "Prefer explicit clean-surface repair input over observed dirty scope defaults.",
                        "task_identity": "Prefer explicit clean-surface repair input over observed dirty scope defaults.",
                    },
                },
            )

            check = self.run_alpha(
                "check",
                "--artifact-root",
                ".synrail",
                "--clean-surface",
                cwd=project_root,
            )
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("doctor override present", check.stdout.lower())
            doctor = load_json(artifact_root / "doctor.json")
            self.assertTrue(doctor["gate_results"]["clean_execution_surface"]["override"])
            self.assertEqual("PASS", doctor["gate_results"]["clean_execution_surface"]["status"])

    def test_check_accepts_git_worktree_when_observed_changes_match_final_result_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_git_observed_scope_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            git_init = run(["git", "init"], cwd=project_root)
            self.assertEqual(0, git_init.returncode, git_init.stdout + git_init.stderr)
            tracked_file = project_root / "src" / "app.py"
            tracked_file.parent.mkdir(parents=True, exist_ok=True)
            tracked_file.write_text("def main():\n    return 0\n")
            git_add = run(["git", "add", "src/app.py"], cwd=project_root)
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
                "Accept honest observed-safe git worktree scope without override gates.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            tracked_file.write_text('def main():\n    print("patched")\n    return 0\n')
            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "Implemented the bounded change and verified it locally.",
                    "modified_files": ["src/app.py"],
                    "git_diff": "",
                    "diff_provenance": {
                        "method": "direct_file_observation",
                        "changed_file": "src/app.py",
                        "added_line": '    print("patched")',
                        "context_before": "def main():",
                        "context_after": "    return 0",
                        "verification_command": "grep -n 'print(\"patched\")' src/app.py",
                        "verification_result": '    print("patched")',
                    },
                    "artifact_identity": {
                        "baseline_identity": "autodetected_python_baseline",
                        "execution_surface_identity": "autodetected_python_worktree",
                        "prompt_identity": "Accept honest observed-safe git worktree scope without override gates.",
                        "task_identity": "Accept honest observed-safe git worktree scope without override gates.",
                    },
                },
            )

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertNotIn("doctor override present", check.stdout.lower())

            doctor = load_json(artifact_root / "doctor.json")
            report = load_json(artifact_root / "report.json")
            thin_output = load_json(artifact_root / "thin_output.json")
            self.assertEqual([], doctor["override_gates"])
            self.assertFalse(doctor["gate_results"]["clean_execution_surface"]["override"])
            self.assertIn("explicitly observed", doctor["gate_results"]["clean_execution_surface"]["note"])
            self.assertNotEqual("DOCTOR_OVERRIDE_PRESENT", report.get("reason", ""))
            self.assertEqual("ACCEPTED", thin_output["outcome_class"])

    def test_check_rejects_git_worktree_when_dirty_files_exceed_proven_scope(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_git_unproven_scope_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            git_init = run(["git", "init"], cwd=project_root)
            self.assertEqual(0, git_init.returncode, git_init.stdout + git_init.stderr)
            intended_file = project_root / "intended.txt"
            unrelated_file = project_root / "unrelated.txt"
            intended_file.write_text("before intended\n")
            unrelated_file.write_text("before unrelated\n")
            git_add = run(["git", "add", "intended.txt", "unrelated.txt"], cwd=project_root)
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
                "Reject non-override observed scope when dirty files exceed proven proof-backed scope.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            intended_file.write_text("after intended\n")
            unrelated_file.write_text("after unrelated\n")
            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "Implemented the bounded change and verified it locally.",
                    "modified_files": ["intended.txt"],
                    "git_diff": "",
                    "diff_provenance": {
                        "method": "direct_file_observation",
                        "changed_file": "intended.txt",
                        "added_line": "after intended",
                        "context_before": "before intended",
                        "verification_command": "grep -n 'after intended' intended.txt",
                        "verification_result": "after intended",
                    },
                    "artifact_identity": {
                        "baseline_identity": "autodetected_python_baseline",
                        "execution_surface_identity": "autodetected_python_worktree",
                        "prompt_identity": "Reject non-override observed scope when dirty files exceed proven proof-backed scope.",
                        "task_identity": "Reject non-override observed scope when dirty files exceed proven proof-backed scope.",
                    },
                },
            )

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, check.returncode, check.stdout + check.stderr)
            self.assertIn("workspace not trusted", check.stdout.lower())
            self.assertIn("workspace is not ready yet", check.stdout.lower())

            doctor = load_json(artifact_root / "doctor.json")
            report = load_json(artifact_root / "report.json")
            thin_output = load_json(artifact_root / "thin_output.json")
            rejected_state = load_json(artifact_root / "state.json")
            self.assertIn("execution surface has out-of-scope modifications", doctor["gate_results"]["clean_execution_surface"]["note"])
            self.assertIn("unrelated.txt", doctor["gate_results"]["clean_execution_surface"]["note"])
            self.assertEqual("FAIL", doctor["gate_results"]["clean_execution_surface"]["status"])
            self.assertEqual([], doctor["override_gates"])
            self.assertEqual("DOCTOR_NOT_GREEN", report.get("reason", ""))
            self.assertNotEqual("ACCEPTED", thin_output["outcome_class"])
            self.assertEqual(1, rejected_state["check_count"])
            self.assertEqual("", rejected_state["closure_timestamp_utc"])

            spoofed_scope = self.run_alpha(
                "check",
                "--artifact-root",
                ".synrail",
                "--changed-file",
                "intended.txt",
                "--allowed-scope-path",
                "intended.txt",
                cwd=project_root,
            )
            self.assertEqual(2, spoofed_scope.returncode, spoofed_scope.stdout + spoofed_scope.stderr)
            self.assertIn("Workspace Not Trusted", spoofed_scope.stdout)
            self.assertNotIn("Status: Accepted", {line.strip() for line in spoofed_scope.stdout.splitlines()})

            spoofed_doctor = load_json(artifact_root / "doctor.json")
            spoofed_report = load_json(artifact_root / "report.json")
            self.assertEqual("FAIL", spoofed_doctor["gate_results"]["clean_execution_surface"]["status"])
            self.assertIn("unrelated.txt", spoofed_doctor["gate_results"]["clean_execution_surface"]["note"])
            self.assertEqual("DOCTOR_NOT_GREEN", spoofed_report.get("reason", ""))

            retry = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(2, retry.returncode, retry.stdout + retry.stderr)
            self.assertIn("Workspace Not Trusted", retry.stdout)
            self.assertIn("--clean-surface", retry.stdout)

            retried_state = load_json(artifact_root / "state.json")
            self.assertEqual(3, retried_state["check_count"])
            self.assertEqual("", retried_state["closure_timestamp_utc"])

    def test_check_waives_cleanup_from_runtime_doctor_truth(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_cleanup_happy_path_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start = self.run_alpha(
                "start",
                "--artifact-root",
                ".synrail",
                "--project-root",
                str(project_root),
                "--task-identity",
                "Let normal synrail check satisfy cleanup from doctor-ready workspace truth.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)

            tracked_file = project_root / "src" / "app.py"
            tracked_file.parent.mkdir(parents=True, exist_ok=True)
            tracked_file.write_text('def main():\n    print("patched")\n    return 0\n')
            state = load_json(artifact_root / "state.json")
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": state["run_id"],
                    "task_class": state["task_class"],
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "Implemented the bounded change and verified it locally.",
                    "modified_files": ["src/app.py"],
                    "git_diff": "",
                    "diff_provenance": {
                        "method": "direct_file_observation",
                        "changed_file": "src/app.py",
                        "added_line": 'print("patched")',
                        "context_before": "def main():",
                        "context_after": "    return 0",
                        "verification_command": "grep -n 'print(\"patched\")' src/app.py",
                        "verification_result": '    print("patched")',
                    },
                    "artifact_identity": {
                        "baseline_identity": "autodetected_generic_baseline",
                        "execution_surface_identity": "autodetected_generic_worktree",
                        "prompt_identity": "Let normal synrail check satisfy cleanup from doctor-ready workspace truth.",
                        "task_identity": "Let normal synrail check satisfy cleanup from doctor-ready workspace truth.",
                    },
                },
            )

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertNotIn("Proof Incomplete", check.stdout)
            self.assertNotIn("record cleanup status in .synrail/final_result.json", check.stdout)

            bundle = load_json(artifact_root / "bundle.json")
            thin_output = load_json(artifact_root / "thin_output.json")
            accepted_state = load_json(artifact_root / "state.json")
            self.assertTrue(bundle["cleanup_status"]["from_doctor"])
            self.assertTrue(bundle["cleanup_status"]["waived_by_runtime_corroboration"])
            self.assertNotIn("cleanup_status", bundle["missing_sections"])
            self.assertEqual("COMPLETE", bundle["status"])
            self.assertEqual("ACCEPTED", thin_output["outcome_class"])
            self.assertTrue(accepted_state["start_timestamp_utc"])
            self.assertTrue(accepted_state["closure_timestamp_utc"])
            self.assertEqual(1, accepted_state["check_count"])

            first_closure_timestamp = accepted_state["closure_timestamp_utc"]
            retry = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, retry.returncode, retry.stdout + retry.stderr)
            self.assertIn("Status: Accepted", retry.stdout)

            retried_state = load_json(artifact_root / "state.json")
            self.assertEqual("CLOSURE_ACCEPTED", retried_state["state"])
            self.assertEqual(2, retried_state["check_count"])
            self.assertEqual(first_closure_timestamp, retried_state["closure_timestamp_utc"])


    def test_start_after_terminal_state_auto_clears_proof(self) -> None:
        """After CLOSURE_ACCEPTED, next synrail start should work without manual cleanup."""
        with tempfile.TemporaryDirectory(prefix="synrail_restart_after_terminal_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            # First run: synrail start
            start1 = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "First task for terminal state test.",
                cwd=project_root,
            )
            self.assertEqual(0, start1.returncode, start1.stdout + start1.stderr)

            # Simulate completed run: modify proof files and set terminal state
            state = load_json(artifact_root / "state.json")
            first_run_id = state["run_id"]
            state["state"] = "CLOSURE_ACCEPTED"
            write_json(artifact_root / "state.json", state)
            (artifact_root / "final_result.json").write_text(
                json.dumps({"status": "DONE", "summary": "completed"}) + "\n"
            )
            (artifact_root / "readback.txt").write_text("Confirmed change in source.\n")
            (artifact_root / "scenario_proof.txt").write_text("Scenario passed.\n")

            # Second run: synrail start should auto-clear and succeed
            start2 = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "Second task after terminal state.",
                cwd=project_root,
            )
            self.assertEqual(0, start2.returncode, start2.stdout + start2.stderr)
            self.assertIn("Controlled run started.", start2.stdout)
            next_state = load_json(artifact_root / "state.json")
            self.assertNotEqual(first_run_id, next_state["run_id"])

    def test_start_after_active_run_still_blocks(self) -> None:
        """Mid-run proof artifacts should still block a new start."""
        with tempfile.TemporaryDirectory(prefix="synrail_restart_blocks_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

            start1 = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "Active run that should not be overwritten.",
                cwd=project_root,
            )
            self.assertEqual(0, start1.returncode, start1.stdout + start1.stderr)

            # Simulate active run: modify proof but state is NOT terminal
            state = load_json(artifact_root / "state.json")
            self.assertNotIn(state["state"], ("CLOSURE_ACCEPTED", "CLOSURE_REJECTED"))
            (artifact_root / "final_result.json").write_text(
                json.dumps({"status": "DONE", "summary": "in progress"}) + "\n"
            )

            # Second start should be blocked
            start2 = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "Should not overwrite active run.",
                cwd=project_root,
            )
            self.assertEqual(2, start2.returncode)
            self.assertIn("proof artifacts already exist", start2.stdout)

    def test_start_reuses_existing_untouched_run(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_restart_reuse_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)

            start1 = self.run_alpha(
                "start",
                "First onboarding run.",
                cwd=project_root,
            )
            self.assertEqual(0, start1.returncode, start1.stdout + start1.stderr)
            first_state = load_json(artifact_root / "state.json")
            first_run_id = first_state["run_id"]
            first_task_identity = (artifact_root / "task_identity.txt").read_text()

            start2 = self.run_alpha(
                "start",
                "Second onboarding run should not silently replace the first.",
                cwd=project_root,
            )
            self.assertEqual(0, start2.returncode, start2.stdout + start2.stderr)
            self.assertIn("Synrail already has a controlled run in progress.", start2.stdout)
            self.assertIn(first_run_id, start2.stdout)
            self.assertIn("Runtime helper: synrail runtime-helper", start2.stdout)

            second_state = load_json(artifact_root / "state.json")
            self.assertEqual(first_run_id, second_state["run_id"])
            self.assertEqual(first_task_identity, (artifact_root / "task_identity.txt").read_text())

    def test_start_rejects_corrupted_existing_state_with_safe_refusal(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_corrupt_start_state_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            state_path = artifact_root / "state.json"
            state_path.write_text('{"schema_version": "run_state_v0", invalid\n')

            start = self.run_alpha(
                "start",
                "--artifact-root", ".synrail",
                "--project-root", str(project_root),
                "--task-identity", "Handle corrupted state safely.",
                cwd=project_root,
            )
            self.assertEqual(2, start.returncode)
            self.assertNotIn("Traceback", start.stdout + start.stderr)
            self.assertNotIn("JSONDecodeError", start.stdout + start.stderr)
            self.assertIn("current run state artifact is unreadable", start.stdout)
            self.assertIn("restore a verified checkpoint", start.stdout)
            self.assertEqual('{"schema_version": "run_state_v0", invalid\n', state_path.read_text())

    def test_check_rejects_artifact_root_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_check_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            outside = Path(tmpdir) / "outside"
            outside.mkdir(parents=True, exist_ok=True)

            result = self.run_alpha(
                "check",
                "--artifact-root",
                str(outside),
                cwd=project_root,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("ERROR", payload["result"])
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("BLOCKING", payload["severity"])
            self.assertFalse(payload["accepted"])
            self.assertFalse(payload["closure_evaluated"])
            self.assertEqual("--artifact-root", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])
            self.assertIn("Status: Blocked", result.stderr)
            self.assertIn("Blocking diagnostic: PATH_SCOPE_VIOLATION", result.stderr)
            self.assertIn("stopped before closure", result.stderr)
            self.assertIn("--ephemeral", result.stderr)
            self.assertNotIn("Status: Accepted", result.stdout + result.stderr)

    def test_check_target_escape_is_blocking_and_never_rendered_as_accepted(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_target_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            outside = Path(tmpdir) / "outside"
            project_root.mkdir(parents=True, exist_ok=True)
            outside.mkdir(parents=True, exist_ok=True)

            result = self.run_alpha(
                "check",
                "--artifact-root",
                str(artifact_root),
                "--project-root",
                str(project_root),
                "--target-path",
                str(outside),
                cwd=project_root,
            )

            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("BLOCKING", payload["severity"])
            self.assertFalse(payload["accepted"])
            self.assertFalse(payload["closure_evaluated"])
            self.assertEqual("--target-path", payload["path_arg"])
            self.assertIn("Status: Blocked", result.stderr)
            self.assertIn("this command did not accept the task", result.stderr)
            self.assertIn("run from the target repository root", result.stderr)
            self.assertNotIn("Warning:", result.stderr)
            self.assertNotIn("Status: Accepted", result.stdout + result.stderr)

    def test_check_dev_mode_keeps_path_scope_failure_machine_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_dev_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            outside = Path(tmpdir) / "outside"
            project_root.mkdir(parents=True, exist_ok=True)
            outside.mkdir(parents=True, exist_ok=True)

            result = self.run_alpha(
                "check",
                "--artifact-root",
                str(outside),
                "--mode",
                "dev",
                cwd=project_root,
            )

            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            self.assertEqual("PATH_SCOPE_VIOLATION", json.loads(result.stdout)["reason"])
            self.assertEqual("", result.stderr)

    def test_check_rejects_child_path_field_before_stale_accepted_report_can_render(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_stale_report_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root = self._create_accepted_greeting_run(project_root)
            outside = Path(tmpdir) / "outside-profile.json"
            outside.write_text("{}\n")

            result = self.run_alpha(
                "check",
                "--artifact-root",
                ".synrail",
                "--coverage-profile-file",
                str(outside),
                cwd=project_root,
            )

            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("--coverage-profile-file", payload["path_arg"])
            self.assertFalse(payload["accepted"])
            self.assertIn("Status: Blocked", result.stderr)
            self.assertNotIn("Status: Accepted", result.stdout + result.stderr)
            self.assertFalse((artifact_root / "report.json").exists())

    def test_check_blocks_corrupt_report_directory_without_traceback(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_report_directory_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root = self._create_accepted_greeting_run(project_root)
            report_path = artifact_root / "report.json"
            report_path.unlink()
            report_path.mkdir()

            result = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)

            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--report-file", payload["path_arg"])
            self.assertIn("not a file surface", payload["detail"])
            self.assertIn("Status: Blocked", result.stderr)
            self.assertNotIn("Traceback", result.stdout + result.stderr)
            self.assertNotIn("Status: Accepted", result.stdout + result.stderr)

    def test_failed_child_cannot_reuse_stale_report_if_parent_scope_map_drifts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_child_failure_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root = self._create_accepted_greeting_run(project_root)
            outside = Path(tmpdir) / "outside-profile.json"
            outside.write_text("{}\n")
            parent_scopes_without_coverage = dict(synrail_cli_v0.CHECK_PATH_SCOPES)
            parent_scopes_without_coverage.pop("coverage_profile_file")
            stdout = StringIO()
            stderr = StringIO()

            with mock.patch.object(
                synrail_cli_v0,
                "CHECK_PATH_SCOPES",
                parent_scopes_without_coverage,
            ), mock.patch.object(
                synrail_cli_v0,
                "current_project_root",
                return_value=project_root,
            ), redirect_stdout(stdout), redirect_stderr(stderr):
                code = synrail_cli_v0.main(
                    [
                        "check",
                        "--artifact-root",
                        str(artifact_root),
                        "--project-root",
                        str(project_root),
                        "--coverage-profile-file",
                        str(outside),
                    ]
                )

            self.assertEqual(2, code, stdout.getvalue() + stderr.getvalue())
            self.assertIn("PATH_SCOPE_VIOLATION", stdout.getvalue())
            self.assertNotIn("Status: Accepted", stdout.getvalue() + stderr.getvalue())
            self.assertFalse((artifact_root / "report.json").exists())

    def test_direct_doctor_rejects_target_identity_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside = Path(tmpdir) / "outside.txt"
            outside.write_text("outside\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--target-identity-file",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--target-identity-file", payload["path_arg"])
            self.assertIn("escapes project and artifact roots", payload["detail"])

    def test_direct_doctor_rejects_symlinked_target_identity_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_target_identity_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            target_identity = project_root / "target_identity.txt"
            target_identity.write_text("EXPECTED_SURFACE_001\n")
            target_identity_link = project_root / "target_identity_link.txt"
            target_identity_link.symlink_to(target_identity)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "EXACT_RETRY_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "exact_retry",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--target-identity-file",
                    str(target_identity_link),
                    "--expected-target-identity",
                    "EXPECTED_SURFACE_001",
                    "--prompt-identity-ok",
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--target-identity-file", payload["path_arg"])
            self.assertIn("symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_prompt_identity_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_prompt_identity_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            prompt_identity = artifact_root / "prompt_identity.txt"
            prompt_identity.write_text("TASK-IDENTITY-001\n")
            prompt_identity_link = artifact_root / "prompt_identity_link.txt"
            prompt_identity_link.symlink_to(prompt_identity)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "EXACT_RETRY_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "exact_retry",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--artifact-path",
                    str(artifact_root / "final_result.json"),
                    "--prompt-identity-file",
                    str(prompt_identity_link),
                    "--expected-task-identity",
                    "TASK-IDENTITY-001",
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--prompt-identity-file", payload["path_arg"])
            self.assertIn("symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_helper_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_helper_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            helper_root = project_root / "helpers"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            helper_root.mkdir(parents=True, exist_ok=True)
            helper = helper_root / "helper.py"
            helper.write_text("print('ok')\n")
            helper_link = project_root / "helper_link.py"
            helper_link.symlink_to(helper)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "SUPPORT_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "support_run",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--helper-path",
                    str(helper_link),
                    "--credentials-ok",
                    "--prompt-identity-ok",
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--helper-path", payload["path_arg"])
            self.assertIn("symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_coverage_profile_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_coverage_profile_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            coverage_profile = project_root / "coverage_profile.json"
            coverage_profile.write_text("{}\n")
            coverage_profile_link = project_root / "coverage_profile_link.json"
            coverage_profile_link.symlink_to(coverage_profile)

            result = self.run_alpha(
                "doctor",
                "--doctor-run-id",
                "R1",
                "--doctor-level",
                "CORE_DOCTOR",
                "--target-path",
                str(project_root),
                "--target-classification",
                "local",
                "--baseline-identity",
                "baseline",
                "--intended-run-class",
                "core_probe",
                "--output",
                str(artifact_root / "doctor.json"),
                "--coverage-profile-file",
                str(coverage_profile_link),
                cwd=project_root,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--coverage-profile-file", payload["path_arg"])
            self.assertIn("symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_coverage_corpus_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_coverage_corpus_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            coverage_corpus = project_root / "coverage_corpus.json"
            coverage_corpus.write_text("[]\n")
            coverage_corpus_link = project_root / "coverage_corpus_link.json"
            coverage_corpus_link.symlink_to(coverage_corpus)

            result = self.run_alpha(
                "doctor",
                "--doctor-run-id",
                "R1",
                "--doctor-level",
                "CORE_DOCTOR",
                "--target-path",
                str(project_root),
                "--target-classification",
                "local",
                "--baseline-identity",
                "baseline",
                "--intended-run-class",
                "core_probe",
                "--output",
                str(artifact_root / "doctor.json"),
                "--coverage-corpus-file",
                str(coverage_corpus_link),
                cwd=project_root,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--coverage-corpus-file", payload["path_arg"])
            self.assertIn("symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_output_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_output_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            real_artifact_root = Path(tmpdir) / "real_artifacts"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_artifact_root.mkdir(parents=True, exist_ok=True)
            output_link = artifact_root / "doctor_link.json"
            output_link.symlink_to(real_artifact_root / "doctor.json")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(output_link),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_state_update_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_state_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            real_artifact_root = Path(tmpdir) / "real_artifacts"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_artifact_root.mkdir(parents=True, exist_ok=True)
            state_link = artifact_root / "state_link.json"
            real_state = real_artifact_root / "state.json"
            real_state.write_text("{}\n")
            state_link.symlink_to(real_state)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--update-state",
                    "--state-file",
                    str(state_link),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--state-file", payload["path_arg"])
            self.assertIn("symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_output_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_output_parent_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            real_artifact_root = project_root / ".synrail_real"
            linked_artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            real_artifact_root.mkdir(parents=True, exist_ok=True)
            linked_artifact_root.symlink_to(real_artifact_root, target_is_directory=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(linked_artifact_root / "doctor.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("parent is a symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_state_update_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_state_parent_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            real_state_root = artifact_root / "real_state"
            linked_state_root = artifact_root / "state_link"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_state_root.mkdir(parents=True, exist_ok=True)
            linked_state_root.symlink_to(real_state_root, target_is_directory=True)
            (real_state_root / "state.json").write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--update-state",
                    "--state-file",
                    str(linked_state_root / "state.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--state-file", payload["path_arg"])
            self.assertIn("parent is a symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_output_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_output_ancestor_symlink_") as tmpdir:
            real_project_root = Path(tmpdir) / "real_project"
            link_root = Path(tmpdir) / "linked_root"
            project_root = link_root / "project"
            artifact_root = project_root / ".synrail"
            real_project_root.mkdir(parents=True, exist_ok=True)
            link_root.symlink_to(real_project_root, target_is_directory=True)
            artifact_root.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("ancestor is a symlink", payload["detail"])

    def test_direct_doctor_rejects_symlinked_state_update_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_doctor_state_ancestor_symlink_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            real_state_ancestor = artifact_root / "real_state_ancestor"
            linked_state_ancestor = artifact_root / "state_ancestor_link"
            real_state_root = real_state_ancestor / "nested"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_state_root.mkdir(parents=True, exist_ok=True)
            linked_state_ancestor.symlink_to(real_state_ancestor, target_is_directory=True)
            (real_state_root / "state.json").write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--update-state",
                    "--state-file",
                    str(linked_state_ancestor / "nested" / "state.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--state-file", payload["path_arg"])
            self.assertIn("ancestor is a symlink", payload["detail"])

    def test_alpha_doctor_rejects_coverage_profile_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_alpha_doctor_coverage_profile_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            outside = Path(tmpdir) / "outside" / "profile.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")

            result = self.run_alpha(
                "doctor",
                "--doctor-run-id",
                "R1",
                "--doctor-level",
                "CORE_DOCTOR",
                "--target-path",
                str(project_root),
                "--target-classification",
                "local",
                "--baseline-identity",
                "baseline",
                "--intended-run-class",
                "core_probe",
                "--output",
                str(artifact_root / "doctor.json"),
                "--coverage-profile-file",
                str(outside),
                cwd=project_root,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--coverage-profile-file", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])

    def test_alpha_doctor_rejects_coverage_corpus_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_alpha_doctor_coverage_corpus_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            outside = Path(tmpdir) / "outside" / "corpus.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("[]\n")

            result = self.run_alpha(
                "doctor",
                "--doctor-run-id",
                "R1",
                "--doctor-level",
                "CORE_DOCTOR",
                "--target-path",
                str(project_root),
                "--target-classification",
                "local",
                "--baseline-identity",
                "baseline",
                "--intended-run-class",
                "core_probe",
                "--output",
                str(artifact_root / "doctor.json"),
                "--coverage-corpus-file",
                str(outside),
                cwd=project_root,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--coverage-corpus-file", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])

    def test_direct_spine_rejects_coverage_profile_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_spine_coverage_profile_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            outside = Path(tmpdir) / "outside" / "profile.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "synrail_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "READY",
                    "target_surface": {"identity": "surface"},
                    "doctor": {"status": "PASS", "override_gates": [], "blocking_failure_classes": []},
                    "proof_bundle": {"status": "PENDING", "artifact_integrity_warning": False},
                    "closure": {"status": "CLAIMED_NOT_ACCEPTED", "blocking_reason": "", "warnings": []},
                    "next_safe_step": "run execution",
                },
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_spine_v0.py"),
                    "orchestrate",
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--doctor-output",
                    str(artifact_root / "doctor.json"),
                    "--final-result",
                    str(artifact_root / "final_result.json"),
                    "--task-class",
                    "bounded_change",
                    "--bundle-output",
                    str(artifact_root / "bundle.json"),
                    "--closure-output",
                    str(artifact_root / "closure.json"),
                    "--report-output",
                    str(artifact_root / "report.json"),
                    "--execution-surface-identity",
                    "surface",
                    "--prompt-identity",
                    "prompt",
                    "--task-identity",
                    "task",
                    "--coverage-profile-file",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--coverage-profile-file", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])

    def test_direct_spine_rejects_final_result_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_spine_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "synrail_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "READY",
                    "target_surface": {"identity": "surface"},
                    "doctor": {"status": "PASS", "override_gates": [], "blocking_failure_classes": []},
                    "proof_bundle": {"status": "PENDING", "artifact_integrity_warning": False},
                    "closure": {"status": "CLAIMED_NOT_ACCEPTED", "blocking_reason": "", "warnings": []},
                    "next_safe_step": "run execution",
                },
            )
            outside = Path(tmpdir) / "outside.json"
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_spine_v0.py"),
                    "orchestrate",
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--doctor-output",
                    str(artifact_root / "doctor.json"),
                    "--final-result",
                    str(outside),
                    "--task-class",
                    "bounded_change",
                    "--bundle-output",
                    str(artifact_root / "bundle.json"),
                    "--closure-output",
                    str(artifact_root / "closure.json"),
                    "--report-output",
                    str(artifact_root / "report.json"),
                    "--execution-surface-identity",
                    "surface",
                    "--prompt-identity",
                    "prompt",
                    "--task-identity",
                    "task",
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--final-result", payload["path_arg"])
            self.assertIn("escapes project and artifact roots", payload["detail"])

    def test_direct_spine_init_rejects_output_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_spine_init_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            outside = Path(tmpdir) / "outside" / "state.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_spine_v0.py"),
                    "init",
                    "--run-id",
                    "R1",
                    "--task-class",
                    "bounded_change",
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])


    def test_alpha_check_rejects_coverage_corpus_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_alpha_check_coverage_corpus_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            outside = Path(tmpdir) / "outside" / "corpus.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("[]\n")
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "run_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "READY",
                    "target_surface": {"status": "ATTESTED", "identity": "surface", "baseline_relation": "baseline"},
                    "doctor": {"status": "PASS", "blocking_failure_classes": [], "override_gates": []},
                    "integrity": {"status": "PASS", "exact_task_identity_ok": True, "bootstrap_provenance_ok": True, "bootstrap_provenance_reason": "CONTROLLED_BOOTSTRAP_CONFIRMED"},
                    "execution": {"status": "NOT_RUN", "artifact_bundle_present": False},
                    "proof_bundle": {"status": "MISSING", "artifact_integrity_warning": False},
                    "closure": {"status": "CLAIMED_NOT_ACCEPTED", "blocking_reason": "", "warnings": []},
                    "recovery": {"status": "NOT_REQUIRED", "reverification_complete": False},
                    "next_safe_step": "run execution"
                },
            )
            write_json(artifact_root / "final_result.json", {
                "request_id": "R1",
                "task_class": "bounded_change",
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "ok",
                "modified_files": [],
                "git_diff": "",
                "diff_provenance": {}
            })

            result = self.run_alpha(
                "check",
                "--artifact-root",
                str(artifact_root),
                "--target-path",
                str(project_root),
                "--baseline-identity",
                "baseline",
                "--execution-surface-identity",
                "surface",
                "--final-result",
                str(artifact_root / "final_result.json"),
                "--coverage-corpus-file",
                str(outside),
                cwd=project_root,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--coverage-corpus-file", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])

    def test_direct_bundle_rejects_scenario_proof_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_bundle_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "final_result.json",
                {
                    "request_id": "R1",
                    "task_class": "bounded_change",
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "ok",
                    "modified_files": [],
                    "git_diff": "",
                    "diff_provenance": {},
                },
            )
            outside = Path(tmpdir) / "outside.txt"
            outside.write_text("outside\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_bundle_v0.py"),
                    "--final-result",
                    str(artifact_root / "final_result.json"),
                    "--task-class",
                    "bounded_change",
                    "--scenario-proof",
                    str(outside),
                    "--output",
                    str(artifact_root / "bundle.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--scenario-proof", payload["path_arg"])
            self.assertIn("escapes project and artifact roots", payload["detail"])

    def test_direct_bundle_rejects_output_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_bundle_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True, exist_ok=True)
            write_json(
                project_root / "final_result.json",
                {
                    "request_id": "R1",
                    "task_class": "bounded_change",
                    "status": "PROVEN",
                    "change_disposition": "modified",
                    "summary": "ok",
                    "modified_files": [],
                    "git_diff": "",
                    "diff_provenance": {},
                },
            )
            outside = Path(tmpdir) / "outside" / "bundle.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_bundle_v0.py"),
                    "--final-result",
                    str(project_root / "final_result.json"),
                    "--task-class",
                    "bounded_change",
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])

    def test_direct_repair_packet_rejects_scenario_proof_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_repair_packet_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "run_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "DOCTOR_BLOCKED",
                    "target_surface": {"identity": "surface", "baseline_relation": "baseline"},
                    "doctor": {"status": "FAIL", "blocking_failure_classes": [], "override_gates": []},
                    "proof_bundle": {"status": "MISSING", "artifact_integrity_warning": False},
                    "closure": {"status": "CLAIMED_NOT_ACCEPTED", "blocking_reason": "DOCTOR_NOT_GREEN", "warnings": []},
                    "next_safe_step": "repair",
                },
            )
            write_json(artifact_root / "repair_handoff.json", {"required_inputs": []})
            outside = Path(tmpdir) / "outside.txt"
            outside.write_text("outside\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_repair_packet_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--artifact-root",
                    str(artifact_root),
                    "--output",
                    str(artifact_root / "repair_packet.json"),
                    "--repair-handoff-file",
                    str(artifact_root / "repair_handoff.json"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--execution-surface-identity",
                    "surface",
                    "--scenario-proof",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--scenario-proof", payload["path_arg"])
            self.assertIn("escapes project and artifact roots", payload["detail"])

    def test_direct_repair_packet_rejects_output_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_repair_packet_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "run_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "DOCTOR_BLOCKED",
                    "target_surface": {"identity": "surface", "baseline_relation": "baseline"},
                    "doctor": {"status": "FAIL", "blocking_failure_classes": [], "override_gates": []},
                    "proof_bundle": {"status": "MISSING", "artifact_integrity_warning": False},
                    "closure": {"status": "CLAIMED_NOT_ACCEPTED", "blocking_reason": "DOCTOR_NOT_GREEN", "warnings": []},
                    "next_safe_step": "repair",
                },
            )
            write_json(artifact_root / "repair_handoff.json", {"required_inputs": []})
            outside = Path(tmpdir) / "outside" / "repair_packet.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_repair_packet_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--artifact-root",
                    str(artifact_root),
                    "--output",
                    str(outside),
                    "--repair-handoff-file",
                    str(artifact_root / "repair_handoff.json"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--execution-surface-identity",
                    "surface",
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_repair_packet_rejects_coverage_corpus_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_repair_packet_coverage_direct_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "run_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "DOCTOR_BLOCKED",
                    "target_surface": {"identity": "surface", "baseline_relation": "baseline"},
                    "doctor": {"status": "FAIL", "blocking_failure_classes": [], "override_gates": []},
                    "proof_bundle": {"status": "MISSING", "artifact_integrity_warning": False},
                    "closure": {"status": "CLAIMED_NOT_ACCEPTED", "blocking_reason": "DOCTOR_NOT_GREEN", "warnings": []},
                    "next_safe_step": "repair",
                },
            )
            write_json(artifact_root / "repair_handoff.json", {"required_inputs": []})
            outside = Path(tmpdir) / "outside_corpus.json"
            write_json(outside, {"cases": []})

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_repair_packet_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--artifact-root",
                    str(artifact_root),
                    "--output",
                    str(artifact_root / "repair_packet.json"),
                    "--repair-handoff-file",
                    str(artifact_root / "repair_handoff.json"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--execution-surface-identity",
                    "surface",
                    "--coverage-corpus-file",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--coverage-corpus-file", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])

    def test_alpha_repair_packet_rejects_coverage_profile_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_repair_packet_coverage_alpha_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "run_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "DOCTOR_BLOCKED",
                    "target_surface": {"identity": "surface", "baseline_relation": "baseline"},
                    "doctor": {"status": "FAIL", "blocking_failure_classes": [], "override_gates": []},
                    "proof_bundle": {"status": "MISSING", "artifact_integrity_warning": False},
                    "closure": {"status": "CLAIMED_NOT_ACCEPTED", "blocking_reason": "DOCTOR_NOT_GREEN", "warnings": []},
                    "next_safe_step": "repair",
                },
            )
            write_json(artifact_root / "repair_handoff.json", {"required_inputs": []})
            outside = Path(tmpdir) / "outside_profile.json"
            write_json(outside, {"profile": []})

            result = self.run_alpha(
                "repair-packet",
                "--state-file",
                str(artifact_root / "state.json"),
                "--artifact-root",
                str(artifact_root),
                "--output",
                str(artifact_root / "repair_packet.json"),
                "--repair-handoff-file",
                str(artifact_root / "repair_handoff.json"),
                "--doctor-run-id",
                "R1",
                "--doctor-level",
                "CORE_DOCTOR",
                "--target-path",
                str(project_root),
                "--target-classification",
                "local",
                "--baseline-identity",
                "baseline",
                "--intended-run-class",
                "core_probe",
                "--execution-surface-identity",
                "surface",
                "--coverage-profile-file",
                str(outside),
                cwd=project_root,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--coverage-profile-file", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])

    def test_direct_second_operator_rejects_run_file_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_second_operator_run_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "run_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "REPAIR_READY",
                },
            )
            write_json(artifact_root / "repair_packet.json", {"continuation_core": {}, "continuation_arbiter": {"resolution_status": "RESOLVED", "precedence_order": [], "conflict_count": 0, "ignored_sources": [], "resolved_decision": {"next_safe_step": "resume", "operator_focus": "focus", "packet_replay_ready": True}}})
            outside = Path(tmpdir) / "outside.json"
            write_json(outside, {"report": {"result": "OK", "reason": "NONE", "next_safe_step": "resume"}, "repair_packet": {}})

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_second_operator_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--run-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "second_operator.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--run-file", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_second_operator_rejects_output_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_second_operator_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "state.json",
                {
                    "schema_version": "run_state_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "state": "REPAIR_READY",
                },
            )
            write_json(artifact_root / "repair_packet.json", {"continuation_core": {}, "continuation_arbiter": {"resolution_status": "RESOLVED", "precedence_order": [], "conflict_count": 0, "ignored_sources": [], "resolved_decision": {"next_safe_step": "resume", "operator_focus": "focus", "packet_replay_ready": True}}})
            write_json(artifact_root / "run.json", {"report": {"result": "OK", "reason": "NONE", "next_safe_step": "resume"}, "repair_packet": {}})
            outside = Path(tmpdir) / "outside" / "second_operator.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_second_operator_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--run-file",
                    str(artifact_root / "run.json"),
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_operator_brief_rejects_doctor_file_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_operator_brief_doctor_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(artifact_root / "state.json", {"run_id": "R1", "task_class": "bounded_change", "state": "REPAIR_READY"})
            write_json(artifact_root / "report.json", {"result": "OK", "reason": "NONE", "next_safe_step": "resume"})
            write_json(artifact_root / "repair_packet.json", {"continuation_core": {}})
            outside = Path(tmpdir) / "outside_doctor.json"
            write_json(outside, {"final_verdict": "PASS"})

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_operator_brief_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(artifact_root / "report.json"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--doctor-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "operator_brief.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--doctor-file", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_operator_brief_rejects_output_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_operator_brief_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(artifact_root / "state.json", {"run_id": "R1", "task_class": "bounded_change", "state": "REPAIR_READY"})
            write_json(artifact_root / "report.json", {"result": "OK", "reason": "NONE", "next_safe_step": "resume"})
            write_json(artifact_root / "repair_packet.json", {"continuation_core": {}})
            outside = Path(tmpdir) / "outside" / "operator_brief.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_operator_brief_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(artifact_root / "report.json"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_observability_rejects_refresh_file_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_observability_refresh_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(artifact_root / "state.json", {"run_id": "R1", "task_class": "bounded_change", "state": "REPAIR_READY"})
            write_json(artifact_root / "report.json", {"result": "OK", "stopping_stage": "accepted", "reason": "NONE", "next_safe_step": "NONE"})
            outside = Path(tmpdir) / "outside_refresh.json"
            write_json(outside, {"dominant_invalidation": "X"})

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_observability_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(artifact_root / "report.json"),
                    "--refresh-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "observability.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--refresh-file", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_observability_rejects_output_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_observability_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(artifact_root / "state.json", {"run_id": "R1", "task_class": "bounded_change", "state": "REPAIR_READY"})
            write_json(artifact_root / "report.json", {"result": "OK", "stopping_stage": "accepted", "reason": "NONE", "next_safe_step": "NONE"})
            outside = Path(tmpdir) / "outside" / "observability.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_observability_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(artifact_root / "report.json"),
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_mode_receipt_rejects_recommendation_file_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_mode_receipt_recommendation_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            outside = Path(tmpdir) / "outside" / "recommendation.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            write_json(
                outside,
                {
                    "schema_version": "mode_recommendation_v0",
                    "recommended_mode": "FULL_GOVERNED_PATH",
                    "scenario_class": "bounded_change",
                    "task_class": "bounded_change",
                    "secondary_exception_mode": "HYBRID_EXCEPTION",
                    "evidence_summary": {
                        "avg_operator_minutes_added_if_synrail": 1,
                        "avg_interventions_added_if_synrail": 1,
                        "avg_closure_latency_minutes_added_if_synrail": 1,
                    },
                    "why": "use the governed path",
                    "next_safe_step": "emit the receipt",
                },
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_mode_receipt_v0.py"),
                    "--recommendation-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "mode_receipt.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--recommendation-file", payload["path_arg"])
            self.assertIn("escapes project root", payload["detail"])

    def test_direct_mode_receipt_rejects_output_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_mode_receipt_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "recommendation.json",
                {
                    "schema_version": "mode_recommendation_v0",
                    "recommended_mode": "FULL_GOVERNED_PATH",
                    "scenario_class": "bounded_change",
                    "task_class": "bounded_change",
                    "secondary_exception_mode": "HYBRID_EXCEPTION",
                    "evidence_summary": {
                        "avg_operator_minutes_added_if_synrail": 1,
                        "avg_interventions_added_if_synrail": 1,
                        "avg_closure_latency_minutes_added_if_synrail": 1,
                    },
                    "why": "use the governed path",
                    "next_safe_step": "emit the receipt",
                },
            )
            outside = Path(tmpdir) / "outside" / "mode_receipt.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_mode_receipt_v0.py"),
                    "--recommendation-file",
                    str(artifact_root / "recommendation.json"),
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_preparation_receipt_rejects_bundle_file_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_preparation_receipt_bundle_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            outside = Path(tmpdir) / "outside" / "bundle.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "plan.json",
                {
                    "schema_version": "proof_bundle_plan_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "required_sections": ["final_result"],
                },
            )
            write_json(
                outside,
                {
                    "schema_version": "proof_bundle_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "status": "COMPLETE",
                    "missing_sections": [],
                },
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_preparation_receipt_v0.py"),
                    "--plan-file",
                    str(artifact_root / "plan.json"),
                    "--bundle-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "preparation_receipt.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--bundle-file", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])

    def test_direct_preparation_receipt_rejects_output_escape_with_bounded_payload(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_path_scope_preparation_receipt_output_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            write_json(
                artifact_root / "plan.json",
                {
                    "schema_version": "proof_bundle_plan_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "required_sections": ["final_result"],
                },
            )
            write_json(
                artifact_root / "bundle.json",
                {
                    "schema_version": "proof_bundle_v0",
                    "run_id": "R1",
                    "task_class": "bounded_change",
                    "status": "COMPLETE",
                    "missing_sections": [],
                },
            )
            outside = Path(tmpdir) / "outside" / "preparation_receipt.json"

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_preparation_receipt_v0.py"),
                    "--plan-file",
                    str(artifact_root / "plan.json"),
                    "--bundle-file",
                    str(artifact_root / "bundle.json"),
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(2, result.returncode, result.stdout + result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--output", payload["path_arg"])
            self.assertIn("escapes artifact root", payload["detail"])


if __name__ == "__main__":
    unittest.main()
