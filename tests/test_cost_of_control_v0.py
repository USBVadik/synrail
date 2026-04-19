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
    def test_everyday_records_surface_fixed_control_mass_and_everyday_status(self) -> None:
        pack = json.loads((REPO_ROOT / "fixtures" / "repeatable_everyday_benchmark_pack_001.json").read_text())
        records = [build_record(task["baseline"], task["synrail"]) for task in pack["tasks"]]

        cost_record = build_cost_record_from_records(
            records,
            source_paths=[f"pack:{task['scenario_id']}" for task in pack["tasks"]],
        )

        self.assertEqual("BASELINE_GOOD_ENOUGH", cost_record["reading"]["everyday_status"])
        self.assertEqual(2, cost_record["aggregate_deltas"]["avg_fixed_control_mass_added"])
        self.assertEqual("EVERYDAY_LOCAL_004", cost_record["hotspots"]["highest_fixed_control_mass_added"]["scenario_id"])

    def test_old_records_without_control_mass_fields_still_aggregate(self) -> None:
        record = build_cost_record(
            [
                REPO_ROOT / "fixtures" / "executable_loop_run_001" / "comparison_economics.json",
                REPO_ROOT / "fixtures" / "executable_loop_run_002" / "comparison_economics.json",
            ]
        )

        self.assertEqual("UNKNOWN", record["reading"]["everyday_status"])
        self.assertEqual(0, record["aggregate_deltas"]["avg_fixed_control_mass_added"])
        self.assertEqual(0, record["hotspots"]["highest_fixed_control_mass_added"]["value"])


if __name__ == "__main__":
    unittest.main()
