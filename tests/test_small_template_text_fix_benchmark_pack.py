#!/usr/bin/env python3
"""Focused executable pack for the small_template_text_fix class."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"
FIXTURE = REPO_ROOT / "fixtures" / "small_template_text_fix_benchmark_pack_001.json"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_baseline_harness_v1 import build_record  # noqa: E402
from synrail_cost_of_control_v0 import build_cost_record_from_records  # noqa: E402


def load_pack() -> dict:
    return json.loads(FIXTURE.read_text())


class SmallTemplateTextFixBenchmarkPackTests(unittest.TestCase):
    def test_pack_has_two_focused_low_drag_tasks(self) -> None:
        pack = load_pack()

        self.assertEqual("SMALL_TEMPLATE_TEXT_FIX_BENCHMARK_PACK_001", pack["pack_id"])
        self.assertEqual("small_template_text_fix_repeatable", pack["scenario_class"])
        self.assertEqual("small_template_text_fix", pack["focus_task_class"])
        self.assertEqual(2, len(pack["tasks"]))
        self.assertEqual(
            {"EVERYDAY_LOCAL_005", "EVERYDAY_LOCAL_006"},
            {task["scenario_id"] for task in pack["tasks"]},
        )

    def test_pack_reads_as_narrow_class_win(self) -> None:
        pack = load_pack()
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]
        cost_record = build_cost_record_from_records(
            records,
            source_paths=[f"pack:{task['scenario_id']}" for task in pack["tasks"]],
        )

        self.assertEqual(2, cost_record["scenario_count"])
        self.assertEqual("small_template_text_fix_repeatable", cost_record["reading"]["primary_scenario_class"])
        self.assertEqual("SYNRAIL_BETTER", cost_record["reading"]["primary_scenario_class_status"])
        self.assertEqual("small_template_text_fix", cost_record["reading"]["focus_task_class"])
        self.assertEqual(2, cost_record["reading"]["focus_task_class_record_count"])
        self.assertEqual("SYNRAIL_BETTER", cost_record["reading"]["focus_task_class_verdict"])
        self.assertEqual("LOW_VARIANCE_REPEATABLE", cost_record["reading"]["focus_task_class_stability"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_operator_minutes_added"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_closure_latency_minutes_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_median_checks_per_accepted_closure_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_median_operator_visible_actions_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_median_got_lost_moments_added"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_fixed_control_mass_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_median_behavioral_control_tax_added"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_total_control_burden_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_operator_minutes_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_closure_latency_minutes_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_checks_per_accepted_closure_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_operator_visible_actions_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_got_lost_moments_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_fixed_control_mass_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_behavioral_control_tax_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_total_control_burden_added"])
        self.assertEqual("FOCUSED_CLASS_CHEAP_ENOUGH", cost_record["reading"]["focus_task_class_priority_one_status"])
        self.assertEqual("", cost_record["reading"]["focus_task_class_priority_one_barrier"])
        self.assertEqual("FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH", cost_record["reading"]["focus_task_class_kernel_cheapness_status"])
        self.assertEqual("", cost_record["reading"]["focus_task_class_kernel_cheapness_barrier"])
        self.assertEqual("FOCUSED_CLASS_BEHAVIOR_CHEAP_BY_DEFAULT", cost_record["reading"]["focus_task_class_behavior_cheapness_status"])
        self.assertEqual("", cost_record["reading"]["focus_task_class_behavior_cheapness_barrier"])
        self.assertEqual(["EVERYDAY_LOCAL_005", "EVERYDAY_LOCAL_006"], cost_record["path_buckets"]["justified_cost_paths"])

    def test_pack_reading_survives_slightly_uglier_same_family_variant(self) -> None:
        pack = load_pack()
        tasks = [*pack["tasks"], {
            "scenario_id": "EVERYDAY_LOCAL_007",
            "task_class": "small_template_text_fix",
            "baseline": {
                "schema_version": "comparison_input_v1",
                "system": "baseline",
                "scenario_id": "EVERYDAY_LOCAL_007",
                "scenario_class": "small_template_text_fix_repeatable",
                "task_class": "small_template_text_fix",
                "path_id": "baseline_guided_search_then_edit",
                "closure_result": "ACCEPTED",
                "blocker_to_closure_cycles": 0,
                "false_success_risk": "LOW",
                "proof_completeness": "LOW",
                "recovery_cost": "LOW",
                "coordination_overhead": "MEDIUM",
                "operator_minutes": 3,
                "intervention_count": 0,
                "repair_cycles": 0,
                "invalidation_count": 0,
                "closure_latency_minutes": 3,
                "false_green_exposure": 1,
                "artifact_completeness_percent": 38,
                "mandatory_mental_steps": 2,
                "trust_bearing_artifact_count": 1,
                "visible_surface_count": 2,
                "skippable_visible_surface_count": 1,
                "notes": "Slightly uglier same-family template copy fix that still needs one quick project search before editing.",
                "operator_visible_action_count": 2,
                "got_lost_moment_count": 0,
            },
            "synrail": {
                "schema_version": "comparison_input_v1",
                "system": "synrail",
                "scenario_id": "EVERYDAY_LOCAL_007",
                "scenario_class": "small_template_text_fix_repeatable",
                "task_class": "small_template_text_fix",
                "path_id": "governed_final_result_first_guided_search",
                "closure_result": "ACCEPTED",
                "blocker_to_closure_cycles": 0,
                "false_success_risk": "LOW",
                "proof_completeness": "MEDIUM",
                "recovery_cost": "LOW",
                "coordination_overhead": "MEDIUM",
                "operator_minutes": 4,
                "intervention_count": 0,
                "repair_cycles": 0,
                "invalidation_count": 0,
                "closure_latency_minutes": 4,
                "false_green_exposure": 0,
                "artifact_completeness_percent": 70,
                "mandatory_mental_steps": 3,
                "trust_bearing_artifact_count": 1,
                "visible_surface_count": 2,
                "skippable_visible_surface_count": 1,
                "notes": "Same-family governed path stays low-drag even when both paths need one quick search before the final template text edit.",
                "operator_visible_action_count": 2,
                "got_lost_moment_count": 0,
            },
        }]
        records = [build_record(task["baseline"], task["synrail"]) for task in tasks]
        cost_record = build_cost_record_from_records(
            records,
            source_paths=[f"pressure:{task['scenario_id']}" for task in tasks],
        )

        self.assertEqual(3, cost_record["scenario_count"])
        self.assertEqual("small_template_text_fix", cost_record["reading"]["focus_task_class"])
        self.assertEqual(3, cost_record["reading"]["focus_task_class_record_count"])
        self.assertEqual("SYNRAIL_BETTER", cost_record["reading"]["focus_task_class_verdict"])
        self.assertEqual("LOW_VARIANCE_REPEATABLE", cost_record["reading"]["focus_task_class_stability"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_operator_minutes_added"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_closure_latency_minutes_added"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_fixed_control_mass_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_median_behavioral_control_tax_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_operator_minutes_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_closure_latency_minutes_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_fixed_control_mass_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_behavioral_control_tax_added"])
        self.assertEqual("FOCUSED_CLASS_CHEAP_ENOUGH", cost_record["reading"]["focus_task_class_priority_one_status"])
        self.assertEqual("FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH", cost_record["reading"]["focus_task_class_kernel_cheapness_status"])
        self.assertEqual("FOCUSED_CLASS_BEHAVIOR_CHEAP_BY_DEFAULT", cost_record["reading"]["focus_task_class_behavior_cheapness_status"])
        self.assertEqual(
            ["EVERYDAY_LOCAL_005", "EVERYDAY_LOCAL_006", "EVERYDAY_LOCAL_007"],
            cost_record["path_buckets"]["justified_cost_paths"],
        )

    def test_pack_surfaces_behavior_drift_even_when_kernel_stays_cheap(self) -> None:
        pack = load_pack()
        tasks = [*pack["tasks"], {
            "scenario_id": "EVERYDAY_LOCAL_008",
            "task_class": "small_template_text_fix",
            "baseline": {
                "schema_version": "comparison_input_v1",
                "system": "baseline",
                "scenario_id": "EVERYDAY_LOCAL_008",
                "scenario_class": "small_template_text_fix_repeatable",
                "task_class": "small_template_text_fix",
                "path_id": "baseline_guided_search_then_edit",
                "closure_result": "ACCEPTED",
                "blocker_to_closure_cycles": 0,
                "false_success_risk": "LOW",
                "proof_completeness": "LOW",
                "recovery_cost": "LOW",
                "coordination_overhead": "MEDIUM",
                "operator_minutes": 3,
                "intervention_count": 0,
                "repair_cycles": 0,
                "invalidation_count": 0,
                "closure_latency_minutes": 3,
                "false_green_exposure": 1,
                "artifact_completeness_percent": 38,
                "mandatory_mental_steps": 2,
                "trust_bearing_artifact_count": 1,
                "visible_surface_count": 2,
                "skippable_visible_surface_count": 1,
                "notes": "Same-family template copy fix where the baseline path stays plain and compact.",
                "operator_visible_action_count": 2,
                "got_lost_moment_count": 0,
            },
            "synrail": {
                "schema_version": "comparison_input_v1",
                "system": "synrail",
                "scenario_id": "EVERYDAY_LOCAL_008",
                "scenario_class": "small_template_text_fix_repeatable",
                "task_class": "small_template_text_fix",
                "path_id": "governed_final_result_first_guided_search",
                "closure_result": "ACCEPTED",
                "blocker_to_closure_cycles": 0,
                "false_success_risk": "LOW",
                "proof_completeness": "MEDIUM",
                "recovery_cost": "LOW",
                "coordination_overhead": "MEDIUM",
                "operator_minutes": 4,
                "intervention_count": 0,
                "repair_cycles": 0,
                "invalidation_count": 0,
                "closure_latency_minutes": 4,
                "false_green_exposure": 0,
                "artifact_completeness_percent": 70,
                "mandatory_mental_steps": 3,
                "trust_bearing_artifact_count": 1,
                "visible_surface_count": 3,
                "skippable_visible_surface_count": 2,
                "notes": "Same-family governed path still closes cheaply at the kernel layer, but less tidy behavior pulls one extra skippable prose surface back into view.",
                "operator_visible_action_count": 2,
                "got_lost_moment_count": 0,
            },
        }]
        records = [build_record(task["baseline"], task["synrail"]) for task in tasks]
        cost_record = build_cost_record_from_records(
            records,
            source_paths=[f"behavior:{task['scenario_id']}" for task in tasks],
        )

        self.assertEqual(3, cost_record["scenario_count"])
        self.assertEqual("small_template_text_fix", cost_record["reading"]["focus_task_class"])
        self.assertEqual(3, cost_record["reading"]["focus_task_class_record_count"])
        self.assertEqual("SYNRAIL_BETTER", cost_record["reading"]["focus_task_class_verdict"])
        self.assertEqual("LOW_VARIANCE_REPEATABLE", cost_record["reading"]["focus_task_class_stability"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_operator_minutes_added"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_closure_latency_minutes_added"])
        self.assertEqual(1, cost_record["reading"]["focus_task_class_median_fixed_control_mass_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_median_operator_visible_actions_added"])
        self.assertEqual(0, cost_record["reading"]["focus_task_class_spread_operator_visible_actions_added"])
        self.assertEqual("FOCUSED_CLASS_CHEAP_ENOUGH", cost_record["reading"]["focus_task_class_priority_one_status"])
        self.assertEqual("", cost_record["reading"]["focus_task_class_priority_one_barrier"])
        self.assertEqual("FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH", cost_record["reading"]["focus_task_class_kernel_cheapness_status"])
        self.assertEqual("", cost_record["reading"]["focus_task_class_kernel_cheapness_barrier"])
        self.assertEqual("FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT", cost_record["reading"]["focus_task_class_behavior_cheapness_status"])
        self.assertEqual("FOCUSED_CLASS_SPREAD_SKIPPABLE_VISIBLE_SURFACES_TOO_HIGH", cost_record["reading"]["focus_task_class_behavior_cheapness_barrier"])
        self.assertEqual(
            ["EVERYDAY_LOCAL_005", "EVERYDAY_LOCAL_006", "EVERYDAY_LOCAL_008"],
            cost_record["path_buckets"]["justified_cost_paths"],
        )


if __name__ == "__main__":
    unittest.main()
