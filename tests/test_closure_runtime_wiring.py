#!/usr/bin/env python3

from __future__ import annotations

import argparse
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools.reference.synrail_commands_v0 import cmd_orchestrate as extracted_cmd_orchestrate


class ClosureRuntimeWiringTests(unittest.TestCase):
    def test_extracted_orchestrate_forwards_closure_certificate_output(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_closure_runtime_wiring_") as tmpdir:
            project_root = Path(tmpdir)
            artifact_root = project_root / ".synrail"
            artifact_root.mkdir(parents=True, exist_ok=True)
            state_file = artifact_root / "state.json"
            state_file.write_text("{}", encoding="utf-8")

            args = argparse.Namespace(
                artifact_root=str(artifact_root),
                state_file=str(state_file),
                doctor_run_id="R1",
                doctor_level="CORE_DOCTOR",
                target_path=str(project_root),
                target_classification="project",
                baseline_identity="baseline",
                intended_run_class="core_probe",
                doctor_output=str(artifact_root / "doctor.json"),
                final_result=str(artifact_root / "final_result.json"),
                task_class="bounded_change",
                bundle_output=str(artifact_root / "bundle.json"),
                closure_output=str(artifact_root / "closure.json"),
                closure_certificate_output=str(artifact_root / "closure_certificate.json"),
                report_output=str(artifact_root / "report.json"),
                execution_surface_identity="surface",
                prompt_identity="prompt",
                task_identity="task",
                resume_from_state="",
                repair_handoff_file="",
                repair_handoff_output="",
                repair_packet_file="",
                repair_packet_output="",
                repair_receipt_file="",
                repair_receipt_output="",
                mode_selection_receipt="",
                readback="",
                scenario_proof="",
                plan_output="",
                preparation_receipt_output="",
                preparation_artifact_root="",
                refresh_output="",
                observability_output="",
                artifact_consistency_output=str(artifact_root / "artifact_consistency.json"),
                closure_certificate_file="",
                refresh_event_type="",
                refresh_doctor_status="",
                refresh_recovery_status="",
                refresh_reverification_complete=False,
                refresh_use_bundle=False,
                refresh_use_closure=False,
                baseline_file="",
                synrail_file="",
                comparison_output="",
                worked_artifact_output=str(artifact_root / "orchestration.json"),
                run_artifact_output=str(artifact_root / "run.json"),
                clean_surface=False,
                artifact_viable=False,
                helper_ok=False,
                credentials_ok=False,
                prompt_identity_ok=False,
                artifact_path="",
                helper_path="",
                prompt_identity_file="",
                target_identity_file="",
                coverage_profile_file="",
                coverage_corpus_file="",
                acceptance_criteria_file="",
                acceptance_validation_output="",
                project_profile_file="",
                bootstrap_provenance_ok=False,
                bootstrap_provenance_reason="",
                changed_file=[],
                allowed_scope_path=[],
                credential_env=[],
                _capture_output=True,
            )

            completed = mock.Mock(returncode=0)
            run_python_capture = mock.Mock(return_value=completed)
            with (
                mock.patch(
                    "tools.reference.synrail_commands_v0.evaluate_verification_gate",
                    return_value={"status": "NOT_CONFIGURED"},
                ),
                mock.patch(
                    "tools.reference.synrail_commands_v0.emit_completed_capture",
                    return_value=None,
                ),
            ):
                rc = extracted_cmd_orchestrate(
                    args,
                    alpha_root_from_args=lambda provided: artifact_root,
                    current_project_root=lambda: project_root,
                    validate_root_within_project=lambda *a, **k: None,
                    apply_alpha_runtime_file_defaults=lambda provided: None,
                    project_root_from_profile=lambda provided: project_root,
                    validate_check_like_paths=lambda *a, **k: None,
                    run_python=lambda *a, **k: 0,
                    run_python_capture=run_python_capture,
                    spine_script=project_root / "tools" / "reference" / "synrail_spine_v0.py",
                )

            self.assertEqual(0, rc)
            forwarded = run_python_capture.call_args.args[1]
            self.assertIn("--closure-certificate-output", forwarded)
            index = forwarded.index("--closure-certificate-output")
            self.assertEqual(str(artifact_root / "closure_certificate.json"), forwarded[index + 1])
            self.assertIn("--artifact-consistency-output", forwarded)


if __name__ == "__main__":
    unittest.main()
