#!/usr/bin/env python3
"""Regression harness for Synrail truth-critical failures."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_ROOT = REPO_ROOT / "tools" / "reference"
FIXTURES_ROOT = REPO_ROOT / "fixtures"

if str(TOOLS_ROOT) not in sys.path:
    sys.path.insert(0, str(TOOLS_ROOT))

from synrail_acceptance_criteria_v0 import build_record as build_acceptance_criteria
from synrail_acceptance_criteria_v0 import validate_record as validate_acceptance_criteria
from synrail_artifact_consistency_v0 import build_record as build_artifact_consistency_record
from synrail_io_v0 import load_json
from synrail_bundle_v0 import artifact_binding_entry, build_bundle
from synrail_checkpoint_v0 import restore_preview, restore_record, restore_target_path_errors, verify_record
from synrail_closure_v0 import build_closure_certificate, build_verdict, persist_closure_certificate
from synrail_continuation_arbiter_v0 import build_record as build_continuation_arbiter
from synrail_doctor_v1 import build_record as build_doctor_record
from synrail_second_operator_v0 import build_record as build_second_operator
from synrail_spine_v0 import OrchestrationContext, _phase_closure, build_canonical_run_artifact
from synrail_cli_v0 import load_repair_packet as load_cli_repair_packet
from synrail_spine_v0 import load_repair_packet as load_spine_repair_packet
import synrail_doctor_v1
import synrail_spine_v0



def controlled_state(state: dict) -> dict:
    payload = copy.deepcopy(state)
    integrity = dict(payload.get("integrity", {}))
    integrity["bootstrap_provenance_ok"] = True
    integrity["bootstrap_provenance_reason"] = "CONTROLLED_BOOTSTRAP_CONFIRMED"
    if "status" not in integrity:
        integrity["status"] = "PASS" if integrity.get("exact_task_identity_ok") else "FAIL"
    payload["integrity"] = integrity
    return payload


def _normalise_grep_result_line(value: str) -> str:
    prefix, sep, rest = value.partition(":")
    return rest if sep and prefix.isdigit() else value


def _recheck_file_content(record: dict) -> str:
    for key in ("added_line", "observed_line", "context_after", "context_before", "verification_result"):
        value = record.get(key, "")
        if isinstance(value, str) and value.strip():
            return _normalise_grep_result_line(value).rstrip("\n") + "\n"
    return "synrail test evidence\n"


def write_project_profile_for_recheck(root: Path, *, project_root: Path) -> Path:
    state_file = root / "state.json"
    if not state_file.exists():
        state_file.write_text("{}\n")
    (root / "project_profile.json").write_text(json.dumps({
        "project_root": str(project_root),
    }, indent=2, ensure_ascii=True) + "\n")
    return state_file


def prepare_recheck_project_context(final_result: Path) -> str:
    try:
        final_payload = json.loads(final_result.read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(final_payload, dict):
        return ""
    record = final_payload.get("diff_provenance", {})
    if not isinstance(record, dict):
        return ""
    changed_file = record.get("changed_file", "")
    if not isinstance(changed_file, str) or not changed_file.strip():
        return ""
    changed_path = Path(changed_file)
    if changed_path.is_absolute() or ".." in changed_path.parts:
        return ""

    repo_path = REPO_ROOT / changed_path
    if repo_path.exists():
        return str(write_project_profile_for_recheck(final_result.parent, project_root=REPO_ROOT))

    project_root = final_result.parent / "recheck_project"
    target = project_root / changed_path
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(_recheck_file_content(record))
    return str(write_project_profile_for_recheck(final_result.parent, project_root=project_root))


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
        state_file=prepare_recheck_project_context(final_result),
        output="",
    )


def build_live_verdict(state: dict, bundle: dict, *, root: Path | None = None) -> dict:
    if root is not None:
        state_path = root / "state.json"
        bundle_path = root / "bundle.json"
        live_state = copy.deepcopy(state)
        live_bundle = copy.deepcopy(bundle)
        binding = live_bundle.get("closure_freshness_binding", {})
        if isinstance(binding, dict):
            rebound_artifacts = []
            synthetic_payloads = {
                "final_result": json.dumps(live_bundle.get("final_result", {}), indent=2, ensure_ascii=True).encode() + b"\n",
                "readback": (live_bundle.get("readback", {}).get("path", "") or "readback placeholder\n").encode(),
                "scenario_proof": (live_bundle.get("scenario_proof", {}).get("path", "") or "scenario placeholder\n").encode(),
                "doctor": json.dumps({"status": "PASS"}, indent=2, ensure_ascii=True).encode() + b"\n",
            }
            for item in binding.get("artifacts", []):
                if not isinstance(item, dict):
                    continue
                rebound_item = copy.deepcopy(item)
                source_path_text = (item.get("path", "") or "").strip()
                artifact_id = (item.get("artifact_id", "") or "artifact").strip() or "artifact"
                target_path = root / f"{artifact_id}.bound"
                payload = synthetic_payloads.get(artifact_id, f"{artifact_id}\n".encode())
                if source_path_text:
                    source_path = Path(source_path_text)
                    if source_path.exists() and source_path.is_file():
                        payload = source_path.read_bytes()
                elif not item.get("required", False) and not item.get("present", False):
                    rebound_artifacts.append(rebound_item)
                    continue
                target_path.write_bytes(payload)
                rebound_item["path"] = str(target_path)
                rebound_item["present"] = True
                rebound_item["sha256"] = hashlib.sha256(payload).hexdigest()
                rebound_artifacts.append(rebound_item)
            live_bundle["closure_freshness_binding"] = {
                **binding,
                "artifacts": rebound_artifacts,
            }
        state_path.write_text(json.dumps(live_state, indent=2, ensure_ascii=True) + "\n")
        bundle_path.write_text(json.dumps(live_bundle, indent=2, ensure_ascii=True) + "\n")
        live_state["_state_file"] = str(state_path)
        live_bundle["_bundle_file"] = str(bundle_path)
        return build_verdict(live_state, live_bundle)
    with tempfile.TemporaryDirectory(prefix="synrail_live_verdict_") as tmpdir:
        return build_live_verdict(state, bundle, root=Path(tmpdir))


def write_state_bound_hash_context(root: Path, *, state: dict, starter_hash: str) -> Path:
    state_file = root / "state.json"
    state_payload = copy.deepcopy(state)
    state_payload["last_known_final_result_hash"] = starter_hash
    state_file.write_text(json.dumps(state_payload, indent=2, ensure_ascii=True) + "\n")
    (root / "project_profile.json").write_text(json.dumps({
        "project_root": str(REPO_ROOT),
    }, indent=2, ensure_ascii=True) + "\n")
    (root / "proof_request.json").write_text(json.dumps({
        "starter_hashes": {"final_result": starter_hash},
    }, indent=2, ensure_ascii=True) + "\n")
    return state_file


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
    def test_legacy_repair_packet_loaders_synthesize_continuation_core(self) -> None:
        packet_path = FIXTURES_ROOT / "repair_packet_run_001" / "packet.json"

        cli_packet = load_cli_repair_packet(packet_path)
        spine_packet = load_spine_repair_packet(packet_path)

        for packet in (cli_packet, spine_packet):
            self.assertEqual("repair_packet_v0", packet["schema_version"])
            self.assertIn("continuation_core", packet)
            self.assertEqual("continuation_core_v0", packet["continuation_core"]["contract_version"])
            self.assertEqual(packet["missing_inputs"], packet["continuation_core"]["next_step_required_inputs"])
            self.assertEqual(packet["next_safe_step"], packet["continuation_core"]["next_safe_step"])
            self.assertTrue(packet["continuation_core"]["packet_replay_ready"])

    def test_artifact_binding_entry_treats_directories_as_absent_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_binding_directory_") as tmpdir:
            entry = artifact_binding_entry(
                artifact_id="final_result",
                path=Path(tmpdir),
                required=True,
            )

        self.assertFalse(entry["present"])
        self.assertEqual("", entry["path"])
        self.assertEqual("", entry["sha256"])

    def test_false_reject_valid_contour_stays_accepted(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = build_bundle(
            bundle_args(final_result=FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "final_result_valid.json")
        )
        verdict = build_live_verdict(state, bundle)

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

    def test_checkpoint_verify_blocks_manifest_path_escape(self) -> None:
        record = load_json(FIXTURES_ROOT / "checkpoint_scope_violation_run_001" / "checkpoint_verify.json")
        source_checkpoint_root = (REPO_ROOT / record["checkpoint_root"]).resolve()

        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_manifest_escape_") as tmpdir:
            checkpoint_root = Path(tmpdir) / "checkpoint"
            shutil.copytree(source_checkpoint_root, checkpoint_root)
            state_path = checkpoint_root / "artifacts" / "state.json"
            state_path.write_text(json.dumps(controlled_state(load_json(state_path)), indent=2, ensure_ascii=True) + "\n")
            record["checkpoint_root"] = str(checkpoint_root)
            record["artifact_manifest"][0]["path"] = "../escaped/state.json"

            verified = verify_record(record)

        self.assertEqual("BLOCKED", verified["result"])
        self.assertEqual("FAILED", verified["verification"]["status"])
        self.assertIn("checkpoint record path validation failed", verified["verification"]["failure_reasons"])
        self.assertIn("artifact path escapes checkpoint root: state", verified["verification"]["failure_reasons"])

    def test_checkpoint_restore_blocks_workspace_target_retarget(self) -> None:
        record = load_json(FIXTURES_ROOT / "checkpoint_scope_violation_run_001" / "checkpoint_verify.json")
        source_checkpoint_root = (REPO_ROOT / record["checkpoint_root"]).resolve()

        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_workspace_retarget_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "restore_target"
            target_root.mkdir(parents=True, exist_ok=True)
            checkpoint_root = tmp / "checkpoint"
            shutil.copytree(source_checkpoint_root, checkpoint_root)
            state_path = checkpoint_root / "artifacts" / "state.json"
            state_path.write_text(json.dumps(controlled_state(load_json(state_path)), indent=2, ensure_ascii=True) + "\n")
            record["checkpoint_root"] = str(checkpoint_root)
            record["workspace_snapshot"] = {
                "type": "git",
                "workspace_family": "clean_commit",
                "project_root": str(tmp / "other_project"),
                "head_ref": "deadbeef",
                "has_uncommitted": False,
                "has_untracked": False,
            }

            restored = restore_record(copy.deepcopy(record), target_root)

        self.assertEqual("BLOCKED", restored["result"])
        self.assertEqual("RESTORE_FAILED", restored["restore"]["status"])
        self.assertIn(
            "workspace restore failed: workspace snapshot project_root is present but checkpoint_root is not inside a checkpoint-owned artifact root",
            restored["restore"]["failure_reasons"],
        )
        self.assertEqual("ROLLED_BACK", restored["rollback"]["status"])
        self.assertEqual("RESTORE_VERIFICATION_FAILED", restored["rollback"]["trigger"])

    def test_checkpoint_verify_blocks_snapshot_dir_escape(self) -> None:
        record = load_json(FIXTURES_ROOT / "checkpoint_scope_violation_run_001" / "checkpoint_verify.json")
        source_checkpoint_root = (REPO_ROOT / record["checkpoint_root"]).resolve()

        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_snapshot_escape_") as tmpdir:
            tmp = Path(tmpdir)
            checkpoint_root = tmp / "checkpoint"
            shutil.copytree(source_checkpoint_root, checkpoint_root)
            state_path = checkpoint_root / "artifacts" / "state.json"
            state_path.write_text(json.dumps(controlled_state(load_json(state_path)), indent=2, ensure_ascii=True) + "\n")
            record["checkpoint_root"] = str(checkpoint_root)
            record["workspace_snapshot"] = {
                "type": "file_copy",
                "workspace_family": "file_copy",
                "project_root": str(tmp),
                "snapshot_dir": str(tmp / "outside_snapshot"),
                "file_count": 1,
            }

            verified = verify_record(record)

        self.assertEqual("BLOCKED", verified["result"])
        self.assertIn("workspace snapshot directory escapes checkpoint root", verified["verification"]["failure_reasons"])
        self.assertIn("checkpoint record path validation failed", verified["verification"]["failure_reasons"])

    def test_checkpoint_restore_blocks_symlinked_target_artifact_parent(self) -> None:
        record = load_json(FIXTURES_ROOT / "checkpoint_scope_violation_run_001" / "checkpoint_verify.json")
        source_checkpoint_root = (REPO_ROOT / record["checkpoint_root"]).resolve()

        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_target_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "restore_target"
            outside_root = tmp / "outside"
            checkpoint_root = tmp / "checkpoint"
            target_root.mkdir(parents=True, exist_ok=True)
            outside_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_checkpoint_root, checkpoint_root)
            state_path = checkpoint_root / "artifacts" / "state.json"
            state_path.write_text(json.dumps(controlled_state(load_json(state_path)), indent=2, ensure_ascii=True) + "\n")
            record["checkpoint_root"] = str(checkpoint_root)
            record["workspace_snapshot"] = {"type": "none", "reason": "no workspace snapshot available"}
            artifact_relpath = Path(record["artifact_manifest"][0]["path"])
            symlink_parent = target_root / artifact_relpath.parent
            symlink_parent.parent.mkdir(parents=True, exist_ok=True)
            symlink_parent.symlink_to(outside_root, target_is_directory=True)
            escaped_target = outside_root / artifact_relpath.name

            restored = restore_record(copy.deepcopy(record), target_root)

        self.assertEqual("BLOCKED", restored["result"])
        self.assertEqual("RESTORE_FAILED", restored["restore"]["status"])
        self.assertIn(
            "restore target path parent is a symlink: state",
            restored["restore"]["failure_reasons"],
        )
        self.assertFalse(escaped_target.exists())
        self.assertEqual("NOT_NEEDED", restored["rollback"]["status"])
        self.assertEqual("NONE", restored["rollback"]["trigger"])

    def test_checkpoint_restore_blocks_symlinked_target_artifact_file(self) -> None:
        record = load_json(FIXTURES_ROOT / "checkpoint_scope_violation_run_001" / "checkpoint_verify.json")
        source_checkpoint_root = (REPO_ROOT / record["checkpoint_root"]).resolve()

        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_target_file_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "restore_target"
            outside_root = tmp / "outside"
            checkpoint_root = tmp / "checkpoint"
            target_root.mkdir(parents=True, exist_ok=True)
            outside_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_checkpoint_root, checkpoint_root)
            state_path = checkpoint_root / "artifacts" / "state.json"
            state_path.write_text(json.dumps(controlled_state(load_json(state_path)), indent=2, ensure_ascii=True) + "\n")
            record["checkpoint_root"] = str(checkpoint_root)
            record["workspace_snapshot"] = {"type": "none", "reason": "no workspace snapshot available"}
            artifact_relpath = Path(record["artifact_manifest"][0]["path"])
            target_path = target_root / artifact_relpath
            target_path.parent.mkdir(parents=True, exist_ok=True)
            escaped_target = outside_root / artifact_relpath.name
            target_path.symlink_to(escaped_target)

            restored = restore_record(copy.deepcopy(record), target_root)

        self.assertEqual("BLOCKED", restored["result"])
        self.assertEqual("RESTORE_FAILED", restored["restore"]["status"])
        self.assertIn(
            "restore target path is a symlink: state",
            restored["restore"]["failure_reasons"],
        )
        self.assertFalse(escaped_target.exists())
        self.assertEqual("NOT_NEEDED", restored["rollback"]["status"])
        self.assertEqual("NONE", restored["rollback"]["trigger"])

    def test_checkpoint_restore_rechecks_target_path_after_preview(self) -> None:
        record = load_json(FIXTURES_ROOT / "checkpoint_scope_violation_run_001" / "checkpoint_verify.json")
        source_checkpoint_root = (REPO_ROOT / record["checkpoint_root"]).resolve()

        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_target_toctou_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "restore_target"
            outside_root = tmp / "outside"
            checkpoint_root = tmp / "checkpoint"
            target_root.mkdir(parents=True, exist_ok=True)
            outside_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_checkpoint_root, checkpoint_root)
            state_path = checkpoint_root / "artifacts" / "state.json"
            state_path.write_text(json.dumps(controlled_state(load_json(state_path)), indent=2, ensure_ascii=True) + "\n")
            record["checkpoint_root"] = str(checkpoint_root)
            record["workspace_snapshot"] = {"type": "none", "reason": "no workspace snapshot available"}
            artifact_relpath = Path(record["artifact_manifest"][0]["path"])
            target_path = target_root / artifact_relpath
            target_path.parent.mkdir(parents=True, exist_ok=True)
            escaped_target = outside_root / artifact_relpath.name

            original_restore_preview = restore_preview
            preview_count = {"value": 0}

            def flip_after_preview(current_record: dict, current_target_root: Path) -> dict:
                preview = original_restore_preview(current_record, current_target_root)
                preview_count["value"] += 1
                if preview_count["value"] == 1:
                    target_path.symlink_to(escaped_target)
                return preview

            with patch("synrail_checkpoint_v0.restore_preview", side_effect=flip_after_preview):
                restored = restore_record(copy.deepcopy(record), target_root)

        self.assertEqual("BLOCKED", restored["result"])
        self.assertEqual("RESTORE_FAILED", restored["restore"]["status"])
        self.assertIn(
            "restore target path is a symlink: state",
            restored["restore"]["failure_reasons"],
        )
        self.assertFalse(escaped_target.exists())
        self.assertEqual("NOT_NEEDED", restored["rollback"]["status"])
        self.assertEqual("NONE", restored["rollback"]["trigger"])

    def test_checkpoint_restore_rechecks_target_path_before_rollback(self) -> None:
        record = load_json(FIXTURES_ROOT / "checkpoint_scope_violation_run_001" / "checkpoint_verify.json")
        source_checkpoint_root = (REPO_ROOT / record["checkpoint_root"]).resolve()

        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_rollback_toctou_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "restore_target"
            outside_root = tmp / "outside"
            checkpoint_root = tmp / "checkpoint"
            target_root.mkdir(parents=True, exist_ok=True)
            outside_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_checkpoint_root, checkpoint_root)
            state_path = checkpoint_root / "artifacts" / "state.json"
            state_path.write_text(json.dumps(controlled_state(load_json(state_path)), indent=2, ensure_ascii=True) + "\n")
            record["checkpoint_root"] = str(checkpoint_root)
            record["workspace_snapshot"] = {
                "type": "git",
                "workspace_family": "clean_commit",
                "project_root": str(tmp / "other_project"),
                "head_ref": "deadbeef",
                "has_uncommitted": False,
                "has_untracked": False,
            }
            artifact_relpath = Path(record["artifact_manifest"][0]["path"])
            target_path = target_root / artifact_relpath
            target_path.parent.mkdir(parents=True, exist_ok=True)
            escaped_target = outside_root / artifact_relpath.name
            backup_source = target_path.parent / "original-state.json"
            backup_source.write_text('{"baseline": true}\n', encoding="utf-8")
            shutil.copy2(backup_source, target_path)

            original_verify_record = verify_record
            verify_count = {"value": 0}

            def flip_before_rollback(current_record: dict, root_override: Path | None = None) -> dict:
                verified = original_verify_record(current_record, root_override=root_override)
                if root_override is not None:
                    verify_count["value"] += 1
                    if verify_count["value"] == 1:
                        target_path.unlink()
                        target_path.symlink_to(escaped_target)
                return verified

            with patch("synrail_checkpoint_v0.verify_record", side_effect=flip_before_rollback):
                restored = restore_record(copy.deepcopy(record), target_root)

        self.assertEqual("ERROR", restored["result"])
        self.assertEqual("RESTORE_FAILED", restored["restore"]["status"])
        self.assertEqual("ROLLBACK_FAILED", restored["rollback"]["status"])
        self.assertEqual("RESTORE_VERIFICATION_FAILED", restored["rollback"]["trigger"])
        self.assertIn(
            "restore target path is a symlink: state",
            restored["rollback"]["failure_reasons"],
        )
        self.assertFalse(escaped_target.exists())
        self.assertFalse(target_path.exists())

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

    def test_doctor_rejects_coverage_profile_escape_outside_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_profile_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            target_root = project_root / "target_surface"
            artifact_path = project_root / "artifacts" / "final_result.json"
            outside = tmp / "outside" / "profile.json"
            project_root.mkdir(parents=True, exist_ok=True)
            target_root.mkdir(parents=True, exist_ok=True)
            (project_root / "artifacts").mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text(json.dumps(load_json(TOOLS_ROOT / "doctor_coverage_profile_v0.json"), indent=2, ensure_ascii=True) + "\n")
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.coverage_profile_file = str(outside)

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_PROFILE_OUT_OF_SCOPE", record["coverage"]["gate_reason"])

    def test_doctor_rejects_coverage_corpus_escape_outside_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_corpus_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            target_root = project_root / "target_surface"
            artifact_path = project_root / "artifacts" / "final_result.json"
            outside = tmp / "outside" / "corpus.json"
            project_root.mkdir(parents=True, exist_ok=True)
            target_root.mkdir(parents=True, exist_ok=True)
            (project_root / "artifacts").mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text(json.dumps(load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json"), indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=outside, target_path=target_root, artifact_path=artifact_path)
            args.coverage_corpus_file = str(outside)

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_CORPUS_OUT_OF_SCOPE", record["coverage"]["gate_reason"])

    def test_doctor_rejects_profile_derived_coverage_corpus_escape(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_profile_corpus_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            target_root = project_root / "target_surface"
            artifact_path = project_root / "artifacts" / "final_result.json"
            outside_corpus = tmp / "outside" / "corpus.json"
            project_root.mkdir(parents=True, exist_ok=True)
            target_root.mkdir(parents=True, exist_ok=True)
            (project_root / "artifacts").mkdir(parents=True, exist_ok=True)
            outside_corpus.parent.mkdir(parents=True, exist_ok=True)
            outside_corpus.write_text(json.dumps(load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json"), indent=2, ensure_ascii=True) + "\n")
            profile = load_json(TOOLS_ROOT / "doctor_coverage_profile_v0.json")
            profile["measured_corpus_file"] = str(outside_corpus)
            profile_path = project_root / "doctor_coverage_profile.json"
            profile_path.write_text(json.dumps(profile, indent=2, ensure_ascii=True) + "\n")
            fallback_corpus = project_root / "fallback_corpus.json"
            fallback_corpus.write_text(json.dumps(load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json"), indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=fallback_corpus, target_path=target_root, artifact_path=artifact_path)
            args.coverage_profile_file = str(profile_path)
            args.coverage_corpus_file = None

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_CORPUS_OUT_OF_SCOPE", record["coverage"]["gate_reason"])

    def test_doctor_rejects_symlinked_coverage_profile_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_profile_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            profile_target = tmp / "real_profile.json"
            profile = load_json(TOOLS_ROOT / "doctor_coverage_profile_v0.json")
            profile_target.write_text(json.dumps(profile, indent=2, ensure_ascii=True) + "\n")
            profile_link = tmp / "profile_link.json"
            profile_link.symlink_to(profile_target)

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.coverage_profile_file = str(profile_link)

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_PROFILE_SYMLINK_SURFACE", record["coverage"]["gate_reason"])

    def test_doctor_rejects_symlinked_coverage_corpus_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_corpus_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)

            corpus_target = tmp / "real_corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_target.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            corpus_link = tmp / "corpus_link.json"
            corpus_link.symlink_to(corpus_target)

            args = doctor_args(corpus_file=corpus_target, target_path=target_root, artifact_path=artifact_path)
            args.coverage_corpus_file = str(corpus_link)

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_CORPUS_SYMLINK_SURFACE", record["coverage"]["gate_reason"])

    def test_doctor_rejects_symlinked_coverage_profile_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_profile_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_profile_root = tmp / "real_profile_root"
            linked_profile_root = tmp / "linked_profile_root"
            real_profile_root.mkdir(parents=True, exist_ok=True)
            linked_profile_root.symlink_to(real_profile_root, target_is_directory=True)
            profile = load_json(TOOLS_ROOT / "doctor_coverage_profile_v0.json")
            (real_profile_root / "profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.coverage_profile_file = str(linked_profile_root / "profile.json")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_PROFILE_PARENT_SYMLINK_SURFACE", record["coverage"]["gate_reason"])

    def test_doctor_rejects_symlinked_coverage_corpus_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_corpus_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)

            real_corpus_root = tmp / "real_corpus_root"
            linked_corpus_root = tmp / "linked_corpus_root"
            real_corpus_root.mkdir(parents=True, exist_ok=True)
            linked_corpus_root.symlink_to(real_corpus_root, target_is_directory=True)
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            (real_corpus_root / "corpus.json").write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=real_corpus_root / "corpus.json", target_path=target_root, artifact_path=artifact_path)
            args.coverage_corpus_file = str(linked_corpus_root / "corpus.json")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_CORPUS_PARENT_SYMLINK_SURFACE", record["coverage"]["gate_reason"])

    def test_doctor_rejects_symlinked_coverage_profile_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_profile_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            corpus_path = tmp / "corpus.json"
            real_inputs_root = tmp / "real_inputs"
            linked_inputs_root = tmp / "linked_inputs"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            (real_inputs_root / "profiles").mkdir(parents=True, exist_ok=True)
            (real_inputs_root / "profiles" / "nested_profile.json").write_text(
                json.dumps(load_json(TOOLS_ROOT / "doctor_coverage_profile_v0.json"), indent=2, ensure_ascii=True) + "\n"
            )
            linked_inputs_root.symlink_to(real_inputs_root, target_is_directory=True)

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.coverage_profile_file = str(linked_inputs_root / "profiles" / "nested_profile.json")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_PROFILE_ANCESTOR_SYMLINK_SURFACE", record["coverage"]["gate_reason"])

    def test_doctor_rejects_symlinked_coverage_corpus_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_corpus_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            real_inputs_root = tmp / "real_inputs"
            linked_inputs_root = tmp / "linked_inputs"
            target_root.mkdir(parents=True, exist_ok=True)
            (real_inputs_root / "corpora").mkdir(parents=True, exist_ok=True)
            (real_inputs_root / "corpora" / "nested_corpus.json").write_text(
                json.dumps(load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json"), indent=2, ensure_ascii=True) + "\n"
            )
            linked_inputs_root.symlink_to(real_inputs_root, target_is_directory=True)

            args = doctor_args(corpus_file=real_inputs_root / "corpora" / "nested_corpus.json", target_path=target_root, artifact_path=artifact_path)
            args.coverage_corpus_file = str(linked_inputs_root / "corpora" / "nested_corpus.json")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertFalse(record["coverage"]["threshold_met"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_CORPUS_ANCESTOR_SYMLINK_SURFACE", record["coverage"]["gate_reason"])

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

    def test_doctor_rejects_symlinked_target_identity_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_target_identity_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            identity_target = tmp / "real_target_identity.txt"
            identity_target.write_text("EXPECTED_SURFACE_001\n")
            identity_link = tmp / "target_identity_link.txt"
            identity_link.symlink_to(identity_target)

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.expected_target_identity = "EXPECTED_SURFACE_001"
            args.target_identity_file = str(identity_link)

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_BASELINE_IDENTITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["baseline_identity"]["status"])
        self.assertIn("symlink", record["gate_results"]["baseline_identity"]["note"])

    def test_doctor_rejects_symlinked_clean_execution_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_clean_execution_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            real_target_root = tmp / "real_target_root"
            linked_target_root = tmp / "linked_target_root"
            artifact_path = tmp / "artifacts" / "final_result.json"
            corpus_path = tmp / "corpus.json"
            real_target_root.mkdir(parents=True, exist_ok=True)
            linked_target_root.symlink_to(real_target_root, target_is_directory=True)
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(
                corpus_file=corpus_path,
                target_path=linked_target_root / "child_target",
                artifact_path=artifact_path,
            )
            args.clean_surface = False

            record = build_doctor_record(args)

        self.assertEqual("FAIL", record["gate_results"]["clean_execution_surface"]["status"])
        self.assertIn("parent is a symlink", record["gate_results"]["clean_execution_surface"]["note"])

    def test_doctor_rejects_symlinked_clean_execution_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_clean_execution_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            real_target_root = tmp / "real_target_root"
            linked_ancestor_root = tmp / "linked_ancestor_root"
            nested_root = linked_ancestor_root / "nested"
            artifact_path = tmp / "artifacts" / "final_result.json"
            corpus_path = tmp / "corpus.json"
            real_target_root.mkdir(parents=True, exist_ok=True)
            linked_ancestor_root.symlink_to(real_target_root, target_is_directory=True)
            (real_target_root / "nested").mkdir(parents=True, exist_ok=True)
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(
                corpus_file=corpus_path,
                target_path=nested_root / "child_target",
                artifact_path=artifact_path,
            )
            args.clean_surface = False

            record = build_doctor_record(args)

        self.assertEqual("FAIL", record["gate_results"]["clean_execution_surface"]["status"])
        self.assertIn("ancestor is a symlink", record["gate_results"]["clean_execution_surface"]["note"])

    def test_doctor_allows_clean_execution_when_symlink_is_above_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_clean_execution_bounded_") as tmpdir:
            tmp = Path(tmpdir)
            real_workspace = tmp / "real_workspace"
            workspace_link = tmp / "workspace_link"
            project_root = workspace_link / "project"
            target_root = project_root / "target_surface"
            artifact_path = project_root / "artifacts" / "final_result.json"
            real_workspace.mkdir(parents=True, exist_ok=True)
            workspace_link.symlink_to(real_workspace, target_is_directory=True)
            target_root.mkdir(parents=True, exist_ok=True)
            (project_root / "artifacts").mkdir(parents=True, exist_ok=True)
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(
                corpus_file=corpus_path,
                target_path=target_root,
                artifact_path=artifact_path,
            )
            args.clean_surface = False

            record = build_doctor_record(args)

        self.assertEqual("PASS", record["gate_results"]["clean_execution_surface"]["status"])
        self.assertIn("explicitly observed", record["gate_results"]["clean_execution_surface"]["note"])

    def test_doctor_rejects_symlinked_target_identity_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_target_identity_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_identity_root = tmp / "real_identity_root"
            linked_identity_root = tmp / "linked_identity_root"
            real_identity_root.mkdir(parents=True, exist_ok=True)
            linked_identity_root.symlink_to(real_identity_root, target_is_directory=True)
            (real_identity_root / "target_identity.txt").write_text("EXPECTED_SURFACE_001\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.expected_target_identity = "EXPECTED_SURFACE_001"
            args.target_identity_file = str(linked_identity_root / "target_identity.txt")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_BASELINE_IDENTITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["baseline_identity"]["status"])
        self.assertIn("parent is a symlink", record["gate_results"]["baseline_identity"]["note"])

    def test_doctor_rejects_symlinked_target_identity_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_target_identity_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_identity_root = tmp / "real_identity_root"
            linked_ancestor_root = tmp / "linked_ancestor_root"
            nested_root = linked_ancestor_root / "nested"
            real_identity_root.mkdir(parents=True, exist_ok=True)
            linked_ancestor_root.symlink_to(real_identity_root, target_is_directory=True)
            (real_identity_root / "nested").mkdir(parents=True, exist_ok=True)
            (real_identity_root / "nested" / "target_identity.txt").write_text("EXPECTED_SURFACE_001\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.expected_target_identity = "EXPECTED_SURFACE_001"
            args.target_identity_file = str(nested_root / "target_identity.txt")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_BASELINE_IDENTITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["baseline_identity"]["status"])
        self.assertIn("ancestor is a symlink", record["gate_results"]["baseline_identity"]["note"])

    def test_doctor_allows_target_identity_when_symlink_is_above_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_target_identity_bounded_") as tmpdir:
            tmp = Path(tmpdir)
            real_workspace = tmp / "real_workspace"
            workspace_link = tmp / "workspace_link"
            project_root = workspace_link / "project"
            target_root = project_root / "target_surface"
            artifact_path = project_root / "artifacts" / "final_result.json"
            real_workspace.mkdir(parents=True, exist_ok=True)
            workspace_link.symlink_to(real_workspace, target_is_directory=True)
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            identity_dir = project_root / "identities"
            identity_dir.mkdir(parents=True, exist_ok=True)
            (identity_dir / "target_identity.txt").write_text("EXPECTED_SURFACE_001\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.expected_target_identity = "EXPECTED_SURFACE_001"
            args.target_identity_file = str(identity_dir / "target_identity.txt")

            record = build_doctor_record(args)

        self.assertEqual("PASS", record["gate_results"]["baseline_identity"]["status"])
        self.assertIn("matches expectation", record["gate_results"]["baseline_identity"]["note"])

    def test_doctor_rejects_symlinked_target_execution_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_target_surface_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            real_target_root = tmp / "real_target_surface"
            target_link = tmp / "target_surface_link"
            artifact_path = tmp / "artifacts" / "final_result.json"
            real_target_root.mkdir(parents=True, exist_ok=True)
            target_link.symlink_to(real_target_root, target_is_directory=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_link, artifact_path=artifact_path)
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DIRTY_SURFACE", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["clean_execution_surface"]["status"])
        self.assertIn("symlink", record["gate_results"]["clean_execution_surface"]["note"])

    def test_doctor_records_override_gates_for_true_bypass_flags(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_override_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True

            record = build_doctor_record(args)

        self.assertIn("clean_execution_surface", record["override_gates"])
        self.assertIn("artifact_viability", record["override_gates"])
        self.assertIn("helper_integrity", record["override_gates"])
        self.assertIn("credential_surface", record["override_gates"])
        self.assertIn("prompt_task_identity", record["override_gates"])
        self.assertEqual(
            "doctor override present: clean_execution_surface, artifact_viability, helper_integrity, credential_surface, prompt_task_identity",
            record["override_summary"],
        )
        self.assertIn(
            "clean_execution_surface: operator bypass via --clean-surface",
            record["override_warnings"],
        )
        self.assertTrue(record["gate_results"]["clean_execution_surface"]["override"])
        self.assertEqual(
            "operator bypass via --clean-surface",
            record["gate_results"]["clean_execution_surface"]["override_reason"],
        )

    def test_doctor_treats_observed_safe_scope_as_non_override(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_observed_scope_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.changed_file = ["tools/reference/synrail_bundle_v0.py"]
            args.allowed_scope_path = ["tools/reference"]
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True

            record = build_doctor_record(args)

        self.assertNotIn("clean_execution_surface", record["override_gates"])
        self.assertEqual("PASS", record["gate_results"]["clean_execution_surface"]["status"])
        self.assertFalse(record["gate_results"]["clean_execution_surface"]["override"])
        self.assertEqual("", record["gate_results"]["clean_execution_surface"]["override_reason"])
        self.assertIn("explicitly observed", record["gate_results"]["clean_execution_surface"]["note"])

    def test_doctor_records_no_override_gates_when_no_bypass_flags_are_used(self) -> None:
        corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
        corpus["cases"] = [
            case
            for case in corpus["cases"]
            if case.get("fail_mode_id") != "helper_entrypoint_missing"
        ]

        with tempfile.TemporaryDirectory(prefix="synrail_doctor_no_override_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.clean_surface = False
            args.artifact_viable = False
            record = build_doctor_record(args)

        self.assertEqual([], record["override_gates"])
        self.assertFalse(record["gate_results"]["clean_execution_surface"]["override"])
        self.assertEqual("", record["gate_results"]["clean_execution_surface"]["override_reason"])

    def test_doctor_rejects_symlinked_prompt_identity_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_prompt_identity_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_root = tmp / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            prompt_target = tmp / "real_prompt_identity.txt"
            prompt_target.write_text("TASK-IDENTITY-001\n")
            prompt_link = tmp / "prompt_identity_link.txt"
            prompt_link.symlink_to(prompt_target)

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "EXACT_RETRY_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.expected_task_identity = "TASK-IDENTITY-001"
            args.prompt_identity_file = str(prompt_link)

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_EXACT_PROMPT_MISSING", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["prompt_task_identity"]["status"])
        self.assertIn("symlink", record["gate_results"]["prompt_task_identity"]["note"])

    def test_doctor_rejects_symlinked_prompt_identity_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_prompt_identity_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_root = tmp / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_prompt_root = tmp / "real_prompt_root"
            linked_prompt_root = tmp / "linked_prompt_root"
            real_prompt_root.mkdir(parents=True, exist_ok=True)
            linked_prompt_root.symlink_to(real_prompt_root, target_is_directory=True)
            (real_prompt_root / "prompt_identity.txt").write_text("TASK-IDENTITY-001\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "EXACT_RETRY_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.expected_task_identity = "TASK-IDENTITY-001"
            args.prompt_identity_file = str(linked_prompt_root / "prompt_identity.txt")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_EXACT_PROMPT_MISSING", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["prompt_task_identity"]["status"])
        self.assertIn("parent is a symlink", record["gate_results"]["prompt_task_identity"]["note"])

    def test_doctor_rejects_symlinked_prompt_identity_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_prompt_identity_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_root = tmp / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_prompt_root = tmp / "real_prompt_root"
            linked_ancestor_root = tmp / "linked_ancestor_root"
            nested_root = linked_ancestor_root / "nested"
            real_prompt_root.mkdir(parents=True, exist_ok=True)
            linked_ancestor_root.symlink_to(real_prompt_root, target_is_directory=True)
            (real_prompt_root / "nested").mkdir(parents=True, exist_ok=True)
            (real_prompt_root / "nested" / "prompt_identity.txt").write_text("TASK-IDENTITY-001\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "EXACT_RETRY_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.expected_task_identity = "TASK-IDENTITY-001"
            args.prompt_identity_file = str(nested_root / "prompt_identity.txt")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_EXACT_PROMPT_MISSING", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["prompt_task_identity"]["status"])
        self.assertIn("ancestor is a symlink", record["gate_results"]["prompt_task_identity"]["note"])

    def test_doctor_allows_prompt_identity_when_symlink_is_above_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_prompt_identity_bounded_") as tmpdir:
            tmp = Path(tmpdir)
            real_workspace = tmp / "real_workspace"
            workspace_link = tmp / "workspace_link"
            project_root = workspace_link / "project"
            target_root = project_root / "target_surface"
            artifact_root = project_root / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            real_workspace.mkdir(parents=True, exist_ok=True)
            workspace_link.symlink_to(real_workspace, target_is_directory=True)
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            prompt_dir = artifact_root / "prompts"
            prompt_dir.mkdir(parents=True, exist_ok=True)
            (prompt_dir / "prompt_identity.txt").write_text("TASK-IDENTITY-001\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "EXACT_RETRY_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.expected_task_identity = "TASK-IDENTITY-001"
            args.prompt_identity_file = str(prompt_dir / "prompt_identity.txt")

            record = build_doctor_record(args)

        self.assertEqual("PASS", record["gate_results"]["prompt_task_identity"]["status"])
        self.assertIn("artifact is present", record["gate_results"]["prompt_task_identity"]["note"])

    def test_doctor_rejects_symlinked_credential_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_credential_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            credential_target = tmp / "real_credentials"
            credential_target.write_text("aws_access_key_id = demo\n")
            credential_link = tmp / "credentials_link"
            credential_link.symlink_to(credential_target)

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.helper_ok = True
            args.prompt_identity_ok = True
            args.credential_env = ["AWS_SHARED_CREDENTIALS_FILE"]

            previous_value = os.environ.get("AWS_SHARED_CREDENTIALS_FILE")
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(credential_link)
            try:
                record = build_doctor_record(args)
            finally:
                if previous_value is None:
                    os.environ.pop("AWS_SHARED_CREDENTIALS_FILE", None)
                else:
                    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = previous_value

        self.assertEqual("NOT_ACCEPTABLE_CREDENTIAL_SURFACE", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["credential_surface"]["status"])
        self.assertIn("symlink", record["gate_results"]["credential_surface"]["note"])

    def test_doctor_rejects_symlinked_credential_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_credential_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_credential_root = tmp / "real_credentials_root"
            linked_credential_root = tmp / "linked_credentials_root"
            real_credential_root.mkdir(parents=True, exist_ok=True)
            linked_credential_root.symlink_to(real_credential_root, target_is_directory=True)
            (real_credential_root / "credentials").write_text("aws_access_key_id = demo\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.helper_ok = True
            args.prompt_identity_ok = True
            args.credential_env = ["AWS_SHARED_CREDENTIALS_FILE"]

            previous_value = os.environ.get("AWS_SHARED_CREDENTIALS_FILE")
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(linked_credential_root / "credentials")
            try:
                record = build_doctor_record(args)
            finally:
                if previous_value is None:
                    os.environ.pop("AWS_SHARED_CREDENTIALS_FILE", None)
                else:
                    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = previous_value

        self.assertEqual("NOT_ACCEPTABLE_CREDENTIAL_SURFACE", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["credential_surface"]["status"])
        self.assertIn("symlinked parent", record["gate_results"]["credential_surface"]["note"])

    def test_doctor_rejects_symlinked_credential_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_credential_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_path = tmp / "artifacts" / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_credential_root = tmp / "real_credentials_root"
            linked_ancestor_root = tmp / "linked_ancestor_root"
            nested_root = linked_ancestor_root / "nested"
            real_credential_root.mkdir(parents=True, exist_ok=True)
            linked_ancestor_root.symlink_to(real_credential_root, target_is_directory=True)
            (real_credential_root / "nested").mkdir(parents=True, exist_ok=True)
            (real_credential_root / "nested" / "credentials").write_text("aws_access_key_id = demo\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.helper_ok = True
            args.prompt_identity_ok = True
            args.credential_env = ["AWS_SHARED_CREDENTIALS_FILE"]

            previous_value = os.environ.get("AWS_SHARED_CREDENTIALS_FILE")
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(nested_root / "credentials")
            try:
                record = build_doctor_record(args)
            finally:
                if previous_value is None:
                    os.environ.pop("AWS_SHARED_CREDENTIALS_FILE", None)
                else:
                    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = previous_value

        self.assertEqual("NOT_ACCEPTABLE_CREDENTIAL_SURFACE", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["credential_surface"]["status"])
        self.assertIn("symlinked ancestor", record["gate_results"]["credential_surface"]["note"])

    def test_doctor_allows_credential_when_symlink_is_above_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_credential_bounded_") as tmpdir:
            tmp = Path(tmpdir)
            real_workspace = tmp / "real_workspace"
            workspace_link = tmp / "workspace_link"
            project_root = workspace_link / "project"
            target_root = project_root / "target_surface"
            artifact_path = project_root / "artifacts" / "final_result.json"
            real_workspace.mkdir(parents=True, exist_ok=True)
            workspace_link.symlink_to(real_workspace, target_is_directory=True)
            target_root.mkdir(parents=True, exist_ok=True)
            (project_root / "artifacts").mkdir(parents=True, exist_ok=True)
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            credential_dir = project_root / "credentials"
            credential_dir.mkdir(parents=True, exist_ok=True)
            (credential_dir / "credentials").write_text("aws_access_key_id = demo\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.helper_ok = True
            args.prompt_identity_ok = True
            args.credential_env = ["AWS_SHARED_CREDENTIALS_FILE"]

            previous_value = os.environ.get("AWS_SHARED_CREDENTIALS_FILE")
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(credential_dir / "credentials")
            try:
                record = build_doctor_record(args)
            finally:
                if previous_value is None:
                    os.environ.pop("AWS_SHARED_CREDENTIALS_FILE", None)
                else:
                    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = previous_value

        self.assertEqual("PASS", record["gate_results"]["credential_surface"]["status"])
        self.assertIn("required credential env is present", record["gate_results"]["credential_surface"]["note"])

    def test_doctor_rejects_credential_escape_outside_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_credential_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            target_root = project_root / "target_surface"
            artifact_path = project_root / "artifacts" / "final_result.json"
            outside_dir = tmp / "outside"
            project_root.mkdir(parents=True, exist_ok=True)
            target_root.mkdir(parents=True, exist_ok=True)
            (project_root / "artifacts").mkdir(parents=True, exist_ok=True)
            outside_dir.mkdir(parents=True, exist_ok=True)
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            (outside_dir / "credentials").write_text("aws_access_key_id = demo\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.helper_ok = True
            args.prompt_identity_ok = True
            args.credential_env = ["AWS_SHARED_CREDENTIALS_FILE"]

            previous_value = os.environ.get("AWS_SHARED_CREDENTIALS_FILE")
            os.environ["AWS_SHARED_CREDENTIALS_FILE"] = str(outside_dir / "credentials")
            try:
                record = build_doctor_record(args)
            finally:
                if previous_value is None:
                    os.environ.pop("AWS_SHARED_CREDENTIALS_FILE", None)
                else:
                    os.environ["AWS_SHARED_CREDENTIALS_FILE"] = previous_value

        self.assertEqual("NOT_ACCEPTABLE_CREDENTIAL_SURFACE", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["credential_surface"]["status"])
        self.assertIn("escapes the trusted target contour", record["gate_results"]["credential_surface"]["note"])

    def test_doctor_rejects_symlinked_helper_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_helper_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_root = tmp / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            helper_target = tmp / "real_helper.py"
            helper_target.write_text("print('ok')\n")
            helper_link = tmp / "helper_link.py"
            helper_link.symlink_to(helper_target)

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.credentials_ok = True
            args.prompt_identity_ok = True
            args.helper_path = str(helper_link)

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_HELPER_INTEGRITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["helper_integrity"]["status"])
        self.assertIn("symlink", record["gate_results"]["helper_integrity"]["note"])

    def test_doctor_rejects_symlinked_helper_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_helper_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_root = tmp / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_helper_root = tmp / "real_helper_root"
            linked_helper_root = tmp / "linked_helper_root"
            real_helper_root.mkdir(parents=True, exist_ok=True)
            linked_helper_root.symlink_to(real_helper_root, target_is_directory=True)
            (real_helper_root / "helper.py").write_text("print('ok')\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.credentials_ok = True
            args.prompt_identity_ok = True
            args.helper_path = str(linked_helper_root / "helper.py")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_HELPER_INTEGRITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["helper_integrity"]["status"])
        self.assertIn("parent is a symlink", record["gate_results"]["helper_integrity"]["note"])

    def test_doctor_rejects_symlinked_helper_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_helper_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifact_root = tmp / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            real_helper_root = tmp / "real_helper_root"
            linked_ancestor_root = tmp / "linked_ancestor_root"
            nested_root = linked_ancestor_root / "nested"
            real_helper_root.mkdir(parents=True, exist_ok=True)
            linked_ancestor_root.symlink_to(real_helper_root, target_is_directory=True)
            (real_helper_root / "nested").mkdir(parents=True, exist_ok=True)
            (real_helper_root / "nested" / "helper.py").write_text("print('ok')\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.credentials_ok = True
            args.prompt_identity_ok = True
            args.helper_path = str(nested_root / "helper.py")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_HELPER_INTEGRITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["helper_integrity"]["status"])
        self.assertIn("ancestor is a symlink", record["gate_results"]["helper_integrity"]["note"])

    def test_doctor_allows_helper_when_symlink_is_above_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_helper_bounded_") as tmpdir:
            tmp = Path(tmpdir)
            real_workspace = tmp / "real_workspace"
            workspace_link = tmp / "workspace_link"
            project_root = workspace_link / "project"
            target_root = project_root / "target_surface"
            artifact_root = project_root / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            real_workspace.mkdir(parents=True, exist_ok=True)
            workspace_link.symlink_to(real_workspace, target_is_directory=True)
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            helper_dir = project_root / "helpers"
            helper_dir.mkdir(parents=True, exist_ok=True)
            (helper_dir / "helper.py").write_text("print('ok')\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.credentials_ok = True
            args.prompt_identity_ok = True
            args.helper_path = str(helper_dir / "helper.py")

            record = build_doctor_record(args)

        self.assertEqual("PASS", record["gate_results"]["helper_integrity"]["status"])
        self.assertIn("parses successfully", record["gate_results"]["helper_integrity"]["note"])

    def test_doctor_rejects_helper_symlink_inside_symlinked_workspace(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_helper_inner_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            real_workspace = tmp / "real_workspace"
            workspace_link = tmp / "workspace_link"
            project_root = workspace_link / "project"
            target_root = project_root / "target_surface"
            artifact_root = project_root / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            real_workspace.mkdir(parents=True, exist_ok=True)
            workspace_link.symlink_to(real_workspace, target_is_directory=True)
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            real_helper_root = project_root / "real_helpers"
            helper_link_root = project_root / "helpers_link"
            real_helper_root.mkdir(parents=True, exist_ok=True)
            helper_link_root.symlink_to(real_helper_root, target_is_directory=True)
            (real_helper_root / "helper.py").write_text("print('ok')\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.clean_surface = False
            args.artifact_viable = False
            args.credentials_ok = True
            args.prompt_identity_ok = True
            args.helper_path = str(helper_link_root / "helper.py")

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_HELPER_INTEGRITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["helper_integrity"]["status"])
        self.assertIn("parent is a symlink", record["gate_results"]["helper_integrity"]["note"])

    def test_doctor_rejects_helper_changed_during_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_helper_toc_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            target_root = project_root / "target_surface"
            artifact_root = project_root / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            helper = project_root / "helpers" / "helper.py"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            helper.parent.mkdir(parents=True, exist_ok=True)
            helper.write_text("print('stable helper')\n")
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.doctor_level = "SUPPORT_DOCTOR"
            args.clean_surface = True
            args.credentials_ok = True
            args.prompt_identity_ok = True
            args.helper_path = str(helper)

            original_run = synrail_doctor_v1.subprocess.run

            def mutating_run(cmd: object, *run_args: object, **run_kwargs: object) -> subprocess.CompletedProcess:
                if isinstance(cmd, list) and "py_compile" in cmd:
                    helper.write_text("print('swapped helper')\n")
                    return subprocess.CompletedProcess(cmd, 0, "", "")
                return original_run(cmd, *run_args, **run_kwargs)

            synrail_doctor_v1.subprocess.run = mutating_run
            try:
                record = build_doctor_record(args)
            finally:
                synrail_doctor_v1.subprocess.run = original_run

        self.assertEqual("NOT_ACCEPTABLE_HELPER_INTEGRITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["helper_integrity"]["status"])
        self.assertIn("changed during validation", record["gate_results"]["helper_integrity"]["note"])

    def test_doctor_cli_rechecks_output_surface_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_output_toc_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside_root = tmp / "outside"
            output_path = artifact_root / "doctor.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside_root.mkdir(parents=True, exist_ok=True)

            violation = synrail_doctor_v1.path_surface_violation(
                str(output_path),
                field="output",
                scope="artifact_root",
                surface_label="output path",
                expected_surface="a direct machine-readable artifact surface",
                stop_at=project_root,
                project_root=project_root,
                artifact_root=artifact_root,
            )
            self.assertIsNone(violation)

            output_path.symlink_to(outside_root / "doctor.json")
            violation = synrail_doctor_v1.path_surface_violation(
                str(output_path),
                field="output",
                scope="artifact_root",
                surface_label="output path",
                expected_surface="a direct machine-readable artifact surface",
                stop_at=project_root,
                project_root=project_root,
                artifact_root=artifact_root,
            )

        self.assertIsNotNone(violation)
        payload = violation.as_payload()
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])
        self.assertFalse((outside_root / "doctor.json").exists())

    def test_doctor_rejects_target_identity_changed_during_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_target_identity_toc_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            target_root = project_root / "target_surface"
            artifact_root = project_root / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            corpus_path = project_root / "corpus.json"
            identity_file = project_root / "target_identity.txt"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")
            identity_file.write_text("EXPECTED_SURFACE_001\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.clean_surface = True
            args.artifact_viable = True
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True
            args.target_identity_file = str(identity_file)
            args.expected_target_identity = "EXPECTED_SURFACE_001"

            original_read = synrail_doctor_v1.read_non_empty_text

            def mutating_read(path: Path) -> str:
                value = original_read(path)
                identity_file.write_text("EXPECTED_SURFACE_001\nCHANGED\n")
                return value

            with patch("synrail_doctor_v1.read_non_empty_text", side_effect=mutating_read):
                record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_BASELINE_IDENTITY", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["baseline_identity"]["status"])
        self.assertIn("changed during validation", record["gate_results"]["baseline_identity"]["note"])

    def test_doctor_rejects_coverage_corpus_changed_during_validation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_coverage_corpus_toc_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            target_root = project_root / "target_surface"
            artifact_root = project_root / "artifacts"
            artifact_path = artifact_root / "final_result.json"
            corpus_path = project_root / "corpus.json"
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.clean_surface = True
            args.artifact_viable = True
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True

            original_load_corpus = synrail_doctor_v1.load_coverage_corpus

            def mutating_load_corpus(*load_args: object, **load_kwargs: object) -> tuple[dict, Path]:
                payload, resolved = original_load_corpus(*load_args, **load_kwargs)
                corpus_path.write_text(json.dumps({**payload, "measured_cases": []}, indent=2, ensure_ascii=True) + "\n")
                return payload, resolved

            with patch("synrail_doctor_v1.load_coverage_corpus", side_effect=mutating_load_corpus):
                record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_DOCTOR_COVERAGE", record["final_verdict"])
        self.assertEqual("BLOCKED", record["coverage"]["gate_status"])
        self.assertEqual("DOCTOR_COVERAGE_CORPUS_CHANGED_DURING_VALIDATION", record["coverage"]["gate_reason"])

    def test_doctor_cli_rechecks_state_surface_before_write(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_state_toc_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside_root = tmp / "outside"
            state_path = artifact_root / "state.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside_root.mkdir(parents=True, exist_ok=True)
            state_path.write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            violation = synrail_doctor_v1.path_surface_violation(
                str(state_path),
                field="state_file",
                scope="artifact_root",
                surface_label="state update path",
                expected_surface="a direct machine-readable state surface",
                stop_at=project_root,
                project_root=project_root,
                artifact_root=artifact_root,
            )
            self.assertIsNone(violation)

            state_path.unlink()
            state_path.symlink_to(outside_root / "state.json")
            violation = synrail_doctor_v1.path_surface_violation(
                str(state_path),
                field="state_file",
                scope="artifact_root",
                surface_label="state update path",
                expected_surface="a direct machine-readable state surface",
                stop_at=project_root,
                project_root=project_root,
                artifact_root=artifact_root,
            )

            self.assertIsNotNone(violation)
            payload = violation.as_payload()
            self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
            self.assertEqual("--state-file", payload["path_arg"])
            self.assertIn("symlink", payload["detail"])
            self.assertFalse((outside_root / "state.json").exists())
            self.assertTrue(state_path.is_symlink())

    def test_bundle_recheck_marks_changed_file_drift_during_recheck(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_changed_file_toc_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            changed_file = "tmp_recheck/app.py"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": [changed_file],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": changed_file,
                    "added_line": "import logging",
                    "context_before": "from os import path",
                    "context_after": "return logging",
                    "verification_command": f"grep -n 'import logging' {changed_file}",
                    "verification_result": "import logging",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": f"Workspace clean after updating only {changed_file} with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            project_root = tmp / "recheck_project"
            target = project_root / changed_file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("import logging\n")

            original_run = subprocess.run

            def mutating_run(cmd: object, *run_args: object, **run_kwargs: object) -> subprocess.CompletedProcess:
                if isinstance(cmd, list) and cmd[:2] == ["grep", "-n"]:
                    target.write_text("import logging\nimport logging changed\n")
                return original_run(cmd, *run_args, **run_kwargs)

            with patch("synrail_bundle_v0.subprocess.run", side_effect=mutating_run):
                bundle = build_bundle(args)
                verdict = build_live_verdict(state, bundle)

            self.assertTrue(bundle["verification_recheck"]["executed"])
            self.assertTrue(bundle["verification_recheck"]["command_allowed"])
            self.assertFalse(bundle["verification_recheck"]["matched"])
            self.assertEqual("changed_file_changed_during_recheck", bundle["verification_recheck"]["skip_reason"])
            self.assertEqual("VERIFICATION_RECHECK_FAILED", verdict["blocking_reason"])
            self.assertEqual("REJECTED", verdict["closure_status"])
            self.assertEqual("PROOF_BUNDLE_REPAIR", verdict["next_allowed_transition"])
            self.assertEqual("import logging\n", bundle["verification_recheck"]["stdout_snippet"])
            self.assertTrue(target.exists())

    def test_bundle_recheck_marks_changed_file_symlink_swap_during_recheck(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_changed_file_symlink_swap_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            changed_file = "tmp_recheck/app.py"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": [changed_file],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": changed_file,
                    "added_line": "import logging",
                    "context_before": "from os import path",
                    "context_after": "return logging",
                    "verification_command": f"grep -n 'import logging' {changed_file}",
                    "verification_result": "import logging",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": f"Workspace clean after updating only {changed_file} with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            project_root = tmp / "recheck_project"
            target = project_root / changed_file
            outside = tmp / "outside.py"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("import logging\n")
            outside.write_text("import logging\n")

            original_run = subprocess.run

            def mutating_run(cmd: object, *run_args: object, **run_kwargs: object) -> subprocess.CompletedProcess:
                if isinstance(cmd, list) and cmd[:2] == ["grep", "-n"]:
                    target.unlink()
                    target.symlink_to(outside)
                return original_run(cmd, *run_args, **run_kwargs)

            with patch("synrail_bundle_v0.subprocess.run", side_effect=mutating_run):
                bundle = build_bundle(args)
                verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("changed_file_changed_during_recheck", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("VERIFICATION_RECHECK_FAILED", verdict["blocking_reason"])
        self.assertEqual("REJECTED", verdict["closure_status"])

    def test_doctor_rejects_symlinked_artifact_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_artifact_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            real_artifacts = tmp / "real_artifacts"
            symlinked_artifacts = tmp / "artifacts_link"
            target_root.mkdir(parents=True, exist_ok=True)
            real_artifacts.mkdir(parents=True, exist_ok=True)
            symlinked_artifacts.symlink_to(real_artifacts, target_is_directory=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            artifact_path = symlinked_artifacts / "final_result.json"
            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_ARTIFACT_PATH", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["artifact_viability"]["status"])
        self.assertIn("symlink", record["gate_results"]["artifact_viability"]["note"])

    def test_doctor_rejects_symlinked_artifact_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_artifact_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            real_artifacts = tmp / "real_artifacts"
            linked_ancestor_root = tmp / "linked_ancestor_root"
            nested_root = linked_ancestor_root / "nested"
            target_root.mkdir(parents=True, exist_ok=True)
            real_artifacts.mkdir(parents=True, exist_ok=True)
            linked_ancestor_root.symlink_to(real_artifacts, target_is_directory=True)
            (real_artifacts / "nested").mkdir(parents=True, exist_ok=True)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            artifact_path = nested_root / "final_result.json"
            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_path)
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_ARTIFACT_PATH", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["artifact_viability"]["status"])
        self.assertIn("ancestor is a symlink", record["gate_results"]["artifact_viability"]["note"])

    def test_doctor_allows_artifact_path_when_symlink_is_above_target_contour(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_artifact_bounded_") as tmpdir:
            tmp = Path(tmpdir)
            real_workspace = tmp / "real_workspace"
            workspace_link = tmp / "workspace_link"
            project_root = workspace_link / "project"
            target_root = project_root / "target_surface"
            artifact_root = project_root / "artifacts" / "nested"
            real_workspace.mkdir(parents=True, exist_ok=True)
            workspace_link.symlink_to(real_workspace, target_is_directory=True)
            target_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_path = project_root / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_root / "final_result.json")
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True

            record = build_doctor_record(args)

        self.assertEqual("PASS", record["gate_results"]["artifact_viability"]["status"])
        self.assertIn("parent exists", record["gate_results"]["artifact_viability"]["note"])

    def test_doctor_rejects_broken_symlinked_artifact_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_artifact_broken_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "target_surface"
            artifacts = tmp / "artifacts"
            broken_target = tmp / "missing_final_result.json"
            artifact_link = artifacts / "final_result.json"
            target_root.mkdir(parents=True, exist_ok=True)
            artifacts.mkdir(parents=True, exist_ok=True)
            artifact_link.symlink_to(broken_target)
            corpus_path = tmp / "corpus.json"
            corpus = load_json(TOOLS_ROOT / "doctor_coverage_corpus_v0.json")
            corpus_path.write_text(json.dumps(corpus, indent=2, ensure_ascii=True) + "\n")

            args = doctor_args(corpus_file=corpus_path, target_path=target_root, artifact_path=artifact_link)
            args.clean_surface = False
            args.artifact_viable = False
            args.helper_ok = True
            args.credentials_ok = True
            args.prompt_identity_ok = True

            record = build_doctor_record(args)

        self.assertEqual("NOT_ACCEPTABLE_ARTIFACT_PATH", record["final_verdict"])
        self.assertEqual("FAIL", record["gate_results"]["artifact_viability"]["status"])
        self.assertIn("symlink", record["gate_results"]["artifact_viability"]["note"])

    def test_doctor_cli_rejects_symlinked_output_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_output_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            real_artifact_root = tmp / "real_artifacts"
            output_link = artifact_root / "doctor_link.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_artifact_root.mkdir(parents=True, exist_ok=True)
            output_link.symlink_to(real_artifact_root / "doctor.json")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(output_link),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_output_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_output_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            real_artifact_root = project_root / ".synrail_real"
            linked_artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            real_artifact_root.mkdir(parents=True, exist_ok=True)
            linked_artifact_root.symlink_to(real_artifact_root, target_is_directory=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(linked_artifact_root / "doctor.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("parent is a symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_state_update_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_state_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            real_artifact_root = tmp / "real_artifacts"
            state_link = artifact_root / "state_link.json"
            real_state = real_artifact_root / "state.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_artifact_root.mkdir(parents=True, exist_ok=True)
            real_state.write_text("{}\n")
            state_link.symlink_to(real_state)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--update-state",
                    "--state-file",
                    str(state_link),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--state-file", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_state_update_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_state_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            real_state_root = artifact_root / "real_state"
            linked_state_root = artifact_root / "state_link"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_state_root.mkdir(parents=True, exist_ok=True)
            linked_state_root.symlink_to(real_state_root, target_is_directory=True)
            (real_state_root / "state.json").write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--update-state",
                    "--state-file",
                    str(linked_state_root / "state.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--state-file", payload["path_arg"])
        self.assertIn("parent is a symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_output_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_output_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            real_project_root = tmp / "real_project"
            link_root = tmp / "linked_root"
            project_root = link_root / "project"
            artifact_root = project_root / ".synrail"
            real_project_root.mkdir(parents=True, exist_ok=True)
            link_root.symlink_to(real_project_root, target_is_directory=True)
            artifact_root.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("ancestor is a symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_state_update_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_state_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            real_state_ancestor = artifact_root / "real_state_ancestor"
            linked_state_ancestor = artifact_root / "state_ancestor_link"
            real_state_root = real_state_ancestor / "nested"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_state_root.mkdir(parents=True, exist_ok=True)
            linked_state_ancestor.symlink_to(real_state_ancestor, target_is_directory=True)
            (real_state_root / "state.json").write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--update-state",
                    "--state-file",
                    str(linked_state_ancestor / "nested" / "state.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--state-file", payload["path_arg"])
        self.assertIn("ancestor is a symlink", payload["detail"])

    def run_doctor_cli(self, *extra_args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                *extra_args,
            ],
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_doctor_cli_rejects_target_identity_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_target_identity_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside.txt"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.write_text("outside\n")

            result = self.run_doctor_cli(
                "--doctor-run-id",
                "R1",
                "--doctor-level",
                "CORE_DOCTOR",
                "--target-path",
                str(project_root),
                "--target-classification",
                "local",
                "--baseline-identity",
                "baseline",
                "--intended-run-class",
                "core_probe",
                "--output",
                str(artifact_root / "doctor.json"),
                "--target-identity-file",
                str(outside),
                cwd=project_root,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--target-identity-file", payload["path_arg"])
        self.assertIn("escapes project and artifact roots", payload["detail"])

    def test_acceptance_criteria_build_rejects_output_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_acceptance_build_output_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "acceptance_criteria.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "project_profile.json").write_text(
                json.dumps(
                    {
                        "schema_version": "project_profile_v0",
                        "project_root": str(project_root),
                        "project_type": "generic",
                        "task_class": "bounded_change",
                        "target_classification": "attested_target_surface",
                        "intended_run_class": "core_probe",
                        "baseline_identity": "trusted_clean",
                        "execution_surface_identity": "clean-clone",
                    },
                    indent=2,
                    ensure_ascii=True,
                )
                + "\n"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_acceptance_criteria_v0.py"),
                    "build",
                    "--project-profile-file",
                    str(artifact_root / "project_profile.json"),
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_acceptance_criteria_validate_rejects_state_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_acceptance_validate_state_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "state.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")
            profile = {
                "schema_version": "project_profile_v0",
                "project_root": str(project_root),
                "project_type": "generic",
                "task_class": "bounded_change",
                "target_classification": "attested_target_surface",
                "intended_run_class": "core_probe",
                "baseline_identity": "trusted_clean",
                "execution_surface_identity": "clean-clone",
            }
            criteria = build_acceptance_criteria(profile, generated_by="truth-regression-suite")
            (artifact_root / "project_profile.json").write_text(json.dumps(profile, indent=2, ensure_ascii=True) + "\n")
            (artifact_root / "acceptance_criteria.json").write_text(json.dumps(criteria, indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_acceptance_criteria_v0.py"),
                    "validate",
                    "--criteria-file",
                    str(artifact_root / "acceptance_criteria.json"),
                    "--state-file",
                    str(outside),
                    "--project-profile-file",
                    str(artifact_root / "project_profile.json"),
                    "--output",
                    str(artifact_root / "acceptance_validation.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--state-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_doctor_cli_rejects_prompt_identity_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_prompt_identity_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = project_root / "prompt_identity.txt"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.write_text("task identity\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "EXACT_RETRY_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "exact_retry",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--prompt-identity-file",
                    str(outside),
                    "--expected-task-identity",
                    "task identity",
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--prompt-identity-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_doctor_cli_rejects_helper_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_helper_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "helper.py"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.write_text("print('ok')\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "SUPPORT_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "support_run",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--helper-path",
                    str(outside),
                    "--artifact-viable",
                    "--credentials-ok",
                    "--prompt-identity-ok",
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--helper-path", payload["path_arg"])
        self.assertIn("escapes project root", payload["detail"])

    def test_doctor_cli_rejects_artifact_path_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_artifact_path_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "final_result.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--artifact-path",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--artifact-path", payload["path_arg"])
        self.assertIn("escapes project and artifact roots", payload["detail"])

    def test_doctor_cli_rejects_coverage_profile_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_coverage_profile_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "profile.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--coverage-profile-file",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--coverage-profile-file", payload["path_arg"])
        self.assertIn("escapes project root", payload["detail"])

    def test_doctor_cli_rejects_coverage_corpus_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_coverage_corpus_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "corpus.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_doctor_v1.py"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "local",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--output",
                    str(artifact_root / "doctor.json"),
                    "--coverage-corpus-file",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--coverage-corpus-file", payload["path_arg"])
        self.assertIn("escapes project root", payload["detail"])

    def test_doctor_cli_rejects_symlinked_target_identity_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_target_identity_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            identity_target = tmp / "real_target_identity.txt"
            identity_target.write_text("EXPECTED_SURFACE_001\n")
            identity_link = tmp / "target_identity_link.txt"
            identity_link.symlink_to(identity_target)

            result = self.run_doctor_cli(
                "--doctor-run-id", "R1",
                "--doctor-level", "CORE_DOCTOR",
                "--target-path", str(project_root),
                "--target-classification", "local",
                "--baseline-identity", "baseline",
                "--intended-run-class", "core_probe",
                "--output", str(artifact_root / "doctor.json"),
                "--target-identity-file", str(identity_link),
                cwd=project_root,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("--target-identity-file", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_prompt_identity_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_prompt_identity_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            prompt_target = tmp / "real_prompt_identity.txt"
            prompt_target.write_text("TASK-IDENTITY-001\n")
            prompt_link = tmp / "prompt_identity_link.txt"
            prompt_link.symlink_to(prompt_target)

            result = self.run_doctor_cli(
                "--doctor-run-id", "R1",
                "--doctor-level", "EXACT_RETRY_DOCTOR",
                "--target-path", str(project_root),
                "--target-classification", "local",
                "--baseline-identity", "baseline",
                "--intended-run-class", "exact_retry",
                "--output", str(artifact_root / "doctor.json"),
                "--prompt-identity-file", str(prompt_link),
                "--expected-task-identity", "TASK-IDENTITY-001",
                cwd=project_root,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("--prompt-identity-file", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_helper_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_helper_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            helper_target = tmp / "real_helper.py"
            helper_target.write_text("print('ok')\n")
            helper_link = tmp / "helper_link.py"
            helper_link.symlink_to(helper_target)

            result = self.run_doctor_cli(
                "--doctor-run-id", "R1",
                "--doctor-level", "SUPPORT_DOCTOR",
                "--target-path", str(project_root),
                "--target-classification", "local",
                "--baseline-identity", "baseline",
                "--intended-run-class", "support_run",
                "--output", str(artifact_root / "doctor.json"),
                "--helper-path", str(helper_link),
                "--artifact-viable",
                "--credentials-ok",
                "--prompt-identity-ok",
                cwd=project_root,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("--helper-path", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_artifact_path_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_artifact_path_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            artifact_target = tmp / "real_final_result.json"
            artifact_target.write_text("{}\n")
            artifact_link = tmp / "artifact_link.json"
            artifact_link.symlink_to(artifact_target)

            result = self.run_doctor_cli(
                "--doctor-run-id", "R1",
                "--doctor-level", "CORE_DOCTOR",
                "--target-path", str(project_root),
                "--target-classification", "local",
                "--baseline-identity", "baseline",
                "--intended-run-class", "core_probe",
                "--output", str(artifact_root / "doctor.json"),
                "--artifact-path", str(artifact_link),
                cwd=project_root,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("--artifact-path", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_coverage_profile_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_coverage_profile_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            profile_target = tmp / "real_profile.json"
            profile_target.write_text("{}\n")
            profile_link = tmp / "profile_link.json"
            profile_link.symlink_to(profile_target)

            result = self.run_doctor_cli(
                "--doctor-run-id", "R1",
                "--doctor-level", "CORE_DOCTOR",
                "--target-path", str(project_root),
                "--target-classification", "local",
                "--baseline-identity", "baseline",
                "--intended-run-class", "core_probe",
                "--output", str(artifact_root / "doctor.json"),
                "--coverage-profile-file", str(profile_link),
                cwd=project_root,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("--coverage-profile-file", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])

    def test_doctor_cli_rejects_symlinked_coverage_corpus_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_doctor_cli_coverage_corpus_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            corpus_target = tmp / "real_corpus.json"
            corpus_target.write_text("[]\n")
            corpus_link = tmp / "corpus_link.json"
            corpus_link.symlink_to(corpus_target)

            result = self.run_doctor_cli(
                "--doctor-run-id", "R1",
                "--doctor-level", "CORE_DOCTOR",
                "--target-path", str(project_root),
                "--target-classification", "local",
                "--baseline-identity", "baseline",
                "--intended-run-class", "core_probe",
                "--output", str(artifact_root / "doctor.json"),
                "--coverage-corpus-file", str(corpus_link),
                cwd=project_root,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("--coverage-corpus-file", payload["path_arg"])
        self.assertIn("symlink", payload["detail"])

    def test_refresh_cli_rejects_bundle_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_refresh_bundle_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "bundle.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_refresh_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--event-type",
                    "bundle_refresh",
                    "--bundle-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "refresh.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--bundle-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_closure_cli_rejects_bundle_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_closure_bundle_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "bundle.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_closure_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--bundle-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "closure.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--bundle-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_artifact_consistency_cli_rejects_report_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_artifact_consistency_report_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "report.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_artifact_consistency_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "artifact_consistency.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--report-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_artifact_consistency_cli_rejects_symlinked_report_file_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_artifact_consistency_report_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            real_report = artifact_root / "real_report.json"
            symlink_report = artifact_root / "report.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_report.write_text("{}\n")
            symlink_report.symlink_to(real_report)
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_artifact_consistency_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(symlink_report),
                    "--output",
                    str(artifact_root / "artifact_consistency.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--report-file", payload["path_arg"])
        self.assertIn("report file is a symlink", payload["detail"])

    def test_artifact_consistency_cli_rejects_symlinked_report_file_parent_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_artifact_consistency_report_parent_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            real_reports = artifact_root / "real_reports"
            symlink_reports = artifact_root / "reports"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_reports.mkdir(parents=True, exist_ok=True)
            symlink_reports.symlink_to(real_reports, target_is_directory=True)
            (real_reports / "report.json").write_text("{}\n")
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_artifact_consistency_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(symlink_reports / "report.json"),
                    "--output",
                    str(artifact_root / "artifact_consistency.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--report-file", payload["path_arg"])
        self.assertIn("report file parent is a symlink", payload["detail"])

    def test_artifact_consistency_cli_rejects_symlinked_report_file_ancestor_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_artifact_consistency_report_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            real_reports = artifact_root / "real_reports"
            linked_reports = artifact_root / "linked_reports"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            real_reports.mkdir(parents=True, exist_ok=True)
            linked_reports.symlink_to(real_reports, target_is_directory=True)
            nested = linked_reports / "nested"
            nested.mkdir(parents=True, exist_ok=True)
            (nested / "report.json").write_text("{}\n")
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_artifact_consistency_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(nested / "report.json"),
                    "--output",
                    str(artifact_root / "artifact_consistency.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--report-file", payload["path_arg"])
        self.assertIn("report file ancestor is a symlink", payload["detail"])

    def test_checkpoint_restore_blocks_symlinked_target_artifact_ancestor(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_target_ancestor_symlink_") as tmpdir:
            tmp = Path(tmpdir)
            target_root = tmp / "restore_target"
            real_parent = target_root / "real_parent"
            linked_parent = target_root / "linked_parent"
            target_root.mkdir(parents=True, exist_ok=True)
            real_parent.mkdir(parents=True, exist_ok=True)
            linked_parent.symlink_to(real_parent, target_is_directory=True)
            record = {
                "artifact_manifest": [
                    {
                        "artifact_id": "state",
                        "path": "linked_parent/nested/state.json",
                    }
                ]
            }

            errors = restore_target_path_errors(record, target_root)

        self.assertEqual(["restore target path ancestor is a symlink: state"], errors)

    def test_continuation_arbiter_cli_rejects_repair_receipt_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_continuation_arbiter_receipt_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "repair_receipt.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")
            state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
            packet = load_json(FIXTURES_ROOT / "continuation_arbiter_run_001" / "repair_packet.json")
            packet["run_id"] = state["run_id"]
            packet["task_class"] = state["task_class"]
            (artifact_root / "state.json").write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            (artifact_root / "repair_packet.json").write_text(json.dumps(packet, indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_continuation_arbiter_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--repair-receipt-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "continuation_arbiter.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--repair-receipt-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_bug_packet_cli_rejects_report_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_bug_packet_report_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "report.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_bug_packet_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "bug_packet.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--report-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_thin_output_cli_rejects_report_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_thin_output_report_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "report.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_thin_output_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(outside),
                    "--mode",
                    "default",
                    "--output",
                    str(artifact_root / "thin_output.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--report-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_repair_handoff_cli_rejects_output_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_repair_handoff_output_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "repair_handoff.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "state.json").write_text(json.dumps(controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json")), indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_repair_handoff_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_artifact_repair_receipt_cli_rejects_report_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_artifact_repair_receipt_report_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "report.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "repair_packet.json").write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_artifact_repair_receipt_v0.py"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--resulting-state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "repair_receipt.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--report-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_checkpoint_preview_cli_rejects_checkpoint_record_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_checkpoint_preview_record_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            outside = tmp / "outside" / "checkpoint_record.json"
            project_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_checkpoint_v0.py"),
                    "preview",
                    "--checkpoint-record-file",
                    str(outside),
                    "--target-root",
                    str(project_root),
                    "--output",
                    str(project_root / "checkpoint_preview.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--checkpoint-record-file", payload["path_arg"])
        self.assertIn("escapes project root", payload["detail"])

    def test_consistency_recovery_cli_rejects_checkpoint_record_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_consistency_recovery_checkpoint_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "checkpoint_record.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "consistency.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_consistency_recovery_v0.py"),
                    "--consistency-file",
                    str(artifact_root / "consistency.json"),
                    "--checkpoint-record-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "consistency_recovery.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--checkpoint-record-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_repair_prompt_bridge_cli_rejects_doctor_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_repair_prompt_bridge_doctor_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "doctor.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "repair_packet.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_repair_prompt_bridge_v0.py"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--doctor-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "prompt.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--doctor-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_governed_cost_cli_rejects_prepared_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_governed_cost_prepared_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "prepared.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "unprepared.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_governed_cost_delta_v0.py"),
                    "--unprepared-file",
                    str(artifact_root / "unprepared.json"),
                    "--prepared-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "governed_cost_delta.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--prepared-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_hybrid_status_cli_rejects_hybrid_record_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_hybrid_status_record_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "hybrid.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "cost.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_hybrid_status_v0.py"),
                    "--cost-record",
                    str(artifact_root / "cost.json"),
                    "--hybrid-record",
                    str(outside),
                    "--output",
                    str(artifact_root / "hybrid_status.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--hybrid-record", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_consistency_recovery_prompt_cli_rejects_thin_output_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_consistency_recovery_prompt_thin_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "thin_output.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "consistency_recovery.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_consistency_recovery_prompt_v0.py"),
                    "--consistency-recovery-file",
                    str(artifact_root / "consistency_recovery.json"),
                    "--thin-output-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "prompt.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--thin-output-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_consistency_recovery_prompt_reading_cli_rejects_prompt_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_consistency_recovery_prompt_reading_prompt_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "prompt.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "consistency_recovery.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_consistency_recovery_prompt_reading_v0.py"),
                    "--consistency-recovery-file",
                    str(artifact_root / "consistency_recovery.json"),
                    "--prompt-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "prompt_reading.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--prompt-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_mode_selector_cli_rejects_governed_cost_delta_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_mode_selector_governed_cost_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "governed_cost_delta.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "cost_record.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_mode_selector_v0.py"),
                    "--cost-record",
                    str(artifact_root / "cost_record.json"),
                    "--scenario-class",
                    "medium_risk_ambiguous_closure",
                    "--task-class",
                    "bounded_change",
                    "--false-success-risk",
                    "LOW",
                    "--recovery-cost",
                    "LOW",
                    "--governed-cost-delta",
                    str(outside),
                    "--output",
                    str(artifact_root / "mode_recommendation.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--governed-cost-delta", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_mode_selector_uses_curated_label_for_curated_local_estimate_provenance(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_mode_selector_provenance_label_") as tmpdir:
            tmp = Path(tmpdir)
            artifact_root = tmp / ".synrail"
            artifact_root.mkdir(parents=True, exist_ok=True)
            comparison_path = artifact_root / "comparison.json"
            cost_path = artifact_root / "cost_record.json"
            output_path = artifact_root / "recommendation.json"
            comparison_path.write_text(json.dumps({
                "schema_version": "baseline_comparison_record_v1",
                "scenario_id": "S1",
                "scenario_class": "repeatable_everyday_local",
                "task_class": "small_template_text_fix",
                "verdict": "BASELINE_GOOD_ENOUGH",
                "baseline_data_provenance": "curated_local_estimate",
                "synrail_data_provenance": "curated_local_estimate",
                "economics_summary": {
                    "operator_minutes_added": 1,
                    "intervention_count_added": 1,
                    "repair_cycles_added": 0,
                    "invalidation_count_added": 0,
                    "closure_latency_minutes_added": 1,
                    "checks_per_accepted_closure_added": 0,
                    "false_green_exposure_reduced": 0,
                    "artifact_completeness_percent_gain": 0,
                    "mandatory_mental_steps_added": 0,
                    "trust_bearing_artifacts_added": 0,
                    "required_visible_surfaces_added": 0,
                    "skippable_visible_surfaces_added": 0,
                    "operator_visible_actions_added": 0,
                    "got_lost_moments_added": 0,
                    "kernel_control_mass_added": 0,
                    "behavioral_control_tax_added": 0,
                    "fixed_control_mass_added": 0,
                    "total_control_burden_added": 1
                }
            }, indent=2, ensure_ascii=True) + "\n")
            cost_path.write_text(json.dumps({
                "schema_version": "cost_of_control_record_v0",
                "source_records": [{"path": str(comparison_path), "scenario_id": "S1", "scenario_class": "repeatable_everyday_local", "verdict": "BASELINE_GOOD_ENOUGH"}],
                "provenance_mix": ["curated_local_estimate"]
            }, indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_mode_selector_v0.py"),
                    "--cost-record",
                    str(cost_path),
                    "--scenario-class",
                    "repeatable_everyday_local",
                    "--task-class",
                    "small_template_text_fix",
                    "--false-success-risk",
                    "LOW",
                    "--recovery-cost",
                    "LOW",
                    "--output",
                    str(output_path),
                ],
                cwd=tmp,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(output_path.read_text())

        self.assertEqual(["curated_local_estimate"], payload["evidence_summary"]["provenance_mix"])
        self.assertIn("current curated-local-estimate class evidence", payload["why"])
        self.assertNotIn("measured class evidence", payload["why"])

    def test_proof_plan_cli_rejects_output_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_proof_plan_output_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "proof_plan.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_proof_plan_v0.py"),
                    "--run-id",
                    "RUN_001",
                    "--task-class",
                    "bounded_change",
                    "--artifact-root",
                    str(artifact_root),
                    "--baseline-identity",
                    "baseline",
                    "--execution-surface-identity",
                    "surface",
                    "--prompt-identity",
                    "prompt",
                    "--task-identity",
                    "task",
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_mode_receipt_cli_rejects_output_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_mode_receipt_output_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "mode_receipt.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "recommendation.json").write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_mode_receipt_v0.py"),
                    "--recommendation-file",
                    str(artifact_root / "recommendation.json"),
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_mode_receipt_carries_selection_evidence_provenance_mix(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_mode_receipt_provenance_mix_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            recommendation = artifact_root / "recommendation.json"
            receipt = artifact_root / "selection_receipt.json"
            recommendation.write_text(json.dumps({
                "schema_version": "mode_recommendation_v0",
                "scenario_class": "repeatable_everyday_local",
                "task_class": "small_template_text_fix",
                "risk_inputs": {
                    "false_success_risk": "LOW",
                    "recovery_cost": "LOW",
                    "execution_surface_ambiguous": False,
                    "artifact_truth_nontrivial": False,
                    "explicit_hybrid_ambiguity": ""
                },
                "evidence_summary": {
                    "class_record_count": 1,
                    "class_verdict": "BASELINE_GOOD_ENOUGH",
                    "hybrid_status": "",
                    "provenance_mix": ["curated_local_estimate"],
                    "avg_operator_minutes_added_if_synrail": 1,
                    "avg_interventions_added_if_synrail": 1,
                    "avg_closure_latency_minutes_added_if_synrail": 1,
                    "avg_false_green_exposure_reduced_if_synrail": 0
                },
                "recommended_mode": "LIGHTWEIGHT_BASELINE",
                "secondary_exception_mode": "",
                "why": "current curated-local-estimate class evidence already says baseline is good enough here",
                "next_safe_step": "use the lightweight baseline"
            }, indent=2, ensure_ascii=True) + "\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_mode_receipt_v0.py"),
                    "--recommendation-file",
                    str(recommendation),
                    "--output",
                    str(receipt),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            payload = json.loads(receipt.read_text())

        self.assertEqual(["curated_local_estimate"], payload["selection_evidence_provenance_mix"])
        self.assertEqual(1, payload["estimated_avoided_operator_minutes"])

    def test_preparation_receipt_cli_rejects_bundle_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_preparation_receipt_bundle_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "bundle.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "plan.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_preparation_receipt_v0.py"),
                    "--plan-file",
                    str(artifact_root / "plan.json"),
                    "--bundle-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "preparation_receipt.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--bundle-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_operator_brief_cli_rejects_doctor_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_operator_brief_doctor_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "doctor.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "state.json").write_text("{}\n")
            (artifact_root / "report.json").write_text("{}\n")
            (artifact_root / "repair_packet.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_operator_brief_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(artifact_root / "report.json"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--doctor-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "operator_brief.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--doctor-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_second_operator_cli_rejects_run_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_second_operator_run_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "run.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "state.json").write_text("{}\n")
            (artifact_root / "repair_packet.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_second_operator_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--repair-packet-file",
                    str(artifact_root / "repair_packet.json"),
                    "--run-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "second_operator.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--run-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_repair_packet_cli_rejects_report_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_repair_packet_report_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "report.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "state.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_repair_packet_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--artifact-root",
                    str(artifact_root),
                    "--report-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "repair_packet.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--report-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_observability_cli_rejects_refresh_file_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_observability_refresh_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "refresh.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "state.json").write_text("{}\n")
            (artifact_root / "report.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_observability_v0.py"),
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--report-file",
                    str(artifact_root / "report.json"),
                    "--refresh-file",
                    str(outside),
                    "--output",
                    str(artifact_root / "observability.json"),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--refresh-file", payload["path_arg"])
        self.assertIn("escapes artifact root", payload["detail"])

    def test_bundle_cli_rejects_output_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_bundle_output_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "bundle.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "final_result.json").write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_bundle_v0.py"),
                    "--final-result",
                    str(artifact_root / "final_result.json"),
                    "--task-class",
                    "bounded_change",
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("escapes project root", payload["detail"])

    def test_cli_bundle_command_rejects_output_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_cli_bundle_output_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "bundle.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "final_result.json").write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_cli_v0.py"),
                    "bundle-check",
                    "--final-result",
                    str(artifact_root / "final_result.json"),
                    "--task-class",
                    "bounded_change",
                    "--output",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--output", payload["path_arg"])
        self.assertIn("escapes project root", payload["detail"])

    def test_spine_orchestrate_rejects_coverage_profile_escape_surface(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_spine_coverage_profile_escape_") as tmpdir:
            tmp = Path(tmpdir)
            project_root = tmp / "project"
            artifact_root = project_root / ".synrail"
            outside = tmp / "outside" / "profile.json"
            project_root.mkdir(parents=True, exist_ok=True)
            artifact_root.mkdir(parents=True, exist_ok=True)
            outside.parent.mkdir(parents=True, exist_ok=True)
            (artifact_root / "state.json").write_text("{}\n")
            (artifact_root / "final_result.json").write_text("{}\n")
            outside.write_text("{}\n")

            result = subprocess.run(
                [
                    sys.executable,
                    str(REPO_ROOT / "tools" / "reference" / "synrail_spine_v0.py"),
                    "orchestrate",
                    "--state-file",
                    str(artifact_root / "state.json"),
                    "--doctor-run-id",
                    "R1",
                    "--doctor-level",
                    "CORE_DOCTOR",
                    "--target-path",
                    str(project_root),
                    "--target-classification",
                    "trusted_worktree",
                    "--baseline-identity",
                    "baseline",
                    "--intended-run-class",
                    "core_probe",
                    "--doctor-output",
                    str(artifact_root / "doctor.json"),
                    "--final-result",
                    str(artifact_root / "final_result.json"),
                    "--task-class",
                    "bounded_change",
                    "--bundle-output",
                    str(artifact_root / "bundle.json"),
                    "--closure-output",
                    str(artifact_root / "closure.json"),
                    "--report-output",
                    str(artifact_root / "report.json"),
                    "--execution-surface-identity",
                    "surface",
                    "--prompt-identity",
                    "prompt",
                    "--task-identity",
                    "task",
                    "--coverage-profile-file",
                    str(outside),
                ],
                cwd=project_root,
                check=False,
                capture_output=True,
                text=True,
            )

        self.assertEqual(2, result.returncode, result.stdout + result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual("PATH_SCOPE_VIOLATION", payload["reason"])
        self.assertEqual("--coverage-profile-file", payload["path_arg"])
        self.assertIn("escapes project root", payload["detail"])

    def test_closure_accepts_with_doctor_override_warning_on_otherwise_valid_bundle(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        state["doctor"]["override_gates"] = ["clean_execution_surface", "artifact_viability"]
        bundle = load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "bundle_valid.json")

        verdict = build_live_verdict(state, bundle)

        self.assertEqual("ACCEPTED", verdict["closure_status"])
        self.assertEqual("", verdict["blocking_reason"])
        self.assertEqual("NONE", verdict["next_allowed_transition"])
        self.assertEqual("NONE", verdict["narrow_next_safe_step"])
        self.assertIn(
            "doctor_override_present: clean_execution_surface, artifact_viability",
            verdict["closure_warnings"],
        )

    def test_closure_rejects_artifact_integrity_drift_on_otherwise_valid_bundle(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = copy.deepcopy(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "bundle_valid.json"))
        bundle["artifact_integrity_warning"] = True

        verdict = build_live_verdict(state, bundle)

        self.assertEqual("REJECTED", verdict["closure_status"])
        self.assertEqual("ARTIFACT_INTEGRITY_FAILED", verdict["blocking_reason"])
        self.assertEqual("PROOF_BUNDLE_REPAIR", verdict["next_allowed_transition"])
        self.assertEqual(
            "rebuild the final result artifact and proof bundle on the current surface",
            verdict["narrow_next_safe_step"],
        )
        self.assertIn("artifact_modified_outside_workflow", verdict["closure_warnings"])

    def test_closure_rejects_post_bundle_final_result_drift_via_freshness_binding(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_closure_freshness_drift_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -Fno 'VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            args = bundle_args(final_result=final_result)
            bundle = build_bundle(args)
            bundle_path = tmp / "bundle.json"
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            state_path = tmp / "state.json"
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            state["_state_file"] = str(state_path)
            bundle["_bundle_file"] = str(bundle_path)

            final_result.write_text(final_result.read_text().replace("PROVEN", "ALREADY_SATISFIED"))
            verdict = build_verdict(copy.deepcopy(state), copy.deepcopy(bundle))

        self.assertEqual("REJECTED", verdict["closure_status"])
        self.assertEqual("CLOSURE_FRESHNESS_FAILED", verdict["blocking_reason"])
        self.assertIn("closure_freshness_binding_mismatch", verdict["closure_warnings"])

    def test_build_verdict_rejects_complete_bundle_without_live_freshness_files(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_closure_not_live_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -Fno 'VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            bundle = build_bundle(bundle_args(final_result=final_result))
            verdict = build_verdict(copy.deepcopy(state), copy.deepcopy(bundle))

        self.assertEqual("REJECTED", verdict["closure_status"])
        self.assertEqual("CLOSURE_FRESHNESS_NOT_LIVE", verdict["blocking_reason"])
        self.assertEqual("PROOF_BUNDLE_REPAIR", verdict["next_allowed_transition"])
        self.assertEqual(
            "rerun closure through the live artifact path so freshness can be verified",
            verdict["narrow_next_safe_step"],
        )

    def test_closure_certificate_carries_bound_hashes_for_live_closure(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_closure_certificate_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -Fno 'VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            args = bundle_args(final_result=final_result)
            bundle = build_bundle(args)
            bundle_path = tmp / "bundle.json"
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            state_path = tmp / "state.json"
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            state["_state_file"] = str(state_path)
            bundle["_bundle_file"] = str(bundle_path)
            verdict = build_verdict(copy.deepcopy(state), copy.deepcopy(bundle))
            certificate = build_closure_certificate(
                state=copy.deepcopy(state),
                bundle=copy.deepcopy(bundle),
                verdict=verdict,
            )
            expected_bundle_sha256 = hashlib.sha256(bundle_path.read_bytes()).hexdigest()
            expected_state_sha256 = hashlib.sha256(state_path.read_bytes()).hexdigest()
            expected_final_result_sha256 = hashlib.sha256(final_result.read_bytes()).hexdigest()

        self.assertEqual("ACCEPTED", verdict["closure_status"])
        self.assertEqual("closure_certificate_v0", certificate["schema_version"])
        self.assertEqual(expected_bundle_sha256, certificate["bundle_sha256"])
        self.assertEqual(expected_state_sha256, certificate["state_sha256"])
        self.assertEqual(expected_final_result_sha256, certificate["final_result_sha256"])
        self.assertEqual("task-001", certificate["task_identity"])
        self.assertEqual(state["run_id"], certificate["final_result_request_id"])
        self.assertEqual(state.get("start_timestamp_utc", ""), certificate["start_timestamp_utc"])
        self.assertEqual(int(state.get("check_count", 0)), certificate["check_count"])
        self.assertEqual(0, certificate["repair_attempt_count"])
        self.assertEqual(0, certificate["repair_max_attempts"])
        self.assertTrue(certificate["closure_timestamp_utc"])
        self.assertTrue(certificate["closure_freshness_binding"]["live_recheck"])
        self.assertTrue(certificate["closure_freshness_binding"]["all_hashes_match"])

    def test_persisted_closure_certificate_tracks_updated_accepted_state(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_persisted_closure_certificate_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -Fno 'VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            args = bundle_args(final_result=final_result)
            bundle = build_bundle(args)
            bundle_path = tmp / "bundle.json"
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            state_path = tmp / "state.json"
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")

            persisted_state = controlled_state(load_json(state_path))
            persisted_state["closure"]["status"] = "ACCEPTED"
            persisted_state["closure"]["blocking_reason"] = ""
            persisted_state["closure"]["next_allowed_transition"] = "NONE"
            persisted_state["closure"]["narrow_next_safe_step"] = "NONE"
            persisted_state["closure"]["missing_sections"] = []
            persisted_state["state"] = "CLOSURE_ACCEPTED"
            persisted_state["closure_timestamp_utc"] = "2026-05-02T07:00:00Z"
            state_path.write_text(json.dumps(persisted_state, indent=2, ensure_ascii=True) + "\n")

            verdict = build_verdict(
                copy.deepcopy(state) | {"_state_file": str(state_path)},
                copy.deepcopy(bundle) | {"_bundle_file": str(bundle_path)},
            )
            certificate_path = tmp / "closure_certificate.json"
            certificate = persist_closure_certificate(
                certificate_path,
                state=persisted_state,
                state_path=state_path,
                bundle=bundle,
                bundle_path=bundle_path,
                verdict=verdict,
            )
            expected_state_sha256 = hashlib.sha256(state_path.read_bytes()).hexdigest()

        self.assertEqual("ACCEPTED", certificate["closure_status"])
        self.assertEqual(expected_state_sha256, certificate["state_sha256"])
        self.assertEqual("2026-05-02T07:00:00Z", certificate["closure_timestamp_utc"])
        self.assertEqual("task-001", certificate["task_identity"])

    def test_canonical_run_artifact_carries_closure_certificate(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        report = {
            "result": "ACCEPTED",
            "stopping_stage": "accepted",
            "reason": "NONE",
            "doctor_verdict": "PASS",
            "resume_applied": False,
            "resume_from_state": "",
            "repair_handoff_applied": False,
            "repair_handoff_from_state": "",
            "repair_handoff_required_inputs": [],
            "missing_continuation_inputs": [],
            "selection_applied": False,
            "selected_mode": "",
            "selected_with_preparation": False,
            "preparation_applied": False,
            "preparation_ready_for_closure": False,
            "bundle_status": "COMPLETE",
            "closure_status": "ACCEPTED",
            "refresh_applied": False,
            "comparison_applied": False,
            "blockers": [],
            "dominant_blocker": "NONE",
            "resulting_state": state["state"],
            "next_safe_step": state["next_safe_step"],
        }
        worked = {
            "resulting_state": state["state"],
            "current_closure_status": state["closure"]["status"],
            "next_safe_step": state["next_safe_step"],
        }
        certificate = {
            "schema_version": "closure_certificate_v0",
            "run_id": state["run_id"],
            "closure_status": "ACCEPTED",
            "bundle_sha256": "bundle-hash",
            "state_sha256": "state-hash",
        }

        run_artifact = build_canonical_run_artifact(
            state=state,
            report=report,
            worked=worked,
            repair_packet=None,
            closure_certificate=certificate,
        )

        self.assertEqual("closure_certificate_v0", run_artifact["closure_certificate"]["schema_version"])
        self.assertEqual(state["run_id"], run_artifact["closure_certificate"]["run_id"])
        self.assertEqual("bundle-hash", run_artifact["closure_certificate"]["bundle_sha256"])

    def test_artifact_consistency_records_closure_certificate(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        certificate = {
            "schema_version": "closure_certificate_v0",
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "closure_status": state["closure"]["status"],
        }

        record = build_artifact_consistency_record(
            state=state,
            closure_certificate=certificate,
        )

        self.assertIn("closure_certificate", record["checked_artifacts"])
        self.assertEqual("KEEP_DERIVED_ARTIFACT", record["artifact_actions"]["closure_certificate"])
        self.assertEqual("CONSISTENT", record["result"])

    def test_artifact_consistency_marks_stale_closure_certificate(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        certificate = {
            "schema_version": "closure_certificate_v0",
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "closure_status": "REJECTED",
        }

        record = build_artifact_consistency_record(
            state=state,
            closure_certificate=certificate,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("closure_certificate", record["stale_artifact_ids"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["closure_certificate"])

    def test_artifact_consistency_marks_stale_run_with_embedded_closure_certificate(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        run_artifact = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": {"state": state["state"]},
            "closure_certificate": {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": "REJECTED",
            },
        }

        record = build_artifact_consistency_record(
            state=state,
            run_artifact=run_artifact,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("run", record["stale_artifact_ids"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["run"])

    def test_artifact_consistency_marks_stale_closure_certificate_hashes(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_closure_certificate_hash_drift_") as tmpdir:
            tmp = Path(tmpdir)
            state["start_timestamp_utc"] = "2026-05-02T06:00:00Z"
            state["check_count"] = 3
            state["closure_timestamp_utc"] = "2026-05-02T07:00:00Z"
            state_path = tmp / "state.json"
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({"status": "PROVEN"}, indent=2, ensure_ascii=True) + "\n")
            bundle_path = tmp / "bundle.json"
            bundle = {
                "run_id": state["run_id"],
                "artifact_identity": {"task_identity": "task-001"},
                "repair_packet": {"repair_attempt_count": 2, "repair_max_attempts": 5},
                "closure_freshness_binding": {
                    "schema_version": "closure_freshness_binding_v0",
                    "bound_at_utc": "2026-05-02T07:00:00Z",
                    "artifacts": [
                        {
                            "artifact_id": "final_result",
                            "path": str(final_result),
                            "required": True,
                            "present": True,
                            "sha256": hashlib.sha256(final_result.read_bytes()).hexdigest(),
                        }
                    ],
                },
            }
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            repair_packet = {
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "from_state": state["state"],
                "repair_termination": {"attempt_count": 2, "max_attempts": 5},
            }
            certificate = {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": state["closure"]["status"],
                "state_sha256": "stale-state-hash",
                "bundle_sha256": "stale-bundle-hash",
                "final_result_sha256": "stale-final-hash",
                "task_identity": "wrong-task",
                "start_timestamp_utc": "stale-start-time",
                "check_count": 9,
                "closure_timestamp_utc": "stale-closure-time",
                "repair_attempt_count": 7,
                "repair_max_attempts": 8,
            }

            record = build_artifact_consistency_record(
                state=state,
                state_file=state_path,
                bundle_file=bundle_path,
                bundle=bundle,
                closure_certificate=certificate,
                repair_packet=repair_packet,
            )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("closure_certificate", record["stale_artifact_ids"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["closure_certificate"])
        self.assertIn("closure_certificate refers to stale final_result_sha256 hash", "\n".join(record["failure_reasons"]))
        self.assertIn("closure_certificate refers to stale task_identity snapshot", record["failure_reasons"])
        self.assertIn("closure_certificate refers to stale start_timestamp_utc snapshot", record["failure_reasons"])
        self.assertIn("closure_certificate refers to stale check_count snapshot", record["failure_reasons"])
        self.assertIn("closure_certificate refers to stale closure_timestamp_utc snapshot", record["failure_reasons"])
        self.assertIn("closure_certificate refers to stale repair_attempt_count snapshot", record["failure_reasons"])
        self.assertIn("closure_certificate refers to stale repair_max_attempts snapshot", record["failure_reasons"])

    def test_artifact_consistency_marks_stale_repair_counter_snapshots(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        repair_packet = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "from_state": state["state"],
            "repair_termination": {"attempt_count": 2, "max_attempts": 5},
        }
        report = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": state["state"],
            "repair_attempt_count": 1,
            "repair_max_attempts": 4,
        }
        orchestration = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": state["state"],
            "repair_packet": {"repair_attempt_count": 1, "repair_max_attempts": 4},
            "repair_history": {"attempt_count": 1, "max_attempts": 4},
        }
        run_artifact = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": {"state": state["state"]},
            "closure_certificate": {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": state["closure"]["status"],
            },
            "repair_packet": {"repair_attempt_count": 1, "repair_max_attempts": 4},
            "repair_history": {"attempt_count": 1, "max_attempts": 4},
        }

        record = build_artifact_consistency_record(
            state=state,
            report=report,
            orchestration=orchestration,
            run_artifact=run_artifact,
            repair_packet=repair_packet,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("report", record["stale_artifact_ids"])
        self.assertIn("orchestration", record["stale_artifact_ids"])
        self.assertIn("run", record["stale_artifact_ids"])
        self.assertIn("report refers to stale repair_attempt_count snapshot", record["failure_reasons"])
        self.assertIn("orchestration refers to stale repair_packet.repair_attempt_count snapshot", record["failure_reasons"])
        self.assertIn("run refers to stale repair_history.attempt_count snapshot", record["failure_reasons"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["report"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["orchestration"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["run"])

    def test_artifact_consistency_marks_stale_run_embedded_closure_timing_snapshots(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        state["start_timestamp_utc"] = "2026-05-02T06:00:00Z"
        state["check_count"] = 4
        run_artifact = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": {"state": state["state"]},
            "closure_certificate": {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": state["closure"]["status"],
                "start_timestamp_utc": "2026-05-02T05:59:59Z",
                "check_count": 2,
            },
        }

        record = build_artifact_consistency_record(
            state=state,
            run_artifact=run_artifact,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("run", record["stale_artifact_ids"])
        self.assertIn("run refers to stale start_timestamp_utc snapshot", record["failure_reasons"])
        self.assertIn("run refers to stale check_count snapshot", record["failure_reasons"])

    def test_artifact_consistency_records_matching_repair_counter_snapshots(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        repair_packet = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "from_state": state["state"],
            "repair_termination": {"attempt_count": 2, "max_attempts": 5},
        }
        report = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": state["state"],
            "repair_attempt_count": 2,
            "repair_max_attempts": 5,
        }
        orchestration = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": state["state"],
            "repair_packet": {"repair_attempt_count": 2, "repair_max_attempts": 5},
            "repair_history": {"attempt_count": 2, "max_attempts": 5},
        }
        run_artifact = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": {"state": state["state"]},
            "closure_certificate": {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": state["closure"]["status"],
                "start_timestamp_utc": state.get("start_timestamp_utc", ""),
                "check_count": int(state.get("check_count", 0)),
                "repair_attempt_count": 2,
                "repair_max_attempts": 5,
            },
            "repair_packet": {"repair_attempt_count": 2, "repair_max_attempts": 5},
            "repair_history": {"attempt_count": 2, "max_attempts": 5},
        }

        record = build_artifact_consistency_record(
            state=state,
            report=report,
            orchestration=orchestration,
            run_artifact=run_artifact,
            repair_packet=repair_packet,
        )

        self.assertEqual("CONSISTENT", record["result"])
        self.assertNotIn("report", record["stale_artifact_ids"])
        self.assertNotIn("orchestration", record["stale_artifact_ids"])
        self.assertNotIn("run", record["stale_artifact_ids"])
        self.assertEqual("KEEP_DERIVED_ARTIFACT", record["artifact_actions"]["report"])
        self.assertEqual("KEEP_DERIVED_ARTIFACT", record["artifact_actions"]["orchestration"])
        self.assertEqual("KEEP_DERIVED_ARTIFACT", record["artifact_actions"]["run"])
        self.assertEqual("KEEP_DERIVED_ARTIFACT", record["artifact_actions"]["repair_packet"])

    def test_phase_closure_rebinds_bundle_and_certificate_to_live_final_result_snapshot(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        state["state"] = "PROOF_BUNDLE_COMPLETE"
        state["closure"]["status"] = "OPEN"
        state["closure"]["blocking_reason"] = ""
        state["closure"]["next_allowed_transition"] = "READY"
        state["closure"]["narrow_next_safe_step"] = "decide closure"

        with tempfile.TemporaryDirectory(prefix="synrail_phase_closure_drift_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -Fno 'VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            state_path = tmp / "state.json"
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            bundle_path = tmp / "bundle.json"
            bundle = build_bundle(bundle_args(final_result=final_result))
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            closure_path = tmp / "closure.json"
            closure_path.write_text("{}\n")
            certificate_path = tmp / "closure_certificate.json"
            report_path = tmp / "report.json"
            doctor_output = tmp / "doctor.json"
            doctor_output.write_text("{}\n")
            final_result.write_text(final_result.read_text().replace("PROVEN", "ALREADY_SATISFIED"))

            args = argparse.Namespace(
                state_file=str(state_path),
                bundle_output=str(bundle_path),
                closure_output=str(closure_path),
                closure_certificate_output=str(certificate_path),
                acceptance_validation_output="",
                project_profile_file="",
                acceptance_criteria_file="",
                final_result=str(final_result),
                task_class="proof_sensitive_fix",
                run_id=state["run_id"],
                readback=str(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "readback.txt"),
                scenario_proof=str(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "scenario.txt"),
                baseline_identity="trusted_clean",
                execution_surface_identity="clean-clone",
                prompt_identity="prompt-001",
                task_identity="task-001",
                doctor_output=str(doctor_output),
                report_output=str(report_path),
                refresh_output="",
                refresh_event_type="",
                refresh_doctor_status="",
                refresh_use_bundle=False,
                observability_output="",
                artifact_consistency_output="",
                output="",
                worked_artifact_output="",
                run_artifact_output="",
                repair_packet_output="",
                repair_handoff_output="",
                repair_receipt_output="",
                plan_output="",
                preparation_receipt_output="",
            )
            ctx = OrchestrationContext(state=state, state_path=state_path, doctor_record={"final_verdict": "ACCEPTABLE_READY"}, bundle=bundle)

            with patch("synrail_spine_v0.run_python_capture", return_value=(0, "")):
                code = _phase_closure(ctx, args)

            rebased_bundle = load_json(bundle_path)
            certificate = load_json(certificate_path)
            closure_payload = load_json(closure_path)

        self.assertIsNone(code)
        self.assertEqual("ALREADY_SATISFIED", rebased_bundle["final_result"]["normalized_status"])
        self.assertEqual("task-001", certificate["task_identity"])
        self.assertEqual(rebased_bundle["verification_recheck"], certificate["verification_recheck"])
        self.assertEqual(rebased_bundle["closure_freshness_binding"]["bound_at_utc"], certificate["closure_freshness_binding"]["bound_at_utc"])
        self.assertEqual(
            rebased_bundle["closure_freshness_binding"]["artifacts"][0]["sha256"],
            certificate["final_result_sha256"],
        )
        self.assertTrue(certificate["closure_timestamp_utc"])
        self.assertEqual(certificate["closure_status"], ctx.state["closure"]["status"])
        self.assertEqual(certificate["closure_status"], closure_payload["closure_status"])
        self.assertEqual(certificate["blocking_reason"], closure_payload["blocking_reason"])
        self.assertEqual(certificate["blocking_reason"], ctx.state["closure"]["blocking_reason"])

    def test_phase_closure_rejects_post_accept_final_result_drift_before_persisting_certificate(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        state["state"] = "PROOF_BUNDLE_COMPLETE"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = ""
        state["closure"]["next_allowed_transition"] = ""
        state["closure"]["narrow_next_safe_step"] = ""
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = "decide closure"
        state["closure_timestamp_utc"] = ""

        with tempfile.TemporaryDirectory(prefix="synrail_phase_closure_atomic_drift_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -Fno 'VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            state_path = tmp / "state.json"
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            bundle_path = tmp / "bundle.json"
            bundle = build_bundle(bundle_args(final_result=final_result))
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            closure_path = tmp / "closure.json"
            closure_path.write_text("{}\n")
            certificate_path = tmp / "closure_certificate.json"
            report_path = tmp / "report.json"
            doctor_output = tmp / "doctor.json"
            doctor_output.write_text("{}\n")

            args = argparse.Namespace(
                state_file=str(state_path),
                bundle_output=str(bundle_path),
                closure_output=str(closure_path),
                closure_certificate_output=str(certificate_path),
                acceptance_validation_output="",
                project_profile_file="",
                acceptance_criteria_file="",
                final_result=str(final_result),
                task_class="proof_sensitive_fix",
                run_id=state["run_id"],
                readback=str(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "readback.txt"),
                scenario_proof=str(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "scenario.txt"),
                baseline_identity="trusted_clean",
                execution_surface_identity="clean-clone",
                prompt_identity="prompt-001",
                task_identity="task-001",
                doctor_output=str(doctor_output),
                report_output=str(report_path),
                refresh_output="",
                refresh_event_type="",
                refresh_doctor_status="",
                refresh_use_bundle=False,
                observability_output="",
                artifact_consistency_output="",
                output="",
                worked_artifact_output="",
                run_artifact_output="",
                repair_packet_output="",
                repair_handoff_output="",
                repair_receipt_output="",
                plan_output="",
                preparation_receipt_output="",
                doctor_run_id=state["run_id"],
                doctor_level="strict",
                target_path="tools/reference/synrail_bundle_v0.py",
                target_classification="repo_file",
                intended_run_class="bounded_change",
                bootstrap_provenance_ok=True,
                bootstrap_provenance_reason="CONTROLLED_BOOTSTRAP_CONFIRMED",
                mode_selection_receipt="",
                preparation_artifact_root="",
                refresh_recovery_status="",
                refresh_reverification_complete=False,
                refresh_use_closure=False,
                comparison_output="",
                comparison_input="",
                repair_packet_file="",
                repair_receipt_file="",
            )
            ctx = OrchestrationContext(state=state, state_path=state_path, doctor_record={"final_verdict": "ACCEPTABLE_READY"}, bundle=bundle)

            original_save_state = synrail_spine_v0.save_state
            mutated = False

            def mutate_after_accept(path: Path, payload: dict) -> None:
                nonlocal mutated
                original_save_state(path, payload)
                if not mutated and payload.get("closure", {}).get("status") == "ACCEPTED":
                    final_result.write_text(final_result.read_text().replace("\"status\": \"PROVEN\"", "\"status\": \"ALREADY_SATISFIED\""))
                    mutated = True

            with patch("synrail_spine_v0.run_python_capture", return_value=(0, "")), patch("synrail_spine_v0.save_state", side_effect=mutate_after_accept), patch("synrail_spine_v0.finalize_runtime_outputs", return_value=None):
                code = _phase_closure(ctx, args)

            certificate = load_json(certificate_path)
            closure_payload = load_json(closure_path)
            persisted_state = load_json(state_path)

        self.assertEqual(0, code)
        self.assertEqual("REJECTED", closure_payload["closure_status"])
        self.assertEqual("CLOSURE_FRESHNESS_FAILED", closure_payload["blocking_reason"])
        self.assertEqual("REJECTED", certificate["closure_status"])
        self.assertEqual("CLOSURE_FRESHNESS_FAILED", certificate["blocking_reason"])
        self.assertEqual("REJECTED", persisted_state["closure"]["status"])
        self.assertEqual("CLOSURE_REJECTED", persisted_state["state"])
        self.assertEqual("", persisted_state["closure_timestamp_utc"])

    def test_artifact_consistency_marks_stale_run_embedded_closure_certificate_hashes(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_run_embedded_certificate_hash_drift_") as tmpdir:
            tmp = Path(tmpdir)
            state_path = tmp / "state.json"
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            bundle_path = tmp / "bundle.json"
            bundle_path.write_text(json.dumps({"run_id": state["run_id"]}, indent=2, ensure_ascii=True) + "\n")
            run_artifact = {
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "resulting_state": {"state": state["state"]},
                "closure_certificate": {
                    "schema_version": "closure_certificate_v0",
                    "run_id": state["run_id"],
                    "task_class": state["task_class"],
                    "closure_status": state["closure"]["status"],
                    "state_sha256": "stale-state-hash",
                    "bundle_sha256": "stale-bundle-hash",
                },
            }

            record = build_artifact_consistency_record(
                state=state,
                state_file=state_path,
                bundle_file=bundle_path,
                run_artifact=run_artifact,
            )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("run", record["stale_artifact_ids"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["run"])

    def test_artifact_consistency_marks_stale_closure_certificate_verification_recheck(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = {
            "verification_recheck": {"executed": True, "matched": True},
            "closure_freshness_binding": {"schema_version": "closure_freshness_binding_v0", "artifacts": []},
        }
        certificate = {
            "schema_version": "closure_certificate_v0",
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "closure_status": state["closure"]["status"],
            "verification_recheck": {"executed": True, "matched": False},
        }

        record = build_artifact_consistency_record(
            state=state,
            bundle=bundle,
            closure_certificate=certificate,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("closure_certificate", record["stale_artifact_ids"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["closure_certificate"])

    def test_artifact_consistency_marks_stale_when_expected_hash_exists_but_source_file_is_missing(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        certificate = {
            "schema_version": "closure_certificate_v0",
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "closure_status": state["closure"]["status"],
            "state_sha256": "expected-state-hash",
        }

        record = build_artifact_consistency_record(
            state=state,
            state_file=Path("/tmp/definitely-missing-synrail-state.json"),
            closure_certificate=certificate,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("closure_certificate", record["stale_artifact_ids"])
        self.assertIn(
            "closure_certificate refers to missing source artifact for state_sha256",
            record["failure_reasons"],
        )

    def test_artifact_consistency_rejects_certificate_final_result_hash_outside_artifact_root(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_artifact_consistency_outside_certificate_") as tmpdir:
            tmp = Path(tmpdir)
            artifact_root = tmp / ".synrail"
            artifact_root.mkdir()
            state_path = artifact_root / "state.json"
            bundle_path = artifact_root / "bundle.json"
            outside = tmp / "outside_final_result.json"
            outside.write_text(json.dumps({"status": "PROVEN"}, indent=2, ensure_ascii=True) + "\n")
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            bundle = {
                "run_id": state["run_id"],
                "closure_freshness_binding": {
                    "schema_version": "closure_freshness_binding_v0",
                    "bound_at_utc": "2026-05-03T00:00:00Z",
                    "artifacts": [
                        {
                            "artifact_id": "final_result",
                            "path": str(outside),
                            "required": True,
                            "present": True,
                            "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                        }
                    ],
                },
            }
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            certificate = {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": state["closure"]["status"],
                "final_result_sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
            }

            record = build_artifact_consistency_record(
                state=state,
                state_file=state_path,
                bundle_file=bundle_path,
                bundle=bundle,
                closure_certificate=certificate,
                project_root=REPO_ROOT,
                artifact_root=artifact_root,
            )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("closure_certificate", record["stale_artifact_ids"])
        self.assertIn(
            "closure_certificate refers to out-of-scope source artifact for final_result_sha256",
            record["failure_reasons"],
        )

    def test_artifact_consistency_rejects_run_embedded_certificate_outside_hash_source(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_artifact_consistency_outside_run_") as tmpdir:
            tmp = Path(tmpdir)
            artifact_root = tmp / ".synrail"
            artifact_root.mkdir()
            state_path = artifact_root / "state.json"
            bundle_path = artifact_root / "bundle.json"
            outside = tmp / "outside_final_result.json"
            outside.write_text(json.dumps({"status": "PROVEN"}, indent=2, ensure_ascii=True) + "\n")
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            bundle = {
                "run_id": state["run_id"],
                "closure_freshness_binding": {
                    "schema_version": "closure_freshness_binding_v0",
                    "bound_at_utc": "2026-05-03T00:00:00Z",
                    "artifacts": [
                        {
                            "artifact_id": "final_result",
                            "path": str(outside),
                            "required": True,
                            "present": True,
                            "sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                        }
                    ],
                },
            }
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            run_artifact = {
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "resulting_state": {"state": state["state"]},
                "closure_certificate": {
                    "schema_version": "closure_certificate_v0",
                    "run_id": state["run_id"],
                    "task_class": state["task_class"],
                    "closure_status": state["closure"]["status"],
                    "final_result_sha256": hashlib.sha256(outside.read_bytes()).hexdigest(),
                },
            }

            record = build_artifact_consistency_record(
                state=state,
                state_file=state_path,
                bundle_file=bundle_path,
                bundle=bundle,
                run_artifact=run_artifact,
                project_root=REPO_ROOT,
                artifact_root=artifact_root,
            )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("run", record["stale_artifact_ids"])
        self.assertIn(
            "run refers to out-of-scope source artifact for final_result_sha256",
            record["failure_reasons"],
        )

    def test_artifact_consistency_accepts_certificate_hash_source_inside_artifact_root(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_artifact_consistency_inside_certificate_") as tmpdir:
            tmp = Path(tmpdir)
            artifact_root = tmp / ".synrail"
            artifact_root.mkdir()
            state_path = artifact_root / "state.json"
            bundle_path = artifact_root / "bundle.json"
            final_result = artifact_root / "final_result.json"
            final_result.write_text(json.dumps({"status": "PROVEN"}, indent=2, ensure_ascii=True) + "\n")
            state_path.write_text(json.dumps(state, indent=2, ensure_ascii=True) + "\n")
            bundle = {
                "run_id": state["run_id"],
                "closure_freshness_binding": {
                    "schema_version": "closure_freshness_binding_v0",
                    "bound_at_utc": "2026-05-03T00:00:00Z",
                    "artifacts": [
                        {
                            "artifact_id": "final_result",
                            "path": str(final_result),
                            "required": True,
                            "present": True,
                            "sha256": hashlib.sha256(final_result.read_bytes()).hexdigest(),
                        }
                    ],
                },
            }
            bundle_path.write_text(json.dumps(bundle, indent=2, ensure_ascii=True) + "\n")
            final_result_hash = hashlib.sha256(final_result.read_bytes()).hexdigest()
            certificate = {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": state["closure"]["status"],
                "final_result_sha256": final_result_hash,
                "closure_freshness_binding": {
                    "present": True,
                    "schema_version": "closure_freshness_binding_v0",
                    "bound_at_utc": "2026-05-03T00:00:00Z",
                    "all_required_present": True,
                    "all_hashes_match": True,
                    "artifacts": [
                        {
                            "artifact_id": "final_result",
                            "path": str(final_result),
                            "required": True,
                            "present": True,
                            "expected_sha256": final_result_hash,
                            "current_sha256": final_result_hash,
                            "hashes_match": True,
                            "live_recheck": True,
                        }
                    ],
                    "live_recheck": True,
                },
            }

            record = build_artifact_consistency_record(
                state=state,
                state_file=state_path,
                bundle_file=bundle_path,
                bundle=bundle,
                closure_certificate=certificate,
                project_root=REPO_ROOT,
                artifact_root=artifact_root,
            )

        self.assertEqual("CONSISTENT", record["result"])
        self.assertNotIn("closure_certificate", record["stale_artifact_ids"])
        self.assertEqual("KEEP_DERIVED_ARTIFACT", record["artifact_actions"]["closure_certificate"])

    def test_artifact_consistency_rejects_one_sided_closure_certificate_verification_recheck(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = {
            "verification_recheck": {"executed": True, "matched": True},
            "closure_freshness_binding": {"schema_version": "closure_freshness_binding_v0", "artifacts": []},
        }
        certificate = {
            "schema_version": "closure_certificate_v0",
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "closure_status": state["closure"]["status"],
        }

        record = build_artifact_consistency_record(
            state=state,
            bundle=bundle,
            closure_certificate=certificate,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("closure_certificate", record["stale_artifact_ids"])
        self.assertIn(
            "closure_certificate refers to stale verification_recheck snapshot",
            record["failure_reasons"],
        )

    def test_artifact_consistency_rejects_one_sided_run_embedded_freshness_binding(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        run_artifact = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": {"state": state["state"]},
            "closure_certificate": {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": state["closure"]["status"],
                "closure_freshness_binding": {"present": True, "artifacts": []},
            },
        }

        record = build_artifact_consistency_record(
            state=state,
            bundle={},
            run_artifact=run_artifact,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("run", record["stale_artifact_ids"])
        self.assertIn("run refers to stale closure_freshness_binding snapshot", record["failure_reasons"])

    def test_artifact_consistency_marks_stale_closure_certificate_freshness_binding(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = {
            "verification_recheck": {"executed": True, "matched": True},
            "closure_freshness_binding": {
                "schema_version": "closure_freshness_binding_v0",
                "bound_at_utc": "2026-05-01T00:00:00Z",
                "artifacts": [],
            },
        }
        certificate = {
            "schema_version": "closure_certificate_v0",
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "closure_status": state["closure"]["status"],
            "closure_freshness_binding": {
                "present": True,
                "schema_version": "closure_freshness_binding_v0",
                "bound_at_utc": "stale-binding",
                "all_required_present": True,
                "all_hashes_match": False,
                "artifacts": [],
                "live_recheck": False,
            },
        }

        record = build_artifact_consistency_record(
            state=state,
            bundle=bundle,
            closure_certificate=certificate,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("closure_certificate", record["stale_artifact_ids"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["closure_certificate"])

    def test_artifact_consistency_marks_stale_run_embedded_closure_certificate_verification_recheck(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))
        bundle = {
            "verification_recheck": {"executed": True, "matched": True},
            "closure_freshness_binding": {"schema_version": "closure_freshness_binding_v0", "artifacts": []},
        }
        run_artifact = {
            "run_id": state["run_id"],
            "task_class": state["task_class"],
            "resulting_state": {"state": state["state"]},
            "closure_certificate": {
                "schema_version": "closure_certificate_v0",
                "run_id": state["run_id"],
                "task_class": state["task_class"],
                "closure_status": state["closure"]["status"],
                "verification_recheck": {"executed": True, "matched": False},
            },
        }

        record = build_artifact_consistency_record(
            state=state,
            bundle=bundle,
            run_artifact=run_artifact,
        )

        self.assertEqual("INCONSISTENT", record["result"])
        self.assertIn("run", record["stale_artifact_ids"])
        self.assertEqual("REEMIT_FROM_STATE", record["artifact_actions"]["run"])

    def test_bundle_recheck_matches_allowed_command(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_match_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -n 'VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            bundle = build_bundle(bundle_args(final_result=final_result))
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertTrue(bundle["verification_recheck"]["matched"])
        self.assertEqual("", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_bundle_marks_structured_diff_without_verification_command_as_partial(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_missing_command_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            changed_file = "tmp_recheck/app.py"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": [changed_file],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": changed_file,
                    "added_line": "import logging",
                    "context_before": "from os import path",
                    "context_after": "return logging",
                    "verification_command": "",
                    "verification_result": "import logging",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": f"Workspace clean after updating only {changed_file} with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            bundle = build_bundle(bundle_args(final_result=final_result))
            verdict = build_live_verdict(state, bundle)

        self.assertFalse(bundle["diff_provenance"]["verification_command_present"])
        self.assertFalse(bundle["diff_provenance"]["structurally_complete"])
        self.assertIn("diff_provenance", bundle["missing_sections"])
        self.assertEqual("PARTIAL", bundle["status"])
        self.assertEqual("PARTIAL", bundle["structural_status"])
        self.assertEqual("MISSING_PROOF_SECTIONS", verdict["blocking_reason"])

    def test_bundle_recheck_matches_grep_output_without_line_number_in_expected(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_body_match_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            changed_file = "tmp_recheck/app.py"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": [changed_file],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": changed_file,
                    "added_line": "import logging",
                    "context_before": "from os import path",
                    "context_after": "return logging",
                    "verification_command": f"grep -n 'import logging' {changed_file}",
                    "verification_result": "import logging",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": f"Workspace clean after updating only {changed_file} with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            project_root = tmp / "recheck_project"
            target = project_root / changed_file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("import logging\n")
            bundle = build_bundle(args)
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertTrue(bundle["verification_recheck"]["matched"])
        self.assertEqual("", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_bundle_recheck_rejects_hostile_substring_output(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_hostile_substring_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            changed_file = "tmp_recheck/app.py"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": [changed_file],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": changed_file,
                    "added_line": "import logging",
                    "context_before": "from os import path",
                    "context_after": "return logging",
                    "verification_command": f"grep -n 'import logging' {changed_file}",
                    "verification_result": "import logging",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": f"Workspace clean after updating only {changed_file} with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            project_root = tmp / "recheck_project"
            target = project_root / changed_file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# DO NOT import logging\n")
            bundle = build_bundle(args)
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("VERIFICATION_RECHECK_FAILED", verdict["blocking_reason"])

    def test_bundle_recheck_rejects_extra_matching_lines(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_extra_lines_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            changed_file = "tmp_recheck/app.py"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": [changed_file],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": changed_file,
                    "added_line": "import logging",
                    "context_before": "from os import path",
                    "context_after": "return logging",
                    "verification_command": f"grep -n 'import logging' {changed_file}",
                    "verification_result": "import logging",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": f"Workspace clean after updating only {changed_file} with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            project_root = tmp / "recheck_project"
            target = project_root / changed_file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("import logging\nimport logging extra\n")
            bundle = build_bundle(args)
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("VERIFICATION_RECHECK_FAILED", verdict["blocking_reason"])

    def test_bundle_recheck_blocks_closure_on_mismatch(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_mismatch_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -n 'VERIFICATION_RECHECK_ALLOWED_BINARIES' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "999:missing expected line",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            bundle = build_bundle(bundle_args(final_result=final_result))
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("VERIFICATION_RECHECK_FAILED", verdict["blocking_reason"])
        self.assertEqual("PROOF_BUNDLE_REPAIR", verdict["next_allowed_transition"])

    def test_bundle_recheck_skips_command_outside_allowlist(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_skip_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "sed -n 1p tools/reference/synrail_bundle_v0.py",
                    "verification_result": "#!/usr/bin/env python3",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            bundle = build_bundle(bundle_args(final_result=final_result))
            verdict = build_live_verdict(state, bundle)

        self.assertFalse(bundle["verification_recheck"]["executed"])
        self.assertFalse(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertTrue(bundle["verification_recheck"]["required"])
        self.assertEqual("command_not_in_allowlist", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("REJECTED", verdict["closure_status"])
        self.assertEqual("VERIFICATION_RECHECK_NOT_EXECUTED", verdict["blocking_reason"])

    def test_bundle_recheck_rejects_python_command_without_executing_it(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_python_block_") as tmpdir:
            tmp = Path(tmpdir)
            marker = tmp / "python_recheck_executed.txt"
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": f"python3 -c \"open({str(marker)!r}, 'w').write('executed')\"",
                    "verification_result": "executed",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            bundle = build_bundle(bundle_args(final_result=final_result))
            verdict = build_live_verdict(state, bundle)

        self.assertFalse(marker.exists())
        self.assertFalse(bundle["verification_recheck"]["executed"])
        self.assertFalse(bundle["verification_recheck"]["command_allowed"])
        self.assertTrue(bundle["verification_recheck"]["required"])
        self.assertEqual("command_not_in_allowlist", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("REJECTED", verdict["closure_status"])
        self.assertEqual("VERIFICATION_RECHECK_NOT_EXECUTED", verdict["blocking_reason"])

    def test_bundle_recheck_marks_timeout(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_recheck_timeout_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "tail -f tools/reference/synrail_bundle_v0.py",
                    "verification_result": "done",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            bundle = build_bundle(bundle_args(final_result=final_result))

        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("timeout", bundle["verification_recheck"]["skip_reason"])

    def test_closure_blocks_on_semantically_thin_proof(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_semantic_thin.json"))
        bundle = build_bundle(
            bundle_args(
                final_result=FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "final_result_semantic_thin.json"
            )
        )
        verdict = build_live_verdict(state, bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertIn("diff_provenance", bundle["semantically_insufficient_sections"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])
        self.assertEqual("PROOF_BUNDLE_STRENGTHENING", verdict["next_allowed_transition"])

    def test_bundle_allows_first_sanctioned_replacement_of_starter_final_result(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_first_proof_replacement_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            starter_payload = {
                "request_id": state["run_id"],
                "task_class": state["task_class"],
                "status": "PENDING_PROOF",
                "change_disposition": "modified",
                "summary": "Replace this starter payload with the actual bounded result for this run.",
            }
            final_result.write_text(json.dumps(starter_payload, indent=2, ensure_ascii=True) + "\n")
            starter_hash = hashlib.sha256(final_result.read_bytes()).hexdigest()

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "task_class": state["task_class"],
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "Tightened closure trust policy and verified it locally.",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "def starter_final_result_replacement_is_sanctioned(",
                    "context_before": "def file_sha256(path: Path) -> str:",
                    "context_after": "def normalize_verification_recheck_text(value: str, *, executable: str) -> str:",
                    "verification_command": "grep -Fno 'def starter_final_result_replacement_is_sanctioned(' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "def starter_final_result_replacement_is_sanctioned(",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            args.state_file = str(write_state_bound_hash_context(tmp, state=state, starter_hash=starter_hash))
            bundle = build_bundle(args)

        verdict = build_live_verdict(state, bundle)

        self.assertFalse(bundle["artifact_integrity_warning"])
        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_bundle_ignores_forged_cli_hashes_for_artifact_integrity(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_hash_cli_bypass_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -Fno 'VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")

            state_file = tmp / "state.json"
            state_payload = copy.deepcopy(state)
            state_payload["last_known_final_result_hash"] = "0" * 64
            state_file.write_text(json.dumps(state_payload, indent=2, ensure_ascii=True) + "\n")
            (tmp / "proof_request.json").write_text(json.dumps({
                "starter_hashes": {"final_result": "1" * 64},
            }, indent=2, ensure_ascii=True) + "\n")

            args = bundle_args(final_result=final_result)
            args.state_file = str(state_file)
            args.last_known_final_result_hash = hashlib.sha256(final_result.read_bytes()).hexdigest()
            args.starter_final_result_hash = args.last_known_final_result_hash
            bundle = build_bundle(args)
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["artifact_integrity_warning"])
        self.assertEqual("REJECTED", verdict["closure_status"])
        self.assertEqual("ARTIFACT_INTEGRITY_FAILED", verdict["blocking_reason"])

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_corroboration"]["has_patch_runtime_verification"])
        self.assertTrue(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertTrue(bundle["readback"]["content_semantically_sufficient"])
        # Scenario prose is now correctly recognized as thin (no command-output evidence in
        # Observed: line), but waiver no longer closes trust if the allowed verification recheck fails.
        self.assertFalse(bundle["scenario_proof"]["content_semantically_sufficient"])
        self.assertTrue(bundle["readback"]["waived_by_runtime_corroboration"])
        self.assertTrue(bundle["scenario_proof"]["waived_by_runtime_corroboration"])
        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("REJECTED", verdict["closure_status"])
        self.assertEqual("VERIFICATION_RECHECK_FAILED", verdict["blocking_reason"])

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

        verdict = build_live_verdict(state, bundle)

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

    def test_structured_diff_provenance_rejects_multi_file_change_with_single_record(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_multi_file_single_record_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "Updated two files but only attested one with structured provenance.",
                "modified_files": ["core/router.py", "tools/cinematic.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "core/router.py",
                    "added_line": "from tools.cinematic import generate_cinematic_zoom",
                    "context_before": "from tools.logging import get_logger",
                    "context_after": "ROUTES = {'/zoom': handle_zoom_request}",
                    "verification_command": "grep -n 'generate_cinematic_zoom' core/router.py",
                    "verification_result": "12:from tools.cinematic import generate_cinematic_zoom",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only core/router.py and tools/cinematic.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "Changed surfaces: core/router.py and tools/cinematic.py\n"
                "Observed: the router imports generate_cinematic_zoom and the helper implements the zoom effect.\n"
            )
            scenario.write_text(
                "Scenario: local zoom path check\n"
                "Command: grep -n 'generate_cinematic_zoom' core/router.py\n"
                "Observed: router import present\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_live_verdict(state, bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertEqual(1, bundle["diff_provenance"]["record_count"])
        self.assertFalse(bundle["diff_provenance"]["structured_record_sufficient"])
        self.assertFalse(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertIn("diff_provenance", bundle["semantically_insufficient_sections"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])

    def test_git_diff_rejects_multi_file_change_when_patch_covers_only_one_named_file(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_multi_file_partial_patch_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "Claimed two files but only included a patch and provenance for one.",
                "modified_files": ["core/router.py", "tools/cinematic.py"],
                "git_diff": (
                    "diff --git a/core/router.py b/core/router.py\n"
                    "--- a/core/router.py\n"
                    "+++ b/core/router.py\n"
                    "@@ -1,2 +1,3 @@\n"
                    " from tools.logging import get_logger\n"
                    "+from tools.cinematic import generate_cinematic_zoom\n"
                    " ROUTES = {'/zoom': handle_zoom_request}\n"
                ),
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "core/router.py",
                    "added_line": "from tools.cinematic import generate_cinematic_zoom",
                    "context_before": "from tools.logging import get_logger",
                    "context_after": "ROUTES = {'/zoom': handle_zoom_request}",
                    "verification_command": "grep -n 'generate_cinematic_zoom' core/router.py",
                    "verification_result": "2:from tools.cinematic import generate_cinematic_zoom",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating core/router.py and tools/cinematic.py.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text("Changed surfaces: core/router.py and tools/cinematic.py\n")
            scenario.write_text(
                "Scenario: local zoom path check\n"
                "Command: grep -n 'generate_cinematic_zoom' core/router.py\n"
                "Observed: router import present\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        verdict = build_live_verdict(state, bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual(["core/router.py"], bundle["diff_provenance"]["patch_paths"])
        self.assertFalse(bundle["diff_provenance"]["patch_covers_modified_files"])
        self.assertFalse(bundle["diff_provenance"]["semantically_sufficient"])
        self.assertIn("diff_provenance", bundle["semantically_insufficient_sections"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])

    def test_git_diff_accepts_multi_file_change_when_patch_covers_every_named_file(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_multi_file_full_patch_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"
            project_root = tmp / "recheck_project"
            (project_root / "core").mkdir(parents=True, exist_ok=True)
            (project_root / "tools").mkdir(parents=True, exist_ok=True)
            (project_root / "core" / "router.py").write_text(
                "from tools.logging import get_logger\n"
                "from tools.cinematic import generate_cinematic_zoom\n"
                "ROUTES = {'/zoom': handle_zoom_request}\n"
            )
            (project_root / "tools" / "cinematic.py").write_text(
                "def generate_cinematic_zoom() -> str:\n"
                "    return \"zoom\"\n"
            )

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "Updated two files and included patch coverage for both.",
                "modified_files": ["core/router.py", "tools/cinematic.py"],
                "git_diff": (
                    "diff --git a/core/router.py b/core/router.py\n"
                    "--- a/core/router.py\n"
                    "+++ b/core/router.py\n"
                    "@@ -1,2 +1,3 @@\n"
                    " from tools.logging import get_logger\n"
                    "+from tools.cinematic import generate_cinematic_zoom\n"
                    " ROUTES = {'/zoom': handle_zoom_request}\n"
                    "diff --git a/tools/cinematic.py b/tools/cinematic.py\n"
                    "--- a/tools/cinematic.py\n"
                    "+++ b/tools/cinematic.py\n"
                    "@@ -0,0 +1,2 @@\n"
                    "+def generate_cinematic_zoom() -> str:\n"
                    "+    return \"zoom\"\n"
                ),
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "core/router.py",
                    "added_line": "from tools.cinematic import generate_cinematic_zoom",
                    "context_before": "from tools.logging import get_logger",
                    "context_after": "ROUTES = {'/zoom': handle_zoom_request}",
                    "verification_command": "grep -n 'generate_cinematic_zoom' core/router.py",
                    "verification_result": "2:from tools.cinematic import generate_cinematic_zoom",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating core/router.py and tools/cinematic.py.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text("Changed surfaces: core/router.py and tools/cinematic.py\n")
            scenario.write_text(
                "Scenario: local zoom path check\n"
                "Command: grep -n 'generate_cinematic_zoom' core/router.py\n"
                "Observed: router import present\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            args.state_file = str(write_project_profile_for_recheck(final_result.parent, project_root=project_root))
            bundle = build_bundle(args)

        verdict = build_live_verdict(state, bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual(["core/router.py", "tools/cinematic.py"], bundle["diff_provenance"]["patch_paths"])
        self.assertTrue(bundle["diff_provenance"]["patch_covers_modified_files"])
        self.assertTrue(bundle["diff_provenance"]["semantically_sufficient"])
        self.assertTrue(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_structured_diff_provenance_accepts_multi_file_change_with_per_file_records(self) -> None:
        state = controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

        with tempfile.TemporaryDirectory(prefix="synrail_multi_file_per_record_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"
            project_root = tmp / "recheck_project"
            (project_root / "core").mkdir(parents=True, exist_ok=True)
            (project_root / "tools").mkdir(parents=True, exist_ok=True)
            (project_root / "core" / "router.py").write_text(
                "from tools.logging import get_logger\n"
                "from tools.cinematic import generate_cinematic_zoom\n"
                "ROUTES = {'/zoom': handle_zoom_request}\n"
            )
            (project_root / "tools" / "cinematic.py").write_text(
                "def generate_cinematic_zoom() -> str:\n"
                "    return \"zoom\"\n"
            )

            final_result.write_text(json.dumps({
                "request_id": state["run_id"],
                "status": "PROVEN",
                "change_disposition": "modified",
                "summary": "Updated two files and attested both with per-file structured provenance.",
                "modified_files": ["core/router.py", "tools/cinematic.py"],
                "git_diff": "",
                "diff_provenance_records": [
                    {
                        "method": "direct_file_observation",
                        "changed_file": "core/router.py",
                        "added_line": "from tools.cinematic import generate_cinematic_zoom",
                        "context_before": "from tools.logging import get_logger",
                        "context_after": "ROUTES = {'/zoom': handle_zoom_request}",
                        "verification_command": "grep -n 'generate_cinematic_zoom' core/router.py",
                        "verification_result": "2:from tools.cinematic import generate_cinematic_zoom",
                    },
                    {
                        "method": "direct_file_observation",
                        "changed_file": "tools/cinematic.py",
                        "added_line": "def generate_cinematic_zoom() -> str:",
                        "context_after": "    return \"zoom\"",
                        "verification_command": "grep -n 'generate_cinematic_zoom' tools/cinematic.py",
                        "verification_result": "1:def generate_cinematic_zoom() -> str:",
                    },
                ],
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only core/router.py and tools/cinematic.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "Changed surfaces: core/router.py and tools/cinematic.py\n"
                "Observed: the router imports generate_cinematic_zoom and the helper defines it directly.\n"
            )
            scenario.write_text(
                "Scenario: local zoom path check\n"
                "Command: grep -n 'generate_cinematic_zoom' core/router.py\n"
                "Observed: router import present\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            args.state_file = str(write_project_profile_for_recheck(final_result.parent, project_root=project_root))
            bundle = build_bundle(args)

        verdict = build_live_verdict(state, bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertEqual(2, bundle["diff_provenance"]["record_count"])
        self.assertTrue(bundle["diff_provenance"]["structured_record_sufficient"])
        self.assertTrue(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["matched"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertEqual(["presentation_alignment"], bundle["semantically_insufficient_sections"])
        self.assertEqual(
            "keep the newly added surface visually plain and close to the requested text-only intent; remove extra emphasis styling unless the task asked for it",
            bundle["semantic_next_safe_step"],
        )
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])


class TestDedicatedProofAttackPack(unittest.TestCase):
    """Named P2 bundle-level attack pack for hostile proof attempts."""

    def _state(self) -> dict:
        return controlled_state(load_json(FIXTURES_ROOT / "semantic_proof_hardening_run_001" / "state_valid.json"))

    def _base_final_result(self, state: dict) -> dict:
        return {
            "request_id": state["run_id"],
            "status": "PROVEN",
            "change_disposition": "modified",
            "summary": "Added a logging import to src/app.py with direct structured provenance.",
            "modified_files": ["src/app.py"],
            "git_diff": "",
            "diff_provenance": {
                "method": "direct_file_observation",
                "changed_file": "src/app.py",
                "added_line": "import logging",
                "context_after": "def run() -> None:",
                "verification_command": "grep -n 'import logging' src/app.py",
                "verification_result": "1:import logging",
            },
            "artifact_identity": {
                "baseline_identity": "trusted_clean",
                "execution_surface_identity": "clean-clone",
                "prompt_identity": "prompt-001",
                "task_identity": "task-001",
            },
            "cleanup_status": {
                "success": True,
                "summary": "Workspace clean after updating only src/app.py with no unintended changes.",
            },
        }

    def _valid_readback_text(self) -> str:
        return (
            "Changed surface: src/app.py\n"
            "Observed: src/app.py now begins with the literal line import logging above def run().\n"
        )

    def _valid_scenario_text(self) -> str:
        return (
            "Scenario: verify logging import\n"
            "Command: grep -n 'import logging' src/app.py\n"
            "Observed: 1:import logging\n"
            "Status: PASSED\n"
        )

    def _build_bundle_with_supporting_artifacts(
        self,
        final_payload: dict,
        *,
        readback_text: str | None = None,
        scenario_text: str | None = None,
        project_files: dict[str, str] | None = None,
    ) -> dict:
        with tempfile.TemporaryDirectory(prefix="synrail_dedicated_attack_pack_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            final_result.write_text(json.dumps(final_payload, indent=2, ensure_ascii=True) + "\n")

            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"
            project_root = tmp / "recheck_project"

            if project_files:
                for relative_path, content in project_files.items():
                    target = project_root / relative_path
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_text(content)

            args = bundle_args(final_result=final_result)
            if project_files:
                args.state_file = str(write_project_profile_for_recheck(final_result.parent, project_root=project_root))

            if readback_text is None:
                args.readback = str(tmp / "missing_readback.txt")
            else:
                readback.write_text(readback_text)
                args.readback = str(readback)

            if scenario_text is None:
                args.scenario_proof = str(tmp / "missing_scenario.txt")
            else:
                scenario.write_text(scenario_text)
                args.scenario_proof = str(scenario)

            return build_bundle(args)

    def test_bundle_rejects_structured_provenance_without_verification_fields(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        final_payload["diff_provenance"].pop("verification_command")
        final_payload["diff_provenance"]["verification_result"] = ""

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=self._valid_readback_text(),
            scenario_text=self._valid_scenario_text(),
        )
        verdict = build_live_verdict(state, bundle)

        self.assertEqual("PARTIAL", bundle["status"])
        self.assertEqual("NOT_EVALUATED", bundle["semantic_status"])
        self.assertFalse(bundle["diff_provenance"]["verification_command_present"])
        self.assertFalse(bundle["diff_provenance"]["structured_record_sufficient"])
        self.assertFalse(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertIn("diff_provenance", bundle["missing_sections"])
        self.assertEqual("MISSING_PROOF_SECTIONS", verdict["blocking_reason"])

    def test_bundle_rejects_structured_provenance_without_changed_file(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        final_payload["diff_provenance"]["changed_file"] = ""

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=self._valid_readback_text(),
            scenario_text=self._valid_scenario_text(),
        )
        verdict = build_live_verdict(state, bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertFalse(bundle["diff_provenance"]["structured_record_sufficient"])
        self.assertFalse(bundle["diff_provenance"]["semantically_sufficient"])
        self.assertIn("diff_provenance", bundle["semantically_insufficient_sections"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])

    def test_bundle_rejects_fabricated_scenario_output_without_runtime_evidence(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        final_payload["diff_provenance"]["verification_command"] = ""
        final_payload["diff_provenance"]["verification_result"] = ""
        scenario_text = (
            "Scenario: verify logging import\n"
            "Command: grep -n 'import logging' src/app.py\n"
            "Observed: grep confirms logging import in src/app.py\n"
            "Status: PASSED\n"
        )

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=self._valid_readback_text(),
            scenario_text=scenario_text,
        )
        verdict = build_live_verdict(state, bundle)

        self.assertEqual("PARTIAL", bundle["status"])
        self.assertEqual("NOT_EVALUATED", bundle["semantic_status"])
        self.assertFalse(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertFalse(bundle["scenario_proof"]["content_semantically_sufficient"])
        self.assertFalse(bundle["scenario_proof"]["waived_by_runtime_corroboration"])
        self.assertIn("diff_provenance", bundle["missing_sections"])
        self.assertEqual("MISSING_PROOF_SECTIONS", verdict["blocking_reason"])

    def test_bundle_rejects_already_satisfied_without_real_observation(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        final_payload["status"] = "ALREADY_SATISFIED"
        final_payload["change_disposition"] = "already_satisfied"
        final_payload["summary"] = "Claimed the requested import already existed before edits."
        final_payload["modified_files"] = []
        final_payload["diff_provenance"] = {
            "method": "direct_file_observation",
            "changed_file": "src/app.py",
            "verification_command": "grep -n 'import logging' src/app.py",
            "verification_result": "1:import logging",
            "provenance_note": "Claimed no-op observation without naming the observed line.",
        }

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=self._valid_readback_text(),
            scenario_text=self._valid_scenario_text(),
        )
        verdict = build_live_verdict(state, bundle)

        self.assertEqual("STRUCTURALLY_COMPLETE", bundle["status"])
        self.assertEqual("INSUFFICIENT", bundle["semantic_status"])
        self.assertFalse(bundle["diff_provenance"]["structured_record_sufficient"])
        self.assertFalse(bundle["diff_provenance"]["semantically_sufficient"])
        self.assertIn("diff_provenance", bundle["semantically_insufficient_sections"])
        self.assertEqual("SEMANTIC_PROOF_INSUFFICIENT", verdict["blocking_reason"])

    def test_recheck_rejects_cat_outside_project_operand(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        with tempfile.TemporaryDirectory(prefix="synrail_recheck_cat_outside_") as tmpdir:
            outside = Path(tmpdir) / "outside.txt"
            outside.write_text("outside-secret\n")
            final_payload["diff_provenance"]["verification_command"] = f"cat {outside}"
            final_payload["diff_provenance"]["verification_result"] = "outside-secret"
            bundle = self._build_bundle_with_supporting_artifacts(
                final_payload,
                readback_text=self._valid_readback_text(),
                scenario_text=self._valid_scenario_text(),
                project_files={"src/app.py": "import logging\ndef run() -> None:\n    pass\n"},
            )
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["required"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["executed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("command_path_out_of_scope", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("VERIFICATION_RECHECK_NOT_EXECUTED", verdict["blocking_reason"])

    def test_recheck_rejects_grep_outside_project_operand(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        with tempfile.TemporaryDirectory(prefix="synrail_recheck_grep_outside_") as tmpdir:
            outside = Path(tmpdir) / "outside.txt"
            outside.write_text("import logging\n")
            final_payload["diff_provenance"]["verification_command"] = f"grep -n 'import logging' {outside}"
            final_payload["diff_provenance"]["verification_result"] = "1:import logging"
            bundle = self._build_bundle_with_supporting_artifacts(
                final_payload,
                readback_text=self._valid_readback_text(),
                scenario_text=self._valid_scenario_text(),
                project_files={"src/app.py": "import logging\ndef run() -> None:\n    pass\n"},
            )
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["required"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["executed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("command_path_out_of_scope", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("VERIFICATION_RECHECK_NOT_EXECUTED", verdict["blocking_reason"])

    def test_recheck_rejects_mixed_safe_and_unsafe_operands(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        with tempfile.TemporaryDirectory(prefix="synrail_recheck_mixed_operands_") as tmpdir:
            outside = Path(tmpdir) / "outside.txt"
            outside.write_text("import logging\n")
            final_payload["diff_provenance"]["verification_command"] = (
                f"grep -n 'import logging' src/app.py {outside}"
            )
            final_payload["diff_provenance"]["verification_result"] = "1:import logging"
            bundle = self._build_bundle_with_supporting_artifacts(
                final_payload,
                readback_text=self._valid_readback_text(),
                scenario_text=self._valid_scenario_text(),
                project_files={"src/app.py": "import logging\ndef run() -> None:\n    pass\n"},
            )
            verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["executed"])
        self.assertEqual("command_path_out_of_scope", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("VERIFICATION_RECHECK_NOT_EXECUTED", verdict["blocking_reason"])

    def test_recheck_rejects_changed_file_path_traversal_before_reading(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        final_payload["modified_files"] = ["../../etc/passwd"]
        final_payload["diff_provenance"]["changed_file"] = "../../etc/passwd"
        final_payload["diff_provenance"]["verification_command"] = "cat ../../etc/passwd"
        final_payload["diff_provenance"]["verification_result"] = "root:x:0:0"

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=self._valid_readback_text(),
            scenario_text=self._valid_scenario_text(),
            project_files={"src/app.py": "import logging\ndef run() -> None:\n    pass\n"},
        )
        verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["required"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["executed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("changed_file_out_of_scope", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("VERIFICATION_RECHECK_NOT_EXECUTED", verdict["blocking_reason"])

    def test_recheck_rejects_git_global_config_rce_shape_without_executing(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        with tempfile.TemporaryDirectory(prefix="synrail_recheck_git_rce_") as tmpdir:
            marker = Path(tmpdir) / "pwned"
            final_payload["diff_provenance"]["verification_command"] = (
                f"git -c core.sshCommand='sh -c \"touch {marker}\"' ls-remote ."
            )
            final_payload["diff_provenance"]["verification_result"] = "anything"
            bundle = self._build_bundle_with_supporting_artifacts(
                final_payload,
                readback_text=self._valid_readback_text(),
                scenario_text=self._valid_scenario_text(),
                project_files={"src/app.py": "import logging\ndef run() -> None:\n    pass\n"},
            )
            verdict = build_live_verdict(state, bundle)
            self.assertFalse(marker.exists())

        self.assertTrue(bundle["verification_recheck"]["required"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["executed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("command_shape_unsupported", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("VERIFICATION_RECHECK_NOT_EXECUTED", verdict["blocking_reason"])

    def test_recheck_rejects_git_ext_diff_option_without_executing(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        final_payload["diff_provenance"]["verification_command"] = "git diff --ext-diff -- src/app.py"
        final_payload["diff_provenance"]["verification_result"] = "diff --git a/src/app.py b/src/app.py"

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=self._valid_readback_text(),
            scenario_text=self._valid_scenario_text(),
            project_files={"src/app.py": "import logging\ndef run() -> None:\n    pass\n"},
        )
        verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["required"])
        self.assertTrue(bundle["verification_recheck"]["command_allowed"])
        self.assertFalse(bundle["verification_recheck"]["executed"])
        self.assertFalse(bundle["verification_recheck"]["matched"])
        self.assertEqual("command_shape_unsupported", bundle["verification_recheck"]["skip_reason"])
        self.assertEqual("VERIFICATION_RECHECK_NOT_EXECUTED", verdict["blocking_reason"])

    def test_recheck_accepts_cat_changed_file_inside_project(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        final_payload["diff_provenance"]["verification_command"] = "cat src/app.py"
        final_payload["diff_provenance"]["verification_result"] = "import logging\ndef run() -> None:\n    pass"
        readback_text = self._valid_readback_text()
        scenario_text = self._valid_scenario_text()
        project_files = {
            "src/app.py": "import logging\ndef run() -> None:\n    pass\n",
        }

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=readback_text,
            scenario_text=scenario_text,
            project_files=project_files,
        )
        verdict = build_live_verdict(state, bundle)

        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["matched"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_recheck_accepts_grep_changed_file_inside_project(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        readback_text = self._valid_readback_text()
        scenario_text = self._valid_scenario_text()
        project_files = {
            "src/app.py": "import logging\ndef run() -> None:\n    pass\n",
        }

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=readback_text,
            scenario_text=scenario_text,
            project_files=project_files,
        )
        verdict = build_live_verdict(state, bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertTrue(bundle["diff_provenance"]["structured_record_sufficient"])
        self.assertTrue(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["matched"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])

    def test_bundle_accepts_dedicated_attack_pack_positive_control(self) -> None:
        state = self._state()
        final_payload = self._base_final_result(state)
        readback_text = self._valid_readback_text()
        scenario_text = self._valid_scenario_text()
        project_files = {
            "src/app.py": "import logging\ndef run() -> None:\n    pass\n",
        }

        bundle = self._build_bundle_with_supporting_artifacts(
            final_payload,
            readback_text=readback_text,
            scenario_text=scenario_text,
            project_files=project_files,
        )
        verdict = build_live_verdict(state, bundle)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertEqual("SUFFICIENT", bundle["semantic_status"])
        self.assertTrue(bundle["diff_provenance"]["structured_record_sufficient"])
        self.assertTrue(bundle["verification_corroboration"]["runtime_verification_sufficient"])
        self.assertTrue(bundle["verification_recheck"]["executed"])
        self.assertTrue(bundle["verification_recheck"]["matched"])
        self.assertEqual("ACCEPTED", verdict["closure_status"])


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

    def test_readback_rejects_padded_parroting_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: core/router.py\n"
            "Observed: core router module contains cinematic zoom trigger handler animation effects ancillary validation context review metadata operator trace stability notes.\n",
            ["core/router.py"],
            task_identity="implement the cinematic zoom trigger handler for the core router module with animation effects",
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

    def test_readback_rejects_verified_functioning_properly_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Readback: src/app.py\n"
            "Verified: functioning properly.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_confirmed_operational_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Confirmed: operational.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_and_correct_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present and correct in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_available_and_correct_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: available and correct in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_successfully_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified successfully in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_looks_correct_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: looks correct in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_ready_for_use_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: ready for use in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_working_as_designed_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: working as designed in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_and_valid_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present and valid in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_and_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present and available in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_exists_as_expected_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: exists as expected in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_successfully_updated_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: successfully updated in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_successfully_applied_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: successfully applied in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_appears_correct_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: appears correct in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_appears_to_be_correct_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: appears to be correct in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_looks_right_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: looks right in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_is_available_now_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: is available now in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_is_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: is ready in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_has_been_verified_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: has been verified in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_confirmed_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: confirmed ready in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_confirmed_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: confirmed available in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_ready_now_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: ready now in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_and_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified and ready in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_now_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: now available in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_now_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: now ready in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verification_passed_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verification passed in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_available_to_use_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: available to use in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_looks_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: looks available in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_ready_for_verification_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: ready for verification in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_as_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified as ready in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_ready_and_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: ready and available in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_is_verified_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: is verified in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_ready_to_use_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: ready to use in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_available_and_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: available and ready in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_and_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified and available in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_looks_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: looks ready in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_ready_to_proceed_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: ready to proceed in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_safe_to_proceed_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: safe to proceed in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_good_to_go_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: good to go in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_appears_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: appears ready in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_in_place_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified in place in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_on_disk_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified on disk in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_on_disk_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present on disk in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_on_the_filesystem_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified on the filesystem in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_in_file_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified in file in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_in_file_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present in file in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_in_the_file_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified in the file in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_in_the_file_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present in the file in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_in_the_source_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified in the source in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_in_the_source_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present in the source in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_in_code_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified in code in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_in_code_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present in code in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_in_the_code_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified in the code in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_in_the_code_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present in the code in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_verified_in_source_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: verified in source in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_present_in_source_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: present in source in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_processes_correctly_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: it processes correctly in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_numeric_thin_path_self_description_without_literal_evidence(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: src/app.py contains the logging import at line 2.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_rejects_numeric_thin_line_self_description_without_literal_evidence(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertFalse(readback_is_semantically_sufficient(
            "Changed surface: src/app.py\n"
            "Observed: line 2 contains the logging import in src/app.py.",
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_accepts_concrete_observation(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: src/app.py\n'
            'Observed: line 2 now reads "import logging" immediately after the existing os import.',
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_accepts_numeric_contains_claim_with_literal_evidence(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: src/app.py\n'
            'Observed: src/app.py line 2 contains "import logging".',
            self.FILES, task_identity=self.TASK,
        ))

    def test_readback_accepts_already_satisfied_contains_line_reference(self) -> None:
        from synrail_bundle_v0 import readback_is_semantically_sufficient
        self.assertTrue(readback_is_semantically_sufficient(
            'Changed surface: warroom/templates/index.html\n'
            'Observed: the template already contains the Local signals only subtitle directly under the Watchlist heading at line 24.',
            ["warroom/templates/index.html"],
            task_identity="Add Local signals only subtitle under Watchlist heading and do not change anything else",
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

    def test_broad_observation_guard_would_fire_for_unmeasured_task_class(self) -> None:
        from synrail_bundle_v0 import broad_observation_guard_would_fire, strict_observation_guard_enabled
        self.assertFalse(strict_observation_guard_enabled("feature_work"))
        self.assertTrue(broad_observation_guard_would_fire(
            "feature_work",
            "Observed: added logging import to src/app.py.",
        ))

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

    def test_bundle_records_shadow_observation_guard_results_without_blocking_unmeasured_task_class(self) -> None:
        with tempfile.TemporaryDirectory(prefix="synrail_shadow_observation_guard_") as tmpdir:
            tmp = Path(tmpdir)
            final_result = tmp / "final_result.json"
            readback = tmp / "readback.txt"
            scenario = tmp / "scenario.txt"

            final_result.write_text(json.dumps({
                "request_id": "RUN_SHADOW_GUARD_001",
                "status": "PROVEN",
                "modified_files": ["tools/reference/synrail_bundle_v0.py"],
                "git_diff": "",
                "diff_provenance": {
                    "method": "direct_file_observation",
                    "changed_file": "tools/reference/synrail_bundle_v0.py",
                    "added_line": "VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                    "context_before": "GENERIC_EXECUTION_STATUSES = {\"SUCCESS\", \"COMPLETED\", \"DONE\", \"OK\", \"PASSED\"}",
                    "context_after": "VERIFICATION_RECHECK_TIMEOUT_SECONDS = 10",
                    "verification_command": "grep -n 'VERIFICATION_RECHECK_ALLOWED_BINARIES' tools/reference/synrail_bundle_v0.py",
                    "verification_result": "39:VERIFICATION_RECHECK_ALLOWED_BINARIES = {\"grep\", \"cat\", \"head\", \"tail\", \"git\"}",
                },
                "artifact_identity": {
                    "baseline_identity": "trusted_clean",
                    "execution_surface_identity": "clean-clone",
                    "prompt_identity": "prompt-001",
                    "task_identity": "task-001",
                },
                "cleanup_status": {
                    "success": True,
                    "summary": "Workspace clean after updating only tools/reference/synrail_bundle_v0.py with no unintended changes.",
                },
            }, indent=2, ensure_ascii=True) + "\n")
            readback.write_text(
                "Changed surface: tools/reference/synrail_bundle_v0.py\n"
                "Observed: added VERIFICATION_RECHECK_ALLOWED_BINARIES to tools/reference/synrail_bundle_v0.py.\n"
            )
            scenario.write_text(
                "Scenario: verify verification recheck allowlist\n"
                "Command: grep -n 'VERIFICATION_RECHECK_ALLOWED_BINARIES' tools/reference/synrail_bundle_v0.py\n"
                "Observed: added VERIFICATION_RECHECK_ALLOWED_BINARIES to tools/reference/synrail_bundle_v0.py.\n"
                "Status: PASSED\n"
            )

            args = bundle_args(final_result=final_result)
            args.task_class = "feature_work"
            args.readback = str(readback)
            args.scenario_proof = str(scenario)
            bundle = build_bundle(args)

        self.assertEqual("COMPLETE", bundle["status"])
        self.assertTrue(bundle["readback"]["semantically_sufficient"])
        self.assertTrue(bundle["scenario_proof"]["semantically_sufficient"])
        self.assertEqual(
            {"would_block": True, "lines_flagged": 2},
            bundle["shadow_observation_guard_results"],
        )

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

    def test_scenario_rejects_verified_functioning_properly_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: functioning properly.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_confirmed_operational_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: operational.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_appears_correct_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: appears correct in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_appears_to_be_correct_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: appears to be correct in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_looks_right_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: looks right in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_is_available_now_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: is available now in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_is_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: is ready in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_ready_now_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: ready now in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_and_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified and ready in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_now_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: now available in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_now_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: now ready in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verification_passed_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verification passed in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_available_to_use_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: available to use in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_looks_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: looks available in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_ready_for_verification_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: ready for verification in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_as_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified as ready in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_ready_and_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: ready and available in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_is_verified_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: is verified in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_ready_to_use_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: ready to use in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_available_and_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: available and ready in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_and_available_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified and available in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_looks_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: looks ready in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_ready_to_proceed_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: ready to proceed in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_safe_to_proceed_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: safe to proceed in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_good_to_go_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: good to go in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_appears_ready_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: appears ready in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_in_place_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified in place in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_on_disk_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified on disk in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_present_on_disk_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: present on disk in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_on_the_filesystem_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified on the filesystem in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_in_file_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified in file in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_present_in_file_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: present in file in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_in_the_file_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified in the file in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_present_in_the_file_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: present in the file in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_in_the_source_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified in the source in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_present_in_the_source_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: present in the source in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_in_code_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified in code in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_present_in_code_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: present in code in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_in_the_code_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified in the code in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_present_in_the_code_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: present in the code in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_verified_in_source_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: verified in source in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_present_in_source_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: present in source in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_has_been_verified_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: has been verified in src/app.py.\n"
            "Status: PASSED",
            task_identity=self.TASK,
        ))

    def test_scenario_rejects_processes_correctly_synonym_bypass(self) -> None:
        from synrail_bundle_v0 import scenario_is_semantically_sufficient
        self.assertFalse(scenario_is_semantically_sufficient(
            "Scenario: verify import\n"
            "Command: grep -n logging src/app.py\n"
            "Observed: it processes correctly in src/app.py.\n"
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

        verdict = build_live_verdict(state, bundle)

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

        verdict = build_live_verdict(state, bundle)

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


class VerificationRecheckEnvTests(unittest.TestCase):
    def test_git_diff_recheck_env_does_not_kill_git_diff(self) -> None:
        """Regression: GIT_EXTERNAL_DIFF="" made `git diff` die under the recheck env."""
        from synrail_bundle_v0 import _verification_recheck_env

        env = _verification_recheck_env("git")
        self.assertIsNotNone(env)
        # The external diff driver must never be handed an empty command; that
        # makes git exec "" and abort with "external diff died".
        self.assertNotEqual("", env.get("GIT_EXTERNAL_DIFF", "unset"))
        self.assertNotIn("GIT_EXTERNAL_DIFF", env)

        with tempfile.TemporaryDirectory(prefix="synrail_recheck_git_diff_env_") as tmpdir:
            tmp = Path(tmpdir)
            subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
            subprocess.run(["git", "config", "user.email", "t@example.com"], cwd=tmp, check=True)
            subprocess.run(["git", "config", "user.name", "synrail-test"], cwd=tmp, check=True)
            tracked = tmp / "gone.py"
            tracked.write_text("first = 1\nsecond = 2\n")
            subprocess.run(["git", "add", "gone.py"], cwd=tmp, check=True)
            subprocess.run(["git", "commit", "-qm", "add gone.py"], cwd=tmp, check=True)
            tracked.unlink()

            result = subprocess.run(
                ["git", "diff", "--", "gone.py"],
                cwd=tmp,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(0, result.returncode, msg=result.stderr)
            self.assertNotIn("external diff died", result.stderr)
            self.assertIn("diff --git", result.stdout)
            self.assertIn("deleted file mode", result.stdout)


if __name__ == "__main__":
    unittest.main()
