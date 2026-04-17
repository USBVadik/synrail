#!/usr/bin/env python3
"""Smoke tests for controlled start, bootstrap gating, and proof guidance."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ALPHA_ENTRY = REPO_ROOT / "alpha.py"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


class ControlledStartSmokeTests(unittest.TestCase):
    def run_alpha(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ)
        existing = env.get("PYTHONPATH", "")
        repo_path = str(REPO_ROOT)
        env["PYTHONPATH"] = repo_path if not existing else repo_path + os.pathsep + existing
        return subprocess.run(
            [sys.executable, str(ALPHA_ENTRY), *args],
            cwd=cwd or REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )

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

    def test_start_creates_bootstrap_and_proof_request(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_controlled_start_") as tmpdir:
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
                "Keep this run controlled from the first action.",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            self.assertIn("Controlled run started.", start.stdout)
            self.assertIn(
                "Do this now: Edit only the starter proof files below in place. Leave every other surface unchanged.",
                start.stdout,
            )
            self.assertIn("Starter proof files are ready for this run.", start.stdout)
            self.assertTrue((artifact_root / "bootstrap.json").exists())
            self.assertTrue((artifact_root / "bootstrap_validation.json").exists())
            self.assertTrue((artifact_root / "proof_request.json").exists())
            self.assertTrue((artifact_root / "target_identity.txt").exists())
            self.assertTrue((artifact_root / "final_result.json").exists())
            self.assertTrue((artifact_root / "readback.txt").exists())
            self.assertTrue((artifact_root / "scenario_proof.txt").exists())

            bootstrap = load_json(artifact_root / "bootstrap.json")
            validation = load_json(artifact_root / "bootstrap_validation.json")
            proof_request = load_json(artifact_root / "proof_request.json")

            self.assertTrue(bootstrap["controlled_mode"])
            self.assertEqual("VALID", validation["status"])
            self.assertEqual("edit_in_place", proof_request["starter_mode"])
            self.assertEqual(".synrail/final_result.json", proof_request["preferred_artifacts"]["final_result"])
            self.assertEqual(64, len(proof_request["starter_hashes"]["final_result"]))

    def test_check_after_plain_init_requires_controlled_start(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_bootstrap_block_") as tmpdir:
            project_root = Path(tmpdir) / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)

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

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertIn("Controlled Run Required", check.stdout)
            self.assertIn("Next command: synrail start", check.stdout)

            thin_output = load_json(artifact_root / "thin_output.json")
            state = load_json(artifact_root / "state.json")

            self.assertEqual("NON_GREEN", thin_output["outcome_class"])
            self.assertEqual("synrail start", thin_output["next_command"])
            self.assertFalse(state["integrity"]["bootstrap_provenance_ok"])
            self.assertEqual("CONTROLLED_BOOTSTRAP_NOT_CONFIRMED", state["closure"]["blocking_reason"])

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
            self.assertIn("waiting for the proof artifacts", check.stdout)
            self.assertIn("edit the starter proof files already placed", check.stdout)
            self.assertIn("final_result: .synrail/final_result.json", check.stdout)
            self.assertIn("readback: .synrail/readback.txt", check.stdout)
            self.assertIn("scenario_proof: .synrail/scenario_proof.txt", check.stdout)
            self.assertIn("synrail readback-template", check.stdout)
            self.assertIn("synrail final-result-template", check.stdout)
            self.assertIn("synrail scenario-proof-template", check.stdout)

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
            self.assertIn('"git_diff": "diff --git', template.stdout)
            self.assertIn('"diff_provenance": {', template.stdout)
            self.assertIn('"artifact_identity": {', template.stdout)
            self.assertIn("workspace clean after updating only path/to/changed_file.ext", template.stdout)

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
            self.assertIn("Runtime hint:", template.stdout)

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

            template = self.run_alpha("scenario-proof-template", cwd=project_root)
            self.assertEqual(0, template.returncode, template.stdout + template.stderr)
            self.assertIn(state["run_id"], template.stdout)
            self.assertIn("Scenario:", template.stdout)
            self.assertIn("Observed:", template.stdout)
            self.assertIn("Status: PASSED", template.stdout)

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
                            "why": "readback evidence does not yet name the changed surface with an observed readback",
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
            self.assertIn("synrail readback-template", explain.stdout)

    def test_explain_proof_surfaces_scenario_helper(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_explain_proof_scenario_") as tmpdir:
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
            self.assertIn("synrail scenario-proof-template", explain.stdout)

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
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertIn("Remote Target Not Supported Yet", check.stdout)

            report = load_json(artifact_root / "report.json")
            thin_output = load_json(artifact_root / "thin_output.json")

            self.assertEqual("REMOTE_TARGET_UNSUPPORTED", report["reason"])
            self.assertEqual("NON_GREEN", thin_output["outcome_class"])
            self.assertEqual("", thin_output["next_command"])
            self.assertFalse((artifact_root / "prompt.json").exists())

    def test_repair_step_names_readback_starter_surface(self) -> None:
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
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)

            repair_step = self.run_alpha("repair-step", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, repair_step.returncode, repair_step.stdout + repair_step.stderr)
            self.assertIn(".synrail/readback.txt", repair_step.stdout)
            self.assertIn("Repair target: record readback in .synrail/readback.txt", repair_step.stdout)
            self.assertIn(
                "Do this now: Record readback in .synrail/readback.txt. Leave every other proof surface unchanged.",
                repair_step.stdout,
            )

            prompt = load_json(artifact_root / "prompt.json")
            self.assertEqual("complete_missing_proof_sections", prompt["current_step_id"])
            self.assertEqual("readback_record", prompt["current_step_subsurface_id"])
            self.assertEqual(".synrail/readback.txt", prompt["current_step_target_path"])
            self.assertEqual("record readback in .synrail/readback.txt", prompt["current_step_focus_summary"])
            self.assertEqual(
                "Record readback in .synrail/readback.txt. Leave every other proof surface unchanged.",
                prompt["current_step_action_instruction"],
            )
            self.assertIn("readback", prompt["current_step_label"])

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
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
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

    def test_repair_step_synthesizes_missing_packet_for_scenario_gap(self) -> None:
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
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertIn("record scenario proof in .synrail/scenario_proof.txt", check.stdout)

            (artifact_root / "repair_packet.json").unlink(missing_ok=True)
            (artifact_root / "prompt.json").unlink(missing_ok=True)

            repair_step = self.run_alpha("repair-step", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, repair_step.returncode, repair_step.stdout + repair_step.stderr)
            self.assertNotIn("does not have the next bounded repair instruction yet", repair_step.stdout.lower())
            self.assertIn(".synrail/scenario_proof.txt", repair_step.stdout)
            self.assertIn("Repair target: record scenario proof in .synrail/scenario_proof.txt", repair_step.stdout)
            self.assertIn("synrail scenario-proof-template", load_json(artifact_root / "prompt.json")["prompt"])


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

            second_state = load_json(artifact_root / "state.json")
            self.assertEqual(first_run_id, second_state["run_id"])
            self.assertEqual(first_task_identity, (artifact_root / "task_identity.txt").read_text())


if __name__ == "__main__":
    unittest.main()
