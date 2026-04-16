#!/usr/bin/env python3
"""Regression harness for Synrail truth-critical failures."""

from __future__ import annotations

import argparse
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"
FIXTURES_ROOT = REPO_ROOT / "fixtures"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_acceptance_criteria_v0 import build_record as build_acceptance_criteria
from synrail_acceptance_criteria_v0 import validate_record as validate_acceptance_criteria
from synrail_bundle_v0 import build_bundle
from synrail_checkpoint_v0 import restore_record, verify_record
from synrail_closure_v0 import build_verdict
from synrail_continuation_arbiter_v0 import build_record as build_continuation_arbiter
from synrail_doctor_v1 import build_record as build_doctor_record
from synrail_second_operator_v0 import build_record as build_second_operator


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def controlled_state(state: dict) -> dict:
    payload = copy.deepcopy(state)
    integrity = dict(payload.get("integrity", {}))
    integrity["bootstrap_provenance_ok"] = True
    integrity["bootstrap_provenance_reason"] = "CONTROLLED_BOOTSTRAP_CONFIRMED"
    if "status" not in integrity:
        integrity["status"] = "PASS" if integrity.get("exact_task_identity_ok") else "FAIL"
    payload["integrity"] = integrity
    return payload


def bundle_args(*, final_result: Path) -> argparse.Namespace:
    return argparse.Namespace(
        final_result=str(final_result),
        task_class="proof_sensitive_fix",
        run_id="",
        readback=str(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "readback.txt"),
        scenario_proof=str(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "scenario.txt"),
        baseline_identity="trusted_clean",
        execution_surface_identity="clean-clone",
        prompt_identity="prompt-001",
        task_identity="task-001",
        output="",
    )


def doctor_args(*, corpus_file: Path, target_path: Path, artifact_path: Path) -> argparse.Namespace:
    return argparse.Namespace(
        doctor_run_id="REGRESSION_DOCTOR_001",
        doctor_level="CORE_DOCTOR",
        target_path=str(target_path),
        target_classification="core_surface",
        baseline_identity="TRUSTED_BASELINE_001",
        intended_run_class="core_probe",
        output="",
        state_file=None,
        update_state=False,
        clean_surface=True,
        artifact_viable=True,
        helper_ok=False,
        credentials_ok=False,
        prompt_identity_ok=False,
        artifact_path=str(artifact_path),
        helper_path="",
        credential_env=[],
        prompt_identity_file="",
        expected_task_identity="",
        target_identity_file="",
        expected_target_identity="",
        changed_file=[],
        allowed_scope_path=[],
        coverage_profile_file=None,
        coverage_corpus_file=str(corpus_file),
    )


class TruthRegressionTests(unittest.TestCase):
    def test_false_reject_valid_contour_stays_accepted(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = build_bundle(
            bundle_args(final_result=FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "final_result_valid.json")
        )
        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertTrue(bundle["structural_decision_trace"])
        self.assertTrue(bundle["semantic_decision_trace"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])
        self.assertEqual("", verdict["blocking_reason"])

    def test_false_accept_stale_acceptance_criteria_block_closure(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "bundle_valid.json")
        profile = {
            "schema_version": "project_profile_v0",
            "project_root": str(REPO_ROOT),
            "project_type": "generic",
            "task_class": state["task_class"],
            "target_path": str(REPO_ROOT),
            "target_classification": "attested_target_surface",
            "intended_run_class": "core_probe",
            "baseline_identity": "trusted_clean",
            "execution_surface_identity": "clean-clone",
            "artifact_path": "artifacts/final_result.json",
        }
        criteria = build_acceptance_criteria(profile, generated_by="truth-regression-suite")
        stale_profile = dict(profile)
        stale_profile["target_classification"] = "moved_target_surface"

        validation = validate_acceptance_criteria(criteria, state=state, profile=stale_profile)
        verdict = build_verdict(copy.deepcopy(state), bundle, validation)

        self.assertEqual("STALE", validation["status"])
        self.assertEqual("CRITERIA_TARGET_CLASSIFICATION_STALE", validation["reason"])
        self.assertEqual("ACCEPTANCE_CRITERIA_STALE", verdict["blocking_reason"])
        self.assertEqual("ACCEPTANCE_CRITERIA_REFRESH", verdict["next_allowed_transition"])

    def test_degraded_after_accepted_requires_reverification(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "bundle_valid.json")
        degraded = copy.deepcopy(state)
        degraded["recovery"]["status"] = "PENDING"
        degraded["recovery"]["reverification_complete"] = False

        verdict = build_verdict(degraded, bundle)

        self.assertEqual("CLAIMED_NOT_ACCEPTED", verdict["closure_status"])
        self.assertEqual("RECOVERY_REVERIFICATION_INCOMPLETE", verdict["blocking_reason"])
        self.assertEqual("RECOVERY_REVERIFICATION", verdict["next_allowed_transition"])

    def test_repair_no_progress_boundary_prevents_resume(self) -> None:
        state = load_json(FIXTURES_ROOT / "repair_convergence_run_005" / "state.json")
        packet = load_json(FIXTURES_ROOT / "repair_convergence_run_005" / "final_repair_packet.json")
        receipt = load_json(FIXTURES_ROOT / "repair_convergence_run_005" / "stage2_repair_receipt.json")

        arbiter = build_continuation_arbiter(state=state, packet=packet, repair_receipt=receipt)
        resolved = arbiter["resolved_decision"]

        self.assertEqual("RESOLVED", arbiter["resolution_status"])
        self.assertEqual("TERMINATE", resolved["termination_status"])
        self.assertEqual("NO_PROGRESS_DETECTED", resolved["termination_reason"])
        self.assertFalse(resolved["ready_for_resume"])
        self.assertEqual("restore_readiness_truth", resolved["current_step_id"])

    def test_checkpoint_restore_integrity_roundtrip(self) -> None:
        record = load_json(FIXTURES_ROOT / "checkpoint_scope_violation_run_001" / "checkpoint_verify.json")
        source_checkpoint_root = (REPO_ROOT / record["checkpoint_root"]).resolve()

        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_restore_") as tmpdir:
            target_root = Path(tmpdir)
            checkpoint_root = target_root / "checkpoint"
            shutil.copytree(source_checkpoint_root, checkpoint_root)
            state_path = checkpoint_root / "artifacts" / "state.json"
            state_path.write_text(json.dumps(controlled_state(load_json(state_path)), indent=2, ensure_ascii=True) + "\n")
            record["checkpoint_root"] = str(checkpoint_root)
            restored = restore_record(copy.deepcopy(record), target_root)
            restored_state = load_json(target_root / "artifacts" / "state.json")
            post_verify = verify_record(record, root_override=target_root)

        self.assertEqual("OK", restored["result"])
        self.assertEqual("RESTORED", restored["restore"]["status"])
        self.assertEqual(record["run_id"], restored_state["run_id"])
        self.assertEqual(record["task_class"], restored_state["task_class"])
        self.assertEqual("OK", post_verify["result"])
        self.assertEqual("PASSED", post_verify["verification"]["status"])

    def test_packet_state_conflict_requires_author_intuition(self) -> None:
        state = load_json(FIXTURES_ROOT / "continuation_arbiter_conflict_run_001" / "state.json")
        packet = load_json(FIXTURES_ROOT / "continuation_arbiter_conflict_run_001" / "repair_packet.json")
        packet.pop("continuation_arbiter", None)
        run_artifact = load_json(FIXTURES_ROOT / "continuation_arbiter_conflict_run_001" / "run.json")

        arbiter = build_continuation_arbiter(state=state, packet=packet, repair_receipt=packet.get("repair_receipt"))
        second_operator = build_second_operator(state=state, packet=packet, run_artifact=run_artifact)

        self.assertEqual("CONFLICT_UNRESOLVED", arbiter["resolution_status"])
        self.assertIn("current_step_id", arbiter["unresolved_surfaces"])
        self.assertEqual("AUTHOR_INTUITION_STILL_REQUIRED", second_operator["verdict"])
        self.assertTrue(second_operator["requires_author_intuition"])

    def test_doctor_false_ready_boundary_is_blocked(self) -> None:
        corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
        corpus["cases"] = [
            case
            for case in corpus["cases"]
            if case.get("fail_mode_id") != "helper_entrypoint_missing"
        ]

        with tempfile.TemporaryDirectory(prefix="synrail_doctor_regression_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "weakened_corpus.json"
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            record = build_doctor_record(
                doctor_args(
                    corpus_file=corpus_path,
                    target_path=target_root,
                    artifact_path=artifact_path,
                )
            )

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertTrue(record["coverage"]["decision_trace"])
        self.assertEqual(
            "CRITICAL_FAIL_MODE_MEASURED_COVERAGE_MISSING_EVIDENCE",
            record["coverage"]["gate_reason"],
        )
        self.assertIn(
            "helper_entrypoint_missing",
            record["coverage"]["critical_modes_without_measured_evidence"],
        )

    def test_doctor_identity_silent_pass_is_now_blocked(self) -> None:
        """Expected target identity specified but no target_identity_file → must FAIL."""
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_identity_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.expected_target_identity = "EXPECTED_SURFACE_001"
            args.target_identity_file = ""

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_BASELINE_IDENTITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["baseline_identity"]["status"])
        self.assertIn("expected target identity specified", record["gate_results"]["baseline_identity"]["note"])

    def test_doctor_identity_matching_passes(self) -> None:
        """Expected target identity + matching file → must PASS the identity gate."""
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_identity_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            identity_file = tmp / "target_identity.txt"
            identity_file.write_text("EXPECTED_SURFACE_001\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.expected_target_identity = "EXPECTED_SURFACE_001"
            args.target_identity_file = str(identity_file)

            record = build_doctor_record(args)

        self.assertEqual("PASS", record["gate_results"]["baseline_identity"]["status"])
        self.assertIn("matches expectation", record["gate_results"]["baseline_identity"]["note"])

    def test_doctor_identity_mismatch_fails(self) -> None:
        """Expected target identity + non-matching file → must FAIL."""
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_identity_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            identity_file = tmp / "target_identity.txt"
            identity_file.write_text("WRONG_SURFACE_999\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.expected_target_identity = "EXPECTED_SURFACE_001"
            args.target_identity_file = str(identity_file)

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_BASELINE_IDENTITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["baseline_identity"]["status"])
        self.assertIn("does not match", record["gate_results"]["baseline_identity"]["note"])

    def test_closure_blocks_on_semantically_thin_proof(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_semantic_thin.json"))
        bundle = build_bundle(
            bundle_args(
                final_result=FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "final_result_semantic_thin.json"
            )
        )
        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertEqual(["diff_provenance"], bundle["semantically_insufficient_sections"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])
        self.assertEqual("PROOF_BUNDLE_STRENGTHENING", verdict["next_allowed_transition"])

    def test_narrative_proof_bundle_is_semantically_blocked(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_narrative_proof_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "success",
                "modified_files": ["core/router.py", "tools/cinematic.py"],
                "git_diff": "--- a/core/router.py\n+++ b/core/router.py\n+from tools.cinematic import generate_cinematic_zoom\n",
                "cleanup_status": {
                    "success": True,
                    "summary": "Bot restarted on Node 2 with new feature enabled.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "Implemented the cinematic zoom flow and wired it into the router for the new feature.\n"
            )
            scenario.write_text(
                "Scenario passed and the bot should now handle zoom requests after restart.\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertEqual(
            ["diff_provenance", "readback", "scenario_proof", "cleanup_status"],
            bundle["semantically_insufficient_sections"],
        )
        self.assertEqual(
            "capture non-empty diff or provenance evidence for the changed files",
            bundle["semantic_next_safe_step"],
        )
        self.assertEqual("CLAIMED_NOT_ACCEPTED", verdict["closure_status"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])


if __name__ == "__main__":
    unittest.main()
