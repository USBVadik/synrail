#!/usr/bin/env python3
"""Executable pack for the repeatable everyday economics class."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"
FIXTURE = REPO_ROOT / "fixtures" / "repeatable_everyday_benchmark_pack_001.json"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_baseline_harness_v1 import build_record  # noqa: E402
from synrail_cost_of_control_v0 import build_cost_record_from_records  # noqa: E402


def load_pack() -> dict:
    return json.loads(FIXTURE.read_text())


class RepeatableEverydayBenchmarkPackTests(unittest.TestCase):
    def test_pack_has_six_repeatable_everyday_tasks(self) -> None:
        pack = load_pack()

        self.assertEqual("REPEATABLE_EVERYDAY_BENCHMARK_PACK_001", pack["pack_id"])
        self.assertEqual("repeatable_everyday_local", pack["scenario_class"])
        self.assertEqual("small_template_text_fix", pack["focus_task_class"])
        self.assertEqual(6, len(pack["tasks"]))
        self.assertEqual(
            {"EVERYDAY_LOCAL_001", "EVERYDAY_LOCAL_002", "EVERYDAY_LOCAL_003", "EVERYDAY_LOCAL_004", "EVERYDAY_LOCAL_005", "EVERYDAY_LOCAL_006"},
            {task["scenario_id"] for task in pack["tasks"]},
        )

    def test_pack_materializes_machine_readable_everyday_reading(self) -> None:
        pack = load_pack()
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]
        cost_record = build_cost_record_from_records(
            records,
            source_paths=[f"pack:{task['scenario_id']}" for task in pack["tasks"]],
        )

        self.assertEqual(6, cost_record["scenario_count"])
        self.assertEqual(["curated_local_estimate"], cost_record["provenance_mix"])
        self.assertEqual("BASELINE_GOOD_ENOUGH", cost_record["reading"]["everyday_status"])
        self.assertEqual(2, cost_record["verdict_counts"]["SYNRAIL_BETTER"])
        self.assertEqual(4, cost_record["verdict_counts"]["BASELINE_GOOD_ENOUGH"])
        self.assertEqual(0, cost_record["verdict_counts"]["UNCLEAR"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_operator_minutes_added"])
        self.assertEqual(0, cost_record["aggregate_deltas"]["avg_checks_per_accepted_closure_added"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_mandatory_mental_steps_added"])
        self.assertEqual(0, cost_record["aggregate_deltas"]["avg_required_visible_surfaces_added"])
        self.assertEqual(0, cost_record["aggregate_deltas"]["avg_skippable_visible_surfaces_added"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_operator_visible_actions_added"])
        self.assertEqual(0, cost_record["aggregate_deltas"]["avg_got_lost_moments_added"])
        self.assertEqual(2, cost_record["aggregate_deltas"]["avg_kernel_control_mass_added"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_behavioral_control_tax_added"])
        self.assertEqual(29, cost_record["aggregate_deltas"]["avg_artifact_completeness_percent_gain"])
        self.assertEqual(2, cost_record["aggregate_deltas"]["avg_fixed_control_mass_added"])
        self.assertEqual(3, cost_record["aggregate_deltas"]["avg_total_control_burden_added"])
        self.assertEqual("EVERYDAY_LOCAL_003", cost_record["reading"]["clearest_overhead_path"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_operator_visible_actions_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_got_lost_moments_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_kernel_control_mass_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_behavioral_control_tax_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_fixed_control_mass_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_total_control_burden_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_005", cost_record["reading"]["strongest_justified_path"])
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

    def test_pack_contains_two_repeatable_low_drag_winners(self) -> None:
        pack = load_pack()
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]
        near_zero_drag = [
            record for record in records
            if record["economics_summary"]["operator_minutes_added"] <= 1
            and record["economics_summary"]["total_control_burden_added"] <= 1
        ]

        self.assertEqual(2, len(near_zero_drag))
        self.assertEqual({"EVERYDAY_LOCAL_005", "EVERYDAY_LOCAL_006"}, {record["scenario_id"] for record in near_zero_drag})
        self.assertEqual({"SYNRAIL_BETTER"}, {record["verdict"] for record in near_zero_drag})

    def test_pack_has_no_remaining_unclear_paths(self) -> None:
        pack = load_pack()
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]

        self.assertEqual([], [record["scenario_id"] for record in records if record["verdict"] == "UNCLEAR"])


if __name__ == "__main__":
    unittest.main()
