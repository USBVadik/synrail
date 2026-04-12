#!/usr/bin/env python3
"""Executable doctor v1 for Synrail with bounded filesystem and env probes."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


VERDICTS = {
    "baseline_identity": "NOT_ACCEPTABLE_BASELINE_IDENTITY",
    "clean_execution_surface": "NOT_ACCEPTABLE_DIRTY_SURFACE",
    "helper_integrity": "NOT_ACCEPTABLE_HELPER_INTEGRITY",
    "credential_surface": "NOT_ACCEPTABLE_CREDENTIAL_SURFACE",
    "artifact_viability": "NOT_ACCEPTABLE_ARTIFACT_PATH",
    "prompt_task_identity": "NOT_ACCEPTABLE_EXACT_PROMPT_MISSING",
}

PASS_VERDICT = {
    "CORE_DOCTOR": "ACCEPTABLE_FOR_CORE_RUN",
    "SUPPORT_DOCTOR": "ACCEPTABLE_FOR_SUPPORT_RUN",
    "EXACT_RETRY_DOCTOR": "ACCEPTABLE_FOR_EXACT_RETRY",
}

FAILURE_CLASSES = {
    "baseline_identity": "baseline-identity ambiguous",
    "clean_execution_surface": "dirty-surface unsafe",
    "helper_integrity": "helper-integrity unknown",
    "credential_surface": "credential-surface missing",
    "artifact_viability": "artifact-viability missing",
    "prompt_task_identity": "exact-prompt-artifact-missing",
}

NEXT_STEPS = {
    "baseline_identity": "restore the trusted baseline and expected target-surface identity",
    "clean_execution_surface": "move to a clean or explicitly observed-safe execution surface",
    "helper_integrity": "trust or safely bypass the helper entrypoint",
    "credential_surface": "restore required provider credentials",
    "artifact_viability": "restore a reliable machine-readable artifact path",
    "prompt_task_identity": "restore the exact prompt and task identity artifacts",
}


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def gate(status: str, note: str) -> dict:
    return {"status": status, "note": note}


def non_empty_identity(value: str) -> bool:
    return bool(value and value.strip() and value.strip().upper() != "UNKNOWN")


def read_non_empty_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text().strip()


def env_value_looks_path_like(name: str, value: str) -> bool:
    upper_name = name.upper()
    if upper_name in {"GOOGLE_APPLICATION_CREDENTIALS", "AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE", "AZURE_CONFIG_DIR"}:
        return True
    if upper_name.endswith("_FILE") or upper_name.endswith("_PATH") or upper_name.endswith("_DIR"):
        return True
    if not value:
        return False
    if value.startswith(("~", "/", "./", "../")):
        return True
    if os.sep in value or (os.altsep and os.altsep in value):
        return True
    return value.endswith(".json")


def probe_baseline_identity(args: argparse.Namespace) -> tuple[dict, str, str]:
    if not non_empty_identity(args.baseline_identity):
        return gate("FAIL", "trusted baseline identity is missing"), "", args.expected_target_identity or ""

    observed_target_identity = ""
    if args.target_identity_file:
        observed_target_identity = read_non_empty_text(Path(args.target_identity_file))
        if not observed_target_identity:
            return gate("FAIL", "target identity artifact is missing or empty"), "", args.expected_target_identity or ""

    expected_target_identity = (args.expected_target_identity or "").strip()
    if observed_target_identity and expected_target_identity and observed_target_identity != expected_target_identity:
        return (
            gate("FAIL", "target identity artifact does not match the expected target surface"),
            observed_target_identity,
            expected_target_identity,
        )

    if observed_target_identity and expected_target_identity:
        return (
            gate("PASS", "trusted baseline identity is present and target identity matches expectation"),
            observed_target_identity,
            expected_target_identity,
        )

    return gate("PASS", "trusted baseline identity is present"), observed_target_identity, expected_target_identity


def probe_clean_execution_surface(args: argparse.Namespace) -> dict:
    if args.clean_surface:
        return gate("PASS", "execution surface is acceptable")

    target = Path(args.target_path)
    if not target.exists():
        return gate("FAIL", "target execution surface does not exist")

    if (target / ".git").exists():
        completed = subprocess.run(
            ["git", "-C", str(target), "status", "--porcelain"],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            return gate("FAIL", "git status could not inspect the target surface")
        if completed.stdout.strip():
            return gate("FAIL", "execution surface has uncommitted changes")
        return gate("PASS", "execution surface is clean under git")

    if target.is_dir():
        return gate("PASS", "non-git execution surface exists and is explicitly observed")

    return gate("FAIL", "target execution surface is not a directory")


def probe_artifact_viability(args: argparse.Namespace) -> dict:
    if args.artifact_viable:
        return gate("PASS", "machine-readable artifact path is viable")

    if not args.artifact_path:
        return gate("FAIL", "artifact path is not specified")

    artifact = Path(args.artifact_path)
    parent = artifact.parent
    if parent.exists() and parent.is_dir():
        return gate("PASS", "artifact path parent exists and is writable by convention")
    return gate("FAIL", "artifact path parent does not exist")


def probe_helper_integrity(args: argparse.Namespace) -> dict:
    if args.helper_ok:
        return gate("PASS", "helper surface is trusted or safely bypassed")

    if args.doctor_level not in {"SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"}:
        return gate("NOT_APPLICABLE", "helper integrity not required for this level")

    if not args.helper_path:
        return gate("FAIL", "helper path is not specified")

    helper = Path(args.helper_path)
    if helper.exists() and helper.is_file():
        return gate("PASS", "helper entrypoint exists")
    return gate("FAIL", "helper entrypoint is missing")


def probe_credential_surface(args: argparse.Namespace) -> dict:
    if args.credentials_ok:
        return gate("PASS", "credential surface is present")

    if args.doctor_level not in {"SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"}:
        return gate("NOT_APPLICABLE", "credential surface not required for this level")

    if not args.credential_env:
        return gate("FAIL", "required credential env names are not specified")

    missing = [name for name in args.credential_env if not os.environ.get(name)]
    if missing:
        return gate("FAIL", f"missing credential env: {', '.join(missing)}")

    invalid_paths = []
    for name in args.credential_env:
        value = os.environ.get(name, "")
        if not env_value_looks_path_like(name, value):
            continue
        candidate = Path(value).expanduser()
        if not candidate.exists():
            invalid_paths.append(f"{name} -> {candidate}")
    if invalid_paths:
        return gate("FAIL", f"credential env points to a missing path: {', '.join(invalid_paths)}")

    return gate("PASS", "required credential env is present")


def probe_prompt_task_identity(args: argparse.Namespace) -> dict:
    if args.prompt_identity_ok:
        return gate("PASS", "exact prompt and task identity are present")

    if args.doctor_level != "EXACT_RETRY_DOCTOR":
        return gate("NOT_APPLICABLE", "prompt/task identity not required for this level")

    if not args.prompt_identity_file:
        return gate("FAIL", "exact prompt identity file is not specified")

    prompt_file = Path(args.prompt_identity_file)
    if prompt_file.exists():
        contents = prompt_file.read_text().strip()
        if not contents:
            return gate("FAIL", "exact prompt or task identity artifact is empty")
        if args.expected_task_identity and args.expected_task_identity not in contents:
            return gate("FAIL", "exact prompt identity artifact does not match the expected task identity")
        return gate("PASS", "exact prompt and task identity artifact is present")
    return gate("FAIL", "exact prompt or task identity artifact is missing")


def build_record(args: argparse.Namespace) -> dict:
    baseline_identity_gate, observed_target_identity, expected_target_identity = probe_baseline_identity(args)
    gates = {
        "baseline_identity": baseline_identity_gate,
        "clean_execution_surface": probe_clean_execution_surface(args),
        "artifact_viability": probe_artifact_viability(args),
        "helper_integrity": probe_helper_integrity(args),
        "credential_surface": probe_credential_surface(args),
        "prompt_task_identity": probe_prompt_task_identity(args),
    }

    blocking_failure_classes = []
    final_verdict = PASS_VERDICT[args.doctor_level]
    next_safe_step = "run execution"

    for key, result in gates.items():
        if result["status"] == "FAIL":
            blocking_failure_classes.append(FAILURE_CLASSES[key])
            final_verdict = VERDICTS[key]
            next_safe_step = NEXT_STEPS[key]
            break

    return {
        "schema_version": "doctor_record_v0",
        "doctor_run_id": args.doctor_run_id,
        "doctor_level": args.doctor_level,
        "target_execution_surface": {
            "path": args.target_path,
            "classification": args.target_classification,
            "observed_identity": observed_target_identity,
            "expected_identity": expected_target_identity,
        },
        "trusted_baseline": {
            "identity": args.baseline_identity,
        },
        "intended_run_class": args.intended_run_class,
        "gate_results": gates,
        "blocking_failure_classes": blocking_failure_classes,
        "final_verdict": final_verdict,
        "recommended_next_safe_step": next_safe_step,
    }


def apply_record_to_state(state: dict, record: dict) -> dict:
    acceptable = record["final_verdict"].startswith("ACCEPTABLE_")
    state["doctor"]["status"] = "PASS" if acceptable else "FAIL"
    state["doctor"]["blocking_failure_classes"] = list(record["blocking_failure_classes"])
    if not acceptable:
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "DOCTOR_NOT_GREEN"
        state["closure"]["next_allowed_transition"] = "DOCTOR_READINESS"
        state["closure"]["narrow_next_safe_step"] = record["recommended_next_safe_step"]
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = record["recommended_next_safe_step"]
    return state


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-doctor-v1")
    parser.add_argument("--doctor-run-id", required=True)
    parser.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    parser.add_argument("--target-path", required=True)
    parser.add_argument("--target-classification", required=True)
    parser.add_argument("--baseline-identity", required=True)
    parser.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    parser.add_argument("--output", required=True)
    parser.add_argument("--state-file")
    parser.add_argument("--update-state", action="store_true")
    parser.add_argument("--clean-surface", action="store_true")
    parser.add_argument("--artifact-viable", action="store_true")
    parser.add_argument("--helper-ok", action="store_true")
    parser.add_argument("--credentials-ok", action="store_true")
    parser.add_argument("--prompt-identity-ok", action="store_true")
    parser.add_argument("--artifact-path")
    parser.add_argument("--helper-path")
    parser.add_argument("--credential-env", action="append", default=[])
    parser.add_argument("--prompt-identity-file")
    parser.add_argument("--expected-task-identity")
    parser.add_argument("--target-identity-file")
    parser.add_argument("--expected-target-identity")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(args)
    save_json(Path(args.output), record)

    if args.update_state:
        if not args.state_file:
            print(json.dumps({"result": "ERROR", "reason": "STATE_FILE_REQUIRED_FOR_UPDATE"}, ensure_ascii=True))
            return 2
        state_path = Path(args.state_file)
        state = load_json(state_path)
        save_json(state_path, apply_record_to_state(state, record))

    print(json.dumps({"result": "OK", "final_verdict": record["final_verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
