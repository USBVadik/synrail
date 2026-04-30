#!/usr/bin/env python3
"""Unit tests for bootstrap starter text guidance."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_bootstrap_v0 import build_proof_starter_contents  # noqa: E402


class BootstrapStarterTextTests(unittest.TestCase):
    def test_multi_file_guidance_does_not_imply_one_changed_file_is_enough(self) -> None:
        contents = build_proof_starter_contents(
            run_id="RUN_123",
            task_class="bounded_change",
            task_identity="Tighten multi-file provenance wording",
            project_root=None,
        )

        self.assertIn(
            "diff_provenance or diff_provenance_records",
            contents["final_result"],
        )
        self.assertIn(
            "for each attested file: changed_file",
            contents["final_result"],
        )
        self.assertIn(
            "use diff_provenance for a single-file change, or use diff_provenance_records/per_file_diff_provenance with one structured direct-observation record per modified file for a multi-file change",
            contents["final_result"],
        )
        self.assertIn(
            "workspace clean after updating only the intended file or files for this run with no unintended changes",
            contents["final_result"],
        )
        self.assertNotIn('"diff_provenance.changed_file"', contents["final_result"])

    def test_fallback_notes_use_explicit_target_wording(self) -> None:
        contents = build_proof_starter_contents(
            run_id="RUN_123",
            task_class="bounded_change",
            task_identity="Tighten fallback wording",
            project_root=None,
        )

        self.assertIn(
            "leave this file untouched unless Synrail explicitly targets this file for readback.",
            contents["readback"],
        )
        self.assertIn(
            "leave this file untouched unless Synrail explicitly targets this file for scenario proof.",
            contents["scenario_proof"],
        )
        self.assertIn(
            "Observed: record only the concrete property needed for the blocker Synrail explicitly targeted",
            contents["readback"],
        )
        self.assertIn(
            "Scenario: name only the exact runtime context needed for the blocker Synrail explicitly targeted",
            contents["scenario_proof"],
        )
        self.assertIn(
            "Command: paste only the local command, request, or test that verified this named blocker",
            contents["scenario_proof"],
        )
        self.assertIn(
            "Observed: paste only the concrete output, rendered fragment, or behavior needed to unblock it",
            contents["scenario_proof"],
        )
        self.assertNotIn("explicitly asks for readback", contents["readback"])
        self.assertNotIn("explicitly asks for scenario proof", contents["scenario_proof"])
        self.assertNotIn("describe what this changed surface now contains, returns, or renders", contents["readback"])
        self.assertNotIn("describe the exact runtime context on the attested target surface", contents["scenario_proof"])


if __name__ == "__main__":
    unittest.main()
