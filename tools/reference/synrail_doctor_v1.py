#!/usr/bin/env python3
"""Executable doctor v1 for Synrail with bounded filesystem and env probes."""

from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
import stat as stat_module
import subprocess
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json

try:
    from .synrail_doctor_coverage_v0 import (
        DEFAULT_CORPUS as DEFAULT_DOCTOR_COVERAGE_CORPUS,
        DEFAULT_PROFILE as DEFAULT_DOCTOR_COVERAGE_PROFILE,
        REPO_ROOT as DOCTOR_COVERAGE_REPO_ROOT,
        build_coverage_record,
        load_corpus as load_coverage_corpus,
        load_profile as load_coverage_profile,
    )
except ImportError:
    from synrail_doctor_coverage_v0 import (
        DEFAULT_CORPUS as DEFAULT_DOCTOR_COVERAGE_CORPUS,
        DEFAULT_PROFILE as DEFAULT_DOCTOR_COVERAGE_PROFILE,
        REPO_ROOT as DOCTOR_COVERAGE_REPO_ROOT,
        build_coverage_record,
        load_corpus as load_coverage_corpus,
        load_profile as load_coverage_profile,
    )

try:
    from .synrail_path_scope_v0 import (
        ARTIFACT_SCOPE,
        DUAL_SCOPE,
        PROJECT_SCOPE,
        PathScopeValidationError,
        path_surface_violation,
        path_within_scope,
        reject_path_surface,
        resolved_path_for_value,
        symlinked_ancestor_within,
        validate_namespace_paths,
        validate_root_within_project,
    )
except ImportError:
    from synrail_path_scope_v0 import (
        ARTIFACT_SCOPE,
        DUAL_SCOPE,
        PROJECT_SCOPE,
        PathScopeValidationError,
        path_surface_violation,
        path_within_scope,
        reject_path_surface,
        resolved_path_for_value,
        symlinked_ancestor_within,
        validate_namespace_paths,
        validate_root_within_project,
    )


DOCTOR_PATH_SCOPES = {
    "output": ARTIFACT_SCOPE,
    "state_file": ARTIFACT_SCOPE,
    "target_path": PROJECT_SCOPE,
    "artifact_path": DUAL_SCOPE,
    "helper_path": PROJECT_SCOPE,
    "prompt_identity_file": ARTIFACT_SCOPE,
    "target_identity_file": DUAL_SCOPE,
    "coverage_profile_file": PROJECT_SCOPE,
    "coverage_corpus_file": PROJECT_SCOPE,
}


VERDICTS = {
    "baseline_identity": "NOT_ACCEPTABLE_BASELINE_IDENTITY",
    "clean_execution_surface": "NOT_ACCEPTABLE_DIRTY_SURFACE",
    "helper_integrity": "NOT_ACCEPTABLE_HELPER_INTEGRITY",
    "credential_surface": "NOT_ACCEPTABLE_CREDENTIAL_SURFACE",
    "artifact_viability": "NOT_ACCEPTABLE_ARTIFACT_PATH",
    "prompt_task_identity": "NOT_ACCEPTABLE_EXACT_PROMPT_MISSING",
    "doctor_coverage": "NOT_ACCEPTABLE_DOCTOR_COVERAGE",
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
    "doctor_coverage": "doctor-coverage incomplete",
}

NEXT_STEPS = {
    "baseline_identity": "restore the trusted baseline and expected target-surface identity",
    "clean_execution_surface": "move to a clean or explicitly observed-safe execution surface",
    "helper_integrity": "repair, replace, or safely bypass the helper entrypoint before execution",
    "credential_surface": "restore required provider credentials",
    "artifact_viability": "restore a reliable machine-readable artifact path",
    "prompt_task_identity": "restore the exact prompt and task identity artifacts",
    "doctor_coverage": "close the agreed critical doctor fail-mode coverage before trusting readiness",
}






def gate(status: str, note: str, *, override: bool = False, override_reason: str = "") -> dict:
    return {
        "status": status,
        "note": note,
        "override": override,
        "override_reason": override_reason,
    }


def blocked_coverage_record(reason: str, *, deployment_context: bool) -> dict:
    return {
        "schema_version": "doctor_coverage_record_v0",
        "doctor_version": "synrail_doctor_v1",
        "coverage_source": "DECLARED_PROFILE_PLUS_MEASURED_CORPUS",
        "corpus_version": "",
        "coverage_threshold_policy": "ALL_CRITICAL_FAIL_MODES_COVERED",
        "critical_fail_modes": [],
        "declared_covered_fail_modes": [],
        "declared_partial_fail_modes": [],
        "declared_uncovered_fail_modes": [],
        "covered_fail_modes": [],
        "partial_fail_modes": [],
        "uncovered_fail_modes": [],
        "measured_case_count": 0,
        "measured_case_match_count": 0,
        "measured_case_problem_count": 0,
        "measured_cases": [],
        "decision_trace": [],
        "critical_fail_mode_count": 0,
        "critical_covered_count": 0,
        "critical_missing_fail_modes": [],
        "critical_modes_without_measured_evidence": [],
        "critical_modes_with_mismatched_evidence": [],
        "deployment_context_confirmed": bool(deployment_context),
        "threshold_met": False,
        "gate_status": "BLOCKED",
        "gate_reason": reason,
    }


def effective_coverage_path(value: str, *, base: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    local = base.parent / candidate
    try:
        local.stat()
        return local
    except FileNotFoundError:
        return DOCTOR_COVERAGE_REPO_ROOT / candidate


def build_override_surface(gates: dict[str, dict], override_gates: list[str]) -> tuple[str, list[str]]:
    if not override_gates:
        return "", []
    warnings: list[str] = []
    for key in override_gates:
        reason = (gates.get(key, {}).get("override_reason", "") or "").strip()
        warnings.append(f"{key}: {reason}" if reason else key)
    return f"doctor override present: {', '.join(override_gates)}", warnings


def non_empty_identity(value: str) -> bool:
    return bool(value and value.strip() and value.strip().upper() != "UNKNOWN")


def read_non_empty_text(path: Path) -> str:
    try:
        return path.read_text().strip()
    except FileNotFoundError:
        return ""
    except IsADirectoryError:
        return ""


def normalize_scope_path(value: str) -> str:
    return value.strip().replace("\\", "/").strip("/")


def detect_out_of_scope_changes(changed_files: list[str], allowed_scope_paths: list[str]) -> list[str]:
    normalized_allowed = [normalize_scope_path(value) for value in allowed_scope_paths if normalize_scope_path(value)]
    if not normalized_allowed:
        return []

    out_of_scope: list[str] = []
    for value in changed_files:
        normalized = normalize_scope_path(value)
        if not normalized:
            continue
        if any(normalized == allowed or normalized.startswith(f"{allowed}/") for allowed in normalized_allowed):
            continue
        out_of_scope.append(value)
    return out_of_scope


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


def env_value_is_placeholder(value: str) -> bool:
    normalized = value.strip().upper()
    if not normalized:
        return False
    placeholders = {
        "CHANGE_ME",
        "REPLACE_ME",
        "PLACEHOLDER",
        "YOUR_TOKEN_HERE",
        "YOUR_API_KEY_HERE",
        "TODO",
        "TBD",
        "INSERT_VALUE",
        "SET_ME",
    }
    return normalized in placeholders


def direct_file_fingerprint(path: Path) -> tuple[int, int, int, int] | None:
    try:
        stat_result = path.stat(follow_symlinks=False)
    except OSError:
        return None
    if not stat_module.S_ISREG(stat_result.st_mode):
        return None
    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
    )


def read_stable_non_empty_text(path: Path) -> tuple[str, str]:
    initial_fingerprint = direct_file_fingerprint(path)
    if initial_fingerprint is None:
        return "", "missing"
    contents = read_non_empty_text(path)
    if direct_file_fingerprint(path) != initial_fingerprint:
        return "", "changed"
    return contents, ""


def load_stable_json_document(path: Path) -> tuple[dict | None, str]:
    initial_fingerprint = direct_file_fingerprint(path)
    if initial_fingerprint is None:
        return None, "missing"
    try:
        payload = load_json(path)
    except json.JSONDecodeError:
        return None, "invalid"
    if direct_file_fingerprint(path) != initial_fingerprint:
        return None, "changed"
    return payload, ""


def probe_baseline_identity(args: argparse.Namespace) -> tuple[dict, str, str]:
    if not non_empty_identity(args.baseline_identity):
        return gate("FAIL", "trusted baseline identity is missing"), "", args.expected_target_identity or ""

    target_contour_root = target_contour_root_for(args)
    observed_target_identity = ""
    if args.target_identity_file:
        target_identity_file = Path(args.target_identity_file)
        if target_identity_file.is_symlink():
            return gate("FAIL", "target identity artifact is a symlink, expected a direct identity surface"), "", args.expected_target_identity or ""
        if target_identity_file.parent.is_symlink():
            return gate("FAIL", "target identity artifact parent is a symlink, expected a direct identity surface"), "", args.expected_target_identity or ""
        ancestor = symlinked_ancestor_within(target_identity_file.parent, stop_at=target_contour_root)
        if ancestor is not None:
            return gate("FAIL", "target identity artifact ancestor is a symlink, expected a direct identity surface"), "", args.expected_target_identity or ""
        observed_target_identity, read_error = read_stable_non_empty_text(target_identity_file)
        if read_error == "changed":
            return gate("FAIL", "target identity artifact changed during validation; rerun doctor on a stable direct identity surface"), "", args.expected_target_identity or ""
        if not observed_target_identity:
            return gate("FAIL", "target identity artifact is missing or empty"), "", args.expected_target_identity or ""

    expected_target_identity = (args.expected_target_identity or "").strip()
    if expected_target_identity and not observed_target_identity:
        return gate("FAIL", "expected target identity specified but target identity artifact not provided"), "", expected_target_identity
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
    out_of_scope = detect_out_of_scope_changes(args.changed_file, args.allowed_scope_path)
    if out_of_scope:
        preview = ", ".join(out_of_scope[:3])
        if len(out_of_scope) > 3:
            preview = f"{preview}, +{len(out_of_scope) - 3} more"
        return gate("FAIL", f"execution surface has out-of-scope modifications: {preview}")

    if args.clean_surface:
        if args.changed_file and args.allowed_scope_path:
            return gate(
                "PASS",
                "execution surface is explicitly observed and changed files stay within the allowed scope",
            )
        return gate(
            "PASS",
            "execution surface is acceptable",
            override=True,
            override_reason="operator bypass via --clean-surface",
        )

    target = Path(args.target_path)
    if target.is_symlink():
        return gate("FAIL", "target execution surface is a symlink, expected a direct execution surface")
    if target.parent.is_symlink():
        return gate("FAIL", "target execution surface parent is a symlink, expected a direct execution surface")
    artifact_parent = Path(args.artifact_path).expanduser().parent if args.artifact_path else target.parent
    target_contour_root = Path(os.path.commonpath([str(target.expanduser()), str(artifact_parent)]))
    ancestor = symlinked_ancestor_within(target, stop_at=target_contour_root)
    if ancestor is not None:
        return gate("FAIL", "target execution surface ancestor is a symlink, expected a direct execution surface")
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
        return gate(
            "PASS",
            "machine-readable artifact path is viable",
            override=True,
            override_reason="operator bypass via --artifact-viable",
        )

    if not args.artifact_path:
        return gate("FAIL", "artifact path is not specified")

    project_root = Path(args.target_path).expanduser().resolve().parent
    artifact_root = Path(args.artifact_path).expanduser().resolve().parent
    if not path_within_scope(args.artifact_path, scope=DUAL_SCOPE, project_root=project_root, artifact_root=artifact_root):
        return gate("FAIL", "artifact path escapes the trusted target contour")

    target_contour_root = target_contour_root_for(args)
    artifact = Path(args.artifact_path)
    if artifact.is_symlink():
        return gate("FAIL", "artifact path is a symlink, expected a direct machine-readable artifact surface")
    parent = artifact.parent
    if parent.is_symlink():
        return gate("FAIL", "artifact path parent is a symlink, expected a direct machine-readable artifact surface")
    ancestor = symlinked_ancestor_within(parent, stop_at=target_contour_root)
    if ancestor is not None:
        return gate("FAIL", "artifact path ancestor is a symlink, expected a direct machine-readable artifact surface")
    if parent.exists() and parent.is_dir():
        return gate("PASS", "artifact path parent exists and is writable by convention")
    return gate("FAIL", "artifact path parent does not exist")


def probe_helper_integrity(args: argparse.Namespace) -> dict:
    if args.helper_ok:
        return gate(
            "PASS",
            "helper surface is trusted or safely bypassed",
            override=True,
            override_reason="operator bypass via --helper-ok",
        )

    if args.doctor_level not in {"SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"}:
        return gate("NOT_APPLICABLE", "helper integrity not required for this level")

    if not args.helper_path:
        return gate("FAIL", "helper path is not specified")

    project_root = Path(args.target_path).expanduser().resolve().parent
    if not path_within_scope(args.helper_path, scope=PROJECT_SCOPE, project_root=project_root, artifact_root=None):
        return gate("FAIL", "helper entrypoint escapes the trusted target contour")

    target_contour_root = target_contour_root_for(args)
    helper = Path(args.helper_path)
    if helper.is_symlink():
        return gate("FAIL", "helper entrypoint is a symlink, expected a direct helper surface")
    if helper.parent.is_symlink():
        return gate("FAIL", "helper entrypoint parent is a symlink, expected a direct helper surface")
    ancestor = symlinked_ancestor_within(helper.parent, stop_at=target_contour_root)
    if ancestor is not None:
        return gate("FAIL", "helper entrypoint ancestor is a symlink, expected a direct helper surface")
    initial_helper_fingerprint = direct_file_fingerprint(helper)
    if initial_helper_fingerprint:
        helper_execution_path = helper.resolve(strict=True)
        if helper.suffix == ".py":
            completed = subprocess.run(
                ["python3", "-m", "py_compile", str(helper_execution_path)],
                check=False,
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPYCACHEPREFIX": "/tmp/synrail_doctor_pycache"},
            )
            if completed.returncode != 0:
                return gate("FAIL", "helper entrypoint exists but python syntax is invalid")
            import_failure = probe_python_helper_import_drift(helper)
            if import_failure:
                return gate("FAIL", import_failure)
        elif helper.suffix in {".sh", ""}:
            completed = subprocess.run(
                ["bash", "-n", str(helper_execution_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                return gate("FAIL", "helper entrypoint exists but shell syntax is invalid")
        if direct_file_fingerprint(helper) != initial_helper_fingerprint:
            return gate("FAIL", "helper entrypoint changed during validation; rerun doctor on a stable direct helper surface")
        return gate("PASS", "helper entrypoint exists and parses successfully")
    return gate("FAIL", "helper entrypoint is missing")


def local_module_exists(module_name: str, *, base: Path) -> bool:
    candidate_file = base / f"{module_name}.py"
    candidate_pkg = base / module_name / "__init__.py"
    return candidate_file.exists() or candidate_pkg.exists()


def relative_module_exists(module_name: str | None, *, helper: Path, level: int) -> bool:
    base = helper.parent
    for _ in range(max(level - 1, 0)):
        base = base.parent
    if not module_name:
        return True
    parts = module_name.split(".")
    candidate_file = base.joinpath(*parts).with_suffix(".py")
    candidate_pkg = base.joinpath(*parts, "__init__.py")
    return candidate_file.exists() or candidate_pkg.exists()


def probe_python_helper_import_drift(helper: Path) -> str:
    try:
        tree = ast.parse(helper.read_text(), filename=str(helper))
    except SyntaxError:
        return ""

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            module_names = [alias.name for alias in node.names]
            level = 0
        elif isinstance(node, ast.ImportFrom):
            module_names = [node.module] if node.module else [None]
            level = node.level
        else:
            continue

        for module_name in module_names:
            if level > 0:
                if not relative_module_exists(module_name, helper=helper, level=level):
                    target = module_name or "."
                    return f"helper entrypoint imports a missing relative module: {target}"
                continue

            if not module_name:
                continue
            root = module_name.split(".")[0]
            if local_module_exists(root, base=helper.parent):
                continue
            if importlib.util.find_spec(root) is None:
                return f"helper entrypoint imports a missing module: {root}"
    return ""


def probe_credential_surface(args: argparse.Namespace) -> dict:
    if args.credentials_ok:
        return gate(
            "PASS",
            "credential surface is present",
            override=True,
            override_reason="operator bypass via --credentials-ok",
        )

    if args.doctor_level not in {"SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"}:
        return gate("NOT_APPLICABLE", "credential surface not required for this level")

    if not args.credential_env:
        return gate("FAIL", "required credential env names are not specified")

    project_root = Path(args.target_path).expanduser().resolve().parent
    missing = [name for name in args.credential_env if not os.environ.get(name)]
    if missing:
        return gate("FAIL", f"missing credential env: {', '.join(missing)}")

    placeholder_values = [name for name in args.credential_env if env_value_is_placeholder(os.environ.get(name, ""))]
    if placeholder_values:
        return gate("FAIL", f"credential env still uses placeholder values: {', '.join(placeholder_values)}")

    target_contour_root = target_contour_root_for(args)
    invalid_paths = []
    for name in args.credential_env:
        value = os.environ.get(name, "")
        if not env_value_looks_path_like(name, value):
            continue
        candidate = Path(value).expanduser()
        if not path_within_scope(str(candidate), scope=PROJECT_SCOPE, project_root=project_root, artifact_root=None):
            invalid_paths.append(f"{name} -> {candidate} escapes the trusted target contour")
            continue
        if not candidate.exists():
            invalid_paths.append(f"{name} -> {candidate}")
            continue
        if candidate.is_symlink():
            invalid_paths.append(f"{name} -> {candidate} is a symlink, expected a direct credential surface")
            continue
        if candidate.parent.is_symlink():
            invalid_paths.append(f"{name} -> {candidate.parent} is a symlinked parent, expected a direct credential surface")
            continue
        ancestor = symlinked_ancestor_within(candidate.parent, stop_at=target_contour_root)
        if ancestor is not None:
            invalid_paths.append(f"{name} -> {ancestor} is a symlinked ancestor, expected a direct credential surface")
            continue
        candidate = candidate.resolve()
        if name.upper().endswith("_FILE") and candidate.is_dir():
            invalid_paths.append(f"{name} -> {candidate} is a directory, expected a file")
            continue
        if candidate.suffix == ".json" and candidate.is_file():
            payload, read_error = load_stable_json_document(candidate)
            if read_error == "changed":
                invalid_paths.append(f"{name} -> {candidate} changed during validation")
                continue
            if payload is None:
                invalid_paths.append(f"{name} -> {candidate} contains invalid json")
    if invalid_paths:
        return gate("FAIL", f"credential env points to an invalid credential surface: {', '.join(invalid_paths)}")

    return gate("PASS", "required credential env is present")


def probe_prompt_task_identity(args: argparse.Namespace) -> dict:
    if args.prompt_identity_ok:
        return gate(
            "PASS",
            "exact prompt and task identity are present",
            override=True,
            override_reason="operator bypass via --prompt-identity-ok",
        )

    if args.doctor_level != "EXACT_RETRY_DOCTOR":
        return gate("NOT_APPLICABLE", "prompt/task identity not required for this level")

    if not args.prompt_identity_file:
        return gate("FAIL", "exact prompt identity file is not specified")

    target_contour_root = target_contour_root_for(args)
    prompt_file = Path(args.prompt_identity_file)
    if prompt_file.is_symlink():
        return gate("FAIL", "exact prompt identity artifact is a symlink, expected a direct identity surface")
    if prompt_file.parent.is_symlink():
        return gate("FAIL", "exact prompt identity artifact parent is a symlink, expected a direct identity surface")
    ancestor = symlinked_ancestor_within(prompt_file.parent, stop_at=target_contour_root)
    if ancestor is not None:
        return gate("FAIL", "exact prompt identity artifact ancestor is a symlink, expected a direct identity surface")
    project_root = Path(args.target_path).expanduser().resolve().parent
    artifact_root = Path(args.artifact_path).expanduser().resolve().parent if args.artifact_path else None
    if not path_within_scope(args.prompt_identity_file, scope=ARTIFACT_SCOPE, project_root=project_root, artifact_root=artifact_root):
        return gate("FAIL", "exact prompt identity artifact escapes the trusted target contour")
    if prompt_file.exists():
        contents, read_error = read_stable_non_empty_text(prompt_file)
        if read_error == "changed":
            return gate("FAIL", "exact prompt identity artifact changed during validation; rerun doctor on a stable direct identity surface")
        if not contents:
            return gate("FAIL", "exact prompt or task identity artifact is empty")
        if args.expected_task_identity and args.expected_task_identity not in contents:
            return gate("FAIL", "exact prompt identity artifact does not match the expected task identity")
        return gate("PASS", "exact prompt and task identity artifact is present")
    return gate("FAIL", "exact prompt or task identity artifact is missing")


def build_record(args: argparse.Namespace) -> dict:
    deployment_context = getattr(args, "deployment_context", False)
    baseline_identity_gate, observed_target_identity, expected_target_identity = probe_baseline_identity(args)
    gates = {
        "baseline_identity": baseline_identity_gate,
        "clean_execution_surface": probe_clean_execution_surface(args),
        "artifact_viability": probe_artifact_viability(args),
        "helper_integrity": probe_helper_integrity(args),
        "credential_surface": probe_credential_surface(args),
        "prompt_task_identity": probe_prompt_task_identity(args),
    }
    coverage_profile_file = Path(args.coverage_profile_file) if args.coverage_profile_file else DEFAULT_DOCTOR_COVERAGE_PROFILE
    target_contour_root = target_contour_root_for(args)
    project_root = Path(args.target_path).expanduser().resolve().parent
    artifact_root = Path(args.artifact_path).expanduser().resolve().parent if args.artifact_path else None
    if args.coverage_profile_file and not path_within_scope(str(coverage_profile_file), scope=PROJECT_SCOPE, project_root=project_root, artifact_root=None):
        coverage = blocked_coverage_record("DOCTOR_COVERAGE_PROFILE_OUT_OF_SCOPE", deployment_context=deployment_context)
    elif coverage_profile_file.is_symlink():
        coverage = blocked_coverage_record("DOCTOR_COVERAGE_PROFILE_SYMLINK_SURFACE", deployment_context=deployment_context)
    elif coverage_profile_file.parent.is_symlink():
        coverage = blocked_coverage_record("DOCTOR_COVERAGE_PROFILE_PARENT_SYMLINK_SURFACE", deployment_context=deployment_context)
    elif symlinked_ancestor_within(coverage_profile_file.parent, stop_at=target_contour_root) is not None:
        coverage = blocked_coverage_record("DOCTOR_COVERAGE_PROFILE_ANCESTOR_SYMLINK_SURFACE", deployment_context=deployment_context)
    else:
        profile_fingerprint = direct_file_fingerprint(coverage_profile_file)
        if profile_fingerprint is None:
            coverage = blocked_coverage_record("DOCTOR_COVERAGE_PROFILE_MISSING", deployment_context=deployment_context)
        else:
            coverage_profile = load_coverage_profile(coverage_profile_file)
            if direct_file_fingerprint(coverage_profile_file) != profile_fingerprint:
                coverage = blocked_coverage_record("DOCTOR_COVERAGE_PROFILE_CHANGED_DURING_VALIDATION", deployment_context=deployment_context)
            else:
                if args.coverage_corpus_file:
                    coverage_corpus_input = Path(args.coverage_corpus_file)
                else:
                    profile_corpus = coverage_profile.get("measured_corpus_file", "")
                    coverage_corpus_input = (
                        effective_coverage_path(profile_corpus, base=coverage_profile_file)
                        if profile_corpus
                        else DEFAULT_DOCTOR_COVERAGE_CORPUS
                    )
                coverage_corpus_requires_scope_validation = bool(args.coverage_corpus_file or args.coverage_profile_file)
                if coverage_corpus_requires_scope_validation and not path_within_scope(str(coverage_corpus_input), scope=PROJECT_SCOPE, project_root=project_root, artifact_root=None):
                    coverage = blocked_coverage_record("DOCTOR_COVERAGE_CORPUS_OUT_OF_SCOPE", deployment_context=deployment_context)
                elif coverage_corpus_input.is_symlink():
                    coverage = blocked_coverage_record("DOCTOR_COVERAGE_CORPUS_SYMLINK_SURFACE", deployment_context=deployment_context)
                elif coverage_corpus_input.parent.is_symlink():
                    coverage = blocked_coverage_record("DOCTOR_COVERAGE_CORPUS_PARENT_SYMLINK_SURFACE", deployment_context=deployment_context)
                elif symlinked_ancestor_within(coverage_corpus_input.parent, stop_at=target_contour_root) is not None:
                    coverage = blocked_coverage_record("DOCTOR_COVERAGE_CORPUS_ANCESTOR_SYMLINK_SURFACE", deployment_context=deployment_context)
                else:
                    corpus_fingerprint = direct_file_fingerprint(coverage_corpus_input)
                    if corpus_fingerprint is None:
                        coverage = blocked_coverage_record("DOCTOR_COVERAGE_CORPUS_MISSING", deployment_context=deployment_context)
                    else:
                        coverage_corpus, coverage_corpus_file = load_coverage_corpus(
                            Path(args.coverage_corpus_file) if args.coverage_corpus_file else None,
                            profile=coverage_profile,
                            profile_file=coverage_profile_file,
                        )
                        if direct_file_fingerprint(coverage_corpus_file) != corpus_fingerprint:
                            coverage = blocked_coverage_record("DOCTOR_COVERAGE_CORPUS_CHANGED_DURING_VALIDATION", deployment_context=deployment_context)
                        else:
                            coverage = build_coverage_record(
                                coverage_profile,
                                coverage_corpus,
                                corpus_file=coverage_corpus_file,
                                deployment_context=deployment_context,
                            )

    blocking_failure_classes = []
    final_verdict = PASS_VERDICT[args.doctor_level]
    next_safe_step = "run execution"

    for key, result in gates.items():
        if result["status"] == "FAIL":
            blocking_failure_classes.append(FAILURE_CLASSES[key])
            final_verdict = VERDICTS[key]
            next_safe_step = NEXT_STEPS[key]
            break

    if final_verdict.startswith("ACCEPTABLE_") and not coverage["threshold_met"]:
        blocking_failure_classes.append(FAILURE_CLASSES["doctor_coverage"])
        final_verdict = VERDICTS["doctor_coverage"]
        next_safe_step = NEXT_STEPS["doctor_coverage"]

    override_gates = [key for key, result in gates.items() if result.get("override")]
    override_summary, override_warnings = build_override_surface(gates, override_gates)

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
        "override_gates": override_gates,
        "override_summary": override_summary,
        "override_warnings": override_warnings,
        "coverage": coverage,
        "blocking_failure_classes": blocking_failure_classes,
        "final_verdict": final_verdict,
        "recommended_next_safe_step": next_safe_step,
    }


def apply_record_to_state(state: dict, record: dict) -> dict:
    acceptable = record["final_verdict"].startswith("ACCEPTABLE_")
    state["doctor"]["status"] = "PASS" if acceptable else "FAIL"
    state["doctor"]["blocking_failure_classes"] = list(record["blocking_failure_classes"])
    state["doctor"]["override_gates"] = list(record.get("override_gates", []))
    state["doctor"]["override_summary"] = record.get("override_summary", "")
    state["doctor"]["override_warnings"] = list(record.get("override_warnings", []))
    if not acceptable:
        state["state"] = "DOCTOR_BLOCKED"
        state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
        state["closure"]["blocking_reason"] = "DOCTOR_NOT_GREEN"
        state["closure"]["next_allowed_transition"] = "DOCTOR_READINESS"
        state["closure"]["narrow_next_safe_step"] = record["recommended_next_safe_step"]
        state["closure"]["missing_sections"] = []
        state["next_safe_step"] = record["recommended_next_safe_step"]
    return state


def current_project_root() -> Path:
    return Path.cwd().resolve()


def project_root_for_args(args: argparse.Namespace) -> Path:
    target_path = Path(args.target_path).expanduser().resolve()
    return target_path if target_path.is_dir() else target_path.parent


def target_contour_root_for(args: argparse.Namespace) -> Path:
    return Path(args.target_path).expanduser().parent.resolve()


def symlinked_ancestor(path: Path) -> Path | None:
    for candidate in path.parents:
        if candidate.is_symlink():
            return candidate
    return None


def validate_doctor_paths(args: argparse.Namespace, *, artifact_root: Path | None, project_root: Path | None) -> None:
    validate_namespace_paths(
        args,
        field_scopes=DOCTOR_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


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
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--allowed-scope-path", action="append", default=[])
    parser.add_argument("--coverage-profile-file")
    parser.add_argument("--coverage-corpus-file")
    parser.add_argument("--deployment-context", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        output_path = Path(args.output).expanduser()
        project_root = project_root_for_args(args)
        target_contour_root = target_contour_root_for(args)
        artifact_root_for_errors = resolved_path_for_value(args.output).parent
        preflight_block = reject_path_surface(
            args.output,
            field="output",
            scope=ARTIFACT_SCOPE,
            surface_label="output path",
            expected_surface="a direct machine-readable artifact surface",
            stop_at=target_contour_root,
            project_root=project_root,
            artifact_root=artifact_root_for_errors,
        )
        if preflight_block is not None:
            return preflight_block
        if args.update_state and args.state_file:
            preflight_block = reject_path_surface(
                args.state_file,
                field="state_file",
                scope=ARTIFACT_SCOPE,
                surface_label="state update path",
                expected_surface="a direct machine-readable state surface",
                stop_at=target_contour_root,
                project_root=project_root,
                artifact_root=artifact_root_for_errors,
            )
            if preflight_block is not None:
                return preflight_block
        for path_value, field, scope, surface_label, expected_surface in [
            (args.artifact_path, "artifact_path", DUAL_SCOPE, "artifact path", "a direct machine-readable artifact surface"),
            (args.helper_path, "helper_path", PROJECT_SCOPE, "helper entrypoint", "a direct helper surface"),
            (args.prompt_identity_file, "prompt_identity_file", ARTIFACT_SCOPE, "exact prompt identity artifact", "a direct identity surface"),
            (args.target_identity_file, "target_identity_file", DUAL_SCOPE, "target identity artifact", "a direct identity surface"),
            (args.coverage_profile_file, "coverage_profile_file", PROJECT_SCOPE, "coverage profile path", "a direct coverage surface"),
            (args.coverage_corpus_file, "coverage_corpus_file", PROJECT_SCOPE, "coverage corpus path", "a direct coverage surface"),
        ]:
            if not path_value:
                continue
            preflight_block = reject_path_surface(
                path_value,
                field=field,
                scope=scope,
                surface_label=surface_label,
                expected_surface=expected_surface,
                stop_at=target_contour_root,
                project_root=project_root,
                artifact_root=artifact_root_for_errors,
            )
            if preflight_block is not None:
                return preflight_block
        write_violation = path_surface_violation(
            args.output,
            field="output",
            scope=ARTIFACT_SCOPE,
            surface_label="output path",
            expected_surface="a direct machine-readable artifact surface",
            stop_at=target_contour_root,
            project_root=project_root,
            artifact_root=artifact_root_for_errors,
        )
        if write_violation is not None:
            print(json.dumps(write_violation.as_payload(), ensure_ascii=True))
            return 2
        artifact_root = output_path.resolve().parent
        validate_root_within_project(
            "output",
            args.output,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_doctor_paths(args, artifact_root=artifact_root, project_root=project_root)
        record = build_record(args)
        save_json(Path(args.output), record)

        if args.update_state:
            if not args.state_file:
                print(json.dumps({"result": "ERROR", "reason": "STATE_FILE_REQUIRED_FOR_UPDATE"}, ensure_ascii=True))
                return 2
            state_write_violation = path_surface_violation(
                args.state_file,
                field="state_file",
                scope=ARTIFACT_SCOPE,
                surface_label="state update path",
                expected_surface="a direct machine-readable state surface",
                stop_at=target_contour_root,
                project_root=project_root,
                artifact_root=artifact_root,
            )
            if state_write_violation is not None:
                print(json.dumps(state_write_violation.as_payload(), ensure_ascii=True))
                return 2
            state_path = Path(args.state_file)
            state = load_json(state_path)
            save_json(state_path, apply_record_to_state(state, record))

        print(json.dumps({"result": "OK", "final_verdict": record["final_verdict"]}, ensure_ascii=True))
        return 0
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2


if __name__ == "__main__":
    sys.exit(main())
