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
        doctor_file="",
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
        self.assertIn("diff_provenance", bundle["semantically_insufficient_sections"])
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
                "status": "PROVEN",
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
            ["diff_provenance", "verification_corroboration", "readback", "scenario_proof", "cleanup_status"],
            bundle["semantically_insufficient_sections"],
        )
        self.assertEqual(
            "prove the patch on the changed files with a patch-shaped git_diff or a structured diff_provenance record, or use a truthful already_satisfied observation record when no edit was required",
            bundle["semantic_next_safe_step"],
        )
        self.assertEqual("CLAIMED_NOT_ACCEPTED", verdict["closure_status"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])

    def test_structured_diff_provenance_and_artifact_identity_fallback_can_complete_bundle(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_structured_provenance_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now contains a Local signals only subtitle directly under the Watchlist heading.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: grep -n \"Local signals only\" warroom/templates/index.html\n"
                "Observed: line 24 shows the inserted subtitle paragraph under the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            args.baseline_identity = ""
            args.execution_surface_identity = ""
            args.prompt_identity = ""
            args.task_identity = ""
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertEqual([], bundle["semantically_insufficient_sections"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_doctor_cleanup_and_run_context_identity_can_complete_bundle_without_authored_duplication(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cleanup_fallback_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"
            doctor_file = tmp / "doctor.json"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now contains a Local signals only subtitle directly under the Watchlist heading.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: grep -n \"Local signals only\" warroom/templates/index.html\n"
                "Observed: line 24 shows the inserted subtitle paragraph under the Watchlist heading\n"
                "Status: PASSED\n"
            )
            doctor_file.write_text(json.dumps({
                "schema_version": "doctor_record_v0",
                "doctor_level": "CORE_DOCTOR",
                "gates": {
                    "clean_execution_surface": {
                        "status": "PASS",
                        "note": "execution surface is acceptable",
                    },
                },
                "final_verdict": "ACCEPTABLE_FOR_CORE_RUN",
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            args.doctor_file = str(doctor_file)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertEqual([], bundle["semantically_insufficient_sections"])
        self.assertFalse(bundle["artifact_identity"]["from_final_result"])
        self.assertTrue(bundle["cleanup_status"]["from_doctor"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_truthful_already_satisfied_noop_can_complete_bundle(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_already_satisfied_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "ALREADY_SATISFIED",
                "change_disposition": "already_satisfied",
                "summary": "Verified that the requested subtitle was already present on the attested surface before any edit, so no file change was required for this run.",
                "modified_files": [],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "observed_line": "                <p class=\"text-[10px] text-blue-500/80 uppercase font-bold tracking-wider mb-4\">Local signals only</p>",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-[10px] text-blue-500/80 uppercase font-bold tracking-wider mb-4\">Local signals only</p>",
                    "provenance_note": "Requested state was already present before edits, so this run attests the existing line truthfully instead of inventing a patch.",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace unchanged apart from proof artifacts; no unintended changes were introduced while attesting the already satisfied state.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: watchlist subtitle already satisfied\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template already contains the Local signals only subtitle directly under the Watchlist heading at line 24.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: watchlist subtitle already satisfied\n"
                "Scenario: local verification of the existing Watchlist subtitle on the homepage template\n"
                "Command: grep -n \"Local signals only\" warroom/templates/index.html\n"
                "Observed: line 24 already shows the subtitle paragraph directly below the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertEqual([], bundle["semantically_insufficient_sections"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_generic_success_status_is_semantically_blocked_even_with_good_evidence(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_final_result_status_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "SUCCESS",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now contains a Local signals only subtitle directly under the Watchlist heading.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: grep -n \"Local signals only\" warroom/templates/index.html\n"
                "Observed: line 24 shows the inserted subtitle paragraph under the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertEqual(["final_result_status"], bundle["semantically_insufficient_sections"])
        self.assertEqual(
            "state a trust-bearing final_result.status: use PROVEN for an evidenced modification run, or ALREADY_SATISFIED for a truthful no-op attestation",
            bundle["semantic_next_safe_step"],
        )
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])

    def test_missing_readback_is_waived_when_final_result_carries_strong_runtime_corroboration(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_runtime_corroborated_without_readback_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: grep -n \"Local signals only\" warroom/templates/index.html\n"
                "Observed: line 24 shows the inserted subtitle paragraph under the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(tmp / "missing_readback.txt")
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertNotIn("readback", bundle["missing_sections"])
        self.assertNotIn("readback", bundle["semantically_insufficient_sections"])
        self.assertTrue(bundle["readback"]["waived_by_runtime_corroboration"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_semantically_thin_readback_is_waived_when_final_result_carries_strong_runtime_corroboration(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_runtime_corroborated_with_brief_readback_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text("Observed: subtitle updated.\n")
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: grep -n \"Local signals only\" warroom/templates/index.html\n"
                "Observed: line 24 shows the inserted subtitle paragraph under the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertFalse(bundle["readback"]["content_semantically_sufficient"])
        self.assertTrue(bundle["readback"]["waived_by_runtime_corroboration"])
        self.assertNotIn("readback", bundle["semantically_insufficient_sections"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_semantically_sufficient_readback_is_still_marked_waived_when_runtime_corroboration_is_strong(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_runtime_corroborated_with_good_readback_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now contains a Local signals only subtitle directly under the Watchlist heading.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: grep -n \"Local signals only\" warroom/templates/index.html\n"
                "Observed: line 24 shows the inserted subtitle paragraph under the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertTrue(bundle["readback"]["content_semantically_sufficient"])
        self.assertTrue(bundle["readback"]["waived_by_runtime_corroboration"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_missing_scenario_proof_is_waived_when_final_result_carries_strong_runtime_corroboration(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_runtime_corroborated_without_scenario_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now contains a Local signals only subtitle directly under the Watchlist heading.\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(tmp / "missing_scenario.txt")
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertNotIn("scenario_proof", bundle["missing_sections"])
        self.assertNotIn("scenario_proof", bundle["semantically_insufficient_sections"])
        self.assertTrue(bundle["scenario_proof"]["waived_by_runtime_corroboration"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_semantically_thin_scenario_proof_is_waived_when_final_result_carries_strong_runtime_corroboration(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_runtime_corroborated_with_brief_scenario_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now contains a Local signals only subtitle directly under the Watchlist heading.\n"
            )
            scenario.write_text("Scenario passed.\n")

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertFalse(bundle["scenario_proof"]["content_semantically_sufficient"])
        self.assertTrue(bundle["scenario_proof"]["waived_by_runtime_corroboration"])
        self.assertNotIn("scenario_proof", bundle["semantically_insufficient_sections"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_semantically_sufficient_scenario_is_still_marked_waived_when_runtime_corroboration_is_strong(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_runtime_corroborated_with_good_scenario_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now contains a Local signals only subtitle directly under the Watchlist heading.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: grep -n \"Local signals only\" warroom/templates/index.html\n"
                "Observed: line 24 shows the inserted subtitle paragraph under the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertTrue(bundle["scenario_proof"]["content_semantically_sufficient"])
        self.assertTrue(bundle["scenario_proof"]["waived_by_runtime_corroboration"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_patch_plus_verification_marks_present_prose_surfaces_waived(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_patch_plus_verification_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["alpha.py"],
                "git_diff": (
                    "diff --git a/alpha.py b/alpha.py\n"
                    "--- a/alpha.py\n"
                    "+++ b/alpha.py\n"
                    "@@ -3,4 +3,5 @@\n"
                    " from __future__ import annotations\n"
                    " \n"
                    " def main() -> int:\n"
                    "+    \"\"\"Entry point for the Synrail CLI.\"\"\"\n"
                    "     from tools.reference.synrail_cli_v0 import main as cli_main\n"
                ),
                "diff_provenance": {
                    "changed_file": "alpha.py",
                    "verification_command": "grep -A 1 \"def main() -> int:\" alpha.py",
                    "verification_result": "def main() -> int:\n    \"\"\"Entry point for the Synrail CLI.\"\"\"",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "workspace clean after updating only alpha.py with no unintended changes",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add alpha docstring\n"
                "Changed surface: alpha.py\n"
                "Observed: the main function now contains a one-line docstring.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: add alpha docstring\n"
                "Scenario: verify the main function docstring in alpha.py\n"
                "Command: grep -A 1 \"def main() -> int:\" alpha.py\n"
                "Observed: the inserted docstring appears immediately below the function signature\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertTrue(bundle["verification_corroboration"]["has_patch_runtime_verification"])
        self.assertTrue(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertTrue(bundle["readback"]["content_semantically_sufficient"])
        # Scenario prose is now correctly recognized as thin (no command-output evidence in
        # Observed: line), but waiver still closes trust through runtime corroboration.
        self.assertFalse(bundle["scenario_proof"]["content_semantically_sufficient"])
        self.assertTrue(bundle["readback"]["waived_by_runtime_corroboration"])
        self.assertTrue(bundle["scenario_proof"]["waived_by_runtime_corroboration"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_missing_method_is_inferred_for_strong_direct_observation_record(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_infer_diff_method_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": "",
                "diff_provenance": {
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p class=\"text-sm text-gray-400 -mt-3 mb-4\">Local signals only</p>",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            args.readback = str(tmp / "missing_readback.txt")
            args.scenario_proof = str(tmp / "missing_scenario.txt")
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("direct_file_observation", bundle["diff_provenance"]["normalized_method"])
        self.assertTrue(bundle["diff_provenance"]["method_inferred"])
        self.assertTrue(bundle["verification_corroboration"]["has_structured_runtime_verification"])
        self.assertTrue(bundle["readback"]["waived_by_runtime_corroboration"])
        self.assertTrue(bundle["scenario_proof"]["waived_by_runtime_corroboration"])
        self.assertEqual([], bundle["missing_sections"])
        self.assertEqual([], bundle["semantically_insufficient_sections"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_already_satisfied_noop_rejects_invented_patch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_already_satisfied_fake_patch_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"

            final_result.write_text(json.dumps({
                "request_id": "RUN_001",
                "status": "ALREADY_SATISFIED",
                "change_disposition": "already_satisfied",
                "summary": "Claimed no-op, but also supplied a patch.",
                "modified_files": [],
                "git_diff": "diff --git a/warroom/templates/index.html b/warroom/templates/index.html\n--- a/warroom/templates/index.html\n+++ b/warroom/templates/index.html\n@@ -1,1 +1,2 @@\n+fake\n",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "observed_line": "                <p>Local signals only</p>",
                    "verification_command": "grep -n 'Local signals only' warroom/templates/index.html",
                    "verification_result": "24:                <p>Local signals only</p>",
                    "provenance_note": "This should fail because a no-op must not also claim a patch.",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace unchanged with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            bundle = build_bundle(args)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertIn("diff_provenance", bundle["semantically_insufficient_sections"])

    def test_additive_only_task_rejects_adjacent_scope_drift(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_scope_alignment_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "Added the requested subtitle but also tightened the adjacent heading margin.",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": (
                    "diff --git a/warroom/templates/index.html b/warroom/templates/index.html\n"
                    "--- a/warroom/templates/index.html\n"
                    "+++ b/warroom/templates/index.html\n"
                    "@@ -21,6 +21,7 @@\n"
                    "-                <h2 class=\"text-2xl font-semibold mb-4 flex items-center\">\n"
                    "+                <h2 class=\"text-2xl font-semibold mb-1 flex items-center\">\n"
                    "                 <span class=\"mr-2\">📊</span> Watchlist\n"
                    "                 </h2>\n"
                    "+                <p class=\"text-sm text-gray-400 mb-4\">Local signals only</p>\n"
                ),
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-sm text-gray-400 mb-4\">Local signals only</p>",
                    "removed_line": "                <h2 class=\"text-2xl font-semibold mb-4 flex items-center\">",
                    "context_before": "            <section class=\"bg-gray-800 p-6 rounded-lg shadow-xl\">",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "curl -s http://localhost:8000/ | grep -C 2 'Local signals only'",
                    "verification_result": "Local signals only rendered under Watchlist",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "add-watchlist-subtitle",
                    "task_identity": "Add Local signals only subtitle under Watchlist heading and do not change anything else",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now renders a Local signals only subtitle under the Watchlist heading.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: curl -s http://localhost:8000/ | grep -C 2 \"Local signals only\"\n"
                "Observed: the subtitle renders below the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            args.prompt_identity = "Add Local signals only subtitle under Watchlist heading"
            args.task_identity = "Add Local signals only subtitle under Watchlist heading and do not change anything else"
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertEqual(["scope_alignment"], bundle["semantically_insufficient_sections"])
        self.assertEqual(
            "keep the implementation inside the requested additive scope and remove unrelated adjacent rewrites or spacing tweaks",
            bundle["semantic_next_safe_step"],
        )
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])

    def test_additive_only_task_rejects_extra_emphasis_styling(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_presentation_alignment_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "Added the requested subtitle with extra emphasis styling.",
                "modified_files": ["warroom/templates/index.html"],
                "git_diff": (
                    "diff --git a/warroom/templates/index.html b/warroom/templates/index.html\n"
                    "--- a/warroom/templates/index.html\n"
                    "+++ b/warroom/templates/index.html\n"
                    "@@ -21,6 +21,7 @@\n"
                    "                 <h2 class=\"text-2xl font-semibold mb-4 flex items-center\">\n"
                    "                     <span class=\"mr-2\">📊</span> Watchlist\n"
                    "                 </h2>\n"
                    "+                <p class=\"text-xs text-gray-400 mb-4 italic opacity-75\">Local signals only</p>\n"
                ),
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "warroom/templates/index.html",
                    "added_line": "                <p class=\"text-xs text-gray-400 mb-4 italic opacity-75\">Local signals only</p>",
                    "context_before": "                </h2>",
                    "context_after": "                <form action=\"/add_token\" method=\"post\" class=\"mb-6 flex gap-2\">",
                    "verification_command": "curl -s http://localhost:8000/ | grep -C 2 'Local signals only'",
                    "verification_result": "<p class=\"text-xs text-gray-400 mb-4 italic opacity-75\">Local signals only</p>",
                    "provenance_note": "Subtitle rendered locally.",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "add-watchlist-subtitle",
                    "task_identity": "Add Local signals only subtitle under Watchlist heading and do not change anything else",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only warroom/templates/index.html with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "### READBACK: add watchlist subtitle\n"
                "Changed surface: warroom/templates/index.html\n"
                "Observed: the template now renders a Local signals only subtitle under the Watchlist heading.\n"
            )
            scenario.write_text(
                "### SCENARIO PROOF: add watchlist subtitle\n"
                "Scenario: local homepage render check for the Watchlist section\n"
                "Command: curl -s http://localhost:8000/ | grep -C 2 \"Local signals only\"\n"
                "Observed: the subtitle renders below the Watchlist heading\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            args.prompt_identity = "Add Local signals only subtitle under Watchlist heading"
            args.task_identity = "Add Local signals only subtitle under Watchlist heading and do not change anything else"
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertEqual(["presentation_alignment"], bundle["semantically_insufficient_sections"])
        self.assertEqual(
            "keep the newly added surface visually plain and close to the requested text-only intent; remove extra emphasis styling unless the task asked for it",
            bundle["semantic_next_safe_step"],
        )
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])


class TestAntiNarrativeGuards(unittest.TestCase):
    """Proof files must contain concrete evidence, not restatements of the task."""

    def test_readback_rejects_single_line(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        # Single line even with a file reference is too thin
        self.assertFalse(readback_is_semantically_sufficient(
            "core/router.py: confirmed it works correctly after the change.",
            ["core/router.py"],
        ))

    def test_readback_rejects_no_concrete_identifier(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        # Multiple lines but generic prose — no function/class/line/path identifiers
        self.assertFalse(readback_is_semantically_sufficient(
            "The change was implemented successfully.\nObserved that the feature now works as intended.\nEverything looks correct.",
            ["core/router.py"],
        ))

    def test_readback_rejects_parroting(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        # Proof that just restates task words with a file reference sprinkled in
        self.assertFalse(readback_is_semantically_sufficient(
            "core/router.py: cinematic zoom trigger handler confirmed for router animation effects module.\n"
            "Observed cinematic zoom trigger handler animation effects router module confirmed.",
            ["core/router.py"],
            task_identity="implement the cinematic zoom trigger handler for the core router module with animation effects",
        ))

    def test_readback_accepts_concrete_evidence(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            "core/router.py line 42: observed the function handle_zoom_request().\nIt imports cinematic_helper from core.effects module.\nConfirmed the route /api/zoom dispatches correctly.",
            ["core/router.py"],
            task_identity="add cinematic zoom trigger",
        ))

    def test_readback_rejects_action_narrative_observed(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        # Alpha run 005 pattern: "Observed: Implemented X" is action, not observation
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: api_service/retry_logic.py\n"
            "Observed: Implemented compute_retry_delay with exponential backoff and cap_seconds.\n"
            "Changed surface: tests/test_retry_logic.py\n"
            "Observed: Added tests for cap_seconds and execute_with_retry with mocked sleep.",
            ["api_service/retry_logic.py", "tests/test_retry_logic.py"],
        ))

    def test_readback_rejects_confirmed_action_narrative(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        # "Confirmed: Created the handler" is action, not confirmation
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/handler.py\n"
            "Confirmed: Created the new request handler with retry logic.\n"
            "Confirmed: Updated the test file to cover edge cases.",
            ["src/handler.py"],
        ))

    def test_readback_accepts_genuine_observation_after_label(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        # "Observed: compute_retry_delay returns 2.0" is a genuine observation
        self.assertTrue(readback_is_semantically_sufficient(
            "Changed surface: api_service/retry_logic.py\n"
            "Observed: compute_retry_delay returns 2.0 for attempt=1 with base=1.0.\n"
            "Observed: execute_with_retry calls sleep() 3 times before raising.",
            ["api_service/retry_logic.py"],
        ))

    def test_readback_accepts_mixed_lines_with_one_genuine(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        # One action-narrative line + one genuine observation → accepts
        self.assertTrue(readback_is_semantically_sufficient(
            "Changed surface: api_service/retry_logic.py\n"
            "Observed: Implemented compute_retry_delay with backoff.\n"
            "Observed: function compute_retry_delay returns float type at line 42.",
            ["api_service/retry_logic.py"],
        ))

    def test_scenario_rejects_two_line_generic(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        # Only 2 lines, no command
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: tested locally.\nStatus: PASSED",
        ))

    def test_scenario_rejects_no_specifics(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        # 3 lines but no concrete command/path/identifier
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: tested the feature end to end.\nObserved the expected behavior after the change.\nStatus: PASSED",
        ))

    def test_scenario_rejects_missing_command_label(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: retry delay on attempt 0\n"
            "python -m pytest tests/test_retry_logic.py::test_attempt_zero_delay -q\n"
            "Observed: test passed with delay 0.0\n"
            "Status: PASSED",
        ))

    def test_scenario_rejects_missing_observed_label(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: retry delay on attempt 0\n"
            "Command: python -m pytest tests/test_retry_logic.py::test_attempt_zero_delay -q\n"
            "delay 0.0 returned for attempt 0\n"
            "Status: PASSED",
        ))

    def test_scenario_rejects_parroting(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        # Proof that merely restates task words without concrete evidence
        self.assertFalse(scenario_is_semantically_sufficient(
            "cinematic zoom trigger handler for core router module animation effects confirmed\n"
            "cinematic zoom trigger handler core router animation effects verified\n"
            "cinematic zoom trigger handler animation effects working",
            task_identity="implement the cinematic zoom trigger handler for the core router module with animation effects",
        ))

    def test_scenario_accepts_concrete_evidence(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertTrue(scenario_is_semantically_sufficient(
            "Scenario: cinematic zoom on core/router.py\nCommand: python -m pytest tests/test_router.py::test_zoom -v\nObserved: test_zoom PASSED, handler returns /api/zoom\nStatus: PASSED",
            task_identity="add cinematic zoom trigger",
        ))

    def test_verification_corroboration_requires_structured_or_labeled_scenario(self) -> None:
        from synrail_bundle_v0 import verification_corroboration_is_semantically_sufficient
        self.assertFalse(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=False,
            scenario_text=(
                "Scenario: retry delay on attempt 0\n"
                "python -m pytest tests/test_retry_logic.py::test_attempt_zero_delay -q\n"
                "delay 0.0 returned for attempt 0\n"
                "Status: PASSED"
            ),
        ))
        self.assertTrue(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=False,
            scenario_text=(
                "Scenario: retry delay on attempt 0\n"
                "Command: python -m pytest tests/test_retry_logic.py::test_attempt_zero_delay -q\n"
                "Observed: line 1 shows 'delay 0.0 returned for attempt 0'\n"
                "Status: PASSED"
            ),
        ))

    def test_verification_corroboration_rejects_labeled_action_narrative(self) -> None:
        from synrail_bundle_v0 import verification_corroboration_is_semantically_sufficient
        self.assertFalse(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=False,
            scenario_text=(
                "Scenario: verify import\n"
                "Command: grep -n logging src/app.py\n"
                "Observed: I added the import to line 2\n"
                "Status: PASSED"
            ),
            task_identity="add logging import to src/app.py",
            task_class="bounded_change",
        ))

    def test_verification_corroboration_rejects_labeled_restatement_without_evidence(self) -> None:
        from synrail_bundle_v0 import verification_corroboration_is_semantically_sufficient
        self.assertFalse(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=False,
            scenario_text=(
                "Scenario: verify import\n"
                "Command: grep -n logging src/app.py\n"
                "Observed: logging import added to src/app.py\n"
                "Result: logging import is in src/app.py\n"
                "Status: PASSED"
            ),
            task_identity="add logging import to src/app.py",
            task_class="bounded_change",
        ))

    def test_verification_corroboration_runtime_path_remains_primary(self) -> None:
        from synrail_bundle_v0 import verification_corroboration_is_semantically_sufficient
        self.assertTrue(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=True,
            scenario_text=(
                "Scenario: verify import\n"
                "Command: grep -n logging src/app.py\n"
                "Observed: I added the import to line 2\n"
                "Status: PASSED"
            ),
            task_identity="add logging import to src/app.py",
            task_class="bounded_change",
        ))

    def test_verification_corroboration_rejects_command_confirms_without_output(self) -> None:
        from synrail_bundle_v0 import verification_corroboration_is_semantically_sufficient
        self.assertFalse(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=False,
            scenario_text=(
                "Scenario: verify import\n"
                "Command: grep -n logging src/app.py\n"
                "Observed: grep confirms logging import in src/app.py\n"
                "Status: PASSED"
            ),
            task_identity="add logging import to src/app.py",
            task_class="bounded_change",
        ))

    def test_verification_corroboration_rejects_output_found_without_literal_output(self) -> None:
        from synrail_bundle_v0 import verification_corroboration_is_semantically_sufficient
        self.assertFalse(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=False,
            scenario_text=(
                "Scenario: verify import\n"
                "Command: grep -n logging src/app.py\n"
                "Output: logging import found in src/app.py\n"
                "Status: PASSED"
            ),
            task_identity="add logging import to src/app.py",
            task_class="bounded_change",
        ))

    def test_verification_corroboration_rejects_output_ok_without_command_evidence(self) -> None:
        from synrail_bundle_v0 import verification_corroboration_is_semantically_sufficient
        self.assertFalse(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=False,
            scenario_text=(
                "Scenario: verify import\n"
                "Command: grep -n logging src/app.py\n"
                "Output: ok\n"
                "Status: PASSED"
            ),
            task_identity="add logging import to src/app.py",
            task_class="bounded_change",
        ))

    def test_verification_corroboration_rejects_exit_code_only_observation(self) -> None:
        from synrail_bundle_v0 import verification_corroboration_is_semantically_sufficient
        self.assertFalse(verification_corroboration_is_semantically_sufficient(
            runtime_verification_sufficient=False,
            scenario_text=(
                "Scenario: verify import\n"
                "Command: grep -n logging src/app.py\n"
                "Observed: exit code 0 for grep on src/app.py\n"
                "Status: PASSED"
            ),
            task_identity="add logging import to src/app.py",
            task_class="bounded_change",
        ))

    def test_parroting_detector_catches_high_overlap(self) -> None:
        from synrail_bundle_v0 import _is_parroting_task
        self.assertTrue(_is_parroting_task(
            "Added the cinematic zoom trigger to the router handler for the bot",
            "add cinematic zoom trigger to the router handler",
        ))

    def test_parroting_detector_allows_genuine_evidence(self) -> None:
        from synrail_bundle_v0 import _is_parroting_task
        self.assertFalse(_is_parroting_task(
            "core/router.py line 42 imports cinematic_helper from core.effects module",
            "add cinematic zoom trigger to the router handler",
        ))

    def test_concrete_identifier_detects_file_path(self) -> None:
        from synrail_bundle_v0 import _has_concrete_identifier
        self.assertTrue(_has_concrete_identifier("Changed file: src/components/App.tsx"))

    def test_concrete_identifier_detects_snake_case(self) -> None:
        from synrail_bundle_v0 import _has_concrete_identifier
        self.assertTrue(_has_concrete_identifier("The function handle_zoom_request was updated"))

    def test_concrete_identifier_detects_camel_case(self) -> None:
        from synrail_bundle_v0 import _has_concrete_identifier
        self.assertTrue(_has_concrete_identifier("Updated handleZoomRequest in the router"))

    def test_concrete_identifier_rejects_plain_prose(self) -> None:
        from synrail_bundle_v0 import _has_concrete_identifier
        self.assertFalse(_has_concrete_identifier("The feature was added and works correctly"))


class TestHostileProofIndependence(unittest.TestCase):
    """Hostile inputs that should be rejected by semantic proof checks (P2 hardening)."""

    FILES = ["src/app.py"]
    TASK = "add logging import to src/app.py"

    def test_readback_rejects_thin_generic_observation(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Readback: src/app.py\n"
            "Observed: the file was updated correctly and everything looks good now.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_first_person_action_narrative(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: I implemented the logging import at the top of the file and confirmed it compiles.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_passive_voice_action_narrative(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Readback: src/app.py\n"
            "Observed: the logging import was added successfully to the application file.\n"
            "Function: run()",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_vacuous_confirmed(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\nConfirmed: change applied.\nLine 2 updated.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_long_vacuous_observation(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Readback evidence for src/app.py:\n"
            "The modification has been applied to the target file as described in the task.\n"
            "Observed: the requested change is now present in the source code.\n"
            "The implementation follows the expected pattern.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_accepts_concrete_observation(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: src/app.py\n'
            'Observed: line 2 now reads "import logging" immediately after the existing os import.',
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_accepts_evidence_with_harmless_generic_tail(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: src/app.py\n'
            'Observed: line 2 now reads "import logging" as requested.',
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_accepts_evidence_with_generic_quality_tail(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: src/app.py\n'
            'Observed: line 2 now reads "import logging" and works correctly.',
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_accepts_evidence_even_if_confirmation_line_is_generic(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: src/app.py\n'
            'Observed: line 2 now reads "import logging". Confirmed: change applied.',
            self.FILES, task_identity=self.TASK,
        ))

    def test_observation_guard_profile_is_strict_only_on_measured_task_classes(self) -> None:
        from synrail_bundle_v0 import observation_guard_profile
        self.assertEqual("STRICT_RUNTIME_EVIDENCE", observation_guard_profile("bounded_change"))
        self.assertEqual("STRICT_RUNTIME_EVIDENCE", observation_guard_profile("proof_sensitive_fix"))
        self.assertEqual("BASELINE_OBSERVATION", observation_guard_profile("orientation_probe"))

    def test_readback_hostile_guard_is_scoped_not_global(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: logging import added to src/app.py.",
            self.FILES,
            task_identity=self.TASK,
            task_class="orientation_probe",
        ))

    def test_scenario_rejects_action_narrative_in_observed(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: check import\n"
            "Command: grep import src/app.py\n"
            "Observed: I added the import to line 2\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_hostile_guard_is_scoped_not_global(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertTrue(scenario_is_semantically_sufficient(
            "Scenario: check import in src/app.py\n"
            "Command: grep logging src/app.py\n"
            "Observed: logging import added to src/app.py\n"
            "Status: PASSED",
            task_identity=self.TASK,
            task_class="orientation_probe",
        ))

    def test_scenario_rejects_restatement_without_evidence(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: add logging import to src/app.py\n"
            "Command: grep logging src/app.py\n"
            "Observed: logging import added to src/app.py\n"
            "Result: logging import is in src/app.py\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_accepts_concrete_command_output(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertTrue(scenario_is_semantically_sufficient(
            "Scenario: verify logging import in src/app.py\n"
            'Command: grep -n "import logging" src/app.py\n'
            'Observed: line 2 shows "import logging"\n'
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_accepts_line_number_output(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertTrue(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: 2:import logging\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_command_confirms_without_literal_output(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: grep confirms logging import in src/app.py\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_output_found_without_literal_output(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Output: logging import found in src/app.py\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_output_ok_without_command_evidence(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Output: ok\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_exit_code_only_observation(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: exit code 0 for grep on src/app.py\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))


class TestCleanupRuntimeWaiver(unittest.TestCase):
    """Cleanup_status is waivable when runtime corroboration + doctor fallback already close trust."""

    def _strong_final_result(self, *, state: dict, include_cleanup: bool = False) -> dict:
        """Build a final_result with strong runtime verification fields."""
        payload: dict = {
            "request_id": state["run_id"],
            "status": "PROVEN",
            "modified_files": ["src/app.py"],
            "git_diff": (
                "diff --git a/src/app.py b/src/app.py\n"
                "--- a/src/app.py\n"
                "+++ b/src/app.py\n"
                "@@ -1,3 +1,4 @@\n"
                " import os\n"
                "+import logging\n"
                " \n"
                " def run():\n"
            ),
            "diff_provenance": {
                "method": "direct_file_observation",
                "changed_file": "src/app.py",
                "added_line": "import logging",
                "context_before": "import os",
                "context_after": "",
                "verification_command": "grep -n 'import logging' src/app.py",
                "verification_result": "2:import logging",
            },
            "artifact_identity": {
                "baseline_identity": "trusted_clean",
                "execution_surface_identity": "clean-clone",
                "prompt_identity": "prompt-001",
                "task_identity": "task-001",
            },
        }
        if include_cleanup:
            payload["cleanup_status"] = {
                "success": True,
                "summary": "Workspace clean after updating only src/app.py with no unintended changes.",
            }
        return payload

    def _doctor_record_clean(self) -> dict:
        """Build a minimal doctor record that matches the runtime doctor shape."""
        return {
            "final_verdict": "ACCEPTABLE_READY",
            "gate_results": {
                "clean_execution_surface": {
                    "status": "PASS",
                    "note": "workspace is clean, no stray files detected",
                },
            },
        }

    def test_cleanup_waived_when_runtime_and_doctor_close_trust(self) -> None:
        """No explicit cleanup_status in final_result, but doctor + runtime waive it → COMPLETE."""
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_cleanup_waiver_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            doctor_file = tmp / "doctor.json"

            final_result.write_text(json.dumps(
                self._strong_final_result(state=state, include_cleanup=False),
                indent=2, ensure_ascii=True,
            ) + "\n")
            doctor_file.write_text(json.dumps(
                self._doctor_record_clean(), indent=2, ensure_ascii=True,
            ) + "\n")

            args = bundle_args(final_result=final_result)
            args.doctor_file = str(doctor_file)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertTrue(bundle["cleanup_status"]["waived_by_runtime_corroboration"])
        self.assertTrue(bundle["cleanup_status"]["structurally_complete"])
        self.assertTrue(bundle["cleanup_status"]["semantically_sufficient"])
        self.assertTrue(bundle["cleanup_status"]["from_doctor"])
        self.assertNotIn("cleanup_status", bundle["missing_sections"])
        self.assertNotIn("cleanup_status", bundle["semantically_insufficient_sections"])
        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_cleanup_not_waived_without_doctor_fallback(self) -> None:
        """Strong runtime but no doctor → cleanup_status missing → not COMPLETE."""
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_cleanup_no_doctor_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"

            final_result.write_text(json.dumps(
                self._strong_final_result(state=state, include_cleanup=False),
                indent=2, ensure_ascii=True,
            ) + "\n")

            args = bundle_args(final_result=final_result)
            bundle = build_bundle(args)

        self.assertFalse(bundle["cleanup_status"]["waived_by_runtime_corroboration"])
        self.assertFalse(bundle["cleanup_status"]["structurally_complete"])
        self.assertIn("cleanup_status", bundle["missing_sections"])
        self.assertIn("PARTIAL", [bundle["status"], bundle["structural_status"]])

    def test_cleanup_not_waived_without_runtime_verification(self) -> None:
        """Doctor present but runtime corroboration missing → cleanup not waived."""
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_cleanup_no_runtime_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            doctor_file = tmp / "doctor.json"

            weak_final = {
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["src/app.py"],
                "git_diff": "",
                "diff_provenance": {
                    "changed_file": "src/app.py",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
            }
            final_result.write_text(json.dumps(weak_final, indent=2, ensure_ascii=True) + "\n")
            doctor_file.write_text(json.dumps(
                self._doctor_record_clean(), indent=2, ensure_ascii=True,
            ) + "\n")

            args = bundle_args(final_result=final_result)
            args.doctor_file = str(doctor_file)
            bundle = build_bundle(args)

        self.assertFalse(bundle["cleanup_status"]["waived_by_runtime_corroboration"])
        self.assertTrue(bundle["cleanup_status"]["from_doctor"])
        # Doctor fallback makes cleanup present but does NOT waive via runtime path
        self.assertTrue(bundle["cleanup_status"]["present"])

    def test_explicit_cleanup_takes_precedence_over_waiver(self) -> None:
        """When final_result has explicit cleanup_status, it is used directly (no waiver needed)."""
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_cleanup_explicit_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            doctor_file = tmp / "doctor.json"

            final_result.write_text(json.dumps(
                self._strong_final_result(state=state, include_cleanup=True),
                indent=2, ensure_ascii=True,
            ) + "\n")
            doctor_file.write_text(json.dumps(
                self._doctor_record_clean(), indent=2, ensure_ascii=True,
            ) + "\n")

            args = bundle_args(final_result=final_result)
            args.doctor_file = str(doctor_file)
            bundle = build_bundle(args)

        verdict = build_verdict(copy.deepcopy(state), bundle)

        self.assertTrue(bundle["cleanup_status"]["content_semantically_sufficient"])
        self.assertFalse(bundle["cleanup_status"]["from_doctor"])
        self.assertTrue(bundle["cleanup_status"]["semantically_sufficient"])
        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_cleanup_waiver_semantic_trace_message(self) -> None:
        """When cleanup is waived, the semantic trace explains the waiver reason."""
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_cleanup_trace_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            doctor_file = tmp / "doctor.json"

            final_result.write_text(json.dumps(
                self._strong_final_result(state=state, include_cleanup=False),
                indent=2, ensure_ascii=True,
            ) + "\n")
            doctor_file.write_text(json.dumps(
                self._doctor_record_clean(), indent=2, ensure_ascii=True,
            ) + "\n")

            args = bundle_args(final_result=final_result)
            args.doctor_file = str(doctor_file)
            bundle = build_bundle(args)

        cleanup_trace = [
            e for e in bundle["semantic_decision_trace"]
            if e["section"] == "cleanup_status"
        ]
        self.assertEqual(1, len(cleanup_trace))
        self.assertIn("waived", cleanup_trace[0]["why"])
        self.assertIn("runtime verification", cleanup_trace[0]["why"])


if __name__ == "__main__":
    unittest.main()
