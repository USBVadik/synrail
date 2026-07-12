#!/usr/bin/env python3
"""Unit tests for previously-untested high-risk Synrail modules.

Covers:
  - synrail_repair_handoff_v0  (continuation_allowed, resumability_family,
    collect_active_pressures, build_artifact_quality_hints, build_repair_policy,
    build_required_input_ids, recommended_repair_order, build_repair_handoff)
  - synrail_repair_packet_v0   (build_repair_termination, merge_previous_packet_context,
    missing_input_ids, build_continuation_core, build_continuation_plan)
  - synrail_refresh_v0         (applicable_invalidations, dominant_invalidation, apply_event)
  - synrail_validate_v0        (validate_document)
  - synrail_thin_output_v0     (classify_outcome, status_label, human_next_step, summary_for)
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

# --- repair_handoff imports ---
from synrail_repair_handoff_v0 import (
    continuation_allowed,
    resumability_family,
    collect_active_pressures,
    build_artifact_quality_hints,
    build_repair_policy,
    build_required_input_ids,
    build_resumability,
    recommended_repair_order,
    build_repair_handoff,
    build_runtime_defaults,
)

# --- repair_packet imports ---
from synrail_repair_packet_v0 import (
    build_repair_termination,
    merge_previous_packet_context,
    missing_input_ids,
    build_continuation_core,
    build_continuation_plan,
    build_selection_context,
    provided_input_ids,
    scalar_arg,
)
from synrail_cli_v0 import apply_resume_output_defaults

# --- refresh imports ---
from synrail_refresh_v0 import (
    applicable_invalidations,
    dominant_invalidation,
    apply_event,
)

# --- validate imports ---
from synrail_validate_v0 import validate_document

# --- thin_output imports ---
from synrail_thin_output_v0 import (
    build_record as build_thin_output_record,
    classify_outcome,
    status_label,
    human_next_step,
    summary_for,
    checkpoint_restore_available,
    matching_recovery,
    resume_available,
    human_reason,
)

# --- operator imports ---
from synrail_operator_brief_v0 import build_record as build_operator_brief_record
from synrail_operator_brief_chain_v0 import build_record as build_operator_brief_chain_record
from synrail_operator_render_v0 import render_brief, render_chain

# --- spine imports (for default_state helper) ---
from synrail_spine_v0 import default_state


# ============================================================================
# Helpers
# ============================================================================

def _handoff_state(
    *,
    state_name: str = "DOCTOR_BLOCKED",
    doctor_status: str = "FAIL",
    doctor_failures: list[str] | None = None,
    proof_status: str = "INVALID",
    closure_status: str = "CLAIMED_NOT_ACCEPTED",
    closure_reason: str = "DOCTOR_NOT_GREEN",
    recovery_status: str = "NOT_REQUIRED",
    recovery_reverification: bool = False,
    run_id: str = "R1",
    task_class: str = "bounded_change",
) -> dict:
    """Build a minimal state dict for repair_handoff tests."""
    state = default_state(run_id, task_class)
    state["state"] = state_name
    state["doctor"]["status"] = doctor_status
    state["doctor"]["blocking_failure_classes"] = doctor_failures or []
    state["proof_bundle"]["status"] = proof_status
    state["closure"]["status"] = closure_status
    state["closure"]["blocking_reason"] = closure_reason
    state["closure"]["missing_sections"] = []
    state["recovery"]["status"] = recovery_status
    state["recovery"]["reverification_complete"] = recovery_reverification
    state["next_safe_step"] = "repair readiness"
    state["target_surface"]["status"] = "ATTESTED"
    state["integrity"]["bootstrap_provenance_ok"] = True
    state["integrity"]["exact_task_identity_ok"] = True
    state["execution"]["status"] = "COMPLETED"
    return state


def _accepted_state(run_id: str = "R1") -> dict:
    state = default_state(run_id, "bounded_change")
    state["state"] = "CLOSURE_ACCEPTED"
    state["closure"]["status"] = "ACCEPTED"
    state["closure"]["blocking_reason"] = ""
    state["next_safe_step"] = "NONE"
    return state


def _ready_state_for_closure(run_id: str = "R1") -> dict:
    """State that would pass all closure gates."""
    state = _handoff_state(
        state_name="PROOF_BUNDLE_COMPLETE",
        doctor_status="PASS",
        proof_status="COMPLETE",
        closure_status="CLAIMED_NOT_ACCEPTED",
        closure_reason="",
    )
    state["proof_bundle"]["missing_sections"] = []
    state["proof_bundle"]["semantically_insufficient_sections"] = []
    return state


# ============================================================================
# synrail_repair_handoff_v0 tests
# ============================================================================

class TestContinuationAllowed(unittest.TestCase):
    """continuation_allowed gates which states permit resume."""

    def test_doctor_blocked_allows(self) -> None:
        state = _handoff_state()
        self.assertTrue(continuation_allowed(state))

    def test_initialized_denies(self) -> None:
        state = _handoff_state(state_name="INITIALIZED")
        self.assertFalse(continuation_allowed(state))

    def test_target_surface_attested_denies(self) -> None:
        state = _handoff_state(state_name="TARGET_SURFACE_ATTESTED")
        self.assertFalse(continuation_allowed(state))

    def test_ready_denies(self) -> None:
        state = _handoff_state(state_name="READY")
        self.assertFalse(continuation_allowed(state))

    def test_closure_accepted_denies(self) -> None:
        state = _accepted_state()
        self.assertFalse(continuation_allowed(state))

    def test_closure_rejected_denies(self) -> None:
        state = _handoff_state(state_name="CLOSURE_REJECTED")
        state["closure"]["status"] = "REJECTED"
        # Even though state is CLOSURE_REJECTED, explicit check is on closure.status
        self.assertFalse(continuation_allowed(state))

    def test_mode_selection_blocked_denies(self) -> None:
        state = _handoff_state(closure_reason="MODE_SELECTION_NOT_GOVERNED")
        self.assertFalse(continuation_allowed(state))

    def test_proof_bundle_invalid_allows(self) -> None:
        state = _handoff_state(state_name="PROOF_BUNDLE_INVALID", proof_status="INVALID",
                               closure_reason="INVALID_PROOF_BUNDLE")
        self.assertTrue(continuation_allowed(state))


class TestCollectActivePressures(unittest.TestCase):
    """collect_active_pressures must detect the right pressure set."""

    def test_fresh_orchestration_on_initialized(self) -> None:
        state = _handoff_state(state_name="INITIALIZED")
        pressures = collect_active_pressures(state)
        self.assertIn("FRESH_ORCHESTRATION", pressures)

    def test_terminal_accepted(self) -> None:
        state = _accepted_state()
        pressures = collect_active_pressures(state)
        self.assertIn("TERMINAL_ACCEPTED", pressures)
        self.assertIn("TERMINAL_STATE", pressures)

    def test_terminal_rejected(self) -> None:
        state = _handoff_state(state_name="CLOSURE_REJECTED")
        state["closure"]["status"] = "REJECTED"
        pressures = collect_active_pressures(state)
        self.assertIn("TERMINAL_REJECTED", pressures)
        self.assertIn("TERMINAL_STATE", pressures)

    def test_doctor_blocked(self) -> None:
        state = _handoff_state(doctor_failures=["dirty-surface unsafe"])
        pressures = collect_active_pressures(state)
        self.assertIn("DOCTOR_BLOCKED", pressures)

    def test_invalid_proof(self) -> None:
        state = _handoff_state(state_name="PROOF_BUNDLE_INVALID", proof_status="INVALID",
                               closure_reason="INVALID_PROOF_BUNDLE")
        pressures = collect_active_pressures(state)
        self.assertIn("INVALID_PROOF", pressures)

    def test_partial_proof(self) -> None:
        state = _handoff_state(state_name="PROOF_BUNDLE_PARTIAL", proof_status="PARTIAL",
                               closure_reason="MISSING_PROOF_SECTIONS")
        state["proof_bundle"]["missing_sections"] = ["readback"]
        pressures = collect_active_pressures(state)
        self.assertIn("PARTIAL_PROOF", pressures)

    def test_recovery_pending(self) -> None:
        state = _handoff_state(state_name="RECOVERY_PENDING", recovery_status="PENDING")
        pressures = collect_active_pressures(state)
        self.assertIn("RECOVERY_PENDING", pressures)

    def test_selection_blocked(self) -> None:
        state = _handoff_state(closure_reason="MODE_SELECTION_NOT_GOVERNED")
        pressures = collect_active_pressures(state)
        self.assertIn("SELECTION_BLOCKED", pressures)


class TestResumabilityFamily(unittest.TestCase):
    """resumability_family classifies the right family string."""

    def test_fresh_orchestration(self) -> None:
        family = resumability_family(
            _handoff_state(state_name="INITIALIZED"),
            ["FRESH_ORCHESTRATION"],
            False,
        )
        self.assertEqual("NOT_RESUMABLE_FRESH_ORCHESTRATION", family)

    def test_terminal_accepted(self) -> None:
        family = resumability_family(_accepted_state(), ["TERMINAL_ACCEPTED", "TERMINAL_STATE"], False)
        self.assertEqual("NOT_RESUMABLE_TERMINAL_ACCEPTED", family)

    def test_terminal_rejected(self) -> None:
        state = _handoff_state(state_name="CLOSURE_REJECTED")
        state["closure"]["status"] = "REJECTED"
        family = resumability_family(state, ["TERMINAL_REJECTED", "TERMINAL_STATE"], False)
        self.assertEqual("NOT_RESUMABLE_TERMINAL_REJECTED", family)

    def test_selection_blocked(self) -> None:
        family = resumability_family(
            _handoff_state(), ["SELECTION_BLOCKED"], False,
        )
        self.assertEqual("NOT_RESUMABLE_SELECTION_BLOCKED", family)

    def test_single_doctor_blocked(self) -> None:
        family = resumability_family(_handoff_state(), ["DOCTOR_BLOCKED"], True)
        self.assertEqual("REPAIRABLE_DOCTOR_BLOCKED", family)

    def test_single_invalid_proof(self) -> None:
        family = resumability_family(_handoff_state(), ["INVALID_PROOF"], True)
        self.assertEqual("REPAIRABLE_INVALID_PROOF", family)

    def test_compound_pressures(self) -> None:
        family = resumability_family(_handoff_state(), ["DOCTOR_BLOCKED", "INVALID_PROOF"], True)
        self.assertEqual("REPAIRABLE_COMPOUND", family)

    def test_recovery_pending(self) -> None:
        family = resumability_family(_handoff_state(), ["RECOVERY_PENDING"], True)
        self.assertEqual("REPAIRABLE_RECOVERY_PENDING", family)

    def test_not_allowed_unknown(self) -> None:
        family = resumability_family(_handoff_state(), [], False)
        self.assertEqual("NOT_RESUMABLE_UNKNOWN", family)


class TestRecommendedRepairOrder(unittest.TestCase):
    """recommended_repair_order returns correct step lists."""

    def test_doctor_blocked_steps(self) -> None:
        steps = recommended_repair_order(["DOCTOR_BLOCKED"], "REPAIRABLE_DOCTOR_BLOCKED")
        self.assertEqual("restore_readiness_truth", steps[0])
        self.assertIn("rerun_closure", steps)

    def test_invalid_proof_steps(self) -> None:
        steps = recommended_repair_order(["INVALID_PROOF"], "REPAIRABLE_INVALID_PROOF")
        self.assertIn("repair_final_result_artifact", steps)
        self.assertIn("rebuild_proof_bundle", steps)
        self.assertIn("rerun_closure", steps)

    def test_compound_steps_cover_both(self) -> None:
        steps = recommended_repair_order(["DOCTOR_BLOCKED", "PARTIAL_PROOF"], "REPAIRABLE_COMPOUND")
        self.assertIn("restore_readiness_truth", steps)
        self.assertIn("complete_missing_proof_sections", steps)
        self.assertIn("rerun_closure", steps)

    def test_terminal_accepted_starts_new_run(self) -> None:
        steps = recommended_repair_order(["TERMINAL_ACCEPTED", "TERMINAL_STATE"], "NOT_RESUMABLE_TERMINAL_ACCEPTED")
        self.assertEqual(["start_new_run"], steps)

    def test_fresh_orchestration_continues_forward(self) -> None:
        steps = recommended_repair_order(["FRESH_ORCHESTRATION"], "NOT_RESUMABLE_FRESH_ORCHESTRATION")
        self.assertEqual(["continue_forward_orchestration"], steps)

    def test_unknown_family_inspects(self) -> None:
        steps = recommended_repair_order([], "NOT_RESUMABLE_UNKNOWN")
        self.assertEqual(["inspect_runtime_state"], steps)


class TestBuildArtifactQualityHints(unittest.TestCase):
    """build_artifact_quality_hints produces correct hints for various states."""

    def test_doctor_failure_produces_readiness_hint(self) -> None:
        state = _handoff_state(doctor_failures=["dirty-surface unsafe"])
        hints = build_artifact_quality_hints(state)
        readiness_hints = [h for h in hints if h["artifact_id"] == "readiness_surface"]
        self.assertEqual(1, len(readiness_hints))
        self.assertIn("clean_surface_confirmation", readiness_hints[0]["mapped_inputs"])

    def test_missing_final_result_produces_hint(self) -> None:
        state = _handoff_state(
            state_name="PROOF_BUNDLE_INVALID",
            proof_status="INVALID",
            closure_reason="INVALID_PROOF_BUNDLE",
        )
        state["proof_bundle"]["missing_sections"] = ["final_result"]
        hints = build_artifact_quality_hints(state)
        fr_hints = [h for h in hints if h["artifact_id"] == "final_result_artifact"]
        self.assertEqual(1, len(fr_hints))

    def test_missing_readback_produces_supporting_hint(self) -> None:
        state = _handoff_state(
            state_name="PROOF_BUNDLE_PARTIAL",
            proof_status="PARTIAL",
            closure_reason="MISSING_PROOF_SECTIONS",
        )
        state["proof_bundle"]["missing_sections"] = ["readback"]
        hints = build_artifact_quality_hints(state)
        supporting = [h for h in hints if h["artifact_id"] == "supporting_proof_artifacts"]
        self.assertEqual(1, len(supporting))
        self.assertIn("readback", supporting[0]["mapped_inputs"])

    def test_missing_readback_with_weak_final_result_also_produces_final_result_hint(self) -> None:
        state = _handoff_state(
            state_name="PROOF_BUNDLE_PARTIAL",
            proof_status="PARTIAL",
            closure_reason="MISSING_PROOF_SECTIONS",
        )
        state["proof_bundle"]["missing_sections"] = ["readback"]
        state["proof_bundle"]["final_result"] = {"semantically_sufficient": False}
        state["proof_bundle"]["verification_corroboration"] = {"semantically_sufficient": False}
        hints = build_artifact_quality_hints(state)
        final_result = [h for h in hints if h["artifact_id"] == "final_result_artifact"]
        supporting = [h for h in hints if h["artifact_id"] == "supporting_proof_artifacts"]
        self.assertEqual(1, len(final_result))
        self.assertEqual(1, len(supporting))
        self.assertIn("final_result_status_record", final_result[0]["still_stale_parts"])
        self.assertIn("diff_provenance_record", final_result[0]["still_stale_parts"])

    def test_recovery_pending_produces_recovery_hint(self) -> None:
        state = _handoff_state(
            state_name="RECOVERY_PENDING",
            doctor_status="PASS",
            proof_status="COMPLETE",
            recovery_status="PENDING",
            closure_reason="RECOVERY_REVERIFICATION_INCOMPLETE",
        )
        hints = build_artifact_quality_hints(state)
        recovery = [h for h in hints if h["artifact_id"] == "recovery_reverification_surface"]
        self.assertEqual(1, len(recovery))

    def test_closure_accepted_produces_terminal_hint(self) -> None:
        state = _accepted_state()
        hints = build_artifact_quality_hints(state)
        terminal = [h for h in hints if h["artifact_id"] == "terminal_run_state"]
        self.assertEqual(1, len(terminal))
        self.assertEqual("NON_RESUMABLE", terminal[0]["quality"])

    def test_initialized_produces_forward_hint(self) -> None:
        state = _handoff_state(state_name="INITIALIZED")
        hints = build_artifact_quality_hints(state)
        forward = [h for h in hints if h["artifact_id"] == "runtime_entrypoint_state"]
        self.assertEqual(1, len(forward))

    def test_no_issues_produces_fallback_hint(self) -> None:
        # State that has no doctor failures, no missing sections, no recovery, no terminal
        state = _handoff_state(
            state_name="EXECUTION_COMPLETED",
            doctor_status="PASS",
            doctor_failures=[],
            proof_status="COMPLETE",
            closure_reason="",
            recovery_status="NOT_REQUIRED",
        )
        hints = build_artifact_quality_hints(state)
        fallback = [h for h in hints if h["artifact_id"] == "runtime_state"]
        self.assertEqual(1, len(fallback))


class TestBuildRepairPolicy(unittest.TestCase):
    """build_repair_policy structures steps correctly."""

    def test_repairable_first_step_ready_now(self) -> None:
        resumability = {
            "status": "REPAIRABLE",
            "recommended_repair_order": ["restore_readiness_truth", "rerun_closure"],
            "active_pressures": ["DOCTOR_BLOCKED"],
        }
        hints = [{"artifact_id": "readiness_surface", "repair_step": "restore_readiness_truth", "mapped_inputs": ["clean_surface_confirmation"]}]
        policy = build_repair_policy(resumability, hints)
        self.assertEqual("MULTI_STEP_REPAIR", policy["policy_type"])
        self.assertEqual("restore_readiness_truth", policy["next_step_id"])
        self.assertIn("restore_readiness_truth", policy["ready_now_step_ids"])
        self.assertEqual("READY_NOW", policy["ordered_steps"][0]["status"])
        self.assertEqual("WAITING_ON_PREVIOUS_STEP", policy["ordered_steps"][1]["status"])

    def test_non_resumable_terminal_next_step(self) -> None:
        resumability = {
            "status": "NOT_RESUMABLE",
            "recommended_repair_order": ["start_new_run"],
            "active_pressures": ["TERMINAL_ACCEPTED"],
        }
        hints = []
        policy = build_repair_policy(resumability, hints)
        self.assertEqual("NON_RESUMABLE_NEXT_STEP", policy["policy_type"])
        self.assertEqual("TERMINAL_NEXT_STEP", policy["ordered_steps"][0]["status"])

    def test_final_result_only_partial_proof_promotes_final_result_repair(self) -> None:
        resumability = {
            "status": "REPAIRABLE",
            "recommended_repair_order": ["complete_missing_proof_sections", "rebuild_proof_bundle", "rerun_closure"],
            "active_pressures": ["PARTIAL_PROOF"],
        }
        hints = [
            {
                "artifact_id": "final_result_artifact",
                "repair_step": "repair_final_result_artifact",
                "mapped_inputs": ["final_result"],
            }
        ]
        policy = build_repair_policy(resumability, hints)
        self.assertEqual("repair_final_result_artifact", policy["next_step_id"])
        self.assertEqual("READY_NOW", policy["ordered_steps"][0]["status"])
        self.assertEqual(["final_result"], policy["ordered_steps"][0]["required_inputs"])

    def test_partial_proof_with_supporting_artifacts_still_promotes_final_result_repair(self) -> None:
        resumability = {
            "status": "REPAIRABLE",
            "recommended_repair_order": ["complete_missing_proof_sections", "rebuild_proof_bundle", "rerun_closure"],
            "active_pressures": ["PARTIAL_PROOF"],
        }
        hints = [
            {
                "artifact_id": "final_result_artifact",
                "repair_step": "repair_final_result_artifact",
                "mapped_inputs": ["final_result"],
            },
            {
                "artifact_id": "supporting_proof_artifacts",
                "repair_step": "complete_missing_proof_sections",
                "mapped_inputs": ["readback", "scenario_proof"],
            },
        ]
        policy = build_repair_policy(resumability, hints)
        self.assertEqual("repair_final_result_artifact", policy["next_step_id"])
        self.assertEqual("repair_final_result_artifact", policy["ready_now_step_ids"][0])
        self.assertEqual(["final_result"], policy["ordered_steps"][0]["required_inputs"])
        self.assertEqual("complete_missing_proof_sections", policy["ordered_steps"][1]["step_id"])


class TestBuildRequiredInputIds(unittest.TestCase):
    """build_required_input_ids maps hints to ready steps."""

    def test_collects_from_ready_steps_only(self) -> None:
        repair_policy = {"ready_now_step_ids": ["restore_readiness_truth"]}
        hints = [
            {"artifact_id": "readiness_surface", "repair_step": "restore_readiness_truth", "mapped_inputs": ["clean_surface_confirmation"]},
            {"artifact_id": "final_result_artifact", "repair_step": "repair_final_result_artifact", "mapped_inputs": ["final_result"]},
        ]
        ids = build_required_input_ids(repair_policy, hints)
        self.assertIn("clean_surface_confirmation", ids)
        self.assertNotIn("final_result", ids)


class TestBuildRuntimeDefaults(unittest.TestCase):
    """build_runtime_defaults sets refresh defaults when recovery inputs required."""

    def test_recovery_inputs_set_refresh_defaults(self) -> None:
        state = _handoff_state()
        defaults = build_runtime_defaults(state, ["refresh_recovery_complete"])
        self.assertEqual("RECOVERY_EVENT", defaults["refresh_event_type"])
        self.assertTrue(defaults["refresh_use_bundle"])
        self.assertTrue(defaults["refresh_use_closure"])

    def test_no_recovery_inputs_empty_defaults(self) -> None:
        state = _handoff_state()
        defaults = build_runtime_defaults(state, ["clean_surface_confirmation"])
        self.assertEqual("", defaults["refresh_event_type"])


class TestBuildRepairHandoffEndToEnd(unittest.TestCase):
    """build_repair_handoff produces a complete, well-formed handoff."""

    def test_doctor_blocked_handoff_structure(self) -> None:
        state = _handoff_state(doctor_failures=["dirty-surface unsafe"])
        handoff = build_repair_handoff(state)
        self.assertEqual("repair_handoff_v0", handoff["schema_version"])
        self.assertTrue(handoff["continuation_allowed"])
        self.assertEqual("resume", handoff["continuation_entrypoint"])
        self.assertEqual("REPAIRABLE", handoff["resumability"]["status"])
        self.assertIn("DOCTOR_BLOCKED", handoff["resumability"]["active_pressures"])
        self.assertGreater(len(handoff["repair_policy"]["ordered_steps"]), 0)

    def test_accepted_handoff_denies_continuation(self) -> None:
        state = _accepted_state()
        handoff = build_repair_handoff(state)
        self.assertFalse(handoff["continuation_allowed"])
        self.assertEqual("NOT_RESUMABLE", handoff["resumability"]["status"])
        self.assertTrue(handoff["resumability"]["requires_new_run"])


# ============================================================================
# synrail_repair_packet_v0 tests
# ============================================================================

class TestScalarArg(unittest.TestCase):
    def test_current_wins_when_present(self) -> None:
        self.assertEqual("A", scalar_arg("A", "B"))

    def test_fallback_when_none(self) -> None:
        self.assertEqual("B", scalar_arg(None, "B"))

    def test_fallback_when_empty(self) -> None:
        self.assertEqual("B", scalar_arg("", "B"))


class TestBuildRepairTermination(unittest.TestCase):
    """build_repair_termination gates repair loop exit."""

    def test_not_resumable_terminates(self) -> None:
        resumability = {"status": "NOT_RESUMABLE"}
        history = {"current_step_id": "restore_readiness_truth"}
        result = build_repair_termination(resumability=resumability, repair_history=history, repair_receipt=None)
        self.assertEqual("TERMINATE", result["status"])
        self.assertEqual("NON_RESUMABLE", result["reason"])

    def test_max_attempts_terminates(self) -> None:
        resumability = {"status": "REPAIRABLE"}
        history = {"current_step_id": "restore_readiness_truth"}
        receipt = {
            "repair_history_chain": [
                {"result": "STEP_COMPLETED", "active_step_id": "s1"},
                {"result": "STEP_COMPLETED", "active_step_id": "s2"},
                {"result": "STEP_COMPLETED", "active_step_id": "s3"},
            ]
        }
        result = build_repair_termination(resumability=resumability, repair_history=history, repair_receipt=receipt)
        self.assertEqual("TERMINATE", result["status"])
        self.assertEqual("MAX_REPAIR_ATTEMPTS", result["reason"])

    def test_no_progress_terminates(self) -> None:
        resumability = {"status": "REPAIRABLE"}
        history = {"current_step_id": "restore_readiness_truth"}
        receipt = {
            "repair_history_chain": [
                {"result": "STEP_NOT_COMPLETED", "active_step_id": "s1", "completed_step_id": "", "next_step_id": "s1"},
                {"result": "STEP_NOT_COMPLETED", "active_step_id": "s1", "completed_step_id": "", "next_step_id": "s1"},
            ]
        }
        result = build_repair_termination(resumability=resumability, repair_history=history, repair_receipt=receipt)
        self.assertEqual("TERMINATE", result["status"])
        self.assertEqual("NO_PROGRESS_DETECTED", result["reason"])

    def test_continue_when_below_limits(self) -> None:
        resumability = {"status": "REPAIRABLE"}
        history = {"current_step_id": "restore_readiness_truth"}
        receipt = {
            "repair_history_chain": [
                {"result": "STEP_COMPLETED", "active_step_id": "s1"},
            ]
        }
        result = build_repair_termination(resumability=resumability, repair_history=history, repair_receipt=receipt)
        self.assertEqual("CONTINUE", result["status"])
        self.assertEqual("", result["reason"])

    def test_continue_when_no_receipt(self) -> None:
        resumability = {"status": "REPAIRABLE"}
        history = {"current_step_id": "s1"}
        result = build_repair_termination(resumability=resumability, repair_history=history, repair_receipt=None)
        self.assertEqual("CONTINUE", result["status"])


class TestMergePreviousPacketContext(unittest.TestCase):
    """merge_previous_packet_context inherits from previous packet."""

    def test_scalar_inheritance(self) -> None:
        args = argparse.Namespace(
            doctor_run_id="", doctor_level="", target_path="", target_classification="",
            baseline_identity="", intended_run_class="", execution_surface_identity="",
            final_result="", prompt_identity="", task_identity="", readback="",
            scenario_proof="", target_identity_file="", artifact_path="", helper_path="",
            prompt_identity_ok=None, clean_surface=None, artifact_viable=None,
            helper_ok=None, credentials_ok=None, credential_env=[],
            refresh_event_type="", refresh_recovery_status="NOT_REQUIRED",
            refresh_reverification_complete=None, refresh_use_bundle=None,
            refresh_use_closure=None, refresh_output="",
        )
        previous = {
            "resume_context": {"doctor_run_id": "D1", "target_path": "/tmp/t"},
            "repair_inputs": {"final_result": "/tmp/fr.json", "clean_surface": True},
            "continuation_plan": {"refresh_event_type": "RECOVERY_EVENT"},
            "output_defaults": {},
        }
        merged = merge_previous_packet_context(args, previous)
        self.assertEqual("D1", merged.doctor_run_id)
        self.assertEqual("/tmp/t", merged.target_path)
        self.assertEqual("/tmp/fr.json", merged.final_result)
        # clean_surface: current is None → inherits True from previous
        self.assertTrue(merged.clean_surface)

    def test_explicit_overrides_previous(self) -> None:
        args = argparse.Namespace(
            doctor_run_id="D2", doctor_level="", target_path="", target_classification="",
            baseline_identity="", intended_run_class="", execution_surface_identity="",
            final_result="", prompt_identity="", task_identity="", readback="",
            scenario_proof="", target_identity_file="", artifact_path="", helper_path="",
            prompt_identity_ok=None, clean_surface=False, artifact_viable=None,
            helper_ok=None, credentials_ok=None, credential_env=[],
            refresh_event_type="", refresh_recovery_status="NOT_REQUIRED",
            refresh_reverification_complete=None, refresh_use_bundle=None,
            refresh_use_closure=None, refresh_output="",
        )
        previous = {
            "resume_context": {"doctor_run_id": "D1"},
            "repair_inputs": {"clean_surface": True},
            "continuation_plan": {},
            "output_defaults": {},
        }
        merged = merge_previous_packet_context(args, previous)
        self.assertEqual("D2", merged.doctor_run_id)
        # Explicit False overrides previous True
        self.assertFalse(merged.clean_surface)

    def test_old_packet_without_closure_certificate_output_still_sets_default(self) -> None:
        args = argparse.Namespace(
            state_file="/tmp/.synrail/state.json",
            doctor_output="",
            bundle_output="",
            closure_output="",
            closure_certificate_output="",
            refresh_output="",
            observability_output="",
            report_output="",
            worked_artifact_output="",
            run_artifact_output="",
            repair_packet_output="",
            plan_output="",
            preparation_receipt_output="",
        )
        state = {"run_id": "R1", "task_class": "bounded_change"}
        apply_resume_output_defaults(args, state)

        output_defaults = {
            "doctor_output": args.doctor_output,
            "bundle_output": args.bundle_output,
            "closure_output": args.closure_output,
            "refresh_output": args.refresh_output,
            "report_output": args.report_output,
            "worked_artifact_output": args.worked_artifact_output,
            "run_artifact_output": args.run_artifact_output,
            "repair_handoff_output": "/tmp/.synrail/repair_handoff.json",
            "repair_packet_output": args.repair_packet_output,
            "plan_output": args.plan_output,
            "preparation_receipt_output": args.preparation_receipt_output,
            "artifact_root": "/tmp/.synrail",
        }
        args.closure_certificate_output = ""

        for attr, value in [
            ("closure_output", output_defaults["closure_output"]),
            ("closure_certificate_output", output_defaults.get("closure_certificate_output", str(Path(output_defaults["closure_output"]).with_name("closure_certificate.json")))),
        ]:
            current = getattr(args, attr, None)
            if current in {None, ""} and value is not None:
                setattr(args, attr, value)

        self.assertTrue(str(args.closure_certificate_output).endswith("/closure_certificate.json"))


class TestMissingInputIds(unittest.TestCase):
    """missing_input_ids returns only inputs not yet provided."""

    def test_all_provided_returns_empty(self) -> None:
        handoff = {"required_inputs": [{"input_id": "clean_surface_confirmation"}, {"input_id": "final_result"}]}
        result = missing_input_ids(handoff, ["clean_surface_confirmation", "final_result"])
        self.assertEqual([], result)

    def test_missing_inputs_returned(self) -> None:
        handoff = {"required_inputs": [{"input_id": "clean_surface_confirmation"}, {"input_id": "final_result"}]}
        result = missing_input_ids(handoff, ["clean_surface_confirmation"])
        self.assertEqual(["final_result"], result)

    def test_empty_handoff_returns_empty(self) -> None:
        handoff = {"required_inputs": []}
        result = missing_input_ids(handoff, ["anything"])
        self.assertEqual([], result)


class TestBuildSelectionContext(unittest.TestCase):
    def test_empty_selection_context_keeps_empty_provenance_mix(self) -> None:
        context = build_selection_context(None)

        self.assertEqual([], context["selection_evidence_provenance_mix"])
        self.assertEqual(0, context["estimated_avoided_operator_minutes"])

    def test_selection_context_carries_provenance_mix_from_receipt(self) -> None:
        context = build_selection_context({
            "scenario_class": "repeatable_everyday_local",
            "recommended_mode": "LIGHTWEIGHT_BASELINE",
            "selected_mode": "LIGHTWEIGHT_BASELINE",
            "followed_recommendation": True,
            "governed_preparation_recommended": False,
            "selected_with_preparation": False,
            "heavier_contour_entered": False,
            "selection_evidence_provenance_mix": ["curated_local_estimate"],
            "estimated_avoided_operator_minutes": 1,
            "estimated_avoided_interventions": 1,
            "estimated_avoided_closure_latency_minutes": 1,
        })

        self.assertEqual(["curated_local_estimate"], context["selection_evidence_provenance_mix"])
        self.assertEqual(1, context["estimated_avoided_operator_minutes"])


class TestBuildContinuationPlan(unittest.TestCase):
    """build_continuation_plan sets refresh flags correctly."""

    def test_recovery_event_sets_refresh(self) -> None:
        args = argparse.Namespace(
            refresh_event_type="RECOVERY_EVENT",
            refresh_recovery_status="COMPLETE",
            refresh_reverification_complete=True,
            refresh_use_bundle=False,
            refresh_use_closure=False,
        )
        handoff = {"runtime_defaults": {}}
        plan = build_continuation_plan(args, handoff)
        self.assertTrue(plan["refresh_required"])
        self.assertTrue(plan["refresh_use_bundle"])
        self.assertTrue(plan["refresh_use_closure"])

    def test_no_event_no_refresh(self) -> None:
        args = argparse.Namespace(
            refresh_event_type="",
            refresh_recovery_status="NOT_REQUIRED",
            refresh_reverification_complete=False,
            refresh_use_bundle=False,
            refresh_use_closure=False,
        )
        handoff = {"runtime_defaults": {}}
        plan = build_continuation_plan(args, handoff)
        self.assertFalse(plan["refresh_required"])


class TestProvidedInputIds(unittest.TestCase):
    """provided_input_ids detects which inputs are supplied."""

    def test_clean_surface_detected(self) -> None:
        args = argparse.Namespace(
            prompt_identity="", task_identity="", target_identity_file="",
            clean_surface=True, artifact_path="", helper_path="",
            credentials_ok=False, credential_env=[], final_result="",
            readback="", scenario_proof="", refresh_recovery_status="NOT_REQUIRED",
            refresh_reverification_complete=False,
        )
        ids = provided_input_ids(args)
        self.assertIn("clean_surface_confirmation", ids)
        self.assertNotIn("final_result", ids)

    def test_final_result_detected(self) -> None:
        args = argparse.Namespace(
            prompt_identity="", task_identity="", target_identity_file="",
            clean_surface=False, artifact_path="", helper_path="",
            credentials_ok=False, credential_env=[], final_result="/tmp/fr.json",
            readback="", scenario_proof="", refresh_recovery_status="NOT_REQUIRED",
            refresh_reverification_complete=False,
        )
        ids = provided_input_ids(args)
        self.assertIn("final_result", ids)


# ============================================================================
# synrail_refresh_v0 tests
# ============================================================================

class TestApplicableInvalidations(unittest.TestCase):
    """applicable_invalidations detects the right invalidation set."""

    def test_doctor_fail_invalidates(self) -> None:
        state = _handoff_state(doctor_status="FAIL", proof_status="COMPLETE")
        inv = applicable_invalidations(state)
        self.assertIn("closure_invalidated_by_doctor", inv)

    def test_invalid_bundle_invalidates(self) -> None:
        state = _handoff_state(doctor_status="PASS", proof_status="INVALID")
        inv = applicable_invalidations(state)
        self.assertIn("closure_invalidated_by_invalid_bundle", inv)

    def test_structurally_complete_invalidates(self) -> None:
        state = _handoff_state(doctor_status="PASS", proof_status="STRUCTURALLY_COMPLETE")
        inv = applicable_invalidations(state)
        self.assertIn("closure_invalidated_by_semantic_bundle", inv)

    def test_partial_bundle_invalidates(self) -> None:
        state = _handoff_state(doctor_status="PASS", proof_status="PARTIAL")
        inv = applicable_invalidations(state)
        self.assertIn("closure_invalidated_by_partial_bundle", inv)

    def test_recovery_pending_invalidates(self) -> None:
        state = _handoff_state(doctor_status="PASS", proof_status="COMPLETE",
                               recovery_status="PENDING", recovery_reverification=False)
        inv = applicable_invalidations(state)
        self.assertIn("closure_invalidated_by_recovery", inv)

    def test_recovery_complete_does_not_invalidate(self) -> None:
        state = _handoff_state(doctor_status="PASS", proof_status="COMPLETE",
                               recovery_status="PENDING", recovery_reverification=True)
        inv = applicable_invalidations(state)
        self.assertNotIn("closure_invalidated_by_recovery", inv)

    def test_all_green_no_invalidations(self) -> None:
        state = _handoff_state(doctor_status="PASS", proof_status="COMPLETE",
                               recovery_status="NOT_REQUIRED")
        inv = applicable_invalidations(state)
        self.assertEqual([], inv)

    def test_unknown_bundle_status_caught_by_catchall(self) -> None:
        """The elif status != 'COMPLETE' catch-all catches unknown statuses."""
        state = _handoff_state(doctor_status="PASS", proof_status="SOME_UNKNOWN_VALUE")
        inv = applicable_invalidations(state)
        self.assertIn("closure_invalidated_by_partial_bundle", inv)


class TestDominantInvalidation(unittest.TestCase):
    """dominant_invalidation follows PRECEDENCE order."""

    def test_doctor_wins_over_bundle(self) -> None:
        inv = ["closure_invalidated_by_invalid_bundle", "closure_invalidated_by_doctor"]
        self.assertEqual("closure_invalidated_by_doctor", dominant_invalidation(inv))

    def test_invalid_bundle_wins_over_partial(self) -> None:
        inv = ["closure_invalidated_by_partial_bundle", "closure_invalidated_by_invalid_bundle"]
        self.assertEqual("closure_invalidated_by_invalid_bundle", dominant_invalidation(inv))

    def test_empty_returns_empty(self) -> None:
        self.assertEqual("", dominant_invalidation([]))

    def test_single_item(self) -> None:
        self.assertEqual("closure_invalidated_by_recovery", dominant_invalidation(["closure_invalidated_by_recovery"]))


class TestApplyEvent(unittest.TestCase):
    """apply_event correctly updates state through the refresh pipeline."""

    def test_doctor_pass_clears_invalidation(self) -> None:
        state = _handoff_state(doctor_status="PASS", proof_status="COMPLETE", recovery_status="NOT_REQUIRED")
        state["closure"]["status"] = "ACCEPTED"
        state["closure"]["blocking_reason"] = ""
        args = argparse.Namespace(
            event_type="DOCTOR_EVENT",
            doctor_status="PASS",
            bundle_file=None,
            closure_file=None,
            recovery_status=None,
            reverification_complete=False,
        )
        updated, report = apply_event(args, state)
        self.assertEqual("CLOSURE_ACCEPTED", updated["state"])
        self.assertEqual("ACCEPTED", report["resulting_closure_status"])

    def test_doctor_fail_invalidates_closure(self) -> None:
        state = _handoff_state(doctor_status="PASS", proof_status="COMPLETE", recovery_status="NOT_REQUIRED")
        state["closure"]["status"] = "ACCEPTED"
        args = argparse.Namespace(
            event_type="DOCTOR_EVENT",
            doctor_status="FAIL",
            bundle_file=None,
            closure_file=None,
            recovery_status=None,
            reverification_complete=False,
        )
        updated, report = apply_event(args, state)
        self.assertEqual("DOCTOR_BLOCKED", updated["state"])
        self.assertEqual("CLAIMED_NOT_ACCEPTED", report["resulting_closure_status"])
        self.assertEqual("closure_invalidated_by_doctor", report["dominant_invalidation"])

    def test_recovery_complete_restores_acceptance(self) -> None:
        """Recovery complete + green doctor + complete bundle → ACCEPTED."""
        state = _handoff_state(
            state_name="RECOVERY_PENDING",
            doctor_status="PASS",
            proof_status="COMPLETE",
            closure_status="CLAIMED_NOT_ACCEPTED",
            closure_reason="RECOVERY_REVERIFICATION_INCOMPLETE",
            recovery_status="PENDING",
            recovery_reverification=False,
        )
        args = argparse.Namespace(
            event_type="RECOVERY_EVENT",
            doctor_status=None,
            bundle_file=None,
            closure_file=None,
            recovery_status="COMPLETE",
            reverification_complete=True,
        )
        updated, report = apply_event(args, state)
        self.assertEqual("CLOSURE_ACCEPTED", updated["state"])
        self.assertEqual("ACCEPTED", report["resulting_closure_status"])


# ============================================================================
# synrail_validate_v0 tests
# ============================================================================

class TestValidateDocument(unittest.TestCase):
    """validate_document catches schema violations."""

    def test_valid_object(self) -> None:
        schema = {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "age": {"type": "integer", "minimum": 0},
            },
        }
        doc = {"name": "Alice", "age": 30}
        self.assertEqual([], validate_document(doc, schema))

    def test_missing_required_field(self) -> None:
        schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
        errors = validate_document({}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("missing required field", errors[0])

    def test_wrong_type(self) -> None:
        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        errors = validate_document({"name": 42}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("expected string", errors[0])

    def test_string_too_short(self) -> None:
        schema = {"type": "object", "properties": {"name": {"type": "string", "minLength": 3}}}
        errors = validate_document({"name": "ab"}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("minLength", errors[0])

    def test_integer_below_minimum(self) -> None:
        schema = {"type": "object", "properties": {"age": {"type": "integer", "minimum": 0}}}
        errors = validate_document({"age": -1}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("minimum", errors[0])

    def test_boolean_wrong_type(self) -> None:
        schema = {"type": "object", "properties": {"active": {"type": "boolean"}}}
        errors = validate_document({"active": "yes"}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("expected boolean", errors[0])

    def test_additional_properties_false(self) -> None:
        schema = {
            "type": "object",
            "additionalProperties": False,
            "properties": {"name": {"type": "string"}},
        }
        errors = validate_document({"name": "Alice", "extra": "field"}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("additional property", errors[0])

    def test_array_validation(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }
        errors = validate_document({"items": ["a", 2]}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("expected string", errors[0])

    def test_array_minimum_and_maximum_size(self) -> None:
        schema = {"type": "array", "minItems": 2, "maxItems": 3, "items": {"type": "string"}}
        too_short = validate_document(["one"], schema)
        too_long = validate_document(["one", "two", "three", "four"], schema)
        self.assertEqual(1, len(too_short))
        self.assertIn("minItems", too_short[0])
        self.assertEqual(1, len(too_long))
        self.assertIn("maxItems", too_long[0])

    def test_string_pattern_validation(self) -> None:
        schema = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
        self.assertEqual([], validate_document("a" * 64, schema))
        errors = validate_document("not-a-hash", schema)
        self.assertEqual(1, len(errors))
        self.assertIn("pattern", errors[0])

    def test_date_time_format_requires_timezone(self) -> None:
        schema = {"type": "string", "format": "date-time"}
        self.assertEqual([], validate_document("2026-07-12T12:34:56Z", schema))
        errors = validate_document("2026-07-12T12:34:56", schema)
        self.assertEqual(1, len(errors))
        self.assertIn("date-time", errors[0])

    def test_const_validation(self) -> None:
        schema = {"type": "object", "properties": {"version": {"type": "string", "const": "v1"}}}
        errors = validate_document({"version": "v2"}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("const", errors[0])

    def test_enum_validation(self) -> None:
        schema = {"type": "object", "properties": {"status": {"type": "string", "enum": ["PASS", "FAIL"]}}}
        errors = validate_document({"status": "MAYBE"}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("expected one of", errors[0])

    def test_nested_object(self) -> None:
        schema = {
            "type": "object",
            "properties": {
                "inner": {
                    "type": "object",
                    "required": ["x"],
                    "properties": {"x": {"type": "integer"}},
                },
            },
        }
        errors = validate_document({"inner": {}}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("$.inner.x", errors[0])

    def test_integer_rejects_bool(self) -> None:
        """Python bool is subclass of int — validator must reject it."""
        schema = {"type": "object", "properties": {"count": {"type": "integer"}}}
        errors = validate_document({"count": True}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("expected integer", errors[0])

    def test_expected_array_gets_object(self) -> None:
        schema = {"type": "object", "properties": {"list": {"type": "array"}}}
        errors = validate_document({"list": {}}, schema)
        self.assertEqual(1, len(errors))
        self.assertIn("expected array", errors[0])


# ============================================================================
# synrail_thin_output_v0 tests
# ============================================================================

class TestClassifyOutcome(unittest.TestCase):
    """classify_outcome maps state/report to outcome codes."""

    def test_accepted(self) -> None:
        state = {"state": "CLOSURE_ACCEPTED", "closure": {"status": "ACCEPTED"}, "proof_bundle": {"status": "COMPLETE"}}
        report = {"closure_status": "ACCEPTED"}
        self.assertEqual("ACCEPTED", classify_outcome(state=state, report=report, repair_packet=None, doctor=None))

    def test_non_resumable_by_termination(self) -> None:
        state = {"state": "DOCTOR_BLOCKED", "closure": {"status": ""}, "proof_bundle": {"status": ""}}
        report = {"reason": "NON_RESUMABLE", "repair_termination_reason": "NON_RESUMABLE"}
        self.assertEqual("NON_RESUMABLE", classify_outcome(state=state, report=report, repair_packet=None, doctor=None))

    def test_closure_rejected(self) -> None:
        state = {"state": "CLOSURE_REJECTED", "closure": {"status": "REJECTED"}, "proof_bundle": {"status": ""}}
        report = {"closure_status": "REJECTED", "reason": ""}
        self.assertEqual("CLOSURE_REJECTED", classify_outcome(state=state, report=report, repair_packet=None, doctor=None))

    def test_proof_invalid(self) -> None:
        state = {"state": "PROOF_BUNDLE_INVALID", "closure": {"status": ""}, "proof_bundle": {"status": "INVALID"}}
        report = {"reason": "INVALID_PROOF_BUNDLE"}
        self.assertEqual("PROOF_INVALID", classify_outcome(state=state, report=report, repair_packet=None, doctor=None))

    def test_proof_thin(self) -> None:
        state = {"state": "PROOF_BUNDLE_STRUCTURALLY_COMPLETE", "closure": {"status": ""}, "proof_bundle": {"status": "STRUCTURALLY_COMPLETE"}}
        report = {"reason": "SEMANTIC_PROOF_INSUFFICIENT"}
        self.assertEqual("PROOF_THIN", classify_outcome(state=state, report=report, repair_packet=None, doctor=None))

    def test_proof_partial(self) -> None:
        state = {"state": "PROOF_BUNDLE_PARTIAL", "closure": {"status": ""}, "proof_bundle": {"status": "PARTIAL"}}
        report = {"reason": "MISSING_PROOF_SECTIONS"}
        self.assertEqual("PROOF_PARTIAL", classify_outcome(state=state, report=report, repair_packet=None, doctor=None))

    def test_repair_stop(self) -> None:
        state = {"state": "DOCTOR_BLOCKED", "closure": {"status": ""}, "proof_bundle": {"status": ""}}
        report = {"reason": "", "repair_termination_reason": "MAX_REPAIR_ATTEMPTS"}
        self.assertEqual("REPAIR_STOP", classify_outcome(state=state, report=report, repair_packet=None, doctor=None))

    def test_doctor_blocked(self) -> None:
        state = {"state": "DOCTOR_BLOCKED", "closure": {"status": ""}, "proof_bundle": {"status": ""}}
        report = {"reason": "DOCTOR_NOT_GREEN"}
        doctor = {"blocking_failure_classes": ["helper-integrity unknown"]}
        self.assertEqual("DOCTOR_BLOCKED", classify_outcome(state=state, report=report, repair_packet=None, doctor=doctor))

    def test_scope_violation_on_dirty_surface(self) -> None:
        state = {"state": "DOCTOR_BLOCKED", "closure": {"status": ""}, "proof_bundle": {"status": ""}}
        report = {"reason": "DOCTOR_NOT_GREEN"}
        doctor = {"blocking_failure_classes": ["dirty-surface unsafe"]}
        self.assertEqual("SCOPE_VIOLATION", classify_outcome(state=state, report=report, repair_packet=None, doctor=doctor))

    def test_non_green_fallback(self) -> None:
        state = {"state": "SOME_STATE", "closure": {"status": ""}, "proof_bundle": {"status": ""}}
        report = {"reason": "ACCEPTANCE_CRITERIA_STALE"}
        self.assertEqual("NON_GREEN", classify_outcome(state=state, report=report, repair_packet=None, doctor=None))


class TestStatusLabel(unittest.TestCase):
    """status_label returns human-readable labels."""

    def test_accepted(self) -> None:
        self.assertEqual("Accepted", status_label("ACCEPTED", report={}, repair_packet=None))

    def test_proof_invalid(self) -> None:
        self.assertEqual("Proof Invalid", status_label("PROOF_INVALID", report={}, repair_packet=None))

    def test_proof_thin(self) -> None:
        self.assertEqual("Proof Too Thin To Trust", status_label("PROOF_THIN", report={}, repair_packet=None))

    def test_repair_stop(self) -> None:
        self.assertEqual("Repair Stopped", status_label("REPAIR_STOP", report={}, repair_packet=None))

    def test_scope_violation(self) -> None:
        self.assertEqual("Workspace Not Trusted", status_label("SCOPE_VIOLATION", report={}, repair_packet=None))

    def test_doctor_blocked(self) -> None:
        self.assertEqual("Workspace Not Ready", status_label("DOCTOR_BLOCKED", report={}, repair_packet=None))

    def test_non_resumable(self) -> None:
        self.assertEqual("Cannot Continue This Run", status_label("NON_RESUMABLE", report={}, repair_packet=None))

    def test_continuation_inputs_missing(self) -> None:
        label = status_label("NON_GREEN", report={"reason": "CONTINUATION_INPUTS_MISSING"}, repair_packet=None)
        self.assertEqual("Finish This Repair First", label)

    def test_acceptance_stale(self) -> None:
        label = status_label("NON_GREEN", report={"reason": "ACCEPTANCE_CRITERIA_STALE"}, repair_packet=None)
        self.assertEqual("Acceptance Rules Need Refresh", label)

    def test_controlled_bootstrap(self) -> None:
        label = status_label("NON_GREEN", report={"reason": "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"}, repair_packet=None)
        self.assertEqual("Controlled Run Required", label)

    def test_arbiter_unresolved(self) -> None:
        packet = {"continuation_arbiter": {"resolution_status": "CONFLICT_UNRESOLVED"}}
        label = status_label("NON_GREEN", report={}, repair_packet=packet)
        self.assertEqual("Continuation Still Ambiguous", label)


class TestHumanNextStep(unittest.TestCase):
    """human_next_step returns actionable English sentences."""

    def test_accepted(self) -> None:
        result = human_next_step(outcome_class="ACCEPTED", raw_next_step="", report={}, repair_packet=None, doctor=None)
        self.assertEqual("No repair step is required.", result)

    def test_proof_invalid(self) -> None:
        result = human_next_step(outcome_class="PROOF_INVALID", raw_next_step="", report={}, repair_packet=None, doctor=None)
        self.assertIn("proof", result.lower())

    def test_repair_stop(self) -> None:
        result = human_next_step(outcome_class="REPAIR_STOP", raw_next_step="", report={}, repair_packet=None, doctor=None)
        self.assertIn("new run", result.lower())

    def test_scope_violation_dirty(self) -> None:
        doctor = {"blocking_failure_classes": ["dirty-surface unsafe"]}
        result = human_next_step(outcome_class="SCOPE_VIOLATION", raw_next_step="", report={}, repair_packet=None, doctor=doctor)
        self.assertIn("clean", result.lower())

    def test_scope_violation_identity(self) -> None:
        doctor = {"blocking_failure_classes": ["baseline-identity ambiguous"]}
        result = human_next_step(outcome_class="SCOPE_VIOLATION", raw_next_step="", report={}, repair_packet=None, doctor=doctor)
        self.assertIn("target", result.lower())


class TestSummaryFor(unittest.TestCase):
    """summary_for returns (summary, diagnosis) tuples."""

    def test_accepted(self) -> None:
        summary, diagnosis = summary_for("ACCEPTED", restore_available=False, recovery=None, report={}, repair_packet=None)
        self.assertIn("accepted", summary.lower())

    def test_non_resumable(self) -> None:
        summary, diagnosis = summary_for("NON_RESUMABLE", restore_available=False, recovery=None, report={}, repair_packet=None)
        self.assertIn("cannot continue", summary.lower())

    def test_restore_available_appended(self) -> None:
        summary, diagnosis = summary_for("NON_RESUMABLE", restore_available=True, recovery=None, report={}, repair_packet=None)
        self.assertIn("checkpoint", diagnosis.lower())

    def test_proof_thin(self) -> None:
        summary, diagnosis = summary_for("PROOF_THIN", restore_available=False, recovery=None, report={}, repair_packet=None)
        self.assertIn("not strong enough", summary.lower())


class TestThinOutputBuildRecord(unittest.TestCase):
    """build_record should surface exact thin proof sections."""

    def test_includes_thin_section_guidance(self) -> None:
        state = default_state("R1", "bounded_change")
        state["state"] = "PROOF_BUNDLE_STRUCTURALLY_COMPLETE"
        state["proof_bundle"]["status"] = "STRUCTURALLY_COMPLETE"
        state["proof_bundle"]["semantically_insufficient_sections"] = ["diff_provenance", "verification_corroboration", "scenario_proof"]
        report = {"reason": "SEMANTIC_PROOF_INSUFFICIENT", "result": "NON_GREEN"}
        record = build_thin_output_record(
            state=state,
            report=report,
            mode="default",
            repair_packet=None,
            doctor=None,
            checkpoint=None,
            recovery=None,
            refresh=None,
        )
        self.assertIn(
            "diff_provenance: prove the patch on the changed files with a patch-shaped git_diff or a structured diff_provenance record",
            record["thin_section_guidance"],
        )
        self.assertIn(
            "verification_corroboration: tie acceptance to explicit local verification evidence: either structured diff_provenance or a labeled scenario Command plus Observed or Result record, not prose-only proof",
            record["thin_section_guidance"],
        )
        self.assertIn(
            "scenario_proof: record a scenario-proof with a labeled Command and Observed or Result line, plus explicit pass/fail \u2014 do not just restate the task",
            record["thin_section_guidance"],
        )

    def test_refresh_change_impact_narrows_doctor_guidance(self) -> None:
        state = _handoff_state(state_name="DOCTOR_BLOCKED", doctor_status="FAIL", proof_status="COMPLETE", closure_reason="DOCTOR_NOT_GREEN")
        report = {"reason": "DOCTOR_NOT_GREEN", "result": "NON_GREEN", "next_safe_step": "repair readiness"}
        refresh = {
            "run_id": "R1",
            "invalidations": ["closure_invalidated_by_doctor"],
            "dominant_invalidation": "closure_invalidated_by_doctor",
            "next_safe_step": "run doctor and clear blocking failure classes",
        }
        record = build_thin_output_record(
            state=state,
            report=report,
            mode="default",
            repair_packet=None,
            doctor={"blocking_failure_classes": ["helper-integrity unknown"]},
            checkpoint=None,
            recovery=None,
            refresh=refresh,
        )
        self.assertEqual("A refresh invalidated closure because readiness became stale.", record["summary"])
        self.assertEqual("Repair only readiness, then rerun synrail check.", record["what_to_do_next"])
        self.assertEqual("Repair only readiness, then rerun synrail check.", record["action_now"])
        self.assertEqual("refresh change impact: closure invalidated by doctor", record["change_impact_focus"])
        self.assertEqual("applicable invalidations: closure invalidated by doctor", record["change_impact_scope"])
        self.assertEqual("run doctor and clear blocking failure classes", record["next_step"])

    def test_refresh_change_impact_appears_in_dev_technical_lines(self) -> None:
        state = _handoff_state(state_name="PROOF_BUNDLE_STRUCTURALLY_COMPLETE", doctor_status="PASS", proof_status="STRUCTURALLY_COMPLETE", closure_reason="SEMANTIC_PROOF_INSUFFICIENT")
        report = {"reason": "SEMANTIC_PROOF_INSUFFICIENT", "result": "NON_GREEN", "next_safe_step": "strengthen the semantic proof evidence before trusting closure"}
        refresh = {
            "run_id": "R1",
            "invalidations": ["closure_invalidated_by_semantic_bundle", "closure_invalidated_by_recovery"],
            "dominant_invalidation": "closure_invalidated_by_semantic_bundle",
            "next_safe_step": "strengthen the semantic proof evidence before trusting closure",
        }
        record = build_thin_output_record(
            state=state,
            report=report,
            mode="dev",
            repair_packet=None,
            doctor=None,
            checkpoint=None,
            recovery=None,
            refresh=refresh,
        )
        self.assertIn("dominant_invalidation=closure_invalidated_by_semantic_bundle", record["technical_lines"])
        self.assertIn("invalidations=closure_invalidated_by_semantic_bundle,closure_invalidated_by_recovery", record["technical_lines"])

    def test_refresh_change_impact_narrows_to_exact_stale_proof_surface(self) -> None:
        state = _handoff_state(
            state_name="PROOF_BUNDLE_STRUCTURALLY_COMPLETE",
            doctor_status="PASS",
            proof_status="STRUCTURALLY_COMPLETE",
            closure_reason="SEMANTIC_PROOF_INSUFFICIENT",
        )
        report = {
            "reason": "SEMANTIC_PROOF_INSUFFICIENT",
            "result": "NON_GREEN",
            "next_safe_step": "strengthen the semantic proof evidence before trusting closure",
        }
        state["proof_bundle"]["final_result"] = {"semantically_sufficient": True}
        state["proof_bundle"]["verification_corroboration"] = {"semantically_sufficient": True}
        state["proof_bundle"]["artifact_identity"] = {"semantically_sufficient": True}
        state["proof_bundle"]["scenario_proof"] = {"semantically_sufficient": False}
        state["proof_bundle"]["diff_provenance"] = {"semantically_sufficient": False}
        refresh = {
            "run_id": "R1",
            "invalidations": ["closure_invalidated_by_semantic_bundle", "closure_invalidated_by_recovery"],
            "dominant_invalidation": "closure_invalidated_by_semantic_bundle",
            "next_safe_step": "strengthen the semantic proof evidence before trusting closure",
        }
        repair_packet = {
            "continuation_core": {
                "current_step_id": "repair_proof_bundle",
                "current_step_subsurface_id": "scenario_proof_record",
                "current_step_target_path": ".synrail/scenario_proof.txt",
                "next_step_subsurface_ids": ["scenario_proof_record", "diff_provenance_record"],
            }
        }
        record = build_thin_output_record(
            state=state,
            report=report,
            mode="default",
            repair_packet=repair_packet,
            doctor=None,
            checkpoint=None,
            recovery=None,
            refresh=refresh,
        )
        self.assertEqual(
            "Repair only this stale proof surface before trusting closure again: record scenario proof in .synrail/scenario_proof.txt.",
            record["diagnosis"],
        )
        self.assertEqual(
            "Record scenario proof in .synrail/scenario_proof.txt. Leave every other proof surface unchanged. Then rerun synrail check.",
            record["what_to_do_next"],
        )
        self.assertEqual(
            "Record scenario proof in .synrail/scenario_proof.txt. Leave every other proof surface unchanged. Then rerun synrail check.",
            record["action_now"],
        )
        self.assertEqual(
            "refresh change impact: closure invalidated by semantic bundle; repair target: record scenario proof in .synrail/scenario_proof.txt",
            record["change_impact_focus"],
        )
        self.assertEqual(
            "applicable invalidations: scenario proof record, diff provenance record; reusable proof surfaces: final result, verification corroboration, artifact identity",
            record["change_impact_scope"],
        )
        self.assertEqual("strengthen the semantic proof evidence before trusting closure", record["next_step"])

    def test_refresh_change_impact_narrows_invalid_bundle_to_exact_final_result_target(self) -> None:
        state = _handoff_state(
            state_name="PROOF_BUNDLE_INVALID",
            doctor_status="PASS",
            proof_status="INVALID",
            closure_reason="INVALID_PROOF_BUNDLE",
        )
        report = {
            "reason": "INVALID_PROOF_BUNDLE",
            "result": "NON_GREEN",
            "next_safe_step": "repair the final-result proof artifact before trusting closure",
        }
        state["proof_bundle"]["missing_sections"] = []
        state["proof_bundle"]["semantically_insufficient_sections"] = []
        state["proof_bundle"]["final_result"] = {"semantically_sufficient": False}
        state["proof_bundle"]["verification_corroboration"] = {"semantically_sufficient": True}
        state["proof_bundle"]["artifact_identity"] = {"semantically_sufficient": True}
        refresh = {
            "run_id": "R1",
            "invalidations": ["closure_invalidated_by_invalid_bundle"],
            "dominant_invalidation": "closure_invalidated_by_invalid_bundle",
            "next_safe_step": "repair the final-result proof artifact before trusting closure",
        }
        repair_packet = {
            "continuation_core": {
                "current_step_id": "repair_final_result_artifact",
                "current_step_subsurface_id": "final_result_payload",
                "current_step_target_path": ".synrail/final_result.json",
            }
        }
        record = build_thin_output_record(
            state=state,
            report=report,
            mode="default",
            repair_packet=repair_packet,
            doctor=None,
            checkpoint=None,
            recovery=None,
            refresh=refresh,
        )
        self.assertEqual(
            "A refresh invalidated closure because the final-result proof artifact became stale.",
            record["summary"],
        )
        self.assertEqual(
            "Repair only this stale proof surface before trusting closure again: update the result payload in .synrail/final_result.json.",
            record["diagnosis"],
        )
        self.assertEqual(
            "Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged. Then rerun synrail check.",
            record["what_to_do_next"],
        )
        self.assertEqual(
            "Update the result payload in .synrail/final_result.json. Leave every other proof surface unchanged. Then rerun synrail check.",
            record["action_now"],
        )
        self.assertEqual(
            "refresh change impact: closure invalidated by invalid bundle; repair target: update the result payload in .synrail/final_result.json",
            record["change_impact_focus"],
        )
        self.assertEqual(
            "applicable invalidations: final result payload; reusable proof surfaces: verification corroboration, artifact identity",
            record["change_impact_scope"],
        )
        self.assertEqual("repair the final-result proof artifact before trusting closure", record["next_step"])

    def test_refresh_change_impact_narrows_partial_bundle_to_single_missing_section(self) -> None:
        state = _handoff_state(
            state_name="PROOF_BUNDLE_PARTIAL",
            doctor_status="PASS",
            proof_status="PARTIAL",
            closure_reason="MISSING_PROOF_SECTIONS",
        )
        report = {
            "reason": "MISSING_PROOF_SECTIONS",
            "result": "NON_GREEN",
            "next_safe_step": "complete the missing proof sections before trusting closure",
        }
        state["proof_bundle"]["missing_sections"] = ["readback"]
        state["proof_bundle"]["semantically_insufficient_sections"] = []
        state["proof_bundle"]["final_result"] = {"semantically_sufficient": True}
        state["proof_bundle"]["verification_corroboration"] = {"semantically_sufficient": True}
        state["proof_bundle"]["artifact_identity"] = {"semantically_sufficient": True}
        state["proof_bundle"]["readback"] = {"semantically_sufficient": False}
        refresh = {
            "run_id": "R1",
            "invalidations": ["closure_invalidated_by_partial_bundle"],
            "dominant_invalidation": "closure_invalidated_by_partial_bundle",
            "next_safe_step": "complete the missing proof sections before trusting closure",
        }
        repair_packet = {
            "continuation_core": {
                "current_step_id": "complete_missing_proof_sections",
                "current_step_subsurface_id": "readback_record",
                "current_step_target_path": ".synrail/readback.txt",
                "next_step_subsurface_ids": ["readback_record"],
            }
        }
        record = build_thin_output_record(
            state=state,
            report=report,
            mode="default",
            repair_packet=repair_packet,
            doctor=None,
            checkpoint=None,
            recovery=None,
            refresh=refresh,
        )
        self.assertEqual(
            "A refresh invalidated closure because required proof sections became stale.",
            record["summary"],
        )
        self.assertEqual(
            "Repair only this stale proof surface before trusting closure again: record readback in .synrail/readback.txt.",
            record["diagnosis"],
        )
        self.assertEqual(
            "Record readback in .synrail/readback.txt. Leave every other proof surface unchanged. Then rerun synrail check.",
            record["what_to_do_next"],
        )
        self.assertEqual(
            "Record readback in .synrail/readback.txt. Leave every other proof surface unchanged. Then rerun synrail check.",
            record["action_now"],
        )
        self.assertEqual(
            "refresh change impact: closure invalidated by partial bundle; repair target: record readback in .synrail/readback.txt",
            record["change_impact_focus"],
        )
        self.assertEqual(
            "applicable invalidations: readback record; reusable proof surfaces: final result, verification corroboration, artifact identity",
            record["change_impact_scope"],
        )
        self.assertEqual("complete the missing proof sections before trusting closure", record["next_step"])


class TestOperatorBriefAndRender(unittest.TestCase):
    """operator brief and render surface reusable proof sections."""

    def test_surfaces_reusable_proof_surfaces(self) -> None:
        state = _handoff_state(
            state_name="PROOF_BUNDLE_STRUCTURALLY_COMPLETE",
            doctor_status="PASS",
            proof_status="STRUCTURALLY_COMPLETE",
            closure_reason="SEMANTIC_PROOF_INSUFFICIENT",
        )
        report = {
            "result": "NON_GREEN",
            "stopping_stage": "closure",
            "reason": "SEMANTIC_PROOF_INSUFFICIENT",
            "next_safe_step": "strengthen the semantic proof evidence before trusting closure",
        }
        packet = {
            "resumability": {"status": "REPAIRABLE", "family": "REPAIRABLE_PROOF"},
            "repair_termination": {"status": "CONTINUE", "reason": "", "attempt_count": 0},
            "repair_policy": {"next_step_id": "repair_proof_bundle", "ready_now_step_ids": ["repair_proof_bundle"]},
            "repair_history": {"history_chain_length": 1, "completed_step_ids": []},
            "continuation_core": {
                "next_safe_step": "strengthen the semantic proof evidence before trusting closure",
                "operator_focus": "repair only the stale proof surfaces",
                "current_step_id": "repair_proof_bundle",
                "current_step_subsurface_id": "scenario_proof_record",
                "current_step_target_path": ".synrail/scenario_proof.txt",
                "next_step_required_inputs": ["refresh_reverification_complete"],
                "next_step_subsurface_ids": ["scenario_proof_record", "diff_provenance_record"],
            },
            "artifact_quality_summary": {
                "stale_artifact_ids": ["supporting_proof_artifacts"],
                "stale_subsurface_ids": ["scenario_proof_record", "diff_provenance_record"],
            },
            "repair_handoff": {
                "state": {
                    "proof_bundle": {
                        "missing_sections": ["scenario_proof", "diff_provenance"],
                        "semantically_insufficient_sections": ["scenario_proof", "diff_provenance"],
                        "final_result": {"semantically_sufficient": True},
                        "verification_corroboration": {"semantically_sufficient": True},
                        "artifact_identity": {"semantically_sufficient": True},
                        "scenario_proof": {"semantically_sufficient": False},
                        "diff_provenance": {"semantically_sufficient": False},
                    }
                }
            },
        }
        brief = build_operator_brief_record(
            state=state,
            report=report,
            packet=packet,
            doctor=None,
            state_file=".synrail/state.json",
            repair_packet_file=".synrail/repair_packet.json",
        )
        self.assertEqual(
            ["final result", "verification corroboration", "artifact identity"],
            brief["reusable_proof_surfaces"],
        )
        rendered = render_brief(brief)
        self.assertIn("## Reusable proof surfaces", rendered)
        self.assertIn("- `final result`", rendered)
        with tempfile.TemporaryDirectory() as tmpdir:
            brief_path = Path(tmpdir) / "stage0_operator_brief.json"
            brief_path.write_text(json.dumps(brief, indent=2, ensure_ascii=True) + "\n")
            chain = build_operator_brief_chain_record([brief_path])
        self.assertEqual(
            ["final result", "verification corroboration", "artifact identity"],
            chain["stage_summaries"][0]["reusable_proof_surfaces"],
        )
        chain_render = render_chain(chain)
        self.assertIn("- reusable proof surfaces:", chain_render)
        self.assertIn("- `verification corroboration`", chain_render)


class TestCheckpointRestoreAvailable(unittest.TestCase):
    """checkpoint_restore_available gates restore eligibility."""

    def test_valid_checkpoint(self) -> None:
        checkpoint = {
            "safe_point_eligible": True,
            "verification": {"status": "PASSED"},
            "run_id": "R1",
            "task_class": "bounded_change",
        }
        state = {"run_id": "R1", "task_class": "bounded_change"}
        self.assertTrue(checkpoint_restore_available(checkpoint, state=state))

    def test_none_checkpoint(self) -> None:
        self.assertFalse(checkpoint_restore_available(None, state={"run_id": "R1", "task_class": "t"}))

    def test_mismatched_run_id(self) -> None:
        checkpoint = {
            "safe_point_eligible": True,
            "verification": {"status": "PASSED"},
            "run_id": "R2",
            "task_class": "bounded_change",
        }
        state = {"run_id": "R1", "task_class": "bounded_change"}
        self.assertFalse(checkpoint_restore_available(checkpoint, state=state))

    def test_not_safe_point(self) -> None:
        checkpoint = {
            "safe_point_eligible": False,
            "verification": {"status": "PASSED"},
            "run_id": "R1",
            "task_class": "bounded_change",
        }
        state = {"run_id": "R1", "task_class": "bounded_change"}
        self.assertFalse(checkpoint_restore_available(checkpoint, state=state))


class TestMatchingRecovery(unittest.TestCase):
    """matching_recovery filters by run_id and task_class."""

    def test_matching(self) -> None:
        recovery = {"run_id": "R1", "task_class": "t", "primary_action": "KEEP"}
        state = {"run_id": "R1", "task_class": "t"}
        self.assertIsNotNone(matching_recovery(recovery, state=state))

    def test_mismatched_run_id(self) -> None:
        recovery = {"run_id": "R2", "task_class": "t"}
        state = {"run_id": "R1", "task_class": "t"}
        self.assertIsNone(matching_recovery(recovery, state=state))

    def test_none(self) -> None:
        self.assertIsNone(matching_recovery(None, state={"run_id": "R1", "task_class": "t"}))


class TestResumeAvailable(unittest.TestCase):
    """resume_available checks if repair-step resume is possible."""

    def test_repairable_with_step(self) -> None:
        report = {"reason": "DOCTOR_NOT_GREEN"}
        packet = {
            "continuation_core": {"current_step_id": "restore_readiness_truth"},
            "repair_termination": {"status": "CONTINUE"},
            "resumability": {"status": "REPAIRABLE"},
            "repair_policy": {},
        }
        self.assertTrue(resume_available(report, packet))

    def test_terminated_denies(self) -> None:
        report = {"reason": "DOCTOR_NOT_GREEN"}
        packet = {
            "continuation_core": {"current_step_id": "restore_readiness_truth"},
            "repair_termination": {"status": "TERMINATE"},
            "resumability": {"status": "REPAIRABLE"},
            "repair_policy": {},
        }
        self.assertFalse(resume_available(report, packet))

    def test_non_resumable_denies(self) -> None:
        report = {"reason": "NON_RESUMABLE"}
        packet = {
            "continuation_core": {"current_step_id": "s1"},
            "repair_termination": {"status": "CONTINUE"},
            "resumability": {"status": "NOT_RESUMABLE"},
            "repair_policy": {},
        }
        self.assertFalse(resume_available(report, packet))

    def test_no_step_id_denies(self) -> None:
        report = {"reason": "DOCTOR_NOT_GREEN"}
        packet = {
            "continuation_core": {},
            "repair_termination": {"status": "CONTINUE"},
            "resumability": {"status": "REPAIRABLE"},
            "repair_policy": {"next_step_id": ""},
        }
        self.assertFalse(resume_available(report, packet))


class TestHumanReason(unittest.TestCase):
    """human_reason maps technical codes to English."""

    def test_known_reason(self) -> None:
        result = human_reason({"reason": "DOCTOR_NOT_GREEN"})
        self.assertEqual("the current workspace is not ready yet", result)

    def test_unknown_reason_humanized(self) -> None:
        result = human_reason({"reason": "SOME_WEIRD_CODE"})
        self.assertEqual("some weird code", result)

    def test_fallback_to_packet(self) -> None:
        result = human_reason({}, {"runtime_truth": {"report_reason": "MAX_REPAIR_ATTEMPTS"}})
        self.assertEqual("the bounded repair limit was reached", result)


if __name__ == "__main__":
    unittest.main()
