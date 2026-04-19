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

from synrail_alpha_evidence_ownership_v0 import build_record  # noqa: E402


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


if __name__ == "__main__":
    unittest.main()
