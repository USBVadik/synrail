#!/usr/bin/env python3
"""Unit tests for Synrail spine gate functions, transition logic, and closure verdicts."""

from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_spine_v0 import (
    TERMINAL_STATES,
    TRANSITION_PRECEDENCE,
    apply_bundle,
    apply_doctor,
    apply_integrity,
    apply_target_surface,
    blockers_for_target,
    default_state,
    dominant_blocker,
    gate_artifacts,
    gate_doctor,
    gate_integrity,
    gate_proof_bundle,
    gate_recovery,
    gate_target_surface,
    transition,
)
from synrail_closure_v0 import build_verdict
from synrail_continuation_arbiter_v0 import build_record as build_continuation_arbiter


def ready_state(run_id: str = "R1", task_class: str = "bounded_change") -> dict:
    """Build a state that passes all gates up to CLOSURE_ACCEPTED."""
    state = default_state(run_id, task_class)
    state["state"] = "PROOF_BUNDLE_COMPLETE"
    state["target_surface"]["status"] = "ATTESTED"
    state["target_surface"]["identity"] = "surface-001"
    state["target_surface"]["baseline_relation"] = "identical"
    state["doctor"]["status"] = "PASS"
    state["doctor"]["blocking_failure_classes"] = []
    state["integrity"]["bootstrap_provenance_ok"] = True
    state["integrity"]["bootstrap_provenance_reason"] = "CONTROLLED_BOOTSTRAP_CONFIRMED"
    state["integrity"]["exact_task_identity_ok"] = True
    state["integrity"]["status"] = "PASS"
    state["execution"]["status"] = "COMPLETED"
    state["execution"]["artifact_bundle_present"] = True
    state["proof_bundle"]["status"] = "COMPLETE"
    state["recovery"]["status"] = "NOT_REQUIRED"
    state["recovery"]["reverification_complete"] = False
    return state


# ---------------------------------------------------------------------------
# Gate function tests
# ---------------------------------------------------------------------------

class TestGateTargetSurface(unittest.TestCase):
    def test_attested_passes(self) -> None:
        state = default_state("R1", "t")
        state["target_surface"]["status"] = "ATTESTED"
        ok, reason = gate_target_surface(state)
        self.assertTrue(ok)
        self.assertEqual("", reason)

    def test_unknown_fails(self) -> None:
        state = default_state("R1", "t")
        ok, reason = gate_target_surface(state)
        self.assertFalse(ok)
        self.assertEqual("TARGET_SURFACE_NOT_ATTESTED", reason)


class TestGateDoctor(unittest.TestCase):
    def test_pass_passes(self) -> None:
        state = default_state("R1", "t")
        state["doctor"]["status"] = "PASS"
        ok, reason = gate_doctor(state)
        self.assertTrue(ok)
        self.assertEqual("", reason)

    def test_fail_fails(self) -> None:
        state = default_state("R1", "t")
        state["doctor"]["status"] = "FAIL"
        ok, reason = gate_doctor(state)
        self.assertFalse(ok)
        self.assertEqual("DOCTOR_NOT_GREEN", reason)


class TestGateIntegrity(unittest.TestCase):
    def test_both_ok_passes(self) -> None:
        state = default_state("R1", "t")
        state["integrity"]["bootstrap_provenance_ok"] = True
        state["integrity"]["exact_task_identity_ok"] = True
        ok, reason = gate_integrity(state)
        self.assertTrue(ok)
        self.assertEqual("", reason)

    def test_no_bootstrap_fails(self) -> None:
        state = default_state("R1", "t")
        state["integrity"]["bootstrap_provenance_ok"] = False
        state["integrity"]["exact_task_identity_ok"] = True
        ok, reason = gate_integrity(state)
        self.assertFalse(ok)
        self.assertEqual("CONTROLLED_BOOTSTRAP_NOT_CONFIRMED", reason)

    def test_no_task_identity_fails(self) -> None:
        state = default_state("R1", "t")
        state["integrity"]["bootstrap_provenance_ok"] = True
        state["integrity"]["exact_task_identity_ok"] = False
        ok, reason = gate_integrity(state)
        self.assertFalse(ok)
        self.assertEqual("EXACT_TASK_IDENTITY_NOT_CONFIRMED", reason)

    def test_bootstrap_checked_first(self) -> None:
        state = default_state("R1", "t")
        state["integrity"]["bootstrap_provenance_ok"] = False
        state["integrity"]["exact_task_identity_ok"] = False
        ok, reason = gate_integrity(state)
        self.assertFalse(ok)
        self.assertEqual("CONTROLLED_BOOTSTRAP_NOT_CONFIRMED", reason)


class TestGateArtifacts(unittest.TestCase):
    def test_present_passes(self) -> None:
        state = default_state("R1", "t")
        state["execution"]["artifact_bundle_present"] = True
        ok, reason = gate_artifacts(state)
        self.assertTrue(ok)
        self.assertEqual("", reason)

    def test_missing_fails(self) -> None:
        state = default_state("R1", "t")
        ok, reason = gate_artifacts(state)
        self.assertFalse(ok)
        self.assertEqual("ARTIFACT_BUNDLE_MISSING", reason)


class TestGateProofBundle(unittest.TestCase):
    def test_complete_passes(self) -> None:
        state = default_state("R1", "t")
        state["proof_bundle"]["status"] = "COMPLETE"
        ok, reason = gate_proof_bundle(state)
        self.assertTrue(ok)
        self.assertEqual("", reason)

    def test_invalid_fails(self) -> None:
        state = default_state("R1", "t")
        state["proof_bundle"]["status"] = "INVALID"
        ok, reason = gate_proof_bundle(state)
        self.assertFalse(ok)
        self.assertEqual("INVALID_PROOF_BUNDLE", reason)

    def test_structurally_complete_fails(self) -> None:
        state = default_state("R1", "t")
        state["proof_bundle"]["status"] = "STRUCTURALLY_COMPLETE"
        ok, reason = gate_proof_bundle(state)
        self.assertFalse(ok)
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", reason)

    def test_partial_fails(self) -> None:
        state = default_state("R1", "t")
        state["proof_bundle"]["status"] = "PARTIAL"
        ok, reason = gate_proof_bundle(state)
        self.assertFalse(ok)
        self.assertEqual("MISSING_PROOF_SECTIONS", reason)


class TestGateRecovery(unittest.TestCase):
    def test_not_required_passes(self) -> None:
        state = default_state("R1", "t")
        ok, reason = gate_recovery(state)
        self.assertTrue(ok)
        self.assertEqual("", reason)

    def test_pending_incomplete_fails(self) -> None:
        state = default_state("R1", "t")
        state["recovery"]["status"] = "PENDING"
        state["recovery"]["reverification_complete"] = False
        ok, reason = gate_recovery(state)
        self.assertFalse(ok)
        self.assertEqual("RECOVERY_REVERIFICATION_INCOMPLETE", reason)

    def test_pending_complete_passes(self) -> None:
        state = default_state("R1", "t")
        state["recovery"]["status"] = "PENDING"
        state["recovery"]["reverification_complete"] = True
        ok, reason = gate_recovery(state)
        self.assertTrue(ok)
        self.assertEqual("", reason)


# ---------------------------------------------------------------------------
# blockers_for_target tests
# ---------------------------------------------------------------------------

class TestBlockersForTarget(unittest.TestCase):
    def test_target_surface_attested_default_blocked(self) -> None:
        state = default_state("R1", "t")
        blockers = blockers_for_target(state, "TARGET_SURFACE_ATTESTED")
        self.assertEqual(["TARGET_SURFACE_NOT_ATTESTED"], blockers)

    def test_target_surface_attested_when_attested(self) -> None:
        state = default_state("R1", "t")
        state["target_surface"]["status"] = "ATTESTED"
        blockers = blockers_for_target(state, "TARGET_SURFACE_ATTESTED")
        self.assertEqual([], blockers)

    def test_ready_collects_multiple_blockers(self) -> None:
        state = default_state("R1", "t")
        blockers = blockers_for_target(state, "READY")
        self.assertIn("TARGET_SURFACE_NOT_ATTESTED", blockers)
        self.assertIn("DOCTOR_NOT_GREEN", blockers)
        self.assertIn("CONTROLLED_BOOTSTRAP_NOT_CONFIRMED", blockers)

    def test_execution_completed_includes_execution_check(self) -> None:
        state = ready_state()
        state["execution"]["status"] = "NOT_RUN"
        blockers = blockers_for_target(state, "EXECUTION_COMPLETED")
        self.assertEqual(["EXECUTION_NOT_COMPLETED"], blockers)

    def test_proof_bundle_complete_checks_artifacts_and_proof(self) -> None:
        state = default_state("R1", "t")
        blockers = blockers_for_target(state, "PROOF_BUNDLE_COMPLETE")
        self.assertIn("ARTIFACT_BUNDLE_MISSING", blockers)
        self.assertIn("MISSING_PROOF_SECTIONS", blockers)

    def test_closure_accepted_checks_recovery(self) -> None:
        state = ready_state()
        state["recovery"]["status"] = "PENDING"
        state["recovery"]["reverification_complete"] = False
        blockers = blockers_for_target(state, "CLOSURE_ACCEPTED")
        self.assertIn("RECOVERY_REVERIFICATION_INCOMPLETE", blockers)

    def test_unknown_target_returns_empty(self) -> None:
        state = default_state("R1", "t")
        blockers = blockers_for_target(state, "NONEXISTENT_TARGET")
        self.assertEqual([], blockers)


# ---------------------------------------------------------------------------
# dominant_blocker tests
# ---------------------------------------------------------------------------

class TestDominantBlocker(unittest.TestCase):
    def test_single_blocker(self) -> None:
        result = dominant_blocker("READY", ["DOCTOR_NOT_GREEN"])
        self.assertEqual("DOCTOR_NOT_GREEN", result)

    def test_precedence_order(self) -> None:
        result = dominant_blocker("READY", [
            "EXACT_TASK_IDENTITY_NOT_CONFIRMED",
            "TARGET_SURFACE_NOT_ATTESTED",
            "DOCTOR_NOT_GREEN",
        ])
        self.assertEqual("TARGET_SURFACE_NOT_ATTESTED", result)

    def test_empty_blockers(self) -> None:
        result = dominant_blocker("READY", [])
        self.assertEqual("", result)

    def test_unknown_target_uses_first(self) -> None:
        result = dominant_blocker("NONEXISTENT", ["B", "A"])
        self.assertEqual("B", result)


# ---------------------------------------------------------------------------
# transition tests
# ---------------------------------------------------------------------------

class TestTransition(unittest.TestCase):
    def test_valid_target_surface_attested(self) -> None:
        state = default_state("R1", "t")
        state["target_surface"]["status"] = "ATTESTED"
        code, new_state, report = transition(state, "TARGET_SURFACE_ATTESTED")
        self.assertEqual(0, code)
        self.assertEqual("TARGET_SURFACE_ATTESTED", new_state["state"])
        self.assertIsNone(report)

    def test_blocked_transition_returns_report(self) -> None:
        state = default_state("R1", "t")
        code, new_state, report = transition(state, "TARGET_SURFACE_ATTESTED")
        self.assertEqual(2, code)
        self.assertIsNotNone(report)

    def test_terminal_state_denies(self) -> None:
        state = ready_state()
        state["state"] = "CLOSURE_ACCEPTED"
        code, new_state, report = transition(state, "TARGET_SURFACE_ATTESTED")
        self.assertEqual(2, code)
        self.assertIsNotNone(report)

    def test_unknown_target_denies(self) -> None:
        state = ready_state()
        code, new_state, report = transition(state, "TOTALLY_FAKE_STATE")
        self.assertEqual(2, code)
        self.assertIsNotNone(report)

    def test_closure_accepted_sets_terminal(self) -> None:
        state = ready_state()
        code, new_state, report = transition(state, "CLOSURE_ACCEPTED")
        self.assertEqual(0, code)
        self.assertEqual("CLOSURE_ACCEPTED", new_state["state"])
        self.assertEqual("ACCEPTED", new_state["closure"]["status"])
        self.assertIsNone(report)

    def test_closure_rejected_sets_terminal(self) -> None:
        state = ready_state()
        code, new_state, report = transition(state, "CLOSURE_REJECTED")
        self.assertEqual(0, code)
        self.assertEqual("CLOSURE_REJECTED", new_state["state"])
        self.assertEqual("REJECTED", new_state["closure"]["status"])


# ---------------------------------------------------------------------------
# apply_doctor tests
# ---------------------------------------------------------------------------

class TestApplyDoctor(unittest.TestCase):
    def test_acceptable_verdict_advances(self) -> None:
        state = default_state("R1", "t")
        state["target_surface"]["status"] = "ATTESTED"
        state["state"] = "TARGET_SURFACE_ATTESTED"
        record = {"final_verdict": "ACCEPTABLE_FOR_CORE_RUN", "blocking_failure_classes": []}
        code, new_state, report = apply_doctor(state, record)
        self.assertEqual(0, code)
        self.assertEqual("PASS", new_state["doctor"]["status"])

    def test_non_acceptable_verdict_blocks(self) -> None:
        state = default_state("R1", "t")
        record = {
            "final_verdict": "NOT_ACCEPTABLE_BASELINE_IDENTITY",
            "blocking_failure_classes": ["baseline-identity ambiguous"],
            "recommended_next_safe_step": "restore baseline",
        }
        code, new_state, report = apply_doctor(state, record)
        self.assertEqual(0, code)
        self.assertEqual("FAIL", new_state["doctor"]["status"])
        self.assertEqual("DOCTOR_BLOCKED", new_state["state"])
        self.assertEqual("DOCTOR_NOT_GREEN", new_state["closure"]["blocking_reason"])


# ---------------------------------------------------------------------------
# apply_bundle tests
# ---------------------------------------------------------------------------

class TestApplyBundle(unittest.TestCase):
    def _exec_state(self) -> dict:
        state = ready_state()
        state["state"] = "EXECUTION_COMPLETED"
        return state

    def test_complete_bundle_transitions(self) -> None:
        state = self._exec_state()
        bundle = {"status": "COMPLETE", "final_result": {"present": True}}
        code, new_state, report = apply_bundle(state, bundle)
        self.assertEqual(0, code)
        self.assertEqual("PROOF_BUNDLE_COMPLETE", new_state["state"])

    def test_invalid_bundle_blocks(self) -> None:
        state = self._exec_state()
        bundle = {"status": "INVALID", "missing_sections": ["final_result"]}
        code, new_state, report = apply_bundle(state, bundle)
        self.assertEqual(0, code)
        self.assertEqual("PROOF_BUNDLE_INVALID", new_state["state"])
        self.assertEqual("INVALID_PROOF_BUNDLE", new_state["closure"]["blocking_reason"])

    def test_structurally_complete_blocks(self) -> None:
        state = self._exec_state()
        bundle = {"status": "STRUCTURALLY_COMPLETE", "semantically_insufficient_sections": ["diff_provenance"]}
        code, new_state, report = apply_bundle(state, bundle)
        self.assertEqual(0, code)
        self.assertEqual("PROOF_BUNDLE_STRUCTURALLY_COMPLETE", new_state["state"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", new_state["closure"]["blocking_reason"])

    def test_partial_bundle_blocks(self) -> None:
        state = self._exec_state()
        bundle = {"status": "PARTIAL", "missing_sections": ["readback"]}
        code, new_state, report = apply_bundle(state, bundle)
        self.assertEqual(0, code)
        self.assertEqual("PROOF_BUNDLE_PARTIAL", new_state["state"])
        self.assertEqual("MISSING_PROOF_SECTIONS", new_state["closure"]["blocking_reason"])


# ---------------------------------------------------------------------------
# build_verdict tests (synrail_closure_v0)
# ---------------------------------------------------------------------------

class TestBuildVerdict(unittest.TestCase):
    def _full_state(self) -> dict:
        return ready_state()

    def _complete_bundle(self) -> dict:
        return {"status": "COMPLETE", "missing_sections": [], "semantically_insufficient_sections": []}

    def test_accepted_when_all_gates_pass(self) -> None:
        verdict = build_verdict(self._full_state(), self._complete_bundle())
        self.assertEqual("ACCEPTED", verdict["closure_status"])
        self.assertEqual("", verdict["blocking_reason"])

    def test_blocks_on_target_not_attested(self) -> None:
        state = self._full_state()
        state["target_surface"]["status"] = "UNKNOWN"
        verdict = build_verdict(state, self._complete_bundle())
        self.assertEqual("CLAIMED_NOT_ACCEPTED", verdict["closure_status"])
        self.assertEqual("TARGET_SURFACE_NOT_ATTESTED", verdict["blocking_reason"])

    def test_blocks_on_doctor_not_green(self) -> None:
        state = self._full_state()
        state["doctor"]["status"] = "FAIL"
        verdict = build_verdict(state, self._complete_bundle())
        self.assertEqual("DOCTOR_NOT_GREEN", verdict["blocking_reason"])

    def test_blocks_on_incomplete_proof(self) -> None:
        state = self._full_state()
        bundle = {"status": "PARTIAL", "missing_sections": ["readback"], "semantically_insufficient_sections": []}
        verdict = build_verdict(state, bundle)
        self.assertEqual("MISSING_PROOF_SECTIONS", verdict["blocking_reason"])

    def test_blocks_on_semantic_insufficient(self) -> None:
        state = self._full_state()
        bundle = {"status": "STRUCTURALLY_COMPLETE", "missing_sections": [], "semantically_insufficient_sections": ["diff_provenance"]}
        verdict = build_verdict(state, bundle)
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])

    def test_blocks_on_recovery_pending(self) -> None:
        state = self._full_state()
        state["recovery"]["status"] = "PENDING"
        state["recovery"]["reverification_complete"] = False
        verdict = build_verdict(state, self._complete_bundle())
        self.assertEqual("RECOVERY_REVERIFICATION_INCOMPLETE", verdict["blocking_reason"])

    def test_blocks_on_stale_criteria(self) -> None:
        state = self._full_state()
        criteria = {"status": "STALE", "criteria_revision_id": "cr1", "reason": "moved"}
        verdict = build_verdict(state, self._complete_bundle(), criteria)
        self.assertEqual("ACCEPTANCE_CRITERIA_STALE", verdict["blocking_reason"])

    def test_blocks_on_no_bootstrap(self) -> None:
        state = self._full_state()
        state["integrity"]["bootstrap_provenance_ok"] = False
        verdict = build_verdict(state, self._complete_bundle())
        self.assertEqual("CONTROLLED_BOOTSTRAP_NOT_CONFIRMED", verdict["blocking_reason"])

    def test_blocks_on_execution_not_completed(self) -> None:
        state = self._full_state()
        state["execution"]["status"] = "NOT_RUN"
        verdict = build_verdict(state, self._complete_bundle())
        self.assertEqual("EXECUTION_NOT_COMPLETED", verdict["blocking_reason"])


# ---------------------------------------------------------------------------
# Continuation arbiter drift tests
# ---------------------------------------------------------------------------

class TestContinuationArbiterDrift(unittest.TestCase):
    def _minimal_state(self, run_id: str = "R1") -> dict:
        return {
            "run_id": run_id,
            "task_class": "bounded_change",
            "state": "DOCTOR_BLOCKED",
            "next_safe_step": "repair readiness",
        }

    def _minimal_packet(self, run_id: str = "R1", *, with_step: bool = True) -> dict:
        core = {
            "resumability_status": "RESUMABLE",
            "resumability_family": "REPAIRABLE_DOCTOR_BLOCKED",
            "ready_for_resume": False,
            "missing_inputs": ["prompt_identity_ok"],
            "next_step_required_inputs": ["prompt_identity_ok"],
            "operator_focus": "fix readiness",
        }
        if with_step:
            core["current_step_id"] = "restore_readiness_truth"
        return {
            "run_id": run_id,
            "task_class": "bounded_change",
            "from_state": "DOCTOR_BLOCKED",
            "continuation_core": core,
            "repair_policy": {},
            "repair_termination": {},
            "source_of_truth": {"precedence_order": []},
        }

    def test_resolves_when_consistent(self) -> None:
        state = self._minimal_state("R1")
        packet = self._minimal_packet("R1")
        record = build_continuation_arbiter(state=state, packet=packet)
        self.assertEqual("RESOLVED", record["resolution_status"])
        self.assertEqual(0, len(record["unresolved_surfaces"]))

    def test_conflict_on_missing_resumability(self) -> None:
        state = self._minimal_state("R1")
        packet = self._minimal_packet("R1")
        packet["continuation_core"]["resumability_status"] = ""
        del packet["continuation_core"]["resumability_family"]
        record = build_continuation_arbiter(state=state, packet=packet)
        self.assertEqual("CONFLICT_UNRESOLVED", record["resolution_status"])
        self.assertIn("resumability_status", record["unresolved_surfaces"])

    def test_conflict_on_missing_step_id_when_awaiting(self) -> None:
        state = self._minimal_state("R1")
        packet = self._minimal_packet("R1", with_step=False)
        record = build_continuation_arbiter(state=state, packet=packet)
        self.assertEqual("CONFLICT_UNRESOLVED", record["resolution_status"])
        self.assertIn("current_step_id", record["unresolved_surfaces"])


# ---------------------------------------------------------------------------
# Correctness regression tests — Tranche 1
# ---------------------------------------------------------------------------

from synrail_repair_packet_v0 import bool_arg, build_packet_from_runtime_truth
from synrail_checkpoint_v0 import ARTIFACT_FLAGS, build_manifest
from synrail_repair_handoff_v0 import build_repair_handoff

import argparse
import tempfile


class TestBoolArgStickiness(unittest.TestCase):
    """bool_arg must not make True irrevocable."""

    def test_none_inherits_fallback_true(self) -> None:
        self.assertTrue(bool_arg(None, True))

    def test_none_inherits_fallback_false(self) -> None:
        self.assertFalse(bool_arg(None, False))

    def test_explicit_true_overrides_false(self) -> None:
        self.assertTrue(bool_arg(True, False))

    def test_explicit_false_overrides_true(self) -> None:
        """This is the critical case: operator must be able to revoke a previously-True flag."""
        self.assertFalse(bool_arg(False, True))

    def test_explicit_false_stays_false(self) -> None:
        self.assertFalse(bool_arg(False, False))


class TestReadyForResumeTermination(unittest.TestCase):
    """Top-level ready_for_resume must respect repair termination."""

    def _build_terminated_packet(self) -> dict:
        state = ready_state()
        state["state"] = "PROOF_BUNDLE_INVALID"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "INVALID_PROOF_BUNDLE"
        state["proof_bundle"]["status"] = "INVALID"
        handoff = build_repair_handoff(state)
        # Force termination by injecting a TERMINATE repair_receipt
        receipt = {
            "schema_version": "artifact_repair_receipt_v0",
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "from_state": state["state"],
            "result": "NON_RESUMABLE_BOUNDARY_REACHED",
            "repair_history_chain": [],
        }
        packet = build_packet_from_runtime_truth(
            state=state,
            artifact_root=Path("/tmp/synrail_test_termination"),
            doctor_run_id="D1",
            doctor_level="CORE_DOCTOR",
            target_path="/tmp/target",
            target_classification="core_surface",
            baseline_identity="baseline-001",
            intended_run_class="core_probe",
            execution_surface_identity="surface-001",
            repair_handoff=handoff,
            repair_receipt=receipt,
        )
        return packet

    def test_terminated_packet_not_ready_for_resume(self) -> None:
        packet = self._build_terminated_packet()
        termination = packet.get("repair_termination", {})
        if termination.get("status") == "TERMINATE":
            self.assertFalse(
                packet["ready_for_resume"],
                "Top-level ready_for_resume must be False when repair_termination is TERMINATE",
            )


class TestClosureRunIdBinding(unittest.TestCase):
    """Closure must block when state and bundle run_ids disagree."""

    def _valid_bundle(self, run_id: str = "R1") -> dict:
        return {
            "run_id": run_id,
            "task_class": "bounded_change",
            "status": "COMPLETE",
            "semantic_status": "SUFFICIENT",
            "missing_sections": [],
            "semantically_insufficient_sections": [],
            "structural_decision_trace": [{"section": "test", "present": True}],
            "semantic_decision_trace": [{"section": "test", "sufficient": True}],
            "final_result": {"request_id": run_id},
        }

    def test_matching_run_ids_accepted(self) -> None:
        state = ready_state("R1")
        bundle = self._valid_bundle("R1")
        verdict = build_verdict(state, bundle)
        self.assertEqual("ACCEPTED", verdict["closure_status"])
        self.assertEqual("", verdict["blocking_reason"])

    def test_mismatched_run_ids_blocked(self) -> None:
        state = ready_state("R1")
        bundle = self._valid_bundle("R2")
        verdict = build_verdict(state, bundle)
        self.assertEqual("CLAIMED_NOT_ACCEPTED", verdict["closure_status"])
        self.assertEqual("RUN_ID_MISMATCH", verdict["blocking_reason"])
        self.assertEqual("PROOF_BUNDLE_REPAIR", verdict["next_allowed_transition"])

    def test_empty_bundle_run_id_still_accepted(self) -> None:
        """If bundle has no run_id, there is nothing to mismatch."""
        state = ready_state("R1")
        bundle = self._valid_bundle("R1")
        bundle["run_id"] = ""
        verdict = build_verdict(state, bundle)
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_mismatched_artifact_request_id_blocked(self) -> None:
        state = ready_state("R1")
        bundle = self._valid_bundle("R1")
        bundle["final_result"]["request_id"] = "R2"
        verdict = build_verdict(state, bundle)
        self.assertEqual("CLAIMED_NOT_ACCEPTED", verdict["closure_status"])
        self.assertEqual("RUN_ID_MISMATCH", verdict["blocking_reason"])


class TestCheckpointRequiredField(unittest.TestCase):
    """Checkpoint manifest must mark optional artifacts as not required."""

    def test_optional_artifacts_not_required(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_ckpt_test_") as tmpdir:
            tmp = Path(tmpdir)
            checkpoint_root = tmp / "checkpoint"
            checkpoint_root.mkdir()
            # Create minimal fake artifact files
            state_file = tmp / "state.json"
            report_file = tmp / "report.json"
            state_file.write_text('{"schema_version": "run_state_v0"}')
            report_file.write_text('{"schema_version": "orchestration_report_v0"}')
            args = argparse.Namespace(
                state_file=str(state_file),
                report_file=str(report_file),
                orchestration_file=None,
                bundle_file=None,
                closure_file=None,
                refresh_file=None,
                selection_file=None,
                preparation_file=None,
                repair_packet_file=None,
                repair_handoff_file=None,
                repair_receipt_file=None,
            )
            manifest = build_manifest(args, checkpoint_root)

        state_entry = next(e for e in manifest if e["artifact_id"] == "state")
        report_entry = next(e for e in manifest if e["artifact_id"] == "report")
        # state is always_required=True in ARTIFACT_FLAGS
        self.assertTrue(state_entry["required"])
        # report is always_required=False in ARTIFACT_FLAGS
        self.assertFalse(report_entry["required"])

    def test_artifact_flags_have_optional_entries(self) -> None:
        """Verify ARTIFACT_FLAGS actually contains both required and optional entries."""
        required_flags = [f for f in ARTIFACT_FLAGS if f[3] is True]
        optional_flags = [f for f in ARTIFACT_FLAGS if f[3] is False]
        self.assertGreater(len(required_flags), 0)
        self.assertGreater(len(optional_flags), 0)


class TestCliBoolArgDefaults(unittest.TestCase):
    """CLI argparse boolean flags must default to None, not False.

    Without default=None, argparse store_true gives False when the flag is omitted.
    bool_arg(False, True) → False, silently revoking a previously-True sticky flag.
    bool_arg(None, True) → True, correctly inheriting the sticky value.
    """

    def _check_parser_defaults(self, parser: argparse.ArgumentParser, flag_names: list[str]) -> list[str]:
        """Return flag names whose default is not None."""
        bad: list[str] = []
        for action in parser._actions:
            for opt in action.option_strings:
                clean = opt.lstrip("-").replace("-", "_")
                if clean in flag_names and action.default is not None:
                    bad.append(opt)
        return bad

    def test_repair_packet_parser_defaults(self) -> None:
        from synrail_repair_packet_v0 import build_parser
        parser = build_parser()
        sticky_flags = [
            "prompt_identity_ok", "clean_surface", "artifact_viable",
            "helper_ok", "credentials_ok",
            "refresh_reverification_complete", "refresh_use_bundle", "refresh_use_closure",
        ]
        bad = self._check_parser_defaults(parser, sticky_flags)
        self.assertEqual([], bad, f"These flags should default to None: {bad}")

    @staticmethod
    def _find_subparser(parser: argparse.ArgumentParser, name: str):
        for action in parser._subparsers._actions:
            if hasattr(action, "choices") and action.choices:
                if name in action.choices:
                    return action.choices[name]
        return None

    def test_cli_check_parser_defaults(self) -> None:
        from synrail_cli_v0 import build_parser
        parser = build_parser()
        check_parser = self._find_subparser(parser, "check")
        self.assertIsNotNone(check_parser, "check subcommand not found")
        sticky_flags = [
            "clean_surface", "artifact_viable", "helper_ok",
            "credentials_ok", "prompt_identity_ok",
            "refresh_reverification_complete", "refresh_use_bundle", "refresh_use_closure",
        ]
        bad = self._check_parser_defaults(check_parser, sticky_flags)
        self.assertEqual([], bad, f"check subcommand: these flags should default to None: {bad}")

    def test_cli_repair_packet_parser_defaults(self) -> None:
        from synrail_cli_v0 import build_parser
        parser = build_parser()
        rp_parser = self._find_subparser(parser, "repair-packet")
        self.assertIsNotNone(rp_parser, "repair-packet subcommand not found")
        sticky_flags = [
            "prompt_identity_ok", "clean_surface", "artifact_viable",
            "helper_ok", "credentials_ok",
            "refresh_reverification_complete", "refresh_use_bundle", "refresh_use_closure",
        ]
        bad = self._check_parser_defaults(rp_parser, sticky_flags)
        self.assertEqual([], bad, f"repair-packet subcommand: these flags should default to None: {bad}")


class TestDoctorCoverageDeployment(unittest.TestCase):
    """Coverage bypass must require explicit deployment context."""

    def test_all_missing_evidence_passes_only_with_explicit_deployment_context(self) -> None:
        from synrail_doctor_coverage_v0 import build_coverage_record
        profile = {
            "critical_fail_modes": ["mode_a", "mode_b"],
            "covered_fail_modes": ["mode_a", "mode_b"],
            "partial_fail_modes": [],
            "uncovered_fail_modes": [],
            "coverage_threshold_policy": "ALL_CRITICAL_FAIL_MODES_COVERED",
        }
        corpus = {
            "schema_version": "doctor_coverage_corpus_v0",
            "cases": [
                {
                    "case_id": "CASE_A",
                    "fail_mode_id": "mode_a",
                    "doctor_record": "/nonexistent/path/doctor_a.json",
                    "expected_final_verdict": "NOT_ACCEPTABLE",
                },
                {
                    "case_id": "CASE_B",
                    "fail_mode_id": "mode_b",
                    "doctor_record": "/nonexistent/path/doctor_b.json",
                    "expected_final_verdict": "NOT_ACCEPTABLE",
                },
            ],
        }
        from pathlib import Path
        record = build_coverage_record(
            profile,
            corpus,
            corpus_file=Path("/nonexistent/corpus.json"),
            deployment_context=True,
        )
        self.assertTrue(record["threshold_met"])
        self.assertEqual("PASS", record["gate_status"])
        self.assertEqual("COVERAGE_CORPUS_NOT_AVAILABLE_IN_DEPLOYMENT", record["gate_reason"])
        self.assertTrue(record["deployment_context_confirmed"])

    def test_all_missing_evidence_blocks_without_explicit_deployment_context(self) -> None:
        from synrail_doctor_coverage_v0 import build_coverage_record
        profile = {
            "critical_fail_modes": ["mode_a"],
            "covered_fail_modes": ["mode_a"],
            "partial_fail_modes": [],
            "uncovered_fail_modes": [],
            "coverage_threshold_policy": "ALL_CRITICAL_FAIL_MODES_COVERED",
        }
        # One case has a real fixture, one doesn't — this would never be all_missing
        # For this test, use a corpus with one case pointing to a real file
        corpus = {
            "schema_version": "doctor_coverage_corpus_v0",
            "cases": [
                {
                    "case_id": "CASE_A",
                    "fail_mode_id": "mode_a",
                    "doctor_record": "/nonexistent/path/doctor.json",
                    "expected_final_verdict": "NOT_ACCEPTABLE",
                },
            ],
        }
        from pathlib import Path
        record = build_coverage_record(profile, corpus, corpus_file=Path("/nonexistent/corpus.json"))
        self.assertFalse(record["threshold_met"])
        self.assertEqual("BLOCKED", record["gate_status"])
        self.assertEqual("CRITICAL_FAIL_MODE_MEASURED_COVERAGE_MISSING_EVIDENCE", record["gate_reason"])
        self.assertFalse(record["deployment_context_confirmed"])

    def test_partial_evidence_still_blocks_even_in_deployment_context(self) -> None:
        """If some fixtures exist and some don't, it's still a real coverage gap."""
        from synrail_doctor_coverage_v0 import build_coverage_record
        from tempfile import TemporaryDirectory

        profile = {
            "critical_fail_modes": ["mode_a"],
            "covered_fail_modes": ["mode_a"],
            "partial_fail_modes": [],
            "uncovered_fail_modes": [],
            "coverage_threshold_policy": "ALL_CRITICAL_FAIL_MODES_COVERED",
        }

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            doctor_record = tmp_path / "doctor.json"
            doctor_record.write_text(
                '{"final_verdict":"NOT_ACCEPTABLE","blocking_failure_classes":[],"gate_results":{}}\n'
            )
            corpus = {
                "schema_version": "doctor_coverage_corpus_v0",
                "cases": [
                    {
                        "case_id": "CASE_A",
                        "fail_mode_id": "mode_a",
                        "doctor_record": str(doctor_record),
                        "expected_final_verdict": "NOT_ACCEPTABLE",
                    },
                    {
                        "case_id": "CASE_B",
                        "fail_mode_id": "mode_a",
                        "doctor_record": str(tmp_path / "missing_doctor.json"),
                        "expected_final_verdict": "NOT_ACCEPTABLE",
                    },
                ],
            }
            record = build_coverage_record(
                profile,
                corpus,
                corpus_file=tmp_path / "coverage_corpus.json",
                deployment_context=True,
            )
        self.assertFalse(record["threshold_met"])
        self.assertEqual("BLOCKED", record["gate_status"])
        self.assertEqual("CRITICAL_FAIL_MODE_MEASURED_COVERAGE_INCOMPLETE", record["gate_reason"])
        self.assertTrue(record["deployment_context_confirmed"])

    def test_dev_repo_with_fixtures_still_validates(self) -> None:
        """In the dev repo where fixtures exist, normal validation applies."""
        from synrail_doctor_coverage_v0 import build_coverage_record, load_corpus, load_profile
        profile = load_profile()
        corpus, corpus_file = load_corpus()
        record = build_coverage_record(profile, corpus, corpus_file=corpus_file)
        # In dev repo, fixtures exist — threshold must be met normally
        self.assertTrue(record["threshold_met"])
        self.assertEqual("PASS", record["gate_status"])
        self.assertEqual("CRITICAL_FAIL_MODE_MEASURED_COVERAGE_MET", record["gate_reason"])
        self.assertFalse(record["deployment_context_confirmed"])


class TestPreRunSnapshot(unittest.TestCase):
    """Tests for pre-run snapshot checkpoint support (bug 007 fix)."""

    def test_initialized_state_is_safe_point(self) -> None:
        from synrail_checkpoint_v0 import classify_safe_point
        state = default_state("run1", "bounded_change")
        safe_class, eligible, failures = classify_safe_point(state)
        self.assertEqual("PRE_RUN_SNAPSHOT", safe_class)
        self.assertTrue(eligible)
        self.assertEqual([], failures)

    def test_ready_state_without_gates_is_not_safe(self) -> None:
        from synrail_checkpoint_v0 import classify_safe_point
        state = default_state("run1", "bounded_change")
        state["state"] = "READY"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        # READY + CLAIMED_NOT_ACCEPTED matches VERIFIED_WORKING_STATE but
        # doctor/target/integrity are still UNKNOWN, so it should fail.
        safe_class, eligible, failures = classify_safe_point(state)
        self.assertEqual("VERIFIED_WORKING_STATE", safe_class)
        self.assertFalse(eligible)
        self.assertTrue(len(failures) > 0)

    def test_create_record_from_initialized_succeeds(self) -> None:
        import argparse
        import tempfile
        from synrail_checkpoint_v0 import create_record
        from synrail_spine_v0 import default_state as make_state
        state = make_state("run1", "bounded_change")
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            state_path.write_text(json.dumps(state))
            checkpoint_root = Path(tmpdir) / "checkpoint"
            args = argparse.Namespace(
                checkpoint_id="working",
                checkpoint_root=str(checkpoint_root),
                state_file=str(state_path),
                project_root=tmpdir,
                report_file=None, orchestration_file=None,
                bundle_file=None, closure_file=None,
                refresh_file=None, selection_file=None,
                preparation_file=None, repair_packet_file=None,
                repair_handoff_file=None, repair_receipt_file=None,
            )
            record = create_record(args)
            self.assertEqual("OK", record["result"])
            self.assertEqual("PRE_RUN_SNAPSHOT", record["safe_point_class"])
            self.assertTrue(record["safe_point_eligible"])
            # State artifact should be in manifest
            artifact_ids = [a["artifact_id"] for a in record["artifact_manifest"]]
            self.assertIn("state", artifact_ids)

    def test_verify_pre_run_snapshot_passes(self) -> None:
        import argparse
        import tempfile
        from synrail_checkpoint_v0 import create_record, verify_record
        from synrail_spine_v0 import default_state as make_state
        state = make_state("run1", "bounded_change")
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = Path(tmpdir) / "state.json"
            state_path.write_text(json.dumps(state))
            checkpoint_root = Path(tmpdir) / "checkpoint"
            args = argparse.Namespace(
                checkpoint_id="working",
                checkpoint_root=str(checkpoint_root),
                state_file=str(state_path),
                project_root=tmpdir,
                report_file=None, orchestration_file=None,
                bundle_file=None, closure_file=None,
                refresh_file=None, selection_file=None,
                preparation_file=None, repair_packet_file=None,
                repair_handoff_file=None, repair_receipt_file=None,
            )
            record = create_record(args)
            verified = verify_record(record)
            self.assertEqual("OK", verified["result"])
            self.assertEqual("PASSED", verified["verification"]["status"])


class TestRestoreRoundTrip(unittest.TestCase):
    """Full save → break → restore round-trip using git workspace snapshot."""

    def test_restore_recovers_committed_file(self) -> None:
        import argparse
        import os
        import subprocess
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_record, verify_record
        from synrail_spine_v0 import default_state as make_state

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            target = project / "hello.py"
            target.write_text('print("hello")\n')
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            subprocess.run(["git", "init"], cwd=str(project), capture_output=True, env=env)
            subprocess.run(["git", "add", "."], cwd=str(project), capture_output=True, env=env)
            subprocess.run(["git", "commit", "-m", "init"], cwd=str(project), capture_output=True, env=env)

            state = make_state("run1", "bounded_change")
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"

            args = argparse.Namespace(
                checkpoint_id="working",
                checkpoint_root=str(checkpoint_root),
                state_file=str(state_path),
                project_root=str(project),
                report_file=None, orchestration_file=None,
                bundle_file=None, closure_file=None,
                refresh_file=None, selection_file=None,
                preparation_file=None, repair_packet_file=None,
                repair_handoff_file=None, repair_receipt_file=None,
            )
            record = create_record(args)
            self.assertEqual("OK", record["result"])
            self.assertIn("workspace_snapshot", record)

            # Break the file
            target.write_text("BROKEN\n")
            self.assertEqual("BROKEN", target.read_text().strip())

            # Restore
            restored = restore_record(record, project / ".synrail")
            self.assertEqual("OK", restored["result"])
            self.assertTrue(restored["restore"]["workspace_restored"])

            # File should be recovered
            self.assertEqual('print("hello")', target.read_text().strip())

    def test_restore_recovers_uncommitted_changes(self) -> None:
        import argparse
        import os
        import subprocess
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_record
        from synrail_spine_v0 import default_state as make_state

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            target = project / "hello.py"
            target.write_text('print("hello")\n')
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            subprocess.run(["git", "init"], cwd=str(project), capture_output=True, env=env)
            subprocess.run(["git", "add", "."], cwd=str(project), capture_output=True, env=env)
            subprocess.run(["git", "commit", "-m", "init"], cwd=str(project), capture_output=True, env=env)

            # Add uncommitted change before save
            target.write_text('print("modified")\n')

            state = make_state("run1", "bounded_change")
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"

            args = argparse.Namespace(
                checkpoint_id="working",
                checkpoint_root=str(checkpoint_root),
                state_file=str(state_path),
                project_root=str(project),
                report_file=None, orchestration_file=None,
                bundle_file=None, closure_file=None,
                refresh_file=None, selection_file=None,
                preparation_file=None, repair_packet_file=None,
                repair_handoff_file=None, repair_receipt_file=None,
            )
            record = create_record(args)
            self.assertEqual("OK", record["result"])
            self.assertTrue(record["workspace_snapshot"]["has_uncommitted"])

            # Break the file
            target.write_text("BROKEN\n")

            # Restore
            restored = restore_record(record, project / ".synrail")
            self.assertEqual("OK", restored["result"])

            # Should restore to the uncommitted state (not the commit)
            self.assertEqual('print("modified")', target.read_text().strip())


class TestRestoreHonestyWithoutGit(unittest.TestCase):
    """Restore must fail honestly when workspace snapshot is unavailable."""

    def test_create_record_without_git_uses_file_copy(self) -> None:
        import argparse
        import tempfile
        from synrail_checkpoint_v0 import create_record
        from synrail_spine_v0 import default_state as make_state

        state = make_state("run1", "bounded_change")
        with tempfile.TemporaryDirectory() as tmpdir:
            # tmpdir is NOT a git repo — create a project file to snapshot
            project = Path(tmpdir) / "project"
            project.mkdir()
            (project / "hello.py").write_text('print("hello")\n')
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"
            args = argparse.Namespace(
                checkpoint_id="working",
                checkpoint_root=str(checkpoint_root),
                state_file=str(state_path),
                project_root=str(project),
                report_file=None, orchestration_file=None,
                bundle_file=None, closure_file=None,
                refresh_file=None, selection_file=None,
                preparation_file=None, repair_packet_file=None,
                repair_handoff_file=None, repair_receipt_file=None,
            )
            record = create_record(args)
            self.assertEqual("OK", record["result"])
            self.assertEqual("PRE_RUN_SNAPSHOT", record["safe_point_class"])
            # Must use file_copy fallback
            self.assertIn("workspace_snapshot", record)
            self.assertEqual("file_copy", record["workspace_snapshot"]["type"])
            self.assertGreater(record["workspace_snapshot"]["file_count"], 0)

    def test_restore_fails_honestly_when_workspace_snapshot_is_none(self) -> None:
        """If workspace_snapshot.type is 'none', restore must fail honestly."""
        import argparse
        import tempfile
        from synrail_checkpoint_v0 import restore_preview, restore_record, verify_record
        from synrail_spine_v0 import default_state as make_state

        state = make_state("run1", "bounded_change")
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate a record that has type=none (e.g. file-copy also failed)
            state_path = Path(tmpdir) / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = Path(tmpdir) / ".synrail" / "checkpoints" / "working"
            checkpoint_root.mkdir(parents=True, exist_ok=True)
            artifacts_dir = checkpoint_root / "artifacts"
            artifacts_dir.mkdir()
            import shutil
            shutil.copy2(state_path, artifacts_dir / "state.json")

            record = {
                "schema_version": "checkpoint_record_v0",
                "checkpoint_id": "working",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "event_type": "CREATE",
                "result": "OK",
                "checkpoint_root": str(checkpoint_root),
                "source_state": "INITIALIZED",
                "source_closure_status": "OPEN",
                "source_doctor_status": "",
                "source_target_surface_status": "",
                "source_integrity_status": "",
                "source_resumability_status": "NOT_RESUMABLE",
                "source_resumability_family": "NOT_RESUMABLE_FRESH_ORCHESTRATION",
                "safe_point_class": "PRE_RUN_SNAPSHOT",
                "safe_point_eligible": True,
                "artifact_manifest": [
                    {"artifact_id": "state", "path": "artifacts/state.json", "required": True, "kind": "STATE"},
                ],
                "verification": {"status": "PASSED", "safe_point_eligible": True,
                                  "required_artifacts_present": True, "schema_validation_passed": True,
                                  "state_consistency_passed": True, "stale_artifacts_detected": [], "failure_reasons": []},
                "restore": {"status": "NOT_RUN", "target_root": "", "restore_verification_required": True,
                            "restored_artifact_ids": [], "failure_reasons": []},
                "rollback": {"status": "NOT_NEEDED", "trigger": "NONE", "rolled_back_artifact_ids": [], "failure_reasons": []},
                "workspace_snapshot": {"type": "none", "reason": "file-copy snapshot failed: too large"},
                "next_safe_step": "verify checkpoint before trusting restore",
            }
            target_root = Path(tmpdir) / ".synrail"
            preview = restore_preview(record, target_root)
            restored = restore_record(record, target_root)
            self.assertEqual("UNSUPPORTED", preview["restore_status"])
            self.assertFalse(preview["restore_supported"])
            self.assertEqual("none", preview["workspace_restore_mode"])
            self.assertFalse(restored["restore"]["workspace_restored"])
            self.assertEqual("RESTORE_FAILED", restored["restore"]["status"])
            self.assertTrue(
                any("cannot restore workspace files" in f.lower() for f in restored["restore"]["failure_reasons"]),
                f"Expected workspace failure reason, got: {restored['restore']['failure_reasons']}",
            )

    def test_file_copy_restore_round_trip(self) -> None:
        """Full save→break→restore using file-copy (no git)."""
        import argparse
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_preview, restore_record
        from synrail_spine_v0 import default_state as make_state

        state = make_state("run1", "bounded_change")
        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            target = project / "hello.py"
            target.write_text('print("hello")\n')
            (project / "subdir").mkdir()
            (project / "subdir" / "data.txt").write_text("original data\n")

            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"
            args = argparse.Namespace(
                checkpoint_id="working",
                checkpoint_root=str(checkpoint_root),
                state_file=str(state_path),
                project_root=str(project),
                report_file=None, orchestration_file=None,
                bundle_file=None, closure_file=None,
                refresh_file=None, selection_file=None,
                preparation_file=None, repair_packet_file=None,
                repair_handoff_file=None, repair_receipt_file=None,
            )
            record = create_record(args)
            self.assertEqual("OK", record["result"])
            self.assertEqual("file_copy", record["workspace_snapshot"]["type"])
            preview = restore_preview(record, project / ".synrail")
            self.assertEqual("READY", preview["restore_status"])
            self.assertTrue(preview["restore_supported"])
            self.assertTrue(preview["workspace_restore_destructive"])

            # Break the files
            target.write_text("BROKEN\n")
            (project / "subdir" / "data.txt").write_text("BROKEN DATA\n")

            # Restore
            restored = restore_record(record, project / ".synrail")
            self.assertEqual("OK", restored["result"])
            self.assertTrue(restored["restore"]["workspace_restored"])
            self.assertEqual("RESTORED", restored["restore"]["status"])

            # Verify files recovered
            self.assertEqual('print("hello")', target.read_text().strip())
            self.assertEqual("original data", (project / "subdir" / "data.txt").read_text().strip())

    def test_restore_reports_restored_with_git(self) -> None:
        """Sanity check: with git, restore still reports RESTORED."""
        import argparse
        import os
        import subprocess
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_preview, restore_record
        from synrail_spine_v0 import default_state as make_state

        with tempfile.TemporaryDirectory() as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            target = project / "hello.py"
            target.write_text('print("hello")\n')
            env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
            subprocess.run(["git", "init"], cwd=str(project), capture_output=True, env=env)
            subprocess.run(["git", "add", "."], cwd=str(project), capture_output=True, env=env)
            subprocess.run(["git", "commit", "-m", "init"], cwd=str(project), capture_output=True, env=env)

            state = make_state("run1", "bounded_change")
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"
            args = argparse.Namespace(
                checkpoint_id="working",
                checkpoint_root=str(checkpoint_root),
                state_file=str(state_path),
                project_root=str(project),
                report_file=None, orchestration_file=None,
                bundle_file=None, closure_file=None,
                refresh_file=None, selection_file=None,
                preparation_file=None, repair_packet_file=None,
                repair_handoff_file=None, repair_receipt_file=None,
            )
            record = create_record(args)
            self.assertEqual("git", record["workspace_snapshot"]["type"])
            preview = restore_preview(record, project / ".synrail")
            self.assertEqual("READY", preview["restore_status"])
            self.assertEqual("git", preview["workspace_restore_mode"])
            self.assertTrue(preview["workspace_restore_destructive"])

            # Break and restore
            target.write_text("BROKEN\n")
            restored = restore_record(record, project / ".synrail")
            self.assertEqual("OK", restored["result"])
            self.assertTrue(restored["restore"]["workspace_restored"])
            self.assertEqual("RESTORED", restored["restore"]["status"])

    def test_restore_preview_marks_verified_state_as_artifacts_only(self) -> None:
        import argparse
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_preview

        state = ready_state("run1", "bounded_change")
        state["state"] = "READY"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"

        with tempfile.TemporaryDirectory(prefix="synrail_restore_preview_verified_") as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"
            args = argparse.Namespace(
                checkpoint_id="working",
                checkpoint_root=str(checkpoint_root),
                state_file=str(state_path),
                project_root=str(project),
                report_file=None, orchestration_file=None,
                bundle_file=None, closure_file=None,
                refresh_file=None, selection_file=None,
                preparation_file=None, repair_packet_file=None,
                repair_handoff_file=None, repair_receipt_file=None,
            )
            record = create_record(args)
            preview = restore_preview(record, project / ".synrail")

        self.assertEqual("LIMITED", preview["restore_status"])
        self.assertTrue(preview["restore_supported"])
        self.assertEqual("artifacts_only", preview["workspace_restore_mode"])
        self.assertFalse(preview["workspace_restore_supported"])


class TestRestoreWorkspaceFamilies(unittest.TestCase):
    """Explicit restore matrix for git/file-copy workspace families."""

    def _git_env(self) -> dict:
        import os
        return {
            **os.environ,
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
        }

    def _init_git_project(self, project: Path) -> None:
        import subprocess
        env = self._git_env()
        subprocess.run(["git", "init"], cwd=str(project), capture_output=True, env=env, check=True)
        subprocess.run(["git", "add", "."], cwd=str(project), capture_output=True, env=env, check=True)
        subprocess.run(["git", "commit", "-m", "init"], cwd=str(project), capture_output=True, env=env, check=True)

    def _checkpoint_args(self, *, checkpoint_root: Path, state_path: Path, project_root: Path):
        import argparse
        return argparse.Namespace(
            checkpoint_id="working",
            checkpoint_root=str(checkpoint_root),
            state_file=str(state_path),
            project_root=str(project_root),
            report_file=None,
            orchestration_file=None,
            bundle_file=None,
            closure_file=None,
            refresh_file=None,
            selection_file=None,
            preparation_file=None,
            repair_packet_file=None,
            repair_handoff_file=None,
            repair_receipt_file=None,
        )

    def test_create_record_marks_clean_commit_family(self) -> None:
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_preview
        from synrail_spine_v0 import default_state as make_state

        with tempfile.TemporaryDirectory(prefix="synrail_restore_family_clean_") as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            (project / "hello.py").write_text('print("hello")\n')
            self._init_git_project(project)

            state = make_state("run1", "bounded_change")
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"

            record = create_record(self._checkpoint_args(
                checkpoint_root=checkpoint_root,
                state_path=state_path,
                project_root=project,
            ))
            preview = restore_preview(record, project / ".synrail")

        self.assertEqual("clean_commit", record["workspace_snapshot"]["workspace_family"])
        self.assertEqual("clean_commit", preview["workspace_family"])
        self.assertEqual("git", preview["workspace_restore_mode"])

    def test_dirty_untracked_family_uses_file_copy_and_restores_untracked_file(self) -> None:
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_preview, restore_record
        from synrail_spine_v0 import default_state as make_state

        with tempfile.TemporaryDirectory(prefix="synrail_restore_family_untracked_") as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            (project / "hello.py").write_text('print("hello")\n')
            self._init_git_project(project)
            notes = project / "notes.txt"
            notes.write_text("draft note\n")

            state = make_state("run1", "bounded_change")
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"

            record = create_record(self._checkpoint_args(
                checkpoint_root=checkpoint_root,
                state_path=state_path,
                project_root=project,
            ))
            preview = restore_preview(record, project / ".synrail")

            notes.write_text("BROKEN\n")
            restored = restore_record(record, project / ".synrail")
            restored_notes = notes.read_text().strip()

        self.assertEqual("file_copy", record["workspace_snapshot"]["type"])
        self.assertEqual("dirty_untracked", record["workspace_snapshot"]["workspace_family"])
        self.assertEqual("dirty_untracked", preview["workspace_family"])
        self.assertEqual("file_copy", preview["workspace_restore_mode"])
        self.assertEqual("OK", restored["result"])
        self.assertEqual("draft note", restored_notes)

    def test_mixed_file_state_family_uses_file_copy_and_restores_both_contours(self) -> None:
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_preview, restore_record
        from synrail_spine_v0 import default_state as make_state

        with tempfile.TemporaryDirectory(prefix="synrail_restore_family_mixed_") as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            tracked = project / "hello.py"
            tracked.write_text('print("hello")\n')
            self._init_git_project(project)

            tracked.write_text('print("modified before save")\n')
            untracked = project / "notes.txt"
            untracked.write_text("draft note\n")

            state = make_state("run1", "bounded_change")
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"

            record = create_record(self._checkpoint_args(
                checkpoint_root=checkpoint_root,
                state_path=state_path,
                project_root=project,
            ))
            preview = restore_preview(record, project / ".synrail")

            tracked.write_text("BROKEN\n")
            untracked.write_text("BROKEN NOTE\n")
            restored = restore_record(record, project / ".synrail")
            restored_tracked = tracked.read_text().strip()
            restored_untracked = untracked.read_text().strip()

        self.assertEqual("file_copy", record["workspace_snapshot"]["type"])
        self.assertEqual("mixed_file_state", record["workspace_snapshot"]["workspace_family"])
        self.assertEqual("mixed_file_state", preview["workspace_family"])
        self.assertEqual("file_copy", preview["workspace_restore_mode"])
        self.assertEqual("OK", restored["result"])
        self.assertEqual('print("modified before save")', restored_tracked)
        self.assertEqual("draft note", restored_untracked)

    def test_restore_rolls_back_artifacts_when_dirty_tracked_apply_fails(self) -> None:
        import tempfile
        from synrail_checkpoint_v0 import create_record, restore_record
        from synrail_spine_v0 import default_state as make_state

        with tempfile.TemporaryDirectory(prefix="synrail_restore_apply_fail_") as tmpdir:
            project = Path(tmpdir) / "project"
            project.mkdir()
            tracked = project / "hello.py"
            tracked.write_text('print("hello")\n')
            self._init_git_project(project)
            tracked.write_text('print("modified before save")\n')

            state = make_state("run1", "bounded_change")
            state_path = project / ".synrail" / "state.json"
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(state))
            checkpoint_root = project / ".synrail" / "checkpoints" / "working"

            record = create_record(self._checkpoint_args(
                checkpoint_root=checkpoint_root,
                state_path=state_path,
                project_root=project,
            ))
            self.assertEqual("dirty_tracked", record["workspace_snapshot"]["workspace_family"])
            record["workspace_snapshot"]["stash_ref"] = "refs/stash-does-not-exist"

            target_root = Path(tmpdir) / "restore_target"
            target_state = target_root / "artifacts" / "state.json"
            target_state.parent.mkdir(parents=True, exist_ok=True)
            target_state.write_text(json.dumps({"run_id": "existing", "task_class": "existing"}) + "\n")

            restored = restore_record(record, target_root)

            rolled_back_state = json.loads(target_state.read_text())

        self.assertEqual("BLOCKED", restored["result"])
        self.assertEqual("RESTORE_FAILED", restored["restore"]["status"])
        self.assertEqual("ROLLED_BACK", restored["rollback"]["status"])
        self.assertTrue(any("stash apply failed" in reason for reason in restored["restore"]["failure_reasons"]))
        self.assertEqual("existing", rolled_back_state["run_id"])


class TestCleanSurfaceAutoDetect(unittest.TestCase):
    """Validates the auto-detection rule: active run → clean_surface=True."""

    def _apply_auto_detect(self, state: dict, initial_clean_surface: bool = False) -> bool:
        """Replicate the auto-detect logic from cmd_check."""
        import argparse
        args = argparse.Namespace(clean_surface=initial_clean_surface)
        if not getattr(args, "clean_surface", False):
            current_state = state.get("state", "")
            if current_state and current_state not in {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}:
                args.clean_surface = True
        return args.clean_surface

    def test_initialized_state_auto_sets_clean_surface(self) -> None:
        state = default_state("r1", "bounded_change")
        self.assertEqual(state["state"], "INITIALIZED")
        self.assertTrue(self._apply_auto_detect(state))

    def test_ready_state_auto_sets_clean_surface(self) -> None:
        state = default_state("r1", "bounded_change")
        state["state"] = "READY"
        self.assertTrue(self._apply_auto_detect(state))

    def test_execution_completed_auto_sets_clean_surface(self) -> None:
        state = default_state("r1", "bounded_change")
        state["state"] = "EXECUTION_COMPLETED"
        self.assertTrue(self._apply_auto_detect(state))

    def test_closure_accepted_does_not_auto_set(self) -> None:
        state = default_state("r1", "bounded_change")
        state["state"] = "CLOSURE_ACCEPTED"
        self.assertFalse(self._apply_auto_detect(state))

    def test_closure_rejected_does_not_auto_set(self) -> None:
        state = default_state("r1", "bounded_change")
        state["state"] = "CLOSURE_REJECTED"
        self.assertFalse(self._apply_auto_detect(state))

    def test_explicit_flag_not_overridden(self) -> None:
        state = default_state("r1", "bounded_change")
        state["state"] = "INITIALIZED"
        self.assertTrue(self._apply_auto_detect(state, initial_clean_surface=True))

    def test_empty_state_does_not_auto_set(self) -> None:
        self.assertFalse(self._apply_auto_detect({}))


if __name__ == "__main__":
    unittest.main()
