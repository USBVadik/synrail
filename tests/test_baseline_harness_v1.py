#!/usr/bin/env python3
"""Focused tests for economics-aware baseline comparison helpers."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_baseline_harness_v1 import compare, economics_summary, required_visible_surface_count  # noqa: E402


def comparison_input(*, system: str, path_id: str, **overrides: int | str) -> dict:
    payload: dict = {
        "schema_version": "comparison_input_v1",
        "system": system,
        "scenario_id": "EVERYDAY_BENCHMARK_001",
        "scenario_class": "repeatable_everyday_local",
        "task_class": "bounded_copy_update",
        "path_id": path_id,
        "closure_result": "ACCEPTED",
        "blocker_to_closure_cycles": 0,
        "false_success_risk": "LOW",
        "proof_completeness": "HIGH" if system == "synrail" else "LOW",
        "recovery_cost": "LOW",
        "coordination_overhead": "LOW" if system == "baseline" else "MEDIUM",
        "operator_minutes": 2 if system == "baseline" else 4,
        "intervention_count": 0 if system == "baseline" else 1,
        "repair_cycles": 0,
        "invalidation_count": 0,
        "closure_latency_minutes": 2 if system == "baseline" else 4,
        "false_green_exposure": 1 if system == "baseline" else 0,
        "artifact_completeness_percent": 35 if system == "baseline" else 90,
        "mandatory_mental_steps": 1 if system == "baseline" else 3,
        "trust_bearing_artifact_count": 1 if system == "baseline" else 2,
        "visible_surface_count": 1 if system == "baseline" else 3,
        "skippable_visible_surface_count": 0 if system == "baseline" else 1,
    }
    payload.update(overrides)
    return payload


class BaselineHarnessV1Tests(unittest.TestCase):
    def test_required_visible_surface_count_subtracts_skippable_surfaces(self) -> None:
        record = comparison_input(system="synrail", path_id="synrail-default")
        self.assertEqual(2, required_visible_surface_count(record))

    def test_economics_summary_tracks_fixed_control_mass_metrics(self) -> None:
        baseline = comparison_input(system="baseline", path_id="baseline")
        synrail = comparison_input(system="synrail", path_id="synrail")

        summary = economics_summary(baseline, synrail)

        self.assertEqual(2, summary["operator_minutes_added"])
        self.assertEqual(2, summary["mandatory_mental_steps_added"])
        self.assertEqual(1, summary["trust_bearing_artifacts_added"])
        self.assertEqual(1, summary["required_visible_surfaces_added"])
        self.assertEqual(1, summary["skippable_visible_surfaces_added"])
        self.assertEqual(4, summary["fixed_control_mass_added"])

    def test_compare_surfaces_fixed_control_mass_reason(self) -> None:
        baseline = comparison_input(system="baseline", path_id="baseline")
        synrail = comparison_input(system="synrail", path_id="synrail")

        verdict, reasons, why, summary = compare(baseline, synrail)

        self.assertIn("synrail_adds_fixed_control_mass", reasons)
        self.assertGreater(summary["fixed_control_mass_added"], 0)
        self.assertIn(verdict, {"SYNRAIL_BETTER", "BASELINE_GOOD_ENOUGH", "UNCLEAR"})
        self.assertTrue(why)

    def test_compare_can_show_zero_required_visible_surface_penalty_when_extra_surfaces_are_skippable(self) -> None:
        baseline = comparison_input(system="baseline", path_id="baseline")
        synrail = comparison_input(
            system="synrail",
            path_id="synrail-thin",
            visible_surface_count=3,
            skippable_visible_surface_count=2,
            mandatory_mental_steps=2,
            trust_bearing_artifact_count=2,
        )

        summary = economics_summary(baseline, synrail)

        self.assertEqual(0, summary["required_visible_surfaces_added"])
        self.assertEqual(2, summary["skippable_visible_surfaces_added"])
        self.assertEqual(2, summary["fixed_control_mass_added"])


if __name__ == "__main__":
    unittest.main()
