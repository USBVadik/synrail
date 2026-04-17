#!/usr/bin/env python3
"""Unit tests for the prompt-chain modules.

Covers:
  - synrail_repair_prompt_bridge_v0 (build_record, prompt text, scope, guardrails)
  - synrail_prompt_followup_v0     (scope drift detection)
  - synrail_prompt_retry_guard_v0  (retry stability between attempts)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_repair_prompt_bridge_v0 import (
    build_record as build_prompt_bridge,
    human_step_label,
    human_failure_label,
    human_scope_label,
    human_required_input,
    failure_reason,
    next_command,
    checkpoint_note,
)
from synrail_prompt_followup_v0 import build_record as build_followup
from synrail_prompt_retry_guard_v0 import build_record as build_retry_guard


# ============================================================================
# Helpers
# ============================================================================

def _minimal_packet(
    *,
    current_step_id: str = "restore_readiness_truth",
    reason: str = "DOCTOR_NOT_GREEN",
    next_safe_step: str = "repair readiness",
    resumability_status: str = "REPAIRABLE",
    termination_status: str = "CONTINUE",
    missing_inputs: list[str] | None = None,
    required_inputs: list[str] | None = None,
    subsurface_ids: list[str] | None = None,
    stale_artifact_ids: list[str] | None = None,
) -> dict:
    return {
        "schema_version": "repair_packet_v0",
        "run_id": "R1",
        "task_class": "bounded_change",
        "from_state": "DOCTOR_BLOCKED",
        "continuation_core": {
            "current_step_id": current_step_id,
            "next_safe_step": next_safe_step,
            "next_step_required_inputs": required_inputs or [],
            "next_step_subsurface_ids": subsurface_ids or [],
            "required_inputs": required_inputs or [],
            "missing_inputs": missing_inputs or [],
            "ready_for_resume": False,
        },
        "repair_history": {"current_step_id": current_step_id},
        "runtime_truth": {
            "report_reason": reason,
            "next_safe_step": next_safe_step,
        },
        "repair_termination": {
            "status": termination_status,
            "reason": "",
        },
        "resumability": {
            "status": resumability_status,
        },
        "artifact_quality_summary": {
            "stale_artifact_ids": stale_artifact_ids or ["readiness_surface"],
            "stale_subsurface_ids": subsurface_ids or [],
            "non_resumable_artifact_ids": [],
            "non_resumable_subsurface_ids": [],
        },
        "repair_policy": {"next_step_id": current_step_id},
        "output_defaults": {"artifact_root": "/tmp/synrail"},
        "resume_context": {"target_path": "/tmp/target"},
    }


def _checkpoint(*, matching: bool = True) -> dict:
    return {
        "safe_point_eligible": True,
        "verification": {"status": "PASSED"},
        "run_id": "R1" if matching else "R2",
        "task_class": "bounded_change",
        "checkpoint_id": "ckpt-001",
    }


# ============================================================================
# synrail_repair_prompt_bridge_v0 tests
# ============================================================================

class TestHumanStepLabel(unittest.TestCase):
    def test_known_step(self) -> None:
        self.assertEqual("repair the final result artifact", human_step_label("repair_final_result_artifact"))

    def test_restore_readiness(self) -> None:
        self.assertEqual("restore a trustworthy workspace", human_step_label("restore_readiness_truth"))

    def test_unknown_step_humanized(self) -> None:
        result = human_step_label("some_custom_step")
        self.assertEqual("some custom step", result)

    def test_empty_step(self) -> None:
        self.assertEqual("unknown current step", human_step_label(""))


class TestHumanFailureLabel(unittest.TestCase):
    def test_known_reason(self) -> None:
        self.assertEqual("the current workspace is not ready yet", human_failure_label("DOCTOR_NOT_GREEN"))

    def test_invalid_proof(self) -> None:
        self.assertEqual("the final result proof could not be trusted", human_failure_label("INVALID_PROOF_BUNDLE"))

    def test_unknown_reason_humanized(self) -> None:
        self.assertEqual("custom reason code", human_failure_label("CUSTOM_REASON_CODE"))

    def test_empty_reason(self) -> None:
        self.assertEqual("unknown blocker", human_failure_label(""))


class TestHumanScopeLabel(unittest.TestCase):
    def test_current_step_only(self) -> None:
        self.assertEqual("only the current bounded repair step", human_scope_label("current_repair_step_only"))

    def test_clean_surface(self) -> None:
        self.assertEqual("the current workspace for this run", human_scope_label("clean_execution_surface_record"))

    def test_unknown_scope(self) -> None:
        self.assertEqual("something custom", human_scope_label("something_custom"))


class TestHumanRequiredInput(unittest.TestCase):
    def test_clean_surface(self) -> None:
        result = human_required_input("clean_surface_confirmation")
        self.assertIn("workspace is clean and safe to use", result)
        self.assertIn("--clean-surface", result)

    def test_unknown_input(self) -> None:
        result = human_required_input("some_new_input")
        self.assertEqual("some new input", result)


class TestFailureReason(unittest.TestCase):
    def test_from_runtime_truth(self) -> None:
        packet = {"runtime_truth": {"report_reason": "DOCTOR_NOT_GREEN"}, "repair_termination": {"reason": ""}}
        self.assertEqual("DOCTOR_NOT_GREEN", failure_reason(packet))

    def test_fallback_to_termination(self) -> None:
        packet = {"runtime_truth": {"report_reason": ""}, "repair_termination": {"reason": "NON_RESUMABLE"}}
        self.assertEqual("NON_RESUMABLE", failure_reason(packet))

    def test_empty(self) -> None:
        packet = {"runtime_truth": {}, "repair_termination": {}}
        self.assertEqual("", failure_reason(packet))


class TestNextCommand(unittest.TestCase):
    def test_repairable_returns_retry(self) -> None:
        packet = {
            "resumability": {"status": "REPAIRABLE"},
            "repair_termination": {"status": "CONTINUE"},
            "resumability_family": "",
        }
        self.assertEqual("synrail retry", next_command(packet, "restore_readiness_truth"))

    def test_terminated_returns_empty(self) -> None:
        packet = {
            "resumability": {"status": "REPAIRABLE"},
            "repair_termination": {"status": "TERMINATE"},
            "resumability_family": "",
        }
        self.assertEqual("", next_command(packet, "restore_readiness_truth"))

    def test_forward_orchestration_returns_check(self) -> None:
        packet = {
            "resumability": {"status": "NOT_RESUMABLE"},
            "repair_termination": {"status": "CONTINUE"},
            "resumability_family": "NOT_RESUMABLE_FRESH_ORCHESTRATION",
        }
        self.assertEqual("synrail check", next_command(packet, "continue_forward_orchestration"))


class TestCheckpointNote(unittest.TestCase):
    def test_matching_checkpoint(self) -> None:
        note = checkpoint_note(_checkpoint(matching=True), repair_packet={"run_id": "R1", "task_class": "bounded_change"})
        self.assertIn("restore point", note)

    def test_mismatched_checkpoint(self) -> None:
        note = checkpoint_note(_checkpoint(matching=False), repair_packet={"run_id": "R1", "task_class": "bounded_change"})
        self.assertEqual("", note)

    def test_none_checkpoint(self) -> None:
        self.assertEqual("", checkpoint_note(None, repair_packet={"run_id": "R1", "task_class": "bounded_change"}))


class TestBuildPromptBridge(unittest.TestCase):
    """build_record produces a well-formed prompt bridge record."""

    def test_basic_structure(self) -> None:
        packet = _minimal_packet()
        record = build_prompt_bridge(repair_packet=packet)
        self.assertEqual("repair_prompt_bridge_record_v0", record["schema_version"])
        self.assertEqual("R1", record["run_id"])
        self.assertEqual("restore_readiness_truth", record["current_step_id"])
        self.assertEqual("restore a trustworthy workspace", record["current_step_label"])
        self.assertIn("the current workspace is not ready yet", record["failure_label"])
        self.assertGreater(len(record["prompt"]), 0)
        self.assertGreater(len(record["must_pass"]), 0)
        self.assertGreater(len(record["forbidden_scope"]), 0)

    def test_readiness_focus_mentions_clean_surface_flag(self) -> None:
        packet = _minimal_packet(
            required_inputs=["clean_surface_confirmation"],
            subsurface_ids=["clean_execution_surface_record"],
        )
        record = build_prompt_bridge(repair_packet=packet)
        self.assertIn("--clean-surface", record["current_step_focus_summary"])
        self.assertIn("--clean-surface", record["current_step_action_instruction"])
        self.assertTrue(any("--clean-surface" in item for item in record["required_input_labels"]))

    def test_prompt_contains_guardrails(self) -> None:
        packet = _minimal_packet()
        record = build_prompt_bridge(repair_packet=packet)
        self.assertIn("Do not touch unrelated files", record["prompt"])
        self.assertIn("Do not broaden scope", record["forbidden_scope"][0])

    def test_prompt_mentions_step_label(self) -> None:
        packet = _minimal_packet()
        record = build_prompt_bridge(repair_packet=packet)
        self.assertIn("restore a trustworthy workspace", record["prompt"])

    def test_prompt_mentions_failure(self) -> None:
        packet = _minimal_packet()
        record = build_prompt_bridge(repair_packet=packet)
        self.assertIn("not ready yet", record["prompt"])

    def test_checkpoint_hint_in_prompt(self) -> None:
        packet = _minimal_packet()
        checkpoint = _checkpoint(matching=True)
        record = build_prompt_bridge(repair_packet=packet, checkpoint=checkpoint)
        self.assertIn("restore point", record["prompt"])

    def test_required_inputs_in_must_pass(self) -> None:
        packet = _minimal_packet(required_inputs=["clean_surface_confirmation"])
        record = build_prompt_bridge(repair_packet=packet)
        input_rules = [r for r in record["must_pass"] if "clean" in r.lower()]
        self.assertGreater(len(input_rules), 0)

    def test_next_command_repairable(self) -> None:
        packet = _minimal_packet(resumability_status="REPAIRABLE", termination_status="CONTINUE")
        record = build_prompt_bridge(repair_packet=packet)
        self.assertEqual("synrail retry", record["next_command"])

    def test_next_command_terminated(self) -> None:
        packet = _minimal_packet(resumability_status="REPAIRABLE", termination_status="TERMINATE")
        record = build_prompt_bridge(repair_packet=packet)
        self.assertEqual("", record["next_command"])

    def test_focused_step_with_subsurface(self) -> None:
        packet = _minimal_packet(
            current_step_id="repair_final_result_artifact",
            reason="INVALID_PROOF_BUNDLE",
            subsurface_ids=["final_result_payload"],
            stale_artifact_ids=["final_result_artifact"],
        )
        record = build_prompt_bridge(repair_packet=packet)
        self.assertEqual("final_result_payload", record["current_step_subsurface_id"])
        self.assertIn("final_result_payload", record["allowed_scope"])
        self.assertIn("Checklist for /tmp/synrail/final_result.json:", record["prompt"])
        self.assertIn("change_disposition", record["prompt"])
        self.assertIn("artifact_identity", record["prompt"])
        self.assertIn("synrail final-result-template", record["prompt"])
        self.assertIn("synrail explain-proof", record["prompt"])

    def test_artifact_identity_subsurface_includes_checklist(self) -> None:
        packet = _minimal_packet(
            current_step_id="repair_final_result_artifact",
            reason="INVALID_PROOF_BUNDLE",
            subsurface_ids=["artifact_identity_record"],
            stale_artifact_ids=["final_result_artifact"],
        )
        record = build_prompt_bridge(repair_packet=packet)
        self.assertEqual("artifact_identity_record", record["current_step_subsurface_id"])
        self.assertIn("Checklist for /tmp/synrail/final_result.json:", record["prompt"])
        self.assertIn("artifact_identity.baseline_identity", record["prompt"])
        self.assertIn("low-level bundle-check reproducible", record["prompt"])

    def test_scenario_subsurface_includes_checklist(self) -> None:
        packet = _minimal_packet(
            current_step_id="complete_missing_proof_sections",
            reason="INVALID_PROOF_BUNDLE",
            subsurface_ids=["scenario_proof_record"],
            stale_artifact_ids=["proof_bundle"],
        )
        record = build_prompt_bridge(repair_packet=packet)
        self.assertEqual("scenario_proof_record", record["current_step_subsurface_id"])
        self.assertIn("Checklist for /tmp/synrail/scenario_proof.txt:", record["prompt"])
        self.assertIn("Status: PASSED", record["prompt"])
        self.assertIn("synrail scenario-proof-template", record["prompt"])
        self.assertIn("synrail explain-proof", record["prompt"])

    def test_readback_subsurface_includes_checklist(self) -> None:
        packet = _minimal_packet(
            current_step_id="complete_missing_proof_sections",
            reason="INVALID_PROOF_BUNDLE",
            subsurface_ids=["readback_record"],
            stale_artifact_ids=["proof_bundle"],
        )
        record = build_prompt_bridge(repair_packet=packet)
        self.assertEqual("readback_record", record["current_step_subsurface_id"])
        self.assertIn("Checklist for /tmp/synrail/readback.txt:", record["prompt"])
        self.assertIn("Changed surface:", record["prompt"])
        self.assertIn("synrail readback-template", record["prompt"])
        self.assertIn("source-only grep", record["prompt"])

    def test_no_subsurface_uses_step_scope(self) -> None:
        packet = _minimal_packet()
        record = build_prompt_bridge(repair_packet=packet)
        # No subsurface → falls back to stale_subsurfaces or "current_repair_step_only"
        self.assertGreater(len(record["allowed_scope"]), 0)


# ============================================================================
# synrail_prompt_followup_v0 tests
# ============================================================================

class TestBuildFollowup(unittest.TestCase):
    """build_record detects scope drift between packet and prompt bridge."""

    def _aligned_prompt_bridge(self, packet: dict) -> dict:
        """Build a prompt bridge that aligns with the packet."""
        return build_prompt_bridge(repair_packet=packet)

    def test_aligned_is_preserved(self) -> None:
        packet = _minimal_packet()
        bridge = self._aligned_prompt_bridge(packet)
        record = build_followup(repair_packet=packet, prompt_bridge=bridge)
        self.assertEqual("FOLLOWUP_SCOPE_PRESERVED", record["verdict"])
        self.assertEqual([], record["missing_markers"])

    def test_mismatched_step_id_drifts(self) -> None:
        packet = _minimal_packet(current_step_id="restore_readiness_truth")
        bridge = self._aligned_prompt_bridge(packet)
        bridge["current_step_id"] = "rebuild_proof_bundle"
        record = build_followup(repair_packet=packet, prompt_bridge=bridge)
        self.assertEqual("FOLLOWUP_SCOPE_DRIFT", record["verdict"])
        self.assertIn("current_step_id", record["missing_markers"])

    def test_missing_guardrail_drifts(self) -> None:
        packet = _minimal_packet()
        bridge = self._aligned_prompt_bridge(packet)
        bridge["prompt"] = bridge["prompt"].replace("Do not touch unrelated files, state transitions, or acceptance logic.", "")
        record = build_followup(repair_packet=packet, prompt_bridge=bridge)
        self.assertEqual("FOLLOWUP_SCOPE_DRIFT", record["verdict"])
        self.assertIn("forbidden_scope_guardrail", record["missing_markers"])

    def test_with_thin_output_next_step(self) -> None:
        packet = _minimal_packet(next_safe_step="repair readiness")
        bridge = self._aligned_prompt_bridge(packet)
        thin = {"next_step": "repair readiness"}
        record = build_followup(repair_packet=packet, prompt_bridge=bridge, thin_output=thin)
        # thin_output next_step should be mentioned in the prompt
        self.assertEqual("FOLLOWUP_SCOPE_PRESERVED", record["verdict"])


# ============================================================================
# synrail_prompt_retry_guard_v0 tests
# ============================================================================

class TestBuildRetryGuard(unittest.TestCase):
    """build_record detects stability across retry attempts."""

    def _bridge_for(self, packet: dict) -> dict:
        return build_prompt_bridge(repair_packet=packet)

    def test_identical_packets_stable(self) -> None:
        packet = _minimal_packet()
        bridge = self._bridge_for(packet)
        record = build_retry_guard(
            packet_a=packet, prompt_a=bridge,
            packet_b=packet, prompt_b=bridge,
        )
        self.assertEqual("RETRY_SCOPE_STABLE", record["verdict"])
        self.assertEqual([], record["missing_markers"])

    def test_step_id_changed_broadened(self) -> None:
        packet_a = _minimal_packet(current_step_id="restore_readiness_truth")
        bridge_a = self._bridge_for(packet_a)
        packet_b = _minimal_packet(current_step_id="rebuild_proof_bundle")
        bridge_b = self._bridge_for(packet_b)
        record = build_retry_guard(
            packet_a=packet_a, prompt_a=bridge_a,
            packet_b=packet_b, prompt_b=bridge_b,
        )
        self.assertEqual("RETRY_SCOPE_BROADENED", record["verdict"])
        self.assertIn("current_step_id_changed", record["missing_markers"])

    def test_scope_changed_broadened(self) -> None:
        packet_a = _minimal_packet(subsurface_ids=["clean_execution_surface_record"])
        bridge_a = self._bridge_for(packet_a)
        packet_b = _minimal_packet(subsurface_ids=["final_result_payload"])
        bridge_b = self._bridge_for(packet_b)
        record = build_retry_guard(
            packet_a=packet_a, prompt_a=bridge_a,
            packet_b=packet_b, prompt_b=bridge_b,
        )
        self.assertEqual("RETRY_SCOPE_BROADENED", record["verdict"])
        self.assertIn("allowed_scope_changed", record["missing_markers"])

    def test_required_inputs_changed_broadened(self) -> None:
        packet_a = _minimal_packet(required_inputs=["clean_surface_confirmation"])
        bridge_a = self._bridge_for(packet_a)
        packet_b = _minimal_packet(required_inputs=["final_result"])
        bridge_b = self._bridge_for(packet_b)
        record = build_retry_guard(
            packet_a=packet_a, prompt_a=bridge_a,
            packet_b=packet_b, prompt_b=bridge_b,
        )
        self.assertEqual("RETRY_SCOPE_BROADENED", record["verdict"])
        self.assertIn("required_inputs_changed", record["missing_markers"])

    def test_next_safe_step_changed_broadened(self) -> None:
        packet_a = _minimal_packet(next_safe_step="repair readiness")
        bridge_a = self._bridge_for(packet_a)
        packet_b = _minimal_packet(next_safe_step="rebuild proof bundle")
        bridge_b = self._bridge_for(packet_b)
        record = build_retry_guard(
            packet_a=packet_a, prompt_a=bridge_a,
            packet_b=packet_b, prompt_b=bridge_b,
        )
        self.assertEqual("RETRY_SCOPE_BROADENED", record["verdict"])
        self.assertIn("next_safe_step_changed", record["missing_markers"])

    def test_record_schema(self) -> None:
        packet = _minimal_packet()
        bridge = self._bridge_for(packet)
        record = build_retry_guard(
            packet_a=packet, prompt_a=bridge,
            packet_b=packet, prompt_b=bridge,
        )
        self.assertEqual("prompt_retry_guard_record_v0", record["schema_version"])
        self.assertEqual("R1", record["run_id"])
        self.assertEqual("bounded_change", record["task_class"])


if __name__ == "__main__":
    unittest.main()
