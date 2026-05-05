#!/usr/bin/env python3
"""Minimal closure engine for Synrail."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json

try:
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


CLOSURE_PATH_SCOPES = {
    "state_file": ARTIFACT_SCOPE,
    "bundle_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
    "certificate_output": ARTIFACT_SCOPE,
    "acceptance_validation_file": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_closure_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=CLOSURE_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


MISSING_SECTION_STEPS = {
    "readback": "collect readback from changed sections on the attested surface",
    "scenario_proof": "rerun the scenario check against the attested target surface",
    "artifact_identity": "restore baseline, execution surface, prompt, and task identity values",
    "cleanup_status": "record cleanup status for the execution surface",
    "final_result": "recover the final result artifact and rerun bundle assembly",
    "modified_files": "recover modified-files evidence from the final result artifact",
    "diff_provenance": "recover diff or provenance evidence from the final result artifact",
}

SEMANTIC_SECTION_STEPS = {
    "modified_files": "record the actual changed files in the final result artifact",
    "diff_provenance": "prove the patch on the changed files with a patch-shaped git_diff or a structured diff_provenance record",
    "final_result_status": "state a trust-bearing final_result.status for this run",
    "readback": "record substantive readback from the changed sections on the attested surface",
    "scenario_proof": "record an explicit scenario-proof result for the attested target surface",
    "artifact_identity": "restore baseline, execution surface, prompt, and task identity values for this run",
    "cleanup_status": "record a successful cleanup status for the execution surface",
}






def first_missing_step(missing_sections: list[str]) -> str:
    for section in missing_sections:
        if section in MISSING_SECTION_STEPS:
            return MISSING_SECTION_STEPS[section]
    return "complete the missing proof sections"


def first_semantic_step(semantically_insufficient_sections: list[str]) -> str:
    for section in semantically_insufficient_sections:
        if section in SEMANTIC_SECTION_STEPS:
            return SEMANTIC_SECTION_STEPS[section]
    return "strengthen the semantic proof evidence before trusting closure"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def evaluate_closure_freshness_binding(binding: object, *, live_recheck: bool) -> dict:
    artifacts = []
    all_required_present = True
    all_hashes_match = True
    if not isinstance(binding, dict):
        return {
            "present": False,
            "schema_version": "",
            "bound_at_utc": "",
            "all_required_present": False,
            "all_hashes_match": False,
            "artifacts": [],
        }
    for item in binding.get("artifacts", []):
        if not isinstance(item, dict):
            continue
        artifact_id = (item.get("artifact_id", "") or "").strip()
        path_text = (item.get("path", "") or "").strip()
        required = bool(item.get("required", False))
        expected_sha = (item.get("sha256", "") or "").strip()
        bound_present = bool(item.get("present", False))
        current_sha = ""
        present = bound_present
        hashes_match = bool(bound_present and expected_sha)
        if live_recheck and path_text:
            candidate = Path(path_text)
            present = candidate.exists() and candidate.is_file()
            if present:
                current_sha = file_sha256(candidate)
                hashes_match = bool(expected_sha and current_sha == expected_sha)
            else:
                hashes_match = False
        if required and not present:
            all_required_present = False
        if present and expected_sha and not hashes_match:
            all_hashes_match = False
        artifacts.append({
            "artifact_id": artifact_id,
            "path": path_text,
            "required": required,
            "present": present,
            "expected_sha256": expected_sha,
            "current_sha256": current_sha,
            "hashes_match": hashes_match,
            "live_recheck": live_recheck,
        })
    return {
        "present": True,
        "schema_version": (binding.get("schema_version", "") or "").strip(),
        "bound_at_utc": (binding.get("bound_at_utc", "") or "").strip(),
        "all_required_present": all_required_present,
        "all_hashes_match": all_hashes_match,
        "artifacts": artifacts,
        "live_recheck": live_recheck,
    }


def build_closure_certificate(*, state: dict, bundle: dict, verdict: dict, criteria_validation: dict | None = None) -> dict:
    criteria_validation = criteria_validation or {}
    freshness = evaluate_closure_freshness_binding(
        bundle.get("closure_freshness_binding", {}),
        live_recheck=bool(state.get("_state_file") and bundle.get("_bundle_file")),
    )
    artifact_identity = dict(bundle.get("artifact_identity", {})) if isinstance(bundle.get("artifact_identity", {}), dict) else {}
    final_result = dict(bundle.get("final_result", {})) if isinstance(bundle.get("final_result", {}), dict) else {}
    return {
        "schema_version": "closure_certificate_v0",
        "run_id": state.get("run_id", bundle.get("run_id", "")),
        "task_class": state.get("task_class", bundle.get("task_class", "")),
        "task_identity": artifact_identity.get("task_identity", ""),
        "prompt_identity": artifact_identity.get("prompt_identity", ""),
        "issued_at_utc": now_iso(),
        "start_timestamp_utc": state.get("start_timestamp_utc", ""),
        "check_count": int(state.get("check_count", 0) or 0),
        "closure_timestamp_utc": state.get("closure_timestamp_utc", "") or now_iso(),
        "closure_status": verdict.get("closure_status", ""),
        "repair_attempt_count": int(((bundle.get("repair_packet", {}) or {}).get("repair_attempt_count", 0) or 0)),
        "repair_max_attempts": int(((bundle.get("repair_packet", {}) or {}).get("repair_max_attempts", 0) or 0)),
        "blocking_reason": verdict.get("blocking_reason", ""),
        "bundle_sha256": file_sha256(Path(bundle["_bundle_file"])) if bundle.get("_bundle_file") else "",
        "state_sha256": file_sha256(Path(state["_state_file"])) if state.get("_state_file") else "",
        "final_result_sha256": next(
            (
                artifact.get("expected_sha256", "")
                for artifact in freshness.get("artifacts", [])
                if artifact.get("artifact_id") == "final_result"
            ),
            "",
        ),
        "final_result_request_id": final_result.get("request_id", ""),
        "acceptance_criteria_status": criteria_validation.get("status", ""),
        "verification_recheck": dict(bundle.get("verification_recheck", {})),
        "closure_freshness_binding": freshness,
    }



def persist_closure_certificate(
    output_path: Path,
    *,
    state: dict,
    state_path: Path | None,
    bundle: dict,
    bundle_path: Path | None,
    verdict: dict,
    criteria_validation: dict | None = None,
) -> dict:
    certificate_state = dict(state)
    certificate_bundle = dict(bundle)
    if state_path is not None:
        certificate_state["_state_file"] = str(state_path)
    if bundle_path is not None:
        certificate_bundle["_bundle_file"] = str(bundle_path)
    certificate = build_closure_certificate(
        state=certificate_state,
        bundle=certificate_bundle,
        verdict=verdict,
        criteria_validation=criteria_validation,
    )
    save_json(output_path, certificate)
    return certificate


def build_verdict(state: dict, bundle: dict, criteria_validation: dict | None = None) -> dict:
    missing_sections = list(bundle.get("missing_sections", []))
    semantically_insufficient_sections = list(bundle.get("semantically_insufficient_sections", []))
    state_run_id = state.get("run_id", "")
    bundle_run_id = bundle.get("run_id", "")
    artifact_request_id = (bundle.get("final_result", {}).get("request_id", "") or "").strip()
    run_id = state_run_id or bundle_run_id
    task_class = state.get("task_class", bundle.get("task_class", ""))
    criteria_validation = criteria_validation or {}

    # Cross-artifact identity binding: if state, bundle, or final-result
    # request_id disagree, the proof was assembled from mixed run surfaces.
    run_id_mismatch = bool(
        (state_run_id and artifact_request_id and state_run_id != artifact_request_id)
        or (state_run_id and bundle_run_id and state_run_id != bundle_run_id)
    )

    verdict = {
        "schema_version": "closure_verdict_v0",
        "run_id": run_id,
        "task_class": task_class,
        "closure_status": "CLAIMED_NOT_ACCEPTED",
        "blocking_reason": "",
        "next_allowed_transition": "",
        "narrow_next_safe_step": "",
        "missing_sections": missing_sections,
        "semantically_insufficient_sections": semantically_insufficient_sections,
        "acceptance_criteria_revision_id": criteria_validation.get("criteria_revision_id", ""),
        "acceptance_criteria_status": criteria_validation.get("status", ""),
        "acceptance_criteria_reason": criteria_validation.get("reason", ""),
        "closure_warnings": [],
    }

    if run_id_mismatch:
        verdict["blocking_reason"] = "RUN_ID_MISMATCH"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "rebuild the proof bundle for the current run"
        return verdict

    criteria_status = criteria_validation.get("status", "")
    if criteria_status == "STALE":
        verdict["blocking_reason"] = "ACCEPTANCE_CRITERIA_STALE"
        verdict["next_allowed_transition"] = "ACCEPTANCE_CRITERIA_REFRESH"
        verdict["narrow_next_safe_step"] = "refresh the acceptance criteria for the current project state"
        return verdict
    if criteria_status == "INVALID":
        verdict["blocking_reason"] = "ACCEPTANCE_CRITERIA_INVALID"
        verdict["next_allowed_transition"] = "ACCEPTANCE_CRITERIA_REPAIR"
        verdict["narrow_next_safe_step"] = "repair or rebuild the acceptance criteria before trusting closure"
        return verdict

    if state["target_surface"]["status"] != "ATTESTED":
        verdict["blocking_reason"] = "TARGET_SURFACE_NOT_ATTESTED"
        verdict["next_allowed_transition"] = "TARGET_SURFACE_ATTESTED"
        verdict["narrow_next_safe_step"] = "attest target surface"
        return verdict

    if state["doctor"]["status"] != "PASS":
        verdict["blocking_reason"] = "DOCTOR_NOT_GREEN"
        verdict["next_allowed_transition"] = "DOCTOR_READINESS"
        verdict["narrow_next_safe_step"] = "run doctor and clear blocking failure classes"
        return verdict

    doctor_overrides = list(state["doctor"].get("override_gates", []))
    if doctor_overrides:
        verdict["closure_warnings"].append(
            f"doctor_override_present: {', '.join(doctor_overrides)}"
        )

    if not state["integrity"].get("bootstrap_provenance_ok", False):
        verdict["blocking_reason"] = "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"
        verdict["next_allowed_transition"] = "CONTROLLED_START"
        verdict["narrow_next_safe_step"] = "start the run in controlled mode before trusting any proof or acceptance"
        return verdict

    if not state["integrity"]["exact_task_identity_ok"]:
        verdict["blocking_reason"] = "EXACT_TASK_IDENTITY_NOT_CONFIRMED"
        verdict["next_allowed_transition"] = "INTEGRITY_RECONFIRMATION"
        verdict["narrow_next_safe_step"] = "reconfirm exact task, prompt, and run-class identity"
        return verdict

    if state["execution"]["status"] != "COMPLETED":
        verdict["blocking_reason"] = "EXECUTION_NOT_COMPLETED"
        verdict["next_allowed_transition"] = "EXECUTION_COMPLETION"
        verdict["narrow_next_safe_step"] = "complete execution and capture the final result artifact"
        return verdict

    if bundle.get("status") == "INVALID":
        verdict["blocking_reason"] = "INVALID_PROOF_BUNDLE"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "repair the final result artifact and rebuild the proof bundle"
        return verdict

    if bundle.get("status") == "STRUCTURALLY_COMPLETE":
        verdict["blocking_reason"] = "SEMANTIC_PROOF_INSUFFICIENT"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_STRENGTHENING"
        verdict["narrow_next_safe_step"] = bundle.get("semantic_next_safe_step", "") or first_semantic_step(semantically_insufficient_sections)
        return verdict

    if bundle.get("status") != "COMPLETE":
        verdict["blocking_reason"] = "MISSING_PROOF_SECTIONS"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_COMPLETION"
        verdict["narrow_next_safe_step"] = first_missing_step(missing_sections)
        return verdict

    recheck = bundle.get("verification_recheck", {})
    if recheck.get("required") and not recheck.get("executed"):
        verdict["closure_status"] = "REJECTED"
        verdict["blocking_reason"] = "VERIFICATION_RECHECK_NOT_EXECUTED"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "replace the verification_command with an allowed local read-only command and rerun check"
        return verdict
    if recheck.get("executed") and not recheck.get("matched"):
        verdict["closure_status"] = "REJECTED"
        verdict["blocking_reason"] = "VERIFICATION_RECHECK_FAILED"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "re-run the verification and update diff_provenance"
        return verdict

    if state["recovery"]["status"] == "PENDING" and not state["recovery"]["reverification_complete"]:
        verdict["blocking_reason"] = "RECOVERY_REVERIFICATION_INCOMPLETE"
        verdict["next_allowed_transition"] = "RECOVERY_REVERIFICATION"
        verdict["narrow_next_safe_step"] = "run reverification against the attested target surface"
        return verdict

    artifact_integrity_warning = bool(bundle.get("artifact_integrity_warning", False))
    if artifact_integrity_warning:
        verdict["closure_warnings"].append("artifact_modified_outside_workflow")
        verdict["closure_status"] = "REJECTED"
        verdict["blocking_reason"] = "ARTIFACT_INTEGRITY_FAILED"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "rebuild the final result artifact and proof bundle on the current surface"
        return verdict

    live_freshness_available = bool(state.get("_state_file") and bundle.get("_bundle_file"))
    freshness = evaluate_closure_freshness_binding(
        bundle.get("closure_freshness_binding", {}),
        live_recheck=live_freshness_available,
    )
    if not live_freshness_available:
        verdict["closure_status"] = "REJECTED"
        verdict["blocking_reason"] = "CLOSURE_FRESHNESS_NOT_LIVE"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "rerun closure through the live artifact path so freshness can be verified"
        return verdict
    if not freshness.get("present", False):
        verdict["closure_status"] = "REJECTED"
        verdict["blocking_reason"] = "CLOSURE_FRESHNESS_BINDING_MISSING"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "rebuild the proof bundle so closure can bind a fresh verified artifact set"
        return verdict
    if not freshness.get("all_required_present", False) or not freshness.get("all_hashes_match", False):
        verdict["closure_warnings"].append("closure_freshness_binding_mismatch")
        verdict["closure_status"] = "REJECTED"
        verdict["blocking_reason"] = "CLOSURE_FRESHNESS_FAILED"
        verdict["next_allowed_transition"] = "PROOF_BUNDLE_REPAIR"
        verdict["narrow_next_safe_step"] = "rebuild the final result artifact and proof bundle on the current surface"
        return verdict

    verdict["closure_status"] = "ACCEPTED"
    verdict["blocking_reason"] = ""
    verdict["next_allowed_transition"] = "NONE"
    verdict["narrow_next_safe_step"] = "NONE"
    verdict["missing_sections"] = []
    return verdict


def apply_verdict_to_state(state: dict, bundle: dict, verdict: dict) -> dict:
    state["execution"]["artifact_bundle_present"] = bool(bundle.get("final_result", {}).get("present", False))
    state["proof_bundle"]["status"] = bundle.get("status", "INVALID")
    state["proof_bundle"]["structural_status"] = bundle.get("structural_status", bundle.get("status", "INVALID"))
    state["proof_bundle"]["semantic_status"] = bundle.get("semantic_status", "NOT_EVALUATED")
    state["proof_bundle"]["missing_sections"] = list(bundle.get("missing_sections", []))
    state["proof_bundle"]["semantically_insufficient_sections"] = list(bundle.get("semantically_insufficient_sections", []))
    state["proof_bundle"]["semantic_next_safe_step"] = bundle.get("semantic_next_safe_step", "")
    state["proof_bundle"]["final_result"] = dict(bundle.get("final_result", {}))
    state["proof_bundle"]["verification_corroboration"] = dict(bundle.get("verification_corroboration", {}))
    state["proof_bundle"]["verification_recheck"] = dict(bundle.get("verification_recheck", {}))
    state["proof_bundle"]["artifact_identity"] = dict(bundle.get("artifact_identity", {}))
    state["proof_bundle"]["cleanup_status"] = dict(bundle.get("cleanup_status", {}))
    state["proof_bundle"]["artifact_integrity_warning"] = bool(bundle.get("artifact_integrity_warning", False))
    state["closure"]["status"] = verdict["closure_status"]
    state["closure"]["blocking_reason"] = verdict["blocking_reason"]
    state["closure"]["next_allowed_transition"] = verdict["next_allowed_transition"]
    state["closure"]["narrow_next_safe_step"] = verdict["narrow_next_safe_step"]
    state["closure"]["missing_sections"] = list(verdict["missing_sections"])
    state["closure"]["warnings"] = list(verdict.get("closure_warnings", []))
    state["next_safe_step"] = verdict["narrow_next_safe_step"]

    if verdict["closure_status"] == "ACCEPTED":
        state["state"] = "CLOSURE_ACCEPTED"
    elif verdict["closure_status"] == "REJECTED":
        state["state"] = "CLOSURE_REJECTED"
    elif state["proof_bundle"]["status"] == "COMPLETE":
        state["state"] = "PROOF_BUNDLE_COMPLETE"
    elif state["proof_bundle"]["status"] == "STRUCTURALLY_COMPLETE":
        state["state"] = "PROOF_BUNDLE_STRUCTURALLY_COMPLETE"

    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-closure-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--bundle-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--certificate-output")
    parser.add_argument("--acceptance-validation-file")
    parser.add_argument("--update-state", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        artifact_root = Path(args.state_file).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "state_file",
            args.state_file,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_closure_paths(args, artifact_root=artifact_root, project_root=project_root)
        state_path = Path(args.state_file)
        bundle_path = Path(args.bundle_file)
        output_path = Path(args.output)
        state = load_json(state_path)
        bundle = load_json(bundle_path)
        state["_state_file"] = str(state_path)
        bundle["_bundle_file"] = str(bundle_path)
        criteria_validation = load_json(Path(args.acceptance_validation_file)) if args.acceptance_validation_file else None
        verdict = build_verdict(
            state,
            bundle,
            criteria_validation,
        )
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(output_path, verdict)

    updated_state = state
    if args.update_state:
        updated_state = apply_verdict_to_state(state, bundle, verdict)
        save_json(state_path, updated_state)

    if args.certificate_output:
        persist_closure_certificate(
            Path(args.certificate_output),
            state=updated_state,
            state_path=state_path,
            bundle=bundle,
            bundle_path=bundle_path,
            verdict=verdict,
            criteria_validation=criteria_validation,
        )

    print(json.dumps({"result": "OK", "closure_status": verdict["closure_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
