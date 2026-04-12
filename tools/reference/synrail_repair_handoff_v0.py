#!/usr/bin/env python3
"""Machine-readable repair handoff generator for Synrail continuation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


INPUT_SPECS = {
    "prompt_identity": {
        "kind": "string",
        "cli_flag": "--prompt-identity",
        "description": "restore the prompt identity used for continuation",
        "required_value": "",
    },
    "task_identity": {
        "kind": "string",
        "cli_flag": "--task-identity",
        "description": "restore the exact task identity used for continuation",
        "required_value": "",
    },
    "target_identity_file": {
        "kind": "file",
        "cli_flag": "--target-identity-file",
        "description": "supply target identity evidence for readiness verification",
        "required_value": "",
    },
    "clean_surface_confirmation": {
        "kind": "flag",
        "cli_flag": "--clean-surface",
        "description": "confirm continuation is running on a clean or explicitly safe execution surface",
        "required_value": "true",
    },
    "artifact_path": {
        "kind": "file",
        "cli_flag": "--artifact-path",
        "description": "restore a viable machine-readable artifact path for readiness",
        "required_value": "",
    },
    "helper_path": {
        "kind": "file",
        "cli_flag": "--helper-path",
        "description": "supply the helper entrypoint needed for readiness verification",
        "required_value": "",
    },
    "credential_surface": {
        "kind": "runtime_input",
        "cli_flag": "--credentials-ok / --credential-env",
        "description": "restore the credential surface needed for continuation readiness",
        "required_value": "",
    },
    "final_result": {
        "kind": "file",
        "cli_flag": "--final-result",
        "description": "supply the final result artifact for bundle repair or closure continuation",
        "required_value": "",
    },
    "readback": {
        "kind": "file",
        "cli_flag": "--readback",
        "description": "supply readback from the changed sections on the attested surface",
        "required_value": "",
    },
    "scenario_proof": {
        "kind": "file",
        "cli_flag": "--scenario-proof",
        "description": "supply scenario proof for the continuation bundle",
        "required_value": "",
    },
    "refresh_recovery_complete": {
        "kind": "enum",
        "cli_flag": "--refresh-recovery-status",
        "description": "mark recovery as complete before resuming closure acceptance",
        "required_value": "COMPLETE",
    },
    "refresh_reverification_complete": {
        "kind": "flag",
        "cli_flag": "--refresh-reverification-complete",
        "description": "confirm recovery reverification is complete before refresh reconciliation",
        "required_value": "true",
    },
}


DOCTOR_FAILURE_INPUTS = {
    "baseline-identity ambiguous": ["target_identity_file"],
    "dirty-surface unsafe": ["clean_surface_confirmation"],
    "helper-integrity unknown": ["helper_path"],
    "credential-surface missing": ["credential_surface"],
    "artifact-viability missing": ["artifact_path"],
    "exact-prompt-artifact-missing": ["prompt_identity", "task_identity"],
}

PROOF_SECTION_INPUTS = {
    "readback": "readback",
    "scenario_proof": "scenario_proof",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def add_unique(target: list[str], value: str) -> None:
    if value not in target:
        target.append(value)


def build_required_input_ids(state: dict) -> list[str]:
    required: list[str] = []

    for failure_class in state.get("doctor", {}).get("blocking_failure_classes", []):
        for input_id in DOCTOR_FAILURE_INPUTS.get(failure_class, []):
            add_unique(required, input_id)

    blocking_reason = state.get("closure", {}).get("blocking_reason", "")
    if blocking_reason in {"ARTIFACT_BUNDLE_MISSING", "INVALID_PROOF_BUNDLE"}:
        add_unique(required, "final_result")

    missing_sections = list(state.get("proof_bundle", {}).get("missing_sections", []))
    for section in state.get("closure", {}).get("missing_sections", []):
        if section not in missing_sections:
            missing_sections.append(section)
    for section in missing_sections:
        mapped = PROOF_SECTION_INPUTS.get(section)
        if mapped:
            add_unique(required, mapped)

    recovery = state.get("recovery", {})
    if recovery.get("status") == "PENDING" and not recovery.get("reverification_complete", False):
        add_unique(required, "refresh_recovery_complete")
        add_unique(required, "refresh_reverification_complete")

    return required


def build_runtime_defaults(state: dict, required_inputs: list[str]) -> dict:
    defaults = {
        "refresh_event_type": "",
        "refresh_use_bundle": False,
        "refresh_use_closure": False,
    }
    if "refresh_recovery_complete" in required_inputs or "refresh_reverification_complete" in required_inputs:
        defaults["refresh_event_type"] = "RECOVERY_EVENT"
        defaults["refresh_use_bundle"] = True
        defaults["refresh_use_closure"] = True
    return defaults


def continuation_allowed(state: dict) -> bool:
    if state.get("state") in {"CLOSURE_ACCEPTED", "CLOSURE_REJECTED"}:
        return False
    if state.get("closure", {}).get("status") == "ACCEPTED":
        return False
    if state.get("closure", {}).get("blocking_reason") == "MODE_SELECTION_NOT_GOVERNED":
        return False
    return True


def build_required_inputs(required_input_ids: list[str]) -> list[dict]:
    required_inputs = []
    for input_id in required_input_ids:
        spec = INPUT_SPECS[input_id]
        required_inputs.append(
            {
                "input_id": input_id,
                "kind": spec["kind"],
                "cli_flag": spec["cli_flag"],
                "description": spec["description"],
                "required_value": spec["required_value"],
            }
        )
    return required_inputs


def build_repair_handoff(state: dict) -> dict:
    required_input_ids = build_required_input_ids(state)
    allowed = continuation_allowed(state)
    return {
        "schema_version": "repair_handoff_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "from_state": state["state"],
        "closure_status": state["closure"]["status"],
        "blocking_reason": state["closure"]["blocking_reason"],
        "continuation_allowed": allowed,
        "continuation_entrypoint": "resume" if allowed else "",
        "required_inputs": build_required_inputs(required_input_ids),
        "runtime_defaults": build_runtime_defaults(state, required_input_ids),
        "next_safe_step": state["next_safe_step"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-repair-handoff-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    handoff = build_repair_handoff(load_json(Path(args.state_file)))
    save_json(Path(args.output), handoff)
    print(
        json.dumps(
            {
                "result": "OK",
                "continuation_allowed": handoff["continuation_allowed"],
                "required_inputs": [item["input_id"] for item in handoff["required_inputs"]],
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
