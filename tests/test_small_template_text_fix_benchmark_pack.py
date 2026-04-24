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
    def test_pack_has_five_focused_low_drag_tasks(self) -> None:
        pack = load_pack()

        self.assertEqual("SMALL_TEMPLATE_TEXT_FIX_BENCHMARK_PACK_001", pack["pack_id"])
        self.assertEqual("small_template_text_fix_repeatable", pack["scenario_class"])
        self.assertEqual("small_template_text_fix", pack["focus_task_class"])
        self.assertEqual(5, len(pack["tasks"]))
        self.assertEqual(
            {
                "EVERYDAY_LOCAL_005",
                "EVERYDAY_LOCAL_006",
                "EVERYDAY_LOCAL_007",
                "EVERYDAY_LOCAL_009",
                "EVERYDAY_LOCAL_010",
            },
            {task["scenario_id"] for task in pack["tasks"]},
        )
        self.assertEqual(
            {"curated_local_estimate"},
            {
                task[side]["data_provenance"]
                for task in pack["tasks"]
                for side in ("baseline", "synrail")
            },
        )

    def test_pack_reads_as_narrow_class_win(self) -> None:
        pack = load_pack()
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]
        cost_record = build_cost_record_from_records(
            records,
            source_paths=[f"pack:{task['scenario_id']}" for task in pack["tasks"]],
        )

        self.assertEqual(5, cost_record["scenario_count"])
        self.assertEqual(["curated_local_estimate"], cost_record["provenance_mix"])
        self.assertEqual("small_template_text_fix_repeatable", cost_record["reading"]["primary_scenario_class"])
        self.assertEqual("SYNRAIL_BETTER", cost_record["reading"]["primary_scenario_class_status"])
        self.assertEqual("small_template_text_fix", cost_record["reading"]["focus_task_class"])
        self.assertEqual(5, cost_record["reading"]["focus_task_class_record_count"])
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
        self.assertEqual(
            [
                "EVERYDAY_LOCAL_005",
                "EVERYDAY_LOCAL_006",
                "EVERYDAY_LOCAL_007",
                "EVERYDAY_LOCAL_009",
                "EVERYDAY_LOCAL_010",
            ],
            cost_record["path_buckets"]["justified_cost_paths"],
        )

    def test_pack_materializes_three_added_same_family_variants(self) -> None:
        pack = load_pack()
        added_tasks = [
            task for task in pack["tasks"] if task["scenario_id"] in {"EVERYDAY_LOCAL_007", "EVERYDAY_LOCAL_009", "EVERYDAY_LOCAL_010"}
        ]

        self.assertEqual(3, len(added_tasks))
        self.assertEqual(
            {
                "EVERYDAY_LOCAL_007": "baseline_multiline_template_edit",
                "EVERYDAY_LOCAL_009": "baseline_search_verify_then_edit",
                "EVERYDAY_LOCAL_010": "baseline_cross_template_touch_up",
            },
            {task["scenario_id"]: task["baseline"]["path_id"] for task in added_tasks},
        )
        self.assertEqual(
            {
                "EVERYDAY_LOCAL_007": "governed_final_result_first_multiline",
                "EVERYDAY_LOCAL_009": "governed_final_result_first_search_verify",
                "EVERYDAY_LOCAL_010": "governed_final_result_first_cross_template_touch_up",
            },
            {task["scenario_id"]: task["synrail"]["path_id"] for task in added_tasks},
        )
        self.assertTrue(all(task["baseline"]["artifact_completeness_percent"] < task["synrail"]["artifact_completeness_percent"] for task in added_tasks))


if __name__ == "__main__":
    unittest.main()
