#!/usr/bin/env python3
"""Validation pack for current critic-facing Synrail claims."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_alpha_evidence_ownership_v0 import build_record, summarize_roadmap_evidence  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


class ClaimValidationPackTests(unittest.TestCase):
    def test_alpha_pack_second_operator_contour_is_followable_without_author_intuition(self) -> None:
        lane = REPO_ROOT / "fixtures" / "alpha_test_pack_run_004" / "lane"
        second_operator = load_json(lane / "second_operator.json")
        operator_reading = load_json(lane / "operator_reading.json")
        thin_output = load_json(lane / "thin_output.json")

        self.assertEqual("FOLLOWABLE_BY_SECOND_OPERATOR", second_operator["verdict"])
        self.assertTrue(second_operator["packet_replay_ready"])
        self.assertFalse(second_operator["requires_author_intuition"])
        self.assertTrue(second_operator["has_explicit_next_step"])
        self.assertTrue(second_operator["has_explicit_operator_focus"])
        self.assertTrue(second_operator["has_explicit_required_inputs"])
        self.assertEqual("repair_final_result_artifact", second_operator["current_step_id"])
        self.assertEqual("final_result_payload", second_operator["current_step_subsurface_id"])
        self.assertEqual(".synrail/final_result.json", second_operator["current_step_target_path"])
        self.assertEqual(
            "repair the final result artifact and rebuild the proof bundle",
            second_operator["expected_next_safe_step"],
        )

        self.assertEqual("FOLLOWABLE_WITH_RENDER", operator_reading["verdict"])
        self.assertTrue(operator_reading["packet_only_entry"])
        self.assertFalse(operator_reading["requires_author_intuition"])
        self.assertEqual([], operator_reading["missing_markers"])
        self.assertEqual(
            second_operator["expected_next_safe_step"],
            operator_reading["next_safe_step"],
        )
        self.assertEqual("PROOF_INVALID", thin_output["outcome_class"])
        self.assertIn(".synrail/final_result.json", thin_output["focused_repair_summary"])

    def test_real_reports_respect_evidence_ownership_split(self) -> None:
        report_021b = (REPO_ROOT / "fixtures" / "alpha_external_run_021b" / "REPORT.md").read_text(encoding="utf-8")
        report_019c = (REPO_ROOT / "fixtures" / "alpha_external_run_019c" / "REPORT.md").read_text(encoding="utf-8")
        report_031 = (REPO_ROOT / "fixtures" / "alpha_external_run_031" / "REPORT.md").read_text(encoding="utf-8")

        harness = build_record(report_text=report_021b, report_path="021b")
        weak_mixed = build_record(report_text=report_019c, report_path="019c")
        strong_mixed = build_record(report_text=report_031, report_path="031")

        self.assertEqual("HARNESS_ONLY_SIGNAL", harness["roadmap_signal_class"])
        self.assertFalse(harness["kernel_roadmap_eligible"])

        self.assertEqual("MIXED_SIGNAL_TOO_WEAK", weak_mixed["roadmap_signal_class"])
        self.assertFalse(weak_mixed["kernel_roadmap_eligible"])

        self.assertEqual("STRONG_MIXED_SIGNAL", strong_mixed["roadmap_signal_class"])
        self.assertTrue(strong_mixed["kernel_roadmap_eligible"])

    def test_real_reports_pass_through_roadmap_decision_gate(self) -> None:
        report_021b = (REPO_ROOT / "fixtures" / "alpha_external_run_021b" / "REPORT.md").read_text(encoding="utf-8")
        report_019c = (REPO_ROOT / "fixtures" / "alpha_external_run_019c" / "REPORT.md").read_text(encoding="utf-8")
        report_031 = (REPO_ROOT / "fixtures" / "alpha_external_run_031" / "REPORT.md").read_text(encoding="utf-8")

        harness = build_record(report_text=report_021b, report_path="021b")
        weak_mixed = build_record(report_text=report_019c, report_path="019c")
        strong_mixed = build_record(report_text=report_031, report_path="031")

        blocked = summarize_roadmap_evidence([harness, weak_mixed])
        cautious = summarize_roadmap_evidence([harness, strong_mixed])

        self.assertFalse(blocked["kernel_roadmap_allowed"])
        self.assertEqual("MANUAL_REVIEW_REQUIRED", blocked["decision"])
        self.assertEqual("manual_review", blocked["recommended_track"])

        self.assertTrue(cautious["kernel_roadmap_allowed"])
        self.assertEqual("ALLOW_KERNEL_MOVE_WITH_CAUTION", cautious["decision"])
        self.assertEqual("kernel_with_caution", cautious["recommended_track"])

    def test_uglier_second_operator_compound_doctor_block_remains_followable(self) -> None:
        lane = REPO_ROOT / "fixtures" / "second_operator_test_002"
        second_operator = load_json(lane / "second_operator.json")
        repair_packet = load_json(lane / "starting_repair_packet.json")
        run_record = load_json(lane / "starting_run.json")

        self.assertEqual("FOLLOWABLE_BY_SECOND_OPERATOR", second_operator["verdict"])
        self.assertTrue(second_operator["packet_only_entry"])
        self.assertFalse(second_operator["requires_author_intuition"])
        self.assertEqual("DOCTOR_NOT_GREEN", second_operator["expected_reason"])
        self.assertEqual(
            "restore the trusted baseline and expected target-surface identity",
            second_operator["expected_next_safe_step"],
        )

        self.assertEqual("REPAIRABLE_COMPOUND", repair_packet["resumability"]["family"])
        self.assertEqual("restore_readiness_truth", repair_packet["repair_policy"]["next_step_id"])
        self.assertTrue(repair_packet["repair_handoff"]["continuation_allowed"])
        self.assertEqual("DOCTOR_BLOCKED", repair_packet["repair_handoff"]["from_state"])

        self.assertEqual("MAX_REPAIR_ATTEMPTS", run_record["repair_history"]["termination_reason"])
        self.assertEqual("TERMINATE", run_record["repair_history"]["termination_status"])
        self.assertEqual(
            second_operator["expected_next_safe_step"],
            run_record["resulting_state"]["next_safe_step"],
        )

    def test_non_resumable_second_operator_boundary_is_explicit(self) -> None:
        lane = REPO_ROOT / "fixtures" / "second_operator_test_006"
        second_operator = load_json(lane / "second_operator.json")
        repair_packet = load_json(lane / "repair_packet.json")
        run_record = load_json(lane / "run.json")

        self.assertEqual("FOLLOWABLE_BY_SECOND_OPERATOR", second_operator["verdict"])
        self.assertTrue(second_operator["packet_only_entry"])
        self.assertFalse(second_operator["requires_author_intuition"])
        self.assertEqual("STATE_NOT_RESUMABLE", second_operator["expected_reason"])
        self.assertEqual(
            "continue through the governed forward path instead of named resume",
            second_operator["expected_next_safe_step"],
        )

        self.assertEqual("NOT_RESUMABLE_FRESH_ORCHESTRATION", repair_packet["resumability"]["family"])
        self.assertEqual("NON_RESUMABLE_NEXT_STEP", repair_packet["repair_policy"]["policy_type"])
        self.assertFalse(repair_packet["repair_handoff"]["continuation_allowed"])
        self.assertEqual("continue_forward_orchestration", repair_packet["repair_policy"]["next_step_id"])

        self.assertEqual("NON_RESUMABLE", run_record["repair_history"]["termination_reason"])
        self.assertEqual("TERMINATE", run_record["repair_history"]["termination_status"])
        self.assertEqual(
            second_operator["expected_next_safe_step"],
            run_record["resulting_state"]["next_safe_step"],
        )

    def test_continuation_inputs_missing_contour_remains_followable_without_author_memory(self) -> None:
        lane = REPO_ROOT / "fixtures" / "continuation_autonomy_run_001"
        second_operator = load_json(lane / "second_operator.json")
        report = load_json(lane / "report.json")
        session_export = load_json(lane / "session_export.json")

        self.assertEqual("FOLLOWABLE_BY_SECOND_OPERATOR", second_operator["verdict"])
        self.assertTrue(second_operator["packet_only_entry"])
        self.assertTrue(second_operator["packet_replay_ready"])
        self.assertFalse(second_operator["requires_author_intuition"])
        self.assertEqual("CONTINUATION_INPUTS_MISSING", second_operator["expected_reason"])
        self.assertEqual(
            "move to a clean or explicitly observed-safe execution surface",
            second_operator["expected_next_safe_step"],
        )

        self.assertEqual("BLOCKED", report["result"])
        self.assertEqual("repair_handoff", report["stopping_stage"])
        self.assertEqual("CONTINUATION_INPUTS_MISSING", report["reason"])
        self.assertEqual("DOCTOR_BLOCKED", report["resulting_state"])
        self.assertEqual(
            second_operator["expected_next_safe_step"],
            report["next_safe_step"],
        )

        self.assertEqual(2, session_export["event_counts"]["repair_attempt_count"])
        self.assertEqual("DOCTOR_BLOCKED", session_export["resulting_state"])
        self.assertTrue(session_export["sanitized_session_export"]["packet_replay_ready"])
        self.assertEqual(
            second_operator["expected_next_safe_step"],
            session_export["report_summary"]["next_safe_step"],
        )

    def test_external_send_docs_are_bound_to_one_selected_snapshot(self) -> None:
        send = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_ALPHA_SEND_001.md")
        checklist = load_text(REPO_ROOT / "docs" / "review" / "REVIEW_HANDOFF_CHECKLIST_001.md")
        critique_pack = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_CRITIQUE_PACK_001.md")
        critic_brief = load_text(REPO_ROOT / "docs" / "review" / "CRITIC_REVIEW_BRIEF_2026-04-19.md")
        full_review = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_FULL_REVIEW_2026-04-21.md")

        self.assertIn("exact repository snapshot at the explicitly selected target commit", send)
        self.assertIn("drifting local working tree", send)
        self.assertIn("exact repository snapshot selected for review", checklist)
        self.assertIn("drifting local working tree", checklist)
        self.assertIn("exact selected repository snapshot at the commit you want reviewed", critique_pack)
        self.assertIn("drifting local working tree", critique_pack)
        self.assertIn("Reviewed snapshot: exact selected repository snapshot prepared for critic handoff", critic_brief)
        self.assertIn("drifting local working tree", critic_brief)
        self.assertIn("Reviewed snapshot: exact selected repository snapshot prepared for critic handoff", full_review)
        self.assertIn("drifting local working tree", full_review)

    def test_review_docs_point_to_focused_pressure_artifacts(self) -> None:
        critique_pack = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_CRITIQUE_PACK_001.md")
        full_review = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_FULL_REVIEW_2026-04-21.md")
        final_audit = load_text(REPO_ROOT / "docs" / "review" / "FINAL_AUDIT_2026-04-22.md")

        for text in (critique_pack, full_review, final_audit):
            self.assertIn("small_template_text_fix_behavior_pressure_pack_001.json", text)
            self.assertIn("cost_of_control_small_template_text_fix_behavior_pressure_001.json", text)

    def test_external_critique_pack_preserves_current_economics_truth_boundary(self) -> None:
        critique_pack = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_CRITIQUE_PACK_001.md")

        self.assertIn("`BASELINE_GOOD_ENOUGH`", critique_pack)
        self.assertIn("`FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT`", critique_pack)
        self.assertIn("behavior cheapness is not fully independent", critique_pack)


if __name__ == "__main__":
    unittest.main()
