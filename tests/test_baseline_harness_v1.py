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

from synrail_baseline_harness_v1 import (  # noqa: E402
    build_record,
    checks_per_accepted_closure,
    compare,
    economics_summary,
    required_visible_surface_count,
)


def comparison_input(*, system: str, path_id: str, **overrides: int | str) -> dict:
    payload: dict = {
        "schema_version": "comparison_input_v1",
        "system": system,
        "scenario_id": "EVERYDAY_BENCHMARK_001",
        "scenario_class": "repeatable_everyday_local",
        "task_class": "bounded_copy_update",
        "path_id": path_id,
        "data_provenance": "curated_local_estimate",
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
        "operator_visible_action_count": 1,
        "got_lost_moment_count": 0,
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

    def test_checks_per_accepted_closure_counts_one_check_plus_retry_cycles(self) -> None:
        accepted = comparison_input(system="synrail", path_id="synrail-default", blocker_to_closure_cycles=2)
        blocked = comparison_input(system="synrail", path_id="synrail-blocked", closure_result="BLOCKED", blocker_to_closure_cycles=4)

        self.assertEqual(3, checks_per_accepted_closure(accepted))
        self.assertEqual(0, checks_per_accepted_closure(blocked))

    def test_build_record_surfaces_input_data_provenance(self) -> None:
        baseline = comparison_input(system="baseline", path_id="baseline")
        synrail = comparison_input(system="synrail", path_id="synrail")

        record = build_record(baseline, synrail)

        self.assertEqual("curated_local_estimate", record["baseline_data_provenance"])
        self.assertEqual("curated_local_estimate", record["synrail_data_provenance"])

    def test_economics_summary_tracks_fixed_control_mass_metrics(self) -> None:
        baseline = comparison_input(system="baseline", path_id="baseline")
        synrail = comparison_input(system="synrail", path_id="synrail", blocker_to_closure_cycles=2)

        summary = economics_summary(baseline, synrail)

        self.assertEqual(2, summary["operator_minutes_added"])
        self.assertEqual(2, summary["checks_per_accepted_closure_added"])
        self.assertEqual(2, summary["mandatory_mental_steps_added"])
        self.assertEqual(1, summary["trust_bearing_artifacts_added"])
        self.assertEqual(1, summary["required_visible_surfaces_added"])
        self.assertEqual(1, summary["skippable_visible_surfaces_added"])
        self.assertEqual(0, summary["operator_visible_actions_added"])
        self.assertEqual(0, summary["got_lost_moments_added"])
        self.assertEqual(4, summary["kernel_control_mass_added"])
        self.assertEqual(0, summary["behavioral_control_tax_added"])
        self.assertEqual(4, summary["fixed_control_mass_added"])
        self.assertEqual(4, summary["total_control_burden_added"])

    def test_compare_surfaces_fixed_control_mass_reason(self) -> None:
        baseline = comparison_input(system="baseline", path_id="baseline")
        synrail = comparison_input(system="synrail", path_id="synrail")

        verdict, reasons, why, summary = compare(baseline, synrail)

        self.assertIn("synrail_adds_fixed_control_mass", reasons)
        self.assertGreater(summary["fixed_control_mass_added"], 0)
        self.assertGreater(summary["total_control_burden_added"], 0)
        self.assertIn(verdict, {"SYNRAIL_BETTER", "BASELINE_GOOD_ENOUGH", "UNCLEAR"})
        self.assertTrue(why)

    def test_economics_summary_tracks_operator_visible_actions_and_got_lost_moments(self) -> None:
        baseline = comparison_input(system="baseline", path_id="baseline", operator_visible_action_count=1, got_lost_moment_count=0)
        synrail = comparison_input(system="synrail", path_id="synrail", operator_visible_action_count=3, got_lost_moment_count=1)

        summary = economics_summary(baseline, synrail)

        self.assertEqual(2, summary["operator_visible_actions_added"])
        self.assertEqual(1, summary["got_lost_moments_added"])
        self.assertEqual(4, summary["kernel_control_mass_added"])
        self.assertEqual(3, summary["behavioral_control_tax_added"])
        self.assertEqual(4, summary["fixed_control_mass_added"])
        self.assertEqual(7, summary["total_control_burden_added"])

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
        self.assertEqual(2, summary["kernel_control_mass_added"])
        self.assertEqual(0, summary["behavioral_control_tax_added"])
        self.assertEqual(2, summary["fixed_control_mass_added"])
        self.assertEqual(2, summary["total_control_burden_added"])

    def test_compare_can_recognize_low_drag_trust_win(self) -> None:
        baseline = comparison_input(
            system="baseline",
            path_id="baseline",
            false_success_risk="LOW",
            false_green_exposure=1,
            proof_completeness="LOW",
            artifact_completeness_percent=35,
        )
        synrail = comparison_input(
            system="synrail",
            path_id="synrail-low-drag-win",
            false_success_risk="LOW",
            false_green_exposure=0,
            proof_completeness="MEDIUM",
            artifact_completeness_percent=70,
            operator_minutes=3,
            intervention_count=0,
            closure_latency_minutes=3,
            mandatory_mental_steps=2,
            trust_bearing_artifact_count=1,
            visible_surface_count=2,
            skippable_visible_surface_count=1,
        )

        verdict, reasons, why, summary = compare(baseline, synrail)

        self.assertEqual("SYNRAIL_BETTER", verdict)
        self.assertEqual(1, summary["false_green_exposure_reduced"])
        self.assertEqual(35, summary["artifact_completeness_percent_gain"])
        self.assertEqual(1, summary["kernel_control_mass_added"])
        self.assertEqual(0, summary["behavioral_control_tax_added"])
        self.assertEqual(1, summary["fixed_control_mass_added"])
        self.assertIn("synrail_reduces_false_green_exposure", reasons)
        self.assertIn("synrail_improves_artifact_completeness", reasons)
        self.assertIn("low-drag trust win", why)

    def test_compare_can_recognize_safety_neutral_low_drag_baseline_path(self) -> None:
        baseline = comparison_input(
            system="baseline",
            path_id="baseline",
            false_success_risk="LOW",
            false_green_exposure=0,
            proof_completeness="LOW",
            artifact_completeness_percent=35,
        )
        synrail = comparison_input(
            system="synrail",
            path_id="synrail-safety-neutral",
            false_success_risk="LOW",
            false_green_exposure=0,
            proof_completeness="MEDIUM",
            artifact_completeness_percent=70,
            operator_minutes=3,
            intervention_count=0,
            closure_latency_minutes=3,
            mandatory_mental_steps=2,
            trust_bearing_artifact_count=2,
            visible_surface_count=2,
            skippable_visible_surface_count=1,
        )

        verdict, reasons, why, summary = compare(baseline, synrail)

        self.assertEqual("BASELINE_GOOD_ENOUGH", verdict)
        self.assertEqual(0, summary["false_green_exposure_reduced"])
        self.assertEqual(35, summary["artifact_completeness_percent_gain"])
        self.assertEqual(1, summary["trust_bearing_artifacts_added"])
        self.assertEqual(2, summary["kernel_control_mass_added"])
        self.assertEqual(0, summary["behavioral_control_tax_added"])
        self.assertEqual(2, summary["fixed_control_mass_added"])
        self.assertEqual(2, summary["total_control_burden_added"])
        self.assertIn("synrail_improves_artifact_completeness", reasons)
        self.assertIn("baseline already keeps false-green exposure low enough", why)


if __name__ == "__main__":
    unittest.main()
