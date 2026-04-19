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
    def test_pack_has_five_repeatable_everyday_tasks(self) -> None:
        pack = load_pack()

        self.assertEqual("REPEATABLE_EVERYDAY_BENCHMARK_PACK_001", pack["pack_id"])
        self.assertEqual("repeatable_everyday_local", pack["scenario_class"])
        self.assertEqual(5, len(pack["tasks"]))
        self.assertEqual(
            {"EVERYDAY_LOCAL_001", "EVERYDAY_LOCAL_002", "EVERYDAY_LOCAL_003", "EVERYDAY_LOCAL_004", "EVERYDAY_LOCAL_005"},
            {task["scenario_id"] for task in pack["tasks"]},
        )

    def test_pack_materializes_machine_readable_everyday_reading(self) -> None:
        pack = load_pack()
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]
        cost_record = build_cost_record_from_records(
            records,
            source_paths=[f"pack:{task['scenario_id']}" for task in pack["tasks"]],
        )

        self.assertEqual(5, cost_record["scenario_count"])
        self.assertEqual("BASELINE_GOOD_ENOUGH", cost_record["reading"]["everyday_status"])
        self.assertEqual(1, cost_record["verdict_counts"]["SYNRAIL_BETTER"])
        self.assertEqual(3, cost_record["verdict_counts"]["BASELINE_GOOD_ENOUGH"])
        self.assertEqual(1, cost_record["verdict_counts"]["UNCLEAR"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_operator_minutes_added"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_mandatory_mental_steps_added"])
        self.assertEqual(0, cost_record["aggregate_deltas"]["avg_required_visible_surfaces_added"])
        self.assertEqual(1, cost_record["aggregate_deltas"]["avg_skippable_visible_surfaces_added"])
        self.assertEqual(29, cost_record["aggregate_deltas"]["avg_artifact_completeness_percent_gain"])
        self.assertEqual(2, cost_record["aggregate_deltas"]["avg_fixed_control_mass_added"])
        self.assertEqual("EVERYDAY_LOCAL_003", cost_record["reading"]["clearest_overhead_path"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_fixed_control_mass_added"]["scenario_id"])
        self.assertEqual("EVERYDAY_LOCAL_005", cost_record["reading"]["strongest_justified_path"])

    def test_pack_contains_one_repeatable_low_drag_winner(self) -> None:
        pack = load_pack()
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]
        near_zero_drag = [
            record for record in records
            if record["economics_summary"]["operator_minutes_added"] <= 1
            and record["economics_summary"]["fixed_control_mass_added"] <= 1
        ]

        self.assertEqual(1, len(near_zero_drag))
        self.assertEqual("EVERYDAY_LOCAL_005", near_zero_drag[0]["scenario_id"])
        self.assertEqual("SYNRAIL_BETTER", near_zero_drag[0]["verdict"])


if __name__ == "__main__":
    unittest.main()
