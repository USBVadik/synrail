#!/usr/bin/env python3
"""Unit tests for bootstrap starter text guidance."""

from __future__ import annotations

import sys
import hashlib
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_bootstrap_v0 import build_proof_request_record, build_proof_starter_contents, write_proof_starter_files  # noqa: E402


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

    def test_runtime_evidence_projects_receive_runtime_helper_guidance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_bootstrap_runtime_hint_") as tmpdir:
            project_root = Path(tmpdir)
            (project_root / "templates").mkdir(parents=True, exist_ok=True)

            contents = build_proof_starter_contents(
                run_id="RUN_123",
                task_class="bounded_change",
                task_identity="Surface runtime helper guidance",
                project_root=project_root,
            )

        self.assertIn('"synrail runtime-helper"', contents["final_result"])
        self.assertIn(
            "Runtime hint: for UI, route, or rendered output changes, prefer a local response or rendered fragment over source-only grep when possible; run `synrail runtime-helper` if you want a small curl or template-render path before browser automation",
            contents["readback"],
        )
        self.assertIn(
            "Runtime hint: prefer a local request, rendered response, or observed runtime output over a source-only grep when possible; run `synrail runtime-helper` if you want a small curl or template-render path before browser automation",
            contents["scenario_proof"],
        )

    def test_final_result_starter_hash_matches_written_bytes(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_bootstrap_hash_") as tmpdir:
            root = Path(tmpdir) / "artifacts"
            project_root = Path(tmpdir) / "project"
            project_root.mkdir(parents=True)
            contents = build_proof_starter_contents(
                run_id="RUN_123",
                task_class="bounded_change",
                task_identity="Windows starter hash regression",
                project_root=project_root,
            )

            write_proof_starter_files(artifact_root=root, starter_contents=contents)
            record = build_proof_request_record(
                run_id="RUN_123",
                task_class="bounded_change",
                task_identity="Windows starter hash regression",
                project_root=project_root,
                artifact_root=root,
            )

            final_result_bytes = (root / "final_result.json").read_bytes()
            expected_hash = hashlib.sha256(final_result_bytes).hexdigest()
            self.assertEqual(record["starter_hashes"]["final_result"], expected_hash)
            self.assertNotIn(b"\r\n", final_result_bytes)


if __name__ == "__main__":
    unittest.main()
