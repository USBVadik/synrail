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
                "status": "success",
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

    def test_truthful_already_satisfied_noop_can_complete_bundle(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_already_satisfied_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "success",
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

    def test_already_satisfied_noop_rejects_invented_patch(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_already_satisfied_fake_patch_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"

            final_result.write_text(json.dumps({
                "request_id": "RUN_001",
                "status": "success",
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
                "status": "success",
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
                "status": "success",
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


if __name__ == "__main__":
    unittest.main()
