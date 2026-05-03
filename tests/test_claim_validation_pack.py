#!/usr/bin/env python3
"""Validation pack for current critic-facing Synrail claims."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_alpha_evidence_ownership_v0 import build_record, summarize_roadmap_evidence  # noqa: E402
from synrail_io_v0 import load_json  # noqa: E402


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
        self.assertIn("FEEDBACK_INTAKE_001.md", send)
        self.assertIn("ALPHA_SIGNAL_SCORECARD_001.md", send)
        self.assertIn("exact repository snapshot selected for review", checklist)
        self.assertIn("drifting local working tree", checklist)
        self.assertIn("docs/review/FEEDBACK_INTAKE_001.md", checklist)
        self.assertIn("docs/review/ALPHA_SIGNAL_SCORECARD_001.md", checklist)
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

    def test_alpha_test_pack_docs_surface_runtime_helper_as_optional_ui_verification_path(self) -> None:
        alpha_pack = load_text(REPO_ROOT / "docs" / "core" / "ALPHA_TEST_PACK_001.md")

        self.assertIn("if you need a small UI/runtime verification path for a rendered or route-facing change", alpha_pack)
        self.assertIn("# synrail runtime-helper", alpha_pack)
        self.assertIn("# optional standalone bounded prompt after a non-green check:", alpha_pack)

    def test_technical_map_lists_runtime_helper_in_current_tester_pack_contour(self) -> None:
        technical_map = load_text(REPO_ROOT / "docs" / "review" / "TECHNICAL_MAP_001.md")

        self.assertIn("Covers the current outside-facing first-run contour plus bounded helper and review surfaces:", technical_map)
        self.assertIn("- `runtime-helper`", technical_map)
        self.assertIn("- `repair-step`", technical_map)

    def test_one_pager_surfaces_runtime_helper_in_current_alpha_lane(self) -> None:
        one_pager = load_text(REPO_ROOT / "docs" / "review" / "ONE_PAGER_001.md")

        self.assertIn("if you need a small UI/runtime verification path for a rendered or route-facing change: `synrail runtime-helper`", one_pager)
        self.assertIn("if a standalone bounded repair prompt helps: `synrail repair-step`", one_pager)

    def test_product_memo_surfaces_runtime_helper_in_current_alpha_lane(self) -> None:
        product_memo = load_text(REPO_ROOT / "docs" / "review" / "PRODUCT_MEMO_001.md")

        self.assertIn("if the change affects rendered UI, a page template, or a server-side route handler, run `synrail runtime-helper`", product_memo)
        self.assertIn("rerun `synrail check`; resolve non-green runtime-helper outcomes locally", product_memo)

    def test_external_full_review_surfaces_runtime_helper_in_current_user_contour(self) -> None:
        full_review = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_FULL_REVIEW_2026-04-21.md")

        self.assertIn("if you need a small UI/runtime verification path for a rendered or route-facing change: `synrail runtime-helper`", full_review)
        self.assertIn("use `synrail repair-step` only if a standalone bounded repair prompt is actually useful", full_review)

    def test_external_critique_pack_surfaces_runtime_helper_as_optional_review_surface(self) -> None:
        critique_pack = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_CRITIQUE_PACK_001.md")

        self.assertIn("if you need a small UI/runtime verification path for a rendered or route-facing change, use `synrail runtime-helper`", critique_pack)
        self.assertIn("optional helper surface, not a default mandatory hop", critique_pack)

    def test_external_alpha_send_surfaces_runtime_helper_as_optional_reviewer_guidance(self) -> None:
        external_send = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_ALPHA_SEND_001.md")

        self.assertIn("if they need a small UI/runtime verification path for a rendered or route-facing change, point them to `synrail runtime-helper`", external_send)
        self.assertIn("optional reviewer guidance rather than a default mandatory step", external_send)

    def test_critic_review_brief_surfaces_runtime_helper_in_current_product_contour(self) -> None:
        critic_brief = load_text(REPO_ROOT / "docs" / "review" / "CRITIC_REVIEW_BRIEF_2026-04-19.md")

        self.assertIn("if you need a small UI/runtime verification path for a rendered or route-facing change, run `synrail runtime-helper`", critic_brief)
        self.assertIn("`synrail runtime-helper` is a guidance-only helper", critic_brief)
        self.assertIn("use `synrail repair-step` only when a standalone bounded repair prompt is actually helpful", critic_brief)

    def test_external_critique_pack_preserves_current_economics_truth_boundary(self) -> None:
        critique_pack = load_text(REPO_ROOT / "docs" / "review" / "EXTERNAL_CRITIQUE_PACK_001.md")

        self.assertIn("`BASELINE_GOOD_ENOUGH`", critique_pack)
        self.assertIn("`FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT`", critique_pack)
        self.assertIn("behavior cheapness is not fully independent", critique_pack)

    def test_alpha_signal_scorecard_spells_out_post_review_decision_rule(self) -> None:
        scorecard = load_text(REPO_ROOT / "docs" / "review" / "ALPHA_SIGNAL_SCORECARD_001.md")

        self.assertIn("## First Fresh Outside Pass Decision", scorecard)
        self.assertIn("broaden packaging only if the review returns `strong wedge signal`", scorecard)
        self.assertIn("if the review is `mixed signal`, do not broaden packaging yet", scorecard)
        self.assertIn("One fresh outside pass should change the roadmap decision", scorecard)


if __name__ == "__main__":
    unittest.main()
