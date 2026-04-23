#!/usr/bin/env python3
"""Focused tests for cost-of-control aggregation."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_baseline_harness_v1 import build_record  # noqa: E402
from synrail_cost_of_control_v0 import build_cost_record, build_cost_record_from_records  # noqa: E402


class CostOfControlV0Tests(unittest.TestCase):
    def test_reference_fixtures_and_schema_include_kernel_cheapness_fields(self) -> None:
        schema = json.loads((REPO_ROOT / "schemas" / "cost_of_control_record_v0.schema.json").read_text())
        reading = schema["properties"]["reading"]

        self.assertIn("focus_task_class_kernel_cheapness_status", reading["required"])
        self.assertIn("focus_task_class_kernel_cheapness_barrier", reading["required"])
        self.assertEqual({"type": "string"}, reading["properties"]["focus_task_class_kernel_cheapness_status"])
        self.assertEqual({"type": "string"}, reading["properties"]["focus_task_class_kernel_cheapness_barrier"])

        everyday_fixture = json.loads((REPO_ROOT / "fixtures" / "cost_of_control_everyday_001.json").read_text())
        focused_fixture = json.loads((REPO_ROOT / "fixtures" / "cost_of_control_small_template_text_fix_001.json").read_text())

        self.assertEqual("FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH", everyday_fixture["reading"]["focus_task_class_kernel_cheapness_status"])
        self.assertEqual("", everyday_fixture["reading"]["focus_task_class_kernel_cheapness_barrier"])
        self.assertEqual("FOCUSED_CLASS_KERNEL_CHEAP_ENOUGH", focused_fixture["reading"]["focus_task_class_kernel_cheapness_status"])
        self.assertEqual("", focused_fixture["reading"]["focus_task_class_kernel_cheapness_barrier"])

    def test_everyday_records_surface_fixed_control_mass_and_everyday_status(self) -> None:
        pack = json.loads((REPO_ROOT / "fixtures" / "repeatable_everyday_benchmark_pack_001.json").read_text())
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]

        cost_record = build_cost_record_from_records(
            records,
            source_paths=[f"pack:{task['scenario_id']}" for task in pack["tasks"]],
        )

        self.assertEqual("BASELINE_GOOD_ENOUGH", cost_record["reading"]["everyday_status"])
        self.assertEqual(0, cost_record["aggregate_deltas"]["avg_checks_per_accepted_closure_added"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_operator_visible_actions_added"])
        self.assertEqual(0, cost_record["aggregate_deltas"]["avg_skippable_visible_surfaces_added"])
        self.assertEqual(0, cost_record["aggregate_deltas"]["avg_got_lost_moments_added"])
        self.assertEqual(2, cost_record["aggregate_deltas"]["avg_kernel_control_mass_added"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_behavioral_control_tax_added"])
        self.assertEqual(2, cost_record["aggregate_deltas"]["avg_fixed_control_mass_added"])
        self.assertEqual(3, cost_record["aggregate_deltas"]["avg_total_control_burden_added"])
        self.assertEqual(0, cost_record["hotspots"]["highest_checks_per_accepted_closure_added"]["value"])
        self.assertEqual("repeatable_everyday_local", cost_record["reading"]["primary_scenario_class"])
        self.assertEqual("BASELINE_GOOD_ENOUGH", cost_record["reading"]["primary_scenario_class_status"])
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
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_operator_visible_actions_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_got_lost_moments_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_kernel_control_mass_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_behavioral_control_tax_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_fixed_control_mass_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_total_control_burden_added"]["scenario_id"])

    def test_old_records_without_control_mass_fields_still_aggregate(self) -> None:
        record = build_cost_record(
            [
                REPO_ROOT / "fixtures" / "executable_loop_run_001" / "comparison_economics.json",
                REPO_ROOT / "fixtures" / "executable_loop_run_002" / "comparison_economics.json",
            ]
        )

        self.assertEqual("UNKNOWN", record["reading"]["everyday_status"])
        self.assertEqual(0, record["aggregate_deltas"]["avg_checks_per_accepted_closure_added"])
        self.assertEqual(0, record["aggregate_deltas"]["avg_operator_visible_actions_added"])
        self.assertEqual(0, record["aggregate_deltas"]["avg_got_lost_moments_added"])
        self.assertEqual(0, record["aggregate_deltas"]["avg_kernel_control_mass_added"])
        self.assertEqual(0, record["aggregate_deltas"]["avg_behavioral_control_tax_added"])
        self.assertEqual(0, record["aggregate_deltas"]["avg_fixed_control_mass_added"])
        self.assertEqual(0, record["aggregate_deltas"]["avg_total_control_burden_added"])
        self.assertEqual(0, record["hotspots"]["highest_checks_per_accepted_closure_added"]["value"])
        self.assertEqual(0, record["hotspots"]["highest_operator_visible_actions_added"]["value"])
        self.assertEqual(0, record["hotspots"]["highest_got_lost_moments_added"]["value"])
        self.assertEqual(0, record["hotspots"]["highest_kernel_control_mass_added"]["value"])
        self.assertEqual(0, record["hotspots"]["highest_behavioral_control_tax_added"]["value"])
        self.assertEqual(0, record["hotspots"]["highest_fixed_control_mass_added"]["value"])
        self.assertEqual(0, record["hotspots"]["highest_total_control_burden_added"]["value"])
        self.assertEqual(24, record["reading"]["focus_task_class_median_operator_minutes_added"])
        self.assertEqual(33, record["reading"]["focus_task_class_median_closure_latency_minutes_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_median_checks_per_accepted_closure_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_median_operator_visible_actions_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_median_got_lost_moments_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_median_fixed_control_mass_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_median_behavioral_control_tax_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_median_total_control_burden_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_spread_operator_minutes_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_spread_closure_latency_minutes_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_spread_checks_per_accepted_closure_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_spread_operator_visible_actions_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_spread_got_lost_moments_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_spread_fixed_control_mass_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_spread_behavioral_control_tax_added"])
        self.assertEqual(0, record["reading"]["focus_task_class_spread_total_control_burden_added"])
        self.assertEqual("FOCUSED_CLASS_NOT_YET_CHEAP_ENOUGH", record["reading"]["focus_task_class_priority_one_status"])
        self.assertEqual("FOCUSED_CLASS_NOT_YET_LOW_VARIANCE", record["reading"]["focus_task_class_priority_one_barrier"])
        self.assertEqual("FOCUSED_CLASS_KERNEL_NOT_YET_CHEAP_ENOUGH", record["reading"]["focus_task_class_kernel_cheapness_status"])
        self.assertEqual("FOCUSED_CLASS_NOT_YET_LOW_VARIANCE", record["reading"]["focus_task_class_kernel_cheapness_barrier"])
        self.assertEqual("FOCUSED_CLASS_BEHAVIOR_NOT_YET_CHEAP_BY_DEFAULT", record["reading"]["focus_task_class_behavior_cheapness_status"])
        self.assertEqual("FOCUSED_CLASS_NOT_YET_LOW_VARIANCE", record["reading"]["focus_task_class_behavior_cheapness_barrier"])


if __name__ == "__main__":
    unittest.main()
