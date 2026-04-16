#!/usr/bin/env python3
"""Smoke test for the current external alpha tester pack contour."""

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


class AlphaTestPackSmokeTests(unittest.TestCase):
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

    def test_current_external_alpha_pack_non_green_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_alpha_pack_") as tmpdir:
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
                "Reject a plain-text final result and keep the repair bounded.",
                "--telemetry-opt-in",
                "--tester-id",
                "alpha_pack_smoke",
                cwd=project_root,
            )
            self.assertEqual(0, start.returncode, start.stdout + start.stderr)
            self.assertTrue((artifact_root / "state.json").exists())
            self.assertTrue((artifact_root / "acceptance_criteria.json").exists())
            self.assertTrue((artifact_root / "bootstrap.json").exists())
            self.assertTrue((artifact_root / "proof_request.json").exists())
            self.assertTrue((artifact_root / "target_identity.txt").exists())
            self.assertTrue((artifact_root / "final_result.json").exists())
            self.assertTrue((artifact_root / "readback.txt").exists())
            self.assertTrue((artifact_root / "scenario_proof.txt").exists())
            self.assertTrue((artifact_root / "telemetry" / "config.json").exists())
            self.assertIn("Artifact root: .synrail", start.stdout)
            self.assertNotIn(str(project_root), start.stdout)

            (artifact_root / "final_result.txt").write_text(
                "Implemented the change and confirmed it locally.\n"
            )

            check = self.run_alpha("check", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, check.returncode, check.stdout + check.stderr)
            self.assertNotIn(str(project_root), check.stdout)
            self.assertIn(
                "Do this now: Run synrail repair-step, then update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.",
                check.stdout,
            )
            self.assertIn("Repair target: update the result payload in .synrail/final_result.json", check.stdout)

            thin_output = load_json(artifact_root / "thin_output.json")
            self.assertEqual("PROOF_INVALID", thin_output["outcome_class"])
            self.assertEqual(
                "Run synrail repair-step, then update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.",
                thin_output["action_now"],
            )
            self.assertEqual(
                "Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.",
                thin_output["current_step_action_instruction"],
            )
            self.assertEqual(
                "update the result payload in .synrail/final_result.json",
                thin_output["focused_repair_summary"],
            )

            repair_step = self.run_alpha("repair-step", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, repair_step.returncode, repair_step.stdout + repair_step.stderr)
            self.assertIn(".synrail/final_result.json", repair_step.stdout)
            self.assertIn("Repair target: update the result payload in .synrail/final_result.json", repair_step.stdout)
            self.assertIn(
                "Do this now: Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.",
                repair_step.stdout,
            )
            self.assertNotIn(str(project_root), repair_step.stdout)

            prompt = load_json(artifact_root / "prompt.json")
            self.assertEqual("repair_final_result_artifact", prompt["current_step_id"])
            self.assertEqual("final_result_payload", prompt["current_step_subsurface_id"])
            self.assertEqual(".synrail/final_result.json", prompt["current_step_target_path"])
            self.assertEqual(
                "update the result payload in .synrail/final_result.json",
                prompt["current_step_focus_summary"],
            )
            self.assertEqual(
                "Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.",
                prompt["current_step_action_instruction"],
            )
            self.assertIn("final_result_payload", prompt["allowed_scope"])

            telemetry_export = self.run_alpha("telemetry", "export", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, telemetry_export.returncode, telemetry_export.stdout + telemetry_export.stderr)
            self.assertIn("Feedback export ready.", telemetry_export.stdout)
            self.assertIn("issue-ready summary", telemetry_export.stdout)

            bug_packet = self.run_alpha("bug-packet", "--artifact-root", ".synrail", cwd=project_root)
            self.assertEqual(0, bug_packet.returncode, bug_packet.stdout + bug_packet.stderr)

            second_operator = self.run_alpha(
                "second-operator",
                "--state-file",
                str(artifact_root / "state.json"),
                "--repair-packet-file",
                str(artifact_root / "repair_packet.json"),
                "--run-file",
                str(artifact_root / "run.json"),
                "--output",
                str(artifact_root / "second_operator.json"),
                cwd=project_root,
            )
            self.assertEqual(0, second_operator.returncode, second_operator.stdout + second_operator.stderr)

            operator_brief = self.run_alpha(
                "operator-brief",
                "--state-file",
                str(artifact_root / "state.json"),
                "--report-file",
                str(artifact_root / "run.json"),
                "--repair-packet-file",
                str(artifact_root / "repair_packet.json"),
                "--output",
                str(artifact_root / "stage0_operator_brief.json"),
                cwd=project_root,
            )
            self.assertEqual(0, operator_brief.returncode, operator_brief.stdout + operator_brief.stderr)

            operator_render = self.run_alpha(
                "operator-render",
                "--brief-file",
                str(artifact_root / "stage0_operator_brief.json"),
                "--output",
                str(artifact_root / "operator_render.md"),
                cwd=project_root,
            )
            self.assertEqual(0, operator_render.returncode, operator_render.stdout + operator_render.stderr)

            operator_reading = self.run_alpha(
                "operator-reading",
                "--second-operator-file",
                str(artifact_root / "second_operator.json"),
                "--brief-file",
                str(artifact_root / "stage0_operator_brief.json"),
                "--render-file",
                str(artifact_root / "operator_render.md"),
                "--label",
                "alpha_pack_smoke",
                "--output",
                str(artifact_root / "operator_reading.json"),
                cwd=project_root,
            )
            self.assertEqual(0, operator_reading.returncode, operator_reading.stdout + operator_reading.stderr)

            stage1_brief = artifact_root / "stage1_operator_brief.json"
            stage1_brief.write_text((artifact_root / "stage0_operator_brief.json").read_text())
            operator_brief_chain = self.run_alpha(
                "operator-brief-chain",
                "--brief",
                str(artifact_root / "stage0_operator_brief.json"),
                "--brief",
                str(stage1_brief),
                "--output",
                str(artifact_root / "operator_brief_chain.json"),
                cwd=project_root,
            )
            self.assertEqual(0, operator_brief_chain.returncode, operator_brief_chain.stdout + operator_brief_chain.stderr)

            operator_chain_render = self.run_alpha(
                "operator-render",
                "--chain-file",
                str(artifact_root / "operator_brief_chain.json"),
                "--output",
                str(artifact_root / "operator_chain_render.md"),
                cwd=project_root,
            )
            self.assertEqual(0, operator_chain_render.returncode, operator_chain_render.stdout + operator_chain_render.stderr)

            session_replay = load_json(artifact_root / "telemetry" / "session_replay.json")
            issue_body = (artifact_root / "telemetry" / "github_issue.md").read_text()
            bug_packet_record = load_json(artifact_root / "bug_packet.json")
            second_operator_record = load_json(artifact_root / "second_operator.json")
            operator_brief_record = load_json(artifact_root / "stage0_operator_brief.json")
            operator_reading_record = load_json(artifact_root / "operator_reading.json")
            operator_brief_chain_record = load_json(artifact_root / "operator_brief_chain.json")
            operator_render_text = (artifact_root / "operator_render.md").read_text()
            operator_chain_render_text = (artifact_root / "operator_chain_render.md").read_text()

            self.assertEqual("PROOF_INVALID", session_replay["latest_result"])
            self.assertIn("repair the final result artifact", session_replay["next_safe_step"])
            self.assertEqual("final_result_payload", session_replay["continuation_summary"]["current_step_subsurface_id"])
            self.assertEqual(".synrail/final_result.json", session_replay["continuation_summary"]["current_step_target_path"])
            self.assertIn("# Synrail Alpha Telemetry", issue_body)
            self.assertIn("INVALID_PROOF_BUNDLE", issue_body)
            self.assertEqual("final_result_payload", bug_packet_record["continuation_summary"]["current_step_subsurface_id"])
            self.assertEqual(".synrail/final_result.json", bug_packet_record["continuation_summary"]["current_step_target_path"])
            self.assertEqual("final_result_payload", second_operator_record["current_step_subsurface_id"])
            self.assertEqual(".synrail/final_result.json", second_operator_record["current_step_target_path"])
            self.assertTrue(second_operator_record["has_explicit_target_path"])
            self.assertEqual("final_result_payload", operator_brief_record["current_step_subsurface_id"])
            self.assertEqual(".synrail/final_result.json", operator_brief_record["current_step_target_path"])
            self.assertEqual(
                ["--state-file", ".synrail/state.json", "--repair-packet-file", ".synrail/repair_packet.json"],
                operator_brief_record["suggested_cli"]["args"],
            )
            self.assertIn("final_result_payload", operator_render_text)
            self.assertIn(".synrail/final_result.json", operator_render_text)
            self.assertIn("update the result payload in .synrail/final_result.json", operator_render_text)
            self.assertIn(
                "Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.",
                operator_render_text,
            )
            self.assertIn("## Do This Now", operator_render_text)
            self.assertNotIn(str(project_root), operator_render_text)
            self.assertEqual("final_result_payload", operator_reading_record["current_step_subsurface_id"])
            self.assertEqual(".synrail/final_result.json", operator_reading_record["current_step_target_path"])
            self.assertEqual("FOLLOWABLE_WITH_RENDER", operator_reading_record["verdict"])
            self.assertEqual("final_result_payload", operator_brief_chain_record["stage_summaries"][0]["current_step_subsurface_id"])
            self.assertEqual(".synrail/final_result.json", operator_brief_chain_record["stage_summaries"][0]["current_step_target_path"])
            self.assertEqual(
                "Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.",
                operator_brief_chain_record["stage_summaries"][0]["current_step_action_instruction"],
            )
            self.assertIn("final_result_payload", operator_chain_render_text)
            self.assertIn(".synrail/final_result.json", operator_chain_render_text)
            self.assertIn("## Stage sequence", operator_chain_render_text)
            self.assertIn(
                "Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged.",
                operator_chain_render_text,
            )


if __name__ == "__main__":
    unittest.main()
