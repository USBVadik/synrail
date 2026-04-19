#!/usr/bin/env python3
"""Tests for alpha evidence ownership classification."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_alpha_evidence_ownership_v0 import (  # noqa: E402
    build_record,
    classify_roadmap_signal,
    extract_markdown_field,
)


class TestAlphaEvidenceOwnership(unittest.TestCase):
    def _report(self, run_id: str) -> str:
        return (REPO_ROOT / "fixtures" / f"alpha_external_run_{run_id}" / "REPORT.md").read_text(encoding="utf-8")

    def test_extracts_nested_failure_owner_and_inline_verdict(self) -> None:
        text = self._report("021b")
        self.assertEqual("harness", extract_markdown_field(text, "Failure owner"))
        self.assertIn("Invalid as a product signal", extract_markdown_field(text, "Verdict"))

    def test_harness_owned_report_is_excluded_from_kernel_roadmap(self) -> None:
        record = build_record(report_text=self._report("021b"), report_path="021b")
        self.assertEqual("HARNESS_ONLY_SIGNAL", record["roadmap_signal_class"])
        self.assertEqual("harness", record["roadmap_track"])
        self.assertFalse(record["kernel_roadmap_eligible"])
        self.assertEqual("INVALID", record["verdict_strength"])

    def test_strong_mixed_report_is_kernel_eligible_with_caution(self) -> None:
        record = build_record(report_text=self._report("031"), report_path="031")
        self.assertEqual("STRONG_MIXED_SIGNAL", record["roadmap_signal_class"])
        self.assertEqual("kernel_with_caution", record["roadmap_track"])
        self.assertTrue(record["kernel_roadmap_eligible"])
        self.assertEqual("STRONG", record["verdict_strength"])

    def test_clean_product_signal_is_kernel_eligible(self) -> None:
        record = classify_roadmap_signal(
            failure_owner="none",
            verdict="strong positive evidence. Accepted closure stayed honest and cheap enough to matter.",
        )
        self.assertEqual("CLEAN_PRODUCT_SIGNAL", record["roadmap_signal_class"])
        self.assertEqual("kernel", record["roadmap_track"])
        self.assertTrue(record["kernel_roadmap_eligible"])

    def test_mixed_report_without_strong_verdict_stays_manual_review(self) -> None:
        record = build_record(report_text=self._report("019c"), report_path="019c")
        self.assertEqual("MIXED_SIGNAL_TOO_WEAK", record["roadmap_signal_class"])
        self.assertEqual("manual_review", record["roadmap_track"])
        self.assertFalse(record["kernel_roadmap_eligible"])


if __name__ == "__main__":
    unittest.main()
