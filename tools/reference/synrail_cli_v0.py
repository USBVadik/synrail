#!/usr/bin/env python3
"""Minimal terminal-first CLI facade for Synrail v0."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shlex
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

try:
    from .synrail_repair_packet_v0 import build_packet_from_runtime_truth
except ImportError:
    from synrail_repair_packet_v0 import build_packet_from_runtime_truth

try:
    from .synrail_alpha_telemetry_v0 import (
        append_command_event,
        build_command_event,
        default_issue_body_file,
        default_session_replay_file,
        enable_telemetry,
        export_session_replay,
        telemetry_enabled,
    )
except ImportError:
    from synrail_alpha_telemetry_v0 import (
        append_command_event,
        build_command_event,
        default_issue_body_file,
        default_session_replay_file,
        enable_telemetry,
        export_session_replay,
        telemetry_enabled,
    )

try:
    from .synrail_bootstrap_v0 import (
        build_bootstrap_record,
        build_proof_request_record,
        build_proof_starter_contents,
        load_json as load_bootstrap_json,
        save_json as save_bootstrap_json,
        validate_bootstrap_record,
        write_proof_starter_files,
    )
except ImportError:
    from synrail_bootstrap_v0 import (
        build_bootstrap_record,
        build_proof_request_record,
        build_proof_starter_contents,
        load_json as load_bootstrap_json,
        save_json as save_bootstrap_json,
        validate_bootstrap_record,
        write_proof_starter_files,
    )


HERE = Path(__file__).resolve().parent
SPINE = HERE / "synrail_spine_v0.py"
BUNDLE = HERE / "synrail_bundle_v0.py"
CLOSURE = HERE / "synrail_closure_v0.py"
REFRESH = HERE / "synrail_refresh_v0.py"
VALIDATE = HERE / "synrail_validate_v0.py"
DOCTOR = HERE / "synrail_doctor_v1.py"
HARNESS_V0 = HERE / "synrail_baseline_harness_v0.py"
HARNESS_V1 = HERE / "synrail_baseline_harness_v1.py"
HARNESS_V2 = HERE / "synrail_substitute_harness_v0.py"
SUBSTITUTE_PRESSURE = HERE / "synrail_substitute_pressure_v0.py"
HYBRID_STATUS = HERE / "synrail_hybrid_status_v0.py"
MODE_SELECTOR = HERE / "synrail_mode_selector_v0.py"
MODE_RECEIPT = HERE / "synrail_mode_receipt_v0.py"
PROOF_PLAN = HERE / "synrail_proof_plan_v0.py"
PREPARATION_RECEIPT = HERE / "synrail_preparation_receipt_v0.py"
GOVERNED_COST = HERE / "synrail_governed_cost_delta_v0.py"
REPAIR_HANDOFF = HERE / "synrail_repair_handoff_v0.py"
REPAIR_PACKET = HERE / "synrail_repair_packet_v0.py"
CHECKPOINT = HERE / "synrail_checkpoint_v0.py"
ARTIFACT_CONSISTENCY = HERE / "synrail_artifact_consistency_v0.py"
OBSERVABILITY = HERE / "synrail_observability_v0.py"
BUG_PACKET = HERE / "synrail_bug_packet_v0.py"
REPRODUCIBILITY = HERE / "synrail_reproducibility_v0.py"
SECOND_OPERATOR = HERE / "synrail_second_operator_v0.py"
OPERATOR_BRIEF = HERE / "synrail_operator_brief_v0.py"
OPERATOR_BRIEF_CHAIN = HERE / "synrail_operator_brief_chain_v0.py"
OPERATOR_RENDER = HERE / "synrail_operator_render_v0.py"
OPERATOR_RENDER_ADOPTION = HERE / "synrail_operator_render_adoption_v0.py"
OPERATOR_RENDER_ADOPTION_DELTA = HERE / "synrail_operator_render_adoption_delta_v0.py"
OPERATOR_READING = HERE / "synrail_operator_reading_v0.py"
EXTERNALITY_PRESSURE = HERE / "synrail_externality_pressure_v0.py"
THIN_OUTPUT = HERE / "synrail_thin_output_v0.py"
PROMPT_BRIDGE = HERE / "synrail_repair_prompt_bridge_v0.py"
THIN_OUTPUT_READING = HERE / "synrail_thin_output_reading_v0.py"
PROMPT_FOLLOWUP = HERE / "synrail_prompt_followup_v0.py"
PROMPT_RETRY_GUARD = HERE / "synrail_prompt_retry_guard_v0.py"
ACCEPTANCE_CRITERIA = HERE / "synrail_acceptance_criteria_v0.py"
CONSISTENCY_RECOVERY = HERE / "synrail_consistency_recovery_v0.py"
CHECKPOINT_OPERATOR_READING = HERE / "synrail_checkpoint_operator_reading_v0.py"
CONSISTENCY_RECOVERY_PROMPT = HERE / "synrail_consistency_recovery_prompt_v0.py"
CONSISTENCY_RECOVERY_PROMPT_READING = HERE / "synrail_consistency_recovery_prompt_reading_v0.py"
ALPHA_TELEMETRY = HERE / "synrail_alpha_telemetry_v0.py"
REFERENCE_RUNNER_MODULE = "reference_runner"

DEFAULT_ALPHA_ARTIFACT_ROOT = ".synrail"
DEFAULT_ALPHA_TASK_CLASS = "bounded_change"
SUPPORTED_ALPHA_TARGET_CLASSIFICATIONS = {"trusted_worktree", "resume_surface"}
ALPHA_FILE_NAMES = {
    "state": "state.json",
    "project_profile": "project_profile.json",
    "bootstrap": "bootstrap.json",
    "bootstrap_validation": "bootstrap_validation.json",
    "proof_request": "proof_request.json",
    "acceptance_criteria": "acceptance_criteria.json",
    "acceptance_validation": "acceptance_validation.json",
    "doctor": "doctor.json",
    "bundle": "bundle.json",
    "closure": "closure.json",
    "refresh": "refresh.json",
    "report": "report.json",
    "orchestration": "orchestration.json",
    "run": "run.json",
    "repair_packet": "repair_packet.json",
    "repair_handoff": "repair_handoff.json",
    "repair_receipt": "repair_receipt.json",
    "observability": "observability.json",
    "bug_packet": "bug_packet.json",
    "session_export": "session_export.json",
    "artifact_consistency": "artifact_consistency.json",
    "consistency_recovery": "consistency_recovery.json",
    "plan": "plan.json",
    "preparation_receipt": "preparation_receipt.json",
    "selection_receipt": "selection_receipt.json",
    "thin_output": "thin_output.json",
    "prompt": "prompt.json",
    "checkpoint_restore": "checkpoint_restore.json",
    "deploy_receipt": "deploy_receipt.json",
}
CHECKPOINT_RECORD_BASENAME = "checkpoint_record.json"
CHECKPOINT_VERIFY_BASENAME = "checkpoint_verify.json"
PROJECT_PROFILE_BASENAME = "project_profile.json"


def run_python(script: Path, args: list[str]) -> int:
    if __package__:
        cmd = [sys.executable, "-m", REFERENCE_RUNNER_MODULE, script.stem, *args]
    else:
        cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, check=False).returncode


def run_python_capture(script: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    if __package__:
        cmd = [sys.executable, "-m", REFERENCE_RUNNER_MODULE, script.stem, *args]
    else:
        cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, check=False, capture_output=True, text=True)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def comparison_harness_for_inputs(baseline_file: str, synrail_file: str) -> Path:
    baseline = load_json(Path(baseline_file))
    synrail = load_json(Path(synrail_file))
    baseline_version = baseline.get("schema_version", "")
    synrail_version = synrail.get("schema_version", "")

    if baseline_version != synrail_version:
        raise ValueError("comparison input schema versions do not match")

    if baseline_version == "comparison_input_v1":
        return HARNESS_V1
    if baseline_version == "comparison_input_v2":
        return HARNESS_V2

    return HARNESS_V0


def default_alpha_run_id() -> str:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"ALPHA_RUN_{stamp}_{uuid.uuid4().hex[:6]}"


def project_profile_file(root: Path) -> Path:
    return root / PROJECT_PROFILE_BASENAME


def write_acceptance_criteria(root: Path, *, generated_by: str) -> subprocess.CompletedProcess[str]:
    return run_python_capture(
        ACCEPTANCE_CRITERIA,
        [
            "build",
            "--project-profile-file", str(project_profile_file(root)),
            "--generated-by", generated_by,
            "--output", str(alpha_file(root, "acceptance_criteria")),
        ],
    )


def write_acceptance_validation(root: Path, *, criteria_file: Path, state_file: Path) -> subprocess.CompletedProcess[str]:
    return run_python_capture(
        ACCEPTANCE_CRITERIA,
        [
            "validate",
            "--criteria-file", str(criteria_file),
            "--state-file", str(state_file),
            "--project-profile-file", str(project_profile_file(root)),
            "--output", str(alpha_file(root, "acceptance_validation")),
        ],
    )


def save_project_profile(root: Path, payload: dict) -> None:
    save_json(project_profile_file(root), payload)


def save_alpha_identity_files(root: Path, *, task_identity: str = "", prompt_identity: str = "") -> None:
    task_text = (task_identity or "").strip()
    prompt_text = (prompt_identity or "").strip() or task_text
    if task_text:
        (root / "task_identity.txt").write_text(task_text + "\n")
    if prompt_text:
        (root / "prompt_identity.txt").write_text(prompt_text + "\n")


def save_alpha_target_identity_file(root: Path, *, target_identity: str) -> None:
    text = (target_identity or "").strip()
    if text:
        (root / "target_identity.txt").write_text(text + "\n")


def relative_artifact_root_for_project(*, project_root: Path, artifact_root: str) -> str:
    artifact_path = Path(artifact_root)
    if artifact_path.is_absolute():
        try:
            return str(artifact_path.relative_to(project_root))
        except ValueError:
            return str(artifact_path)
    return str(artifact_path)


def render_agent_policy_markdown(*, artifact_root: str) -> str:
    lines = [
        "# Agent Workflow",
        "",
        "This repo uses Synrail to keep one bounded local change inside one controlled run.",
        "",
        "## Before You Edit",
        "",
        "1. Start one controlled run before mutating code:",
        "```bash",
        f'ARTIFACT_ROOT="$(pwd)/{artifact_root}"',
        'synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "Describe the bounded local change."',
        "```",
        "",
        "2. Keep the change local and bounded to the stated task.",
        f"3. Edit the starter proof files under `{artifact_root}/` in place as the work becomes real.",
        "4. Run the local commands needed to verify the change honestly.",
        "",
        "## Before You Claim Success",
        "",
        "```bash",
        'synrail check --artifact-root "$ARTIFACT_ROOT"',
        "```",
        "",
        "If Synrail is non-green, run:",
        "",
        "```bash",
        'synrail repair-step --artifact-root "$ARTIFACT_ROOT"',
        "```",
        "",
        "Then repair only the named gap and re-check.",
        "",
        "## Important",
        "",
        "- Do not skip Synrail and try to legalize edits afterward.",
        "- Do not claim success without real local verification.",
        "- If `synrail` is unavailable on this machine, stop and report that the control tool is missing instead of bypassing it.",
        "",
    ]
    return "\n".join(lines)


def render_gemini_policy_markdown(*, artifact_root: str) -> str:
    lines = [
        "# Gemini Workflow",
        "",
        "Use Synrail as the default local control path for this repo.",
        "",
        "## Start",
        "",
        "Before editing code, start one controlled run:",
        "",
        "```bash",
        f'ARTIFACT_ROOT="$(pwd)/{artifact_root}"',
        'synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "Describe the bounded local change."',
        "```",
        "",
        "## Work",
        "",
        f"- Keep edits bounded and local to this repo.",
        f"- Update the starter proof files in `{artifact_root}/` as the change becomes real.",
        "- Run the local verification commands needed for the task.",
        "",
        "## Finish",
        "",
        "```bash",
        'synrail check --artifact-root "$ARTIFACT_ROOT"',
        "```",
        "",
        "If non-green, run `synrail repair-step --artifact-root \"$ARTIFACT_ROOT\"`, repair only the named gap, and re-check.",
        "",
        "Do not bypass Synrail and do not claim success without real local verification.",
        "",
    ]
    return "\n".join(lines)


def render_agent_policy_block(*, title: str, intro: str, artifact_root: str) -> str:
    lines = [
        f"## {title}",
        "",
        intro,
        "",
        "```bash",
        f'ARTIFACT_ROOT="$(pwd)/{artifact_root}"',
        'synrail start --artifact-root "$ARTIFACT_ROOT" --project-root "$(pwd)" --task-identity "Describe the bounded local change."',
        "```",
        "",
        "Before claiming success, run:",
        "",
        "```bash",
        'synrail check --artifact-root "$ARTIFACT_ROOT"',
        "```",
        "",
        'If non-green, run `synrail repair-step --artifact-root "$ARTIFACT_ROOT"` and repair only the named gap before re-checking.',
        "",
        "Do not bypass Synrail and do not claim success without real local verification.",
    ]
    return "\n".join(lines)


def managed_policy_markers(path: Path) -> tuple[str, str]:
    stem = path.stem.upper().replace(".", "_")
    return (f"<!-- SYNRAIL_{stem}_START -->", f"<!-- SYNRAIL_{stem}_END -->")


def wrap_managed_policy_block(path: Path, body: str) -> str:
    start_marker, end_marker = managed_policy_markers(path)
    return f"{start_marker}\n{body.rstrip()}\n{end_marker}\n"


def upsert_managed_policy_block(current: str, *, path: Path, block: str) -> tuple[str, str]:
    start_marker, end_marker = managed_policy_markers(path)
    current_text = current or ""
    managed_block = wrap_managed_policy_block(path, block)
    if start_marker in current_text and end_marker in current_text:
        prefix, rest = current_text.split(start_marker, 1)
        _, suffix = rest.split(end_marker, 1)
        updated = prefix.rstrip() + "\n\n" + managed_block + suffix.lstrip("\n")
        state = "updated"
    elif current_text.strip():
        updated = current_text.rstrip() + "\n\n" + managed_block
        state = "appended"
    else:
        updated = managed_block
        state = "written"
    if updated == current_text:
        return current_text, "unchanged"
    return updated, state


def backup_existing_policy_file(path: Path) -> Path:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = path.with_name(f"{path.name}.synrail.bak.{timestamp}")
    backup_path.write_text(path.read_text())
    return backup_path


def write_agent_policy_file(
    path: Path,
    full_content: str,
    *,
    managed_block: str,
    force: bool,
) -> tuple[bool, str, Path | None]:
    if path.exists():
        current = path.read_text()
        if current == full_content:
            return False, "unchanged", None
        if force:
            backup_path = backup_existing_policy_file(path)
            path.write_text(full_content)
            return True, "written", backup_path
        updated, state = upsert_managed_policy_block(current, path=path, block=managed_block)
        if state == "unchanged":
            return False, state, None
        path.write_text(updated)
        return True, state, None
    path.write_text(full_content)
    return True, "written", None


def cmd_install_agent_files(args: argparse.Namespace) -> int:
    project_root = Path(args.project_root or ".").resolve()
    artifact_root = relative_artifact_root_for_project(
        project_root=project_root,
        artifact_root=args.artifact_root,
    )
    agents_path = project_root / "AGENTS.md"
    gemini_path = project_root / "GEMINI.md"

    agents_content = render_agent_policy_markdown(artifact_root=artifact_root)
    gemini_content = render_gemini_policy_markdown(artifact_root=artifact_root)
    agents_block = render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="This repo uses Synrail to keep one bounded local change inside one controlled run.",
        artifact_root=artifact_root,
    )
    gemini_block = render_agent_policy_block(
        title="Synrail Local Workflow",
        intro="Use Synrail as the default local control path for this repo.",
        artifact_root=artifact_root,
    )

    agents_written, agents_state, agents_backup = write_agent_policy_file(
        agents_path,
        agents_content,
        managed_block=agents_block,
        force=args.force,
    )
    gemini_written, gemini_state, gemini_backup = write_agent_policy_file(
        gemini_path,
        gemini_content,
        managed_block=gemini_block,
        force=args.force,
    )

    print("Agent adoption files are ready.")
    print(f"Project root: {project_root}")
    print(f"Artifact root hint: {artifact_root}")
    print(f"AGENTS.md: {agents_state}")
    print(f"GEMINI.md: {gemini_state}")
    if agents_backup:
        print(f"AGENTS.md backup: {agents_backup}")
    if gemini_backup:
        print(f"GEMINI.md backup: {gemini_backup}")
    if agents_state in {"appended", "updated"} or gemini_state in {"appended", "updated"}:
        print("What to do next: review the managed Synrail block added to the existing agent file and commit it if the wording fits the repo.")
    elif agents_written or gemini_written:
        print("What to do next: commit these files into the repo so local agents discover Synrail before editing.")
    else:
        print("What to do next: keep these files committed so local agents continue discovering the same Synrail entrypoint.")
    return 0


def load_text_if_exists(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text().strip()


def expected_target_identity_for_root(root: Path) -> str:
    target_identity = load_text_if_exists(root / "target_identity.txt")
    if target_identity:
        return target_identity
    bootstrap_file = alpha_file(root, "bootstrap")
    if bootstrap_file.exists():
        bootstrap = load_bootstrap_json(bootstrap_file)
        for field in ["target_identity", "execution_surface_identity"]:
            value = (bootstrap.get(field, "") or "").strip()
            if value:
                return value
    profile = load_project_profile(root) or {}
    return (profile.get("execution_surface_identity", "") or "").strip()


def load_project_profile(root: Path | None) -> dict | None:
    if not root:
        return None
    profile_path = project_profile_file(root)
    if not profile_path.exists():
        return None
    return load_json(profile_path)


def detect_project_type(project_root: Path) -> str:
    markers = [
        ("package.json", "node"),
        ("pyproject.toml", "python"),
        ("setup.py", "python"),
        ("setup.cfg", "python"),
        ("requirements.txt", "python"),
        ("go.mod", "go"),
        ("Cargo.toml", "rust"),
        ("Gemfile", "ruby"),
        ("composer.json", "php"),
    ]
    for marker, project_type in markers:
        if (project_root / marker).exists():
            return project_type
    return "generic"


def candidate_paths(project_root: Path, root: Path, names: list[str]) -> list[str]:
    ordered: list[Path] = []
    for base in [root, project_root]:
        for name in names:
            candidate = (base / name).resolve()
            if candidate not in ordered:
                ordered.append(candidate)
    return [str(path) for path in ordered]


def build_project_profile(*, project_root: Path, root: Path, task_class: str) -> dict:
    project_type = detect_project_type(project_root)
    return {
        "schema_version": "alpha_project_profile_v0",
        "project_root": str(project_root),
        "project_type": project_type,
        "task_class": task_class,
        "target_path": str(project_root),
        "target_classification": "trusted_worktree",
        "intended_run_class": "core_probe",
        "baseline_identity": f"autodetected_{project_type}_baseline",
        "execution_surface_identity": f"autodetected_{project_type}_worktree",
        "artifact_path": str((root / "final_result.json").resolve()),
        "final_result_candidates": candidate_paths(project_root, root, ["final_result.json", "final_result.txt", "result.json", "result.txt"]),
        "readback_candidates": candidate_paths(project_root, root, ["readback.json", "readback.txt"]),
        "scenario_proof_candidates": candidate_paths(project_root, root, ["scenario_proof.json", "scenario_proof.md", "scenario_proof.txt"]),
    }


def discover_candidate_file(candidates: list[str]) -> str | None:
    return discover_candidate_file_filtered(candidates, ignored_paths=set())


def discover_candidate_file_filtered(candidates: list[str], *, ignored_paths: set[Path]) -> str | None:
    for value in candidates:
        candidate = Path(value)
        if candidate.exists() and candidate.is_file() and candidate.resolve() not in ignored_paths:
            return str(candidate)
    return None


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        return str(resolved)
    text = str(relative)
    return text or "."


def display_path_from_base(path: Path, *, base: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(base.resolve())
    except ValueError:
        return str(resolved)
    text = str(relative)
    return text or "."


def shell_command(root: Path, *parts: str) -> str:
    return " ".join(shlex.quote(part) for part in ["synrail", *parts, "--artifact-root", display_path(root)])


def preferred_proof_paths(root: Path, *, project_root: Path) -> dict[str, str]:
    payload = build_proof_request_record(
        run_id="PROOF_REQUEST_PREVIEW",
        task_class=DEFAULT_ALPHA_TASK_CLASS,
        task_identity="proof request preview",
        project_root=project_root,
        artifact_root=root,
    )
    return dict(payload["preferred_artifacts"])


def preferred_proof_artifact_paths(root: Path) -> dict[str, Path]:
    return {
        "final_result": root / "final_result.json",
        "readback": root / "readback.txt",
        "scenario_proof": root / "scenario_proof.txt",
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def untouched_preferred_proof_paths(root: Path | None) -> set[Path]:
    if not root:
        return set()
    proof_request_file = alpha_file(root, "proof_request")
    if not proof_request_file.exists():
        return set()
    proof_request = load_bootstrap_json(proof_request_file)
    starter_hashes = proof_request.get("starter_hashes", {})
    if not isinstance(starter_hashes, dict):
        return set()
    untouched: set[Path] = set()
    for artifact_id, path in preferred_proof_artifact_paths(root).items():
        expected_hash = starter_hashes.get(artifact_id, "")
        if expected_hash and path.exists() and path.is_file() and file_sha256(path) == expected_hash:
            untouched.add(path.resolve())
    return untouched


def unsupported_remote_target_reason(*, target_path: str, target_classification: str) -> str:
    classification = (target_classification or "").strip()
    path = (target_path or "").strip()
    if classification and classification not in SUPPORTED_ALPHA_TARGET_CLASSIFICATIONS:
        return "REMOTE_TARGET_UNSUPPORTED"
    if "://" in path:
        return "REMOTE_TARGET_UNSUPPORTED"
    if "@" in path and ":" in path and not path.startswith("/"):
        return "REMOTE_TARGET_UNSUPPORTED"
    return ""


def command_path_from_args(args: argparse.Namespace) -> list[str]:
    path = [args.cmd]
    if args.cmd == "checkpoint" and getattr(args, "checkpoint_cmd", None):
        path.append(args.checkpoint_cmd)
    if args.cmd == "telemetry" and getattr(args, "telemetry_cmd", None):
        path.append(args.telemetry_cmd)
    return path


def telemetry_flag_names(argv: list[str]) -> list[str]:
    return [token.split("=", 1)[0] for token in argv if token.startswith("--")]


def should_capture_alpha_telemetry(args: argparse.Namespace) -> bool:
    path = command_path_from_args(args)
    return path[0] in {"init", "start", "check", "refresh-acceptance", "generate-prompt", "next-step", "repair-step", "restore", "resume", "continue", "checkpoint", "session-export", "bug-packet"}


def maybe_capture_alpha_telemetry(
    args: argparse.Namespace,
    *,
    exit_code: int,
    explicit_error_class: str = "",
) -> None:
    if not should_capture_alpha_telemetry(args):
        return
    root = alpha_root_from_args(args)
    if not root or not telemetry_enabled(root):
        return
    event = build_command_event(
        root,
        command_path=command_path_from_args(args),
        flag_names=telemetry_flag_names(sys.argv[1:]),
        exit_code=exit_code,
        explicit_error_class=explicit_error_class,
    )
    append_command_event(root, event)


def alpha_root_from_args(args: argparse.Namespace, *, ensure: bool = False) -> Path | None:
    value = getattr(args, "artifact_root", None)
    if not value:
        return None
    root = Path(value).expanduser().resolve()
    if ensure:
        root.mkdir(parents=True, exist_ok=True)
    return root


def alpha_file(root: Path, file_id: str) -> Path:
    return root / ALPHA_FILE_NAMES[file_id]


def maybe_existing_alpha_file(root: Path | None, file_id: str) -> str | None:
    if not root:
        return None
    candidate = alpha_file(root, file_id)
    if candidate.exists():
        return str(candidate)
    return None


def apply_alpha_profile_defaults(args: argparse.Namespace, *, root: Path | None) -> None:
    profile = load_project_profile(root)
    if not profile:
        return
    ignored_paths = untouched_preferred_proof_paths(root)
    profile_artifact_path = profile.get("artifact_path", "")
    for field in [
        "target_path",
        "target_classification",
        "baseline_identity",
        "execution_surface_identity",
        "artifact_path",
        "intended_run_class",
    ]:
        if not getattr(args, field, None):
            value = profile.get(field)
            if value:
                setattr(args, field, value)
    if not getattr(args, "final_result", None):
        discovered = discover_candidate_file_filtered(list(profile.get("final_result_candidates", [])), ignored_paths=ignored_paths)
        if discovered:
            args.final_result = discovered
            current_artifact_path = getattr(args, "artifact_path", None)
            if (
                not current_artifact_path
                or (
                    root is not None
                    and current_artifact_path == profile_artifact_path
                    and Path(current_artifact_path).resolve() == (root / "final_result.json").resolve()
                )
            ):
                args.artifact_path = discovered
                if root is not None and profile.get("artifact_path", "") != discovered:
                    profile["artifact_path"] = discovered
                    save_project_profile(root, profile)
    if not getattr(args, "readback", None):
        discovered = discover_candidate_file_filtered(list(profile.get("readback_candidates", [])), ignored_paths=ignored_paths)
        if discovered:
            args.readback = discovered
    if not getattr(args, "scenario_proof", None):
        discovered = discover_candidate_file_filtered(list(profile.get("scenario_proof_candidates", [])), ignored_paths=ignored_paths)
        if discovered:
            args.scenario_proof = discovered


def checkpoint_root(root: Path, checkpoint_id: str) -> Path:
    return root / "checkpoints" / checkpoint_id


def checkpoint_record_file(root: Path, checkpoint_id: str) -> Path:
    return checkpoint_root(root, checkpoint_id) / CHECKPOINT_RECORD_BASENAME


def checkpoint_verify_file(root: Path, checkpoint_id: str) -> Path:
    return checkpoint_root(root, checkpoint_id) / CHECKPOINT_VERIFY_BASENAME


def discover_checkpoint_record(root: Path, checkpoint_id: str | None) -> str | None:
    checkpoints_root = root / "checkpoints"
    if checkpoint_id:
        verified = checkpoint_verify_file(root, checkpoint_id)
        if verified.exists():
            return str(verified)
        created = checkpoint_record_file(root, checkpoint_id)
        if created.exists():
            return str(created)
        return None
    if not checkpoints_root.exists():
        return None
    working_verified = checkpoint_verify_file(root, "working")
    if working_verified.exists():
        return str(working_verified)
    working_created = checkpoint_record_file(root, "working")
    if working_created.exists():
        return str(working_created)
    verified_candidates = sorted(
        list(checkpoints_root.glob("*/checkpoint_verify.json")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if verified_candidates:
        return str(verified_candidates[0])
    created_candidates = sorted(
        list(checkpoints_root.glob("*/checkpoint_record.json")),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not created_candidates:
        return None
    return str(created_candidates[0])


def apply_alpha_runtime_file_defaults(args: argparse.Namespace) -> None:
    root = alpha_root_from_args(args, ensure=True)
    if not root:
        return

    def existing_alpha_variant(*names: str) -> Path | None:
        for name in names:
            candidate = root / name
            if candidate.exists():
                return candidate
        return None

    if not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    for attr, file_id in [
        ("doctor_output", "doctor"),
        ("bundle_output", "bundle"),
        ("closure_output", "closure"),
        ("refresh_output", "refresh"),
        ("report_output", "report"),
        ("worked_artifact_output", "orchestration"),
        ("run_artifact_output", "run"),
        ("repair_packet_output", "repair_packet"),
        ("repair_handoff_output", "repair_handoff"),
        ("repair_receipt_output", "repair_receipt"),
        ("acceptance_validation_output", "acceptance_validation"),
        ("observability_output", "observability"),
        ("artifact_consistency_output", "artifact_consistency"),
        ("plan_output", "plan"),
        ("preparation_receipt_output", "preparation_receipt"),
    ]:
        if not getattr(args, attr, None):
            setattr(args, attr, str(alpha_file(root, file_id)))
    if not getattr(args, "repair_packet_file", None):
        existing = maybe_existing_alpha_file(root, "repair_packet")
        if existing:
            args.repair_packet_file = existing
    if not getattr(args, "acceptance_criteria_file", None):
        existing = maybe_existing_alpha_file(root, "acceptance_criteria")
        if existing:
            args.acceptance_criteria_file = existing
    if not getattr(args, "project_profile_file", None):
        profile = project_profile_file(root)
        if profile.exists():
            args.project_profile_file = str(profile)
    if not getattr(args, "prompt_identity_file", None):
        candidate = existing_alpha_variant("prompt_identity.txt")
        if candidate:
            args.prompt_identity_file = str(candidate)
    if not getattr(args, "target_identity_file", None):
        candidate = existing_alpha_variant("target_identity.txt")
        if candidate:
            args.target_identity_file = str(candidate)
    if not getattr(args, "prompt_identity", None):
        candidate = existing_alpha_variant("prompt_identity.txt")
        if candidate:
            args.prompt_identity = candidate.read_text().strip()
    if not getattr(args, "task_identity", None):
        candidate = existing_alpha_variant("task_identity.txt")
        if candidate:
            args.task_identity = candidate.read_text().strip()


def write_controlled_start_artifacts(
    root: Path,
    *,
    project_root: Path,
    run_id: str,
    task_class: str,
    task_identity: str,
    prompt_identity: str,
    profile: dict,
    started_via: str,
) -> None:
    starter_contents = build_proof_starter_contents(
        run_id=run_id,
        task_class=task_class,
        task_identity=task_identity,
    )
    proof_request = build_proof_request_record(
        run_id=run_id,
        task_class=task_class,
        task_identity=task_identity,
        project_root=project_root,
        artifact_root=root,
    )
    write_proof_starter_files(artifact_root=root, starter_contents=starter_contents)
    save_alpha_target_identity_file(root, target_identity=profile["execution_surface_identity"])
    bootstrap = build_bootstrap_record(
        run_id=run_id,
        task_class=task_class,
        started_via=started_via,
        project_root=project_root,
        artifact_root=root,
        task_identity=task_identity,
        prompt_identity=prompt_identity,
        target_path=profile["target_path"],
        target_classification=profile["target_classification"],
        target_identity=profile["execution_surface_identity"],
        baseline_identity=profile["baseline_identity"],
        execution_surface_identity=profile["execution_surface_identity"],
        intended_run_class=profile["intended_run_class"],
        intended_proof_path=dict(proof_request["preferred_artifacts"]),
    )
    save_bootstrap_json(alpha_file(root, "bootstrap"), bootstrap)
    save_bootstrap_json(alpha_file(root, "proof_request"), proof_request)


def resolve_start_identities(args: argparse.Namespace, *, root: Path) -> tuple[str, str]:
    task_identity = (getattr(args, "task_identity", "") or "").strip()
    prompt_identity = (getattr(args, "prompt_identity", "") or "").strip()
    if not task_identity:
        task_identity = load_text_if_exists(root / "task_identity.txt")
    if not prompt_identity:
        prompt_identity = load_text_if_exists(root / "prompt_identity.txt")
    if not prompt_identity:
        prompt_identity = task_identity
    return task_identity, prompt_identity


def existing_preferred_proof_artifacts(root: Path) -> list[str]:
    discovered: list[str] = []
    untouched = untouched_preferred_proof_paths(root)
    for artifact_id, path in preferred_proof_artifact_paths(root).items():
        if path.exists() and path.resolve() not in untouched:
            discovered.append(f"{artifact_id}:{display_path(path)}")
    return discovered


def clear_runtime_artifacts_for_start(root: Path) -> None:
    keep = {
        "state",
        "project_profile",
        "bootstrap",
        "bootstrap_validation",
        "proof_request",
        "acceptance_criteria",
    }
    for file_id, name in ALPHA_FILE_NAMES.items():
        if file_id in keep:
            continue
        (root / name).unlink(missing_ok=True)


def apply_bootstrap_defaults(args: argparse.Namespace, *, root: Path | None) -> dict | None:
    if not root:
        return None
    state_file = Path(getattr(args, "state_file", "") or alpha_file(root, "state"))
    profile = load_project_profile(root)
    if not state_file.exists() or not profile:
        return None
    bootstrap_path = alpha_file(root, "bootstrap")
    record = load_bootstrap_json(bootstrap_path) if bootstrap_path.exists() else None
    validation = validate_bootstrap_record(record, state=load_json(state_file), profile=profile, artifact_root=root)
    save_bootstrap_json(alpha_file(root, "bootstrap_validation"), validation)
    args.bootstrap_provenance_ok = validation["status"] == "VALID"
    args.bootstrap_provenance_reason = validation["reason"]
    if record and validation["status"] == "VALID":
        bootstrap_defaults = {
            "task_identity": record.get("task_identity", ""),
            "prompt_identity": record.get("prompt_identity", ""),
            "target_path": record.get("target_path", ""),
            "target_classification": record.get("target_classification", ""),
            "baseline_identity": record.get("baseline_identity", ""),
            "execution_surface_identity": record.get("execution_surface_identity", ""),
            "intended_run_class": record.get("intended_run_class", ""),
        }
        for field, value in bootstrap_defaults.items():
            if value and not getattr(args, field, None):
                setattr(args, field, value)
        if not getattr(args, "target_identity_file", None):
            candidate = root / "target_identity.txt"
            if candidate.exists():
                args.target_identity_file = str(candidate)
    return validation


def write_bootstrap_required_block(*, args: argparse.Namespace, root: Path, validation: dict) -> int:
    state_path = Path(args.state_file)
    state = load_json(state_path)
    task_identity = (getattr(args, "task_identity", "") or "").strip() or load_text_if_exists(root / "task_identity.txt")
    prompt_identity = (getattr(args, "prompt_identity", "") or "").strip() or load_text_if_exists(root / "prompt_identity.txt")
    state["integrity"]["status"] = "FAIL"
    state["integrity"]["exact_task_identity_ok"] = bool(task_identity and prompt_identity)
    state["integrity"]["bootstrap_provenance_ok"] = False
    state["integrity"]["bootstrap_provenance_reason"] = validation["reason"]
    state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
    state["closure"]["blocking_reason"] = "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"
    state["closure"]["next_allowed_transition"] = "CONTROLLED_START"
    state["closure"]["narrow_next_safe_step"] = "start the run in controlled mode before trusting any proof or acceptance"
    state["closure"]["missing_sections"] = []
    state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
    save_json(state_path, state)
    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "BLOCKED",
        "stopping_stage": "bootstrap",
        "reason": "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED",
        "doctor_verdict": "",
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
        "bundle_status": state["proof_bundle"]["status"],
        "closure_status": state["closure"]["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "repair_termination_status": "",
        "repair_termination_reason": "",
        "repair_attempt_count": 0,
        "repair_max_attempts": 0,
        "repair_no_progress_window": 0,
        "repair_stalled_step_id": "",
        "blockers": ["CONTROLLED_BOOTSTRAP_NOT_CONFIRMED"],
        "dominant_blocker": "CONTROLLED_BOOTSTRAP_NOT_CONFIRMED",
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }
    save_json(Path(args.report_file), report)
    args._suppress_summary = True
    thin_code = cmd_thin_output(args)
    if thin_code == 0 and args.mode == "default":
        print_thin_output_summary(Path(args.output))
    return thin_code


def write_remote_unsupported_block(*, args: argparse.Namespace, root: Path) -> int:
    state_path = Path(args.state_file)
    state = load_json(state_path)
    state["closure"]["status"] = "CLAIMED_NOT_ACCEPTED"
    state["closure"]["blocking_reason"] = "REMOTE_TARGET_UNSUPPORTED"
    state["closure"]["next_allowed_transition"] = "LOCAL_TRUSTED_WORKTREE_START"
    state["closure"]["narrow_next_safe_step"] = "rerun this alpha lane on a local trusted worktree; the remote or ops lane is not supported yet"
    state["closure"]["missing_sections"] = []
    state["next_safe_step"] = state["closure"]["narrow_next_safe_step"]
    save_json(state_path, state)
    report = {
        "schema_version": "orchestration_report_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "result": "BLOCKED",
        "stopping_stage": "target_support",
        "reason": "REMOTE_TARGET_UNSUPPORTED",
        "doctor_verdict": "",
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
        "bundle_status": state["proof_bundle"]["status"],
        "closure_status": state["closure"]["status"],
        "refresh_applied": False,
        "refresh_resulting_closure_status": "",
        "comparison_applied": False,
        "comparison_verdict": "",
        "repair_termination_status": "",
        "repair_termination_reason": "",
        "repair_attempt_count": 0,
        "repair_max_attempts": 0,
        "repair_no_progress_window": 0,
        "repair_stalled_step_id": "",
        "blockers": ["REMOTE_TARGET_UNSUPPORTED"],
        "dominant_blocker": "REMOTE_TARGET_UNSUPPORTED",
        "resulting_state": state["state"],
        "next_safe_step": state["next_safe_step"],
    }
    save_json(Path(args.report_file), report)
    args._suppress_summary = True
    thin_code = cmd_thin_output(args)
    if thin_code == 0 and args.mode == "default":
        print_thin_output_summary(Path(args.output))
    return thin_code


def sync_restored_checkpoint_artifacts(target_root: Path) -> list[str]:
    restored_root = target_root / "artifacts"
    if not restored_root.exists():
        return []
    synced: list[str] = []
    for artifact in sorted(restored_root.glob("*.json")):
        destination = target_root / artifact.name
        shutil.copy2(artifact, destination)
        synced.append(destination.name)
    return synced


def print_thin_output_summary(output_file: Path) -> None:
    if not output_file.exists():
        return
    payload = load_json(output_file)
    lines = [
        f"Status: {payload.get('status_label', payload.get('outcome_class', ''))}",
    ]
    action_now = payload.get("action_now", "")
    if action_now:
        lines.append(f"Do this now: {action_now}")
    lines.extend([
        f"What happened: {payload.get('what_happened', payload.get('summary', ''))}",
        f"What it means: {payload.get('what_it_means', payload.get('diagnosis', ''))}",
        f"What to do next: {payload.get('what_to_do_next', payload.get('next_step', ''))}",
    ])
    focused_repair_summary = payload.get("focused_repair_summary", "")
    if focused_repair_summary:
        lines.append(f"Repair target: {focused_repair_summary}")
    thin_sections = list(payload.get("thin_section_guidance", []))
    if thin_sections:
        lines.append("Thin proof sections:")
        lines.extend([f"- {item}" for item in thin_sections])
    next_command = payload.get("next_command", "")
    restore_command = payload.get("restore_command", "")
    if next_command:
        lines.append(f"Next command: {next_command}")
    elif payload.get("suggested_command", "") and payload.get("suggested_command", "") != "no next command required":
        lines.append(f"Suggested path: {payload.get('suggested_command', '')}")
    if restore_command:
        lines.append(f"Restore option: {restore_command}")
    print("\n".join(line for line in lines if line))


def print_prompt_summary(output_file: Path) -> None:
    print_prompt_summary_compact(output_file, include_prompt=True)


def print_prompt_summary_compact(output_file: Path, *, include_prompt: bool = False) -> None:
    if not output_file.exists():
        return
    payload = load_json(output_file)
    stale_artifacts = list(payload.get("stale_artifact_ids", []))
    stale_subsurfaces = list(payload.get("stale_subsurface_ids", []))
    allowed_scope = list(payload.get("allowed_scope", []))
    allowed_scope_labels = list(payload.get("allowed_scope_labels", []))
    required_input_labels = list(payload.get("required_input_labels", []))
    forbidden_scope = list(payload.get("forbidden_scope", []))
    lines = [
        "The next bounded repair instruction is ready.",
        (
            f"Do this now: {payload.get('current_step_action_instruction', '')}"
            if payload.get("current_step_action_instruction", "")
            else "Do this now: keep the repair inside the current bounded repair surface."
        ),
        f"What failed: {payload.get('failure_label', payload.get('failure_reason', ''))}",
        f"Current repair task: {payload.get('current_step_label', payload.get('current_step_id', ''))}",
        f"Stale artifacts: {', '.join(stale_artifacts) if stale_artifacts else 'none'}",
        f"Stale subsurfaces: {', '.join(stale_subsurfaces) if stale_subsurfaces else 'none'}",
        f"Allowed scope: {', '.join(allowed_scope_labels) if allowed_scope_labels else (', '.join(allowed_scope) if allowed_scope else 'current repair step only')}",
        f"Required inputs: {', '.join(required_input_labels) if required_input_labels else 'none'}",
        f"Do not touch: {', '.join(forbidden_scope) if forbidden_scope else 'unrelated files or acceptance logic'}",
    ]
    current_step_focus_summary = payload.get("current_step_focus_summary", "")
    if current_step_focus_summary:
        lines.append(f"Repair target: {current_step_focus_summary}")
    current_step_target_path = payload.get("current_step_target_path", "")
    if current_step_target_path:
        lines.append(f"Edit in place: {current_step_target_path}")
    acceptance = payload.get("acceptance_criteria", [])
    if acceptance:
        lines.append("Must pass:")
        lines.extend([f"- {item}" for item in acceptance])
    next_command = payload.get("next_command", "")
    if next_command:
        lines.append(f"After this repair, run: {next_command}")
    prompt = payload.get("prompt", "")
    if include_prompt and prompt:
        lines.append("")
        lines.append("Prompt for the next agent attempt:")
        lines.append(prompt)
    print("\n".join(line for line in lines if line))


def print_init_summary(*, root: Path, state_file: Path) -> None:
    state = load_json(state_file)
    profile = load_project_profile(root) or {}
    lines = [
        "Synrail setup is ready.",
        f"Artifact root: {display_path(root)}",
        f"Detected project type: {profile.get('project_type', 'generic')}",
        "This setup is not a controlled run yet.",
        "Next command: " + shell_command(root, "start"),
    ]
    checkpoint_suggestion = shell_command(root, "save")
    lines.append(f"Optional safety fallback: {checkpoint_suggestion}")
    print("\n".join(lines))


def print_start_summary(*, root: Path, state_file: Path, project_root: Path) -> None:
    state = load_json(state_file)
    proof_request = load_bootstrap_json(alpha_file(root, "proof_request"))
    preferred = proof_request.get("preferred_artifacts", {})
    lines = [
        "Controlled run started.",
        "Do this now: Edit only the starter proof files below in place. Leave every other surface unchanged.",
        f"Artifact root: {display_path(root)}",
        f"Run id: {state.get('run_id', '')}",
        "Starter proof files are ready for this run.",
        f"- final result: {preferred.get('final_result', display_path_from_base(root / 'final_result.json', base=project_root))}",
        f"- readback: {preferred.get('readback', display_path_from_base(root / 'readback.txt', base=project_root))}",
        f"- scenario proof: {preferred.get('scenario_proof', display_path_from_base(root / 'scenario_proof.txt', base=project_root))}",
        "Then run: " + shell_command(root, "check"),
        "Optional safety fallback: " + shell_command(root, "save"),
    ]
    print("\n".join(lines))


def print_acceptance_refresh_summary(*, root: Path) -> None:
    criteria = load_json(alpha_file(root, "acceptance_criteria"))
    lines = [
        "Acceptance rules refreshed.",
        "Revision: " + criteria.get("criteria_revision_id", ""),
    ]
    validation_file = alpha_file(root, "acceptance_validation")
    if validation_file.exists():
        validation = load_json(validation_file)
        lines.append("Validation: " + validation.get("status", ""))
        if validation.get("reason", "") and validation.get("reason", "") != "CRITERIA_VALID":
            lines.append("Why: " + validation.get("reason", ""))
    lines.append("Next command: " + shell_command(root, "check"))
    print("\n".join(lines))


def human_safe_point_class(value: str) -> str:
    mapping = {
        "VERIFIED_WORKING_STATE": "Verified working state",
        "VERIFIED_ACCEPTED_STATE": "Verified accepted state",
        "NOT_SAFE_POINT": "Not a verified restore point",
    }
    return mapping.get(value, value)


def print_checkpoint_summary(record_file: Path, *, action: str, root: Path | None = None) -> None:
    if not record_file.exists():
        return
    payload = load_json(record_file)

    def human_checkpoint_step(text: str) -> str:
        mapping = {
            "checkpoint verified; restore is now allowed": "This restore point is ready. You can use synrail restore if you need it.",
            "inspect or continue from the restored checkpoint state": "Inspect the restored state or continue from it.",
        }
        return mapping.get(text, text)

    lines = []
    if action == "create":
        lines = [
            f"Fallback saved: {payload.get('checkpoint_id', '')}",
            f"Fallback type: {human_safe_point_class(payload.get('safe_point_class', ''))}",
            "What to do next: confirm this fallback only if you want to re-check it explicitly before restore.",
            "Next command: " + (
                shell_command(root, "confirm-restore")
                if root
                else payload.get("next_safe_step", "")
            ),
        ]
    elif action == "verify":
        lines = [
            f"Restore point confirmation: {payload.get('verification', {}).get('status', '')}",
            human_checkpoint_step(payload.get("next_safe_step", "")),
        ]
    elif action == "restore":
        restore = payload.get("restore", {})
        rollback = payload.get("rollback", {})
        lines = [
            f"Restore result: {restore.get('status', '')}",
            human_checkpoint_step(payload.get("next_safe_step", "")),
        ]
        if rollback.get("status", "") == "ROLLED_BACK":
            lines.append("Restore rollback was applied because verification failed.")
    print("\n".join(line for line in lines if line))


def print_save_summary(record_file: Path, verify_file: Path, *, root: Path | None = None) -> None:
    if not verify_file.exists():
        print_checkpoint_summary(record_file, action="create", root=root)
        return
    record = load_json(record_file) if record_file.exists() else {}
    verify = load_json(verify_file)
    verification = verify.get("verification", {})
    lines = [
        f"Fallback ready: {verify.get('checkpoint_id', record.get('checkpoint_id', ''))}",
        f"Fallback type: {human_safe_point_class(record.get('safe_point_class', verify.get('safe_point_class', '')))}",
    ]
    if verification.get("status") == "PASSED":
        lines.extend(
            [
                "What it means: You now have a trusted fallback if this run goes non-green.",
                "What to do next: continue the current workflow. Restore is ready if you need it.",
            ]
        )
        if root:
            lines.append("Restore command: " + shell_command(root, "restore"))
    else:
        lines.extend(
            [
                "What happened: Synrail saved the restore point but could not fully confirm it yet.",
                "What to do next: inspect the save and rerun restore-point confirmation before depending on restore.",
            ]
        )
        if root:
            lines.append("Next command: " + shell_command(root, "confirm-restore"))
    print("\n".join(line for line in lines if line))


def cmd_status(args: argparse.Namespace) -> int:
    state = load_json(Path(args.state_file))
    summary = {
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "state": state["state"],
        "target_surface": state["target_surface"]["status"],
        "doctor": state["doctor"]["status"],
        "proof_bundle": state["proof_bundle"]["status"],
        "closure": state["closure"]["status"],
        "next_safe_step": state["next_safe_step"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=True))
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    project_root = Path(getattr(args, "project_root", "") or Path.cwd()).resolve()
    if not getattr(args, "run_id", None):
        args.run_id = default_alpha_run_id()
    if not getattr(args, "task_class", None):
        args.task_class = DEFAULT_ALPHA_TASK_CLASS
    if not getattr(args, "output", None):
        if not root:
            raise ValueError("output or artifact root is required")
        args.output = str(alpha_file(root, "state"))
    forwarded = [
        "init",
        "--run-id", args.run_id,
        "--task-class", args.task_class,
        "--output", args.output,
    ]
    if args.mode == "dev":
        code = run_python(SPINE, forwarded)
        if code == 0 and root:
            save_project_profile(root, build_project_profile(project_root=project_root, root=root, task_class=args.task_class))
            save_alpha_identity_files(
                root,
                task_identity=getattr(args, "task_identity", ""),
                prompt_identity=getattr(args, "prompt_identity", ""),
            )
            criteria_completed = write_acceptance_criteria(root, generated_by="synrail init")
            if criteria_completed.returncode != 0:
                return criteria_completed.returncode
        return code
    completed = run_python_capture(SPINE, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    if root:
        save_project_profile(root, build_project_profile(project_root=project_root, root=root, task_class=args.task_class))
        save_alpha_identity_files(
            root,
            task_identity=getattr(args, "task_identity", ""),
            prompt_identity=getattr(args, "prompt_identity", ""),
        )
        criteria_completed = write_acceptance_criteria(root, generated_by="synrail init")
        if criteria_completed.returncode != 0:
            if criteria_completed.stderr.strip():
                print(criteria_completed.stderr.strip(), file=sys.stderr)
            if criteria_completed.stdout.strip():
                print(criteria_completed.stdout.strip())
            return criteria_completed.returncode
        print_init_summary(root=root, state_file=Path(args.output))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    project_root = Path(getattr(args, "project_root", "") or Path.cwd()).resolve()
    if not getattr(args, "output", None):
        if not root:
            raise ValueError("output or artifact root is required")
        args.output = str(alpha_file(root, "state"))

    existing_state_path = Path(args.output)
    existing_state = load_json(existing_state_path) if existing_state_path.exists() else None
    if not getattr(args, "run_id", None):
        args.run_id = default_alpha_run_id()
    if not getattr(args, "task_class", None):
        args.task_class = existing_state.get("task_class", DEFAULT_ALPHA_TASK_CLASS) if existing_state else DEFAULT_ALPHA_TASK_CLASS

    task_identity, prompt_identity = resolve_start_identities(args, root=root)
    if not task_identity:
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "TASK_IDENTITY_REQUIRED_FOR_CONTROLLED_START"}, ensure_ascii=True))
        else:
            print("Synrail could not start a controlled run yet.")
            print("What is missing: the original task request for this run.")
            print("What to do next: pass --task-identity or save the task request first, then rerun synrail start.")
        return 2

    existing_proof = existing_preferred_proof_artifacts(root)
    if existing_proof:
        previous_state = existing_state.get("state", "") if existing_state else ""
        if previous_state in ("CLOSURE_ACCEPTED", "CLOSURE_REJECTED"):
            for _aid, path in preferred_proof_artifact_paths(root).items():
                path.unlink(missing_ok=True)
            proof_request_path = alpha_file(root, "proof_request")
            proof_request_path.unlink(missing_ok=True)
            existing_proof = []
        if existing_proof:
            if args.mode == "dev":
                print(json.dumps({"result": "ERROR", "reason": "CONTROLLED_START_REQUIRES_CLEAN_PROOF_SURFACE", "existing_proof_artifacts": existing_proof}, ensure_ascii=True))
            else:
                print("Synrail could not start this run in controlled mode yet.")
                print("What happened: proof artifacts already exist, so this looks like a post-hoc run instead of a controlled start.")
                print("What to do next: clear those proof artifacts or begin a fresh run before trusting Synrail acceptance.")
            return 2

    forwarded = [
        "init",
        "--run-id", args.run_id,
        "--task-class", args.task_class,
        "--output", args.output,
    ]
    completed = run_python_capture(SPINE, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode

    profile = build_project_profile(project_root=project_root, root=root, task_class=args.task_class)
    save_project_profile(root, profile)
    clear_runtime_artifacts_for_start(root)
    save_alpha_identity_files(root, task_identity=task_identity, prompt_identity=prompt_identity)
    write_controlled_start_artifacts(
        root,
        project_root=project_root,
        run_id=args.run_id,
        task_class=args.task_class,
        task_identity=task_identity,
        prompt_identity=prompt_identity,
        profile=profile,
        started_via="synrail start",
    )
    criteria_completed = write_acceptance_criteria(root, generated_by="synrail start")
    if criteria_completed.returncode != 0:
        if criteria_completed.stderr.strip():
            print(criteria_completed.stderr.strip(), file=sys.stderr)
        if criteria_completed.stdout.strip():
            print(criteria_completed.stdout.strip())
        return criteria_completed.returncode
    validation = apply_bootstrap_defaults(args, root=root)
    if validation:
        save_bootstrap_json(alpha_file(root, "bootstrap_validation"), validation)
    print_start_summary(root=root, state_file=Path(args.output), project_root=project_root)
    return 0


def cmd_refresh_acceptance(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if not root:
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2
    profile = project_profile_file(root)
    if not profile.exists():
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "PROJECT_PROFILE_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not refresh the acceptance rules yet.")
            print("What to do next: run synrail start first so Synrail can capture the controlled project profile.")
        return 2
    completed = write_acceptance_criteria(root, generated_by="synrail refresh-acceptance")
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    state_file = alpha_file(root, "state")
    if state_file.exists():
        validation_completed = write_acceptance_validation(root, criteria_file=alpha_file(root, "acceptance_criteria"), state_file=state_file)
        if validation_completed.returncode != 0:
            if validation_completed.stderr.strip():
                print(validation_completed.stderr.strip(), file=sys.stderr)
            if validation_completed.stdout.strip():
                print(validation_completed.stdout.strip())
            return validation_completed.returncode
    if args.mode == "dev":
        print(json.dumps(
            {
                "criteria": load_json(alpha_file(root, "acceptance_criteria")),
                "validation": load_json(alpha_file(root, "acceptance_validation")) if alpha_file(root, "acceptance_validation").exists() else None,
            },
            indent=2,
            ensure_ascii=True,
        ))
    else:
        print_acceptance_refresh_summary(root=root)
    return 0


def cmd_telemetry_enable(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    config = enable_telemetry(root, args.tester_id)
    print(json.dumps({"result": "OK", "telemetry_session_id": config["telemetry_session_id"]}, ensure_ascii=True))
    return 0


def cmd_telemetry_export(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if not root:
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2
    if not getattr(args, "output", None):
        args.output = str(default_session_replay_file(root))
    if not getattr(args, "issue_output", None):
        args.issue_output = str(default_issue_body_file(root))
    try:
        record = export_session_replay(root, Path(args.output), Path(args.issue_output))
    except ValueError as exc:
        print("Synrail could not export feedback yet.")
        print("What happened: telemetry is not enabled for this artifact root.")
        print("What to do next: rerun synrail start with --telemetry-opt-in or use synrail telemetry enable before exporting feedback.")
        return 2
    print("Feedback export ready.")
    print("What it includes: one session replay and one issue-ready summary.")
    print(f"Command count captured: {record['command_count']}")
    print("Use this when you want to send back a non-green run without hand-assembling artifacts.")
    return 0


def cmd_bundle_check(args: argparse.Namespace) -> int:
    forwarded = [
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--output", args.output,
    ]
    optional_pairs = [
        ("--run-id", args.run_id),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--baseline-identity", args.baseline_identity),
        ("--execution-surface-identity", args.execution_surface_identity),
        ("--prompt-identity", args.prompt_identity),
        ("--task-identity", args.task_identity),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    return run_python(BUNDLE, forwarded)


def cmd_apply_bundle(args: argparse.Namespace) -> int:
    return run_python(SPINE, ["apply-bundle", args.state_file, args.bundle_file])


def cmd_closure(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--bundle-file", args.bundle_file,
        "--output", args.output,
    ]
    if args.update_state:
        forwarded.append("--update-state")
    return run_python(CLOSURE, forwarded)


def cmd_apply_closure(args: argparse.Namespace) -> int:
    return run_python(SPINE, ["apply-closure", args.state_file, args.closure_file])


def cmd_refresh(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--event-type", args.event_type,
        "--output", args.output,
    ]
    optional_pairs = [
        ("--doctor-status", args.doctor_status),
        ("--bundle-file", args.bundle_file),
        ("--closure-file", args.closure_file),
        ("--recovery-status", args.recovery_status),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    if args.reverification_complete:
        forwarded.append("--reverification-complete")
    if args.update_state:
        forwarded.append("--update-state")
    return run_python(REFRESH, forwarded)


def cmd_validate(args: argparse.Namespace) -> int:
    forwarded = [
        "--schema", args.schema,
        "--document", args.document,
    ]
    return run_python(VALIDATE, forwarded)


def cmd_doctor(args: argparse.Namespace) -> int:
    forwarded = [
        "--doctor-run-id", args.doctor_run_id,
        "--doctor-level", args.doctor_level,
        "--target-path", args.target_path,
        "--target-classification", args.target_classification,
        "--baseline-identity", args.baseline_identity,
        "--intended-run-class", args.intended_run_class,
        "--output", args.output,
    ]
    if args.state_file:
        forwarded.extend(["--state-file", args.state_file])
    if args.update_state:
        forwarded.append("--update-state")
    if args.clean_surface:
        forwarded.append("--clean-surface")
    if args.artifact_viable:
        forwarded.append("--artifact-viable")
    if args.helper_ok:
        forwarded.append("--helper-ok")
    if args.credentials_ok:
        forwarded.append("--credentials-ok")
    if args.prompt_identity_ok:
        forwarded.append("--prompt-identity-ok")
    optional_pairs = [
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--prompt-identity-file", args.prompt_identity_file),
        ("--expected-task-identity", args.expected_task_identity),
        ("--target-identity-file", args.target_identity_file),
        ("--expected-target-identity", args.expected_target_identity),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    for changed_file in args.changed_file:
        forwarded.extend(["--changed-file", changed_file])
    for allowed_scope_path in args.allowed_scope_path:
        forwarded.extend(["--allowed-scope-path", allowed_scope_path])
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    return run_python(DOCTOR, forwarded)


def cmd_compare(args: argparse.Namespace) -> int:
    try:
        baseline = load_json(Path(args.baseline_file))
        harness = comparison_harness_for_inputs(args.baseline_file, args.synrail_file)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": "COMPARISON_INPUT_SCHEMA_MISMATCH", "detail": str(exc)}, ensure_ascii=True))
        return 2
    if baseline.get("schema_version") == "comparison_input_v2":
        forwarded = [
            "--substitute-file", args.baseline_file,
            "--synrail-file", args.synrail_file,
            "--output", args.output,
        ]
    else:
        forwarded = [
            "--baseline-file", args.baseline_file,
            "--synrail-file", args.synrail_file,
            "--output", args.output,
        ]
    return run_python(harness, forwarded)


def cmd_substitute_pressure(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    for record in args.record:
        forwarded.extend(["--record", record])
    forwarded.extend(["--output", args.output])
    return run_python(SUBSTITUTE_PRESSURE, forwarded)


def cmd_hybrid_status(args: argparse.Namespace) -> int:
    forwarded = [
        "--cost-record", args.cost_record,
        "--output", args.output,
    ]
    for hybrid_record in args.hybrid_record:
        forwarded.extend(["--hybrid-record", hybrid_record])
    return run_python(HYBRID_STATUS, forwarded)


def cmd_recommend_mode(args: argparse.Namespace) -> int:
    forwarded = [
        "--cost-record", args.cost_record,
        "--scenario-class", args.scenario_class,
        "--task-class", args.task_class,
        "--false-success-risk", args.false_success_risk,
        "--recovery-cost", args.recovery_cost,
        "--output", args.output,
    ]
    if args.hybrid_status:
        forwarded.extend(["--hybrid-status", args.hybrid_status])
    if args.governed_cost_delta:
        forwarded.extend(["--governed-cost-delta", args.governed_cost_delta])
    if args.execution_surface_ambiguous:
        forwarded.append("--execution-surface-ambiguous")
    if args.artifact_truth_nontrivial:
        forwarded.append("--artifact-truth-nontrivial")
    if args.explicit_hybrid_ambiguity:
        forwarded.extend(["--explicit-hybrid-ambiguity", args.explicit_hybrid_ambiguity])
    return run_python(MODE_SELECTOR, forwarded)


def cmd_select_mode(args: argparse.Namespace) -> int:
    forwarded = [
        "--recommendation-file", args.recommendation_file,
        "--output", args.output,
    ]
    if args.selected_mode:
        forwarded.extend(["--selected-mode", args.selected_mode])
    if args.selected_with_preparation:
        forwarded.append("--selected-with-preparation")
    return run_python(MODE_RECEIPT, forwarded)


def cmd_plan_proof(args: argparse.Namespace) -> int:
    forwarded = [
        "--run-id", args.run_id,
        "--task-class", args.task_class,
        "--artifact-root", args.artifact_root,
        "--baseline-identity", args.baseline_identity,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
        "--output", args.output,
    ]
    return run_python(PROOF_PLAN, forwarded)


def cmd_preparation_receipt(args: argparse.Namespace) -> int:
    forwarded = [
        "--plan-file", args.plan_file,
        "--bundle-file", args.bundle_file,
        "--output", args.output,
    ]
    return run_python(PREPARATION_RECEIPT, forwarded)


def cmd_governed_cost(args: argparse.Namespace) -> int:
    forwarded = [
        "--unprepared-file", args.unprepared_file,
        "--prepared-file", args.prepared_file,
        "--output", args.output,
    ]
    return run_python(GOVERNED_COST, forwarded)


def cmd_create_checkpoint(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if root and not getattr(args, "checkpoint_id", None):
        args.checkpoint_id = "working"
    if root and not getattr(args, "checkpoint_root", None):
        args.checkpoint_root = str(checkpoint_root(root, args.checkpoint_id))
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and not getattr(args, "output", None):
        args.output = str(checkpoint_record_file(root, args.checkpoint_id))
    if root:
        for attr, file_id in [
            ("report_file", "report"),
            ("orchestration_file", "orchestration"),
            ("bundle_file", "bundle"),
            ("closure_file", "closure"),
            ("refresh_file", "refresh"),
            ("selection_file", "selection_receipt"),
            ("preparation_file", "preparation_receipt"),
            ("repair_packet_file", "repair_packet"),
            ("repair_handoff_file", "repair_handoff"),
            ("repair_receipt_file", "repair_receipt"),
        ]:
            if not getattr(args, attr, None):
                existing = maybe_existing_alpha_file(root, file_id)
                if existing:
                    setattr(args, attr, existing)
    forwarded = [
        "create",
        "--checkpoint-id", args.checkpoint_id,
        "--checkpoint-root", args.checkpoint_root,
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    optional_pairs = [
        ("--report-file", args.report_file),
        ("--orchestration-file", args.orchestration_file),
        ("--bundle-file", args.bundle_file),
        ("--closure-file", args.closure_file),
        ("--refresh-file", args.refresh_file),
        ("--selection-file", args.selection_file),
        ("--preparation-file", args.preparation_file),
        ("--repair-packet-file", args.repair_packet_file),
        ("--repair-handoff-file", args.repair_handoff_file),
        ("--repair-receipt-file", args.repair_receipt_file),
    ]
    for flag, value in optional_pairs:
        if value:
            forwarded.extend([flag, value])
    if args.mode == "dev":
        return run_python(CHECKPOINT, forwarded)
    completed = run_python_capture(CHECKPOINT, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    print_checkpoint_summary(Path(args.output), action="create", root=root)
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if args.mode == "dev":
        return cmd_create_checkpoint(args)
    checkpoint_id = getattr(args, "checkpoint_id", None) or "working"
    record_output = Path(getattr(args, "output", "") or checkpoint_record_file(root, checkpoint_id))
    record_root = Path(getattr(args, "checkpoint_root", "") or checkpoint_root(root, checkpoint_id))
    state_file = Path(getattr(args, "state_file", "") or alpha_file(root, "state"))
    create_forwarded = [
        "create",
        "--checkpoint-id", checkpoint_id,
        "--checkpoint-root", str(record_root),
        "--state-file", str(state_file),
        "--output", str(record_output),
    ]
    for attr, flag in [
        ("report_file", "--report-file"),
        ("orchestration_file", "--orchestration-file"),
        ("bundle_file", "--bundle-file"),
        ("closure_file", "--closure-file"),
        ("refresh_file", "--refresh-file"),
        ("selection_file", "--selection-file"),
        ("preparation_file", "--preparation-file"),
        ("repair_packet_file", "--repair-packet-file"),
        ("repair_handoff_file", "--repair-handoff-file"),
        ("repair_receipt_file", "--repair-receipt-file"),
    ]:
        value = getattr(args, attr, None)
        if not value and root:
            file_id = {
                "report_file": "report",
                "orchestration_file": "orchestration",
                "bundle_file": "bundle",
                "closure_file": "closure",
                "refresh_file": "refresh",
                "selection_file": "selection_receipt",
                "preparation_file": "preparation_receipt",
                "repair_packet_file": "repair_packet",
                "repair_handoff_file": "repair_handoff",
                "repair_receipt_file": "repair_receipt",
            }[attr]
            value = maybe_existing_alpha_file(root, file_id)
        if value:
            create_forwarded.extend([flag, value])
    created = run_python_capture(CHECKPOINT, create_forwarded)
    if created.returncode != 0:
        if created.stderr.strip():
            print(created.stderr.strip(), file=sys.stderr)
        if created.stdout.strip():
            print(created.stdout.strip())
        return created.returncode
    verify_output = Path(checkpoint_verify_file(root, checkpoint_id))
    verified = run_python_capture(
        CHECKPOINT,
        [
            "verify",
            "--checkpoint-record-file", str(record_output),
            "--output", str(verify_output),
        ],
    )
    if verified.returncode != 0:
        if verified.stderr.strip():
            print(verified.stderr.strip(), file=sys.stderr)
        if verified.stdout.strip():
            print(verified.stdout.strip())
        print_checkpoint_summary(record_output, action="create", root=root)
        return verified.returncode
    print_save_summary(record_output, verify_output, root=root)
    return 0


def cmd_verify_checkpoint(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if root and not getattr(args, "output", None):
        checkpoint_id = getattr(args, "checkpoint_id", None) or (Path(args.checkpoint_record_file).parent.name if getattr(args, "checkpoint_record_file", None) else "working")
        args.output = str(checkpoint_verify_file(root, checkpoint_id))
    if not getattr(args, "checkpoint_record_file", None):
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_RECORD_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not find a restore point to confirm.")
            if root:
                print("What to do next: create one while the project is in a verified working state.")
                print("Next command: " + shell_command(root, "save"))
        return 2
    if not getattr(args, "output", None):
        print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_VERIFY_OUTPUT_REQUIRED"}, ensure_ascii=True))
        return 2
    forwarded = [
        "verify",
        "--checkpoint-record-file", args.checkpoint_record_file,
        "--output", args.output,
    ]
    if args.mode == "dev":
        return run_python(CHECKPOINT, forwarded)
    completed = run_python_capture(CHECKPOINT, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    print_checkpoint_summary(Path(args.output), action="verify", root=root)
    return 0


def cmd_restore_checkpoint(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if root and not getattr(args, "target_root", None):
        args.target_root = str(root)
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "checkpoint_restore"))
    if not getattr(args, "checkpoint_record_file", None):
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "CHECKPOINT_RECORD_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not find a verified restore point to restore.")
            if root:
                print("What to do next: create one while the project is in a verified working state.")
                print("Next command: " + shell_command(root, "save"))
        return 2
    forwarded = [
        "restore",
        "--checkpoint-record-file", args.checkpoint_record_file,
        "--target-root", args.target_root,
        "--output", args.output,
    ]
    if args.mode == "dev":
        code = run_python(CHECKPOINT, forwarded)
    else:
        completed = run_python_capture(CHECKPOINT, forwarded)
        if completed.returncode != 0:
            if completed.stderr.strip():
                print(completed.stderr.strip(), file=sys.stderr)
            if completed.stdout.strip():
                print(completed.stdout.strip())
            return completed.returncode
        code = 0
    if code == 0:
        sync_restored_checkpoint_artifacts(Path(args.target_root))
        if args.mode != "dev":
            print_checkpoint_summary(Path(args.output), action="restore", root=root)
    return code


def cmd_restore(args: argparse.Namespace) -> int:
    return cmd_restore_checkpoint(args)


def cmd_artifact_consistency(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "artifact_consistency"))
    if root:
        for attr, file_id in [
            ("report_file", "report"),
            ("orchestration_file", "orchestration"),
            ("run_file", "run"),
            ("repair_packet_file", "repair_packet"),
            ("repair_handoff_file", "repair_handoff"),
            ("repair_receipt_file", "repair_receipt"),
        ]:
            if not getattr(args, attr, None):
                existing = maybe_existing_alpha_file(root, file_id)
                if existing:
                    setattr(args, attr, existing)
    forwarded = [
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    for flag, value in [
        ("--report-file", args.report_file),
        ("--orchestration-file", args.orchestration_file),
        ("--run-file", args.run_file),
        ("--repair-packet-file", args.repair_packet_file),
        ("--repair-handoff-file", args.repair_handoff_file),
        ("--repair-receipt-file", args.repair_receipt_file),
    ]:
        if value:
            forwarded.extend([flag, value])
    return run_python(ARTIFACT_CONSISTENCY, forwarded)


def cmd_thin_output(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and not getattr(args, "report_file", None):
        args.report_file = str(alpha_file(root, "report"))
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "thin_output"))
    if root and not getattr(args, "repair_packet_file", None):
        existing = maybe_existing_alpha_file(root, "repair_packet")
        if existing:
            args.repair_packet_file = existing
    if root and not getattr(args, "doctor_file", None):
        existing = maybe_existing_alpha_file(root, "doctor")
        if existing:
            args.doctor_file = existing
    if root and not getattr(args, "consistency_recovery_file", None):
        existing = maybe_existing_alpha_file(root, "consistency_recovery")
        if existing:
            args.consistency_recovery_file = existing
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--mode", args.mode,
        "--output", args.output,
    ]
    for flag, value in [
        ("--repair-packet-file", args.repair_packet_file),
        ("--doctor-file", args.doctor_file),
        ("--checkpoint-record-file", args.checkpoint_record_file),
        ("--consistency-recovery-file", args.consistency_recovery_file),
    ]:
        if value:
            forwarded.extend([flag, value])
    if args.mode == "dev":
        return run_python(THIN_OUTPUT, forwarded)
    completed = run_python_capture(THIN_OUTPUT, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
    elif not getattr(args, "_suppress_summary", False):
        print_thin_output_summary(Path(args.output))
    return completed.returncode


def cmd_generate_prompt(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root and not getattr(args, "repair_packet_file", None):
        args.repair_packet_file = str(alpha_file(root, "repair_packet"))
    if root and not getattr(args, "doctor_file", None):
        existing = maybe_existing_alpha_file(root, "doctor")
        if existing:
            args.doctor_file = existing
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "prompt"))
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    if not args.repair_packet_file or not Path(args.repair_packet_file).exists():
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "REPAIR_PACKET_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail does not have the next bounded repair instruction yet.")
            if root:
                print("What to do next: run one check first so Synrail can build the bounded next step.")
                print("Next command: " + shell_command(root, "check"))
        return 2
    forwarded = [
        "--repair-packet-file", args.repair_packet_file,
        "--output", args.output,
    ]
    if args.checkpoint_record_file:
        forwarded.extend(["--checkpoint-record-file", args.checkpoint_record_file])
    if getattr(args, "doctor_file", None):
        forwarded.extend(["--doctor-file", args.doctor_file])
    if args.mode == "dev":
        return run_python(PROMPT_BRIDGE, forwarded)
    completed = run_python_capture(PROMPT_BRIDGE, forwarded)
    if completed.returncode != 0:
        if completed.stderr.strip():
            print(completed.stderr.strip(), file=sys.stderr)
        if completed.stdout.strip():
            print(completed.stdout.strip())
        return completed.returncode
    print_prompt_summary(Path(args.output))
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if root and not getattr(args, "state_file", None):
        args.state_file = str(alpha_file(root, "state"))
    if root and not getattr(args, "report_file", None):
        args.report_file = str(alpha_file(root, "report"))
    if root and not getattr(args, "output", None):
        args.output = str(alpha_file(root, "thin_output"))
    if root and not getattr(args, "doctor_file", None):
        existing = maybe_existing_alpha_file(root, "doctor")
        if existing:
            args.doctor_file = existing
    if root and not getattr(args, "repair_packet_file", None):
        existing = maybe_existing_alpha_file(root, "repair_packet")
        if existing:
            args.repair_packet_file = existing
    if root and not getattr(args, "consistency_recovery_file", None):
        existing = maybe_existing_alpha_file(root, "consistency_recovery")
        if existing:
            args.consistency_recovery_file = existing
    if root and not getattr(args, "checkpoint_record_file", None):
        discovered = discover_checkpoint_record(root, getattr(args, "checkpoint_id", None))
        if discovered:
            args.checkpoint_record_file = discovered
    apply_alpha_profile_defaults(args, root=root)
    bootstrap_validation = apply_bootstrap_defaults(args, root=root) if root else None
    if root and project_profile_file(root).exists():
        args.acceptance_validation_output = str(alpha_file(root, "acceptance_validation"))
        args.project_profile_file = str(project_profile_file(root))
        existing_criteria = maybe_existing_alpha_file(root, "acceptance_criteria")
        if existing_criteria:
            args.acceptance_criteria_file = existing_criteria

    if (
        root
        and bootstrap_validation
        and bootstrap_validation.get("status", "") != "VALID"
        and Path(getattr(args, "state_file", "")).exists()
    ):
        return write_bootstrap_required_block(args=args, root=root, validation=bootstrap_validation)

    if (
        root
        and unsupported_remote_target_reason(
            target_path=getattr(args, "target_path", ""),
            target_classification=getattr(args, "target_classification", ""),
        )
        and Path(getattr(args, "state_file", "")).exists()
    ):
        return write_remote_unsupported_block(args=args, root=root)

    runtime_requested = all(
        [
            getattr(args, "target_path", None),
            getattr(args, "baseline_identity", None),
            getattr(args, "execution_surface_identity", None),
            getattr(args, "final_result", None),
        ]
    )

    if runtime_requested:
        state = load_json(Path(args.state_file))
        orchestrate_args = argparse.Namespace(
            artifact_root=args.artifact_root,
            state_file=args.state_file,
            resume_from_state="",
            repair_handoff_file=getattr(args, "repair_handoff_file", None),
            repair_handoff_output=getattr(args, "repair_handoff_output", None),
            repair_packet_file=getattr(args, "repair_packet_file", None),
            repair_packet_output=getattr(args, "repair_packet_output", None),
            repair_receipt_file=getattr(args, "repair_receipt_file", None),
            repair_receipt_output=getattr(args, "repair_receipt_output", None),
            mode_selection_receipt=getattr(args, "mode_selection_receipt", None),
            doctor_run_id=args.doctor_run_id or state["run_id"],
            doctor_level=args.doctor_level,
            target_path=args.target_path,
            target_classification=args.target_classification,
            baseline_identity=args.baseline_identity,
            intended_run_class=args.intended_run_class,
            doctor_output=getattr(args, "doctor_output", None),
            final_result=args.final_result,
            task_class=state["task_class"],
            bundle_output=getattr(args, "bundle_output", None),
            closure_output=getattr(args, "closure_output", None),
            report_output=args.report_file,
            execution_surface_identity=args.execution_surface_identity,
            prompt_identity=args.prompt_identity or "",
            task_identity=args.task_identity or "",
            bootstrap_provenance_ok=getattr(args, "bootstrap_provenance_ok", False),
            bootstrap_provenance_reason=getattr(args, "bootstrap_provenance_reason", ""),
            readback=getattr(args, "readback", None),
            scenario_proof=getattr(args, "scenario_proof", None),
            plan_output=getattr(args, "plan_output", None),
            preparation_receipt_output=getattr(args, "preparation_receipt_output", None),
            preparation_artifact_root=getattr(args, "preparation_artifact_root", None),
            refresh_output=getattr(args, "refresh_output", None),
            observability_output=getattr(args, "observability_output", None),
            artifact_consistency_output=getattr(args, "artifact_consistency_output", None),
            refresh_event_type=getattr(args, "refresh_event_type", None),
            refresh_doctor_status=getattr(args, "refresh_doctor_status", None),
            refresh_recovery_status=getattr(args, "refresh_recovery_status", None),
            refresh_reverification_complete=getattr(args, "refresh_reverification_complete", False),
            refresh_use_bundle=getattr(args, "refresh_use_bundle", False),
            refresh_use_closure=getattr(args, "refresh_use_closure", False),
            baseline_file=getattr(args, "baseline_file", None),
            synrail_file=getattr(args, "synrail_file", None),
            comparison_output=getattr(args, "comparison_output", None),
            worked_artifact_output=getattr(args, "worked_artifact_output", None),
            run_artifact_output=getattr(args, "run_artifact_output", None),
            clean_surface=getattr(args, "clean_surface", False),
            artifact_viable=getattr(args, "artifact_viable", False),
            helper_ok=getattr(args, "helper_ok", False),
            credentials_ok=getattr(args, "credentials_ok", False),
            prompt_identity_ok=getattr(args, "prompt_identity_ok", False),
            artifact_path=getattr(args, "artifact_path", None),
            helper_path=getattr(args, "helper_path", None),
            credential_env=list(getattr(args, "credential_env", [])),
            prompt_identity_file=getattr(args, "prompt_identity_file", None),
            target_identity_file=getattr(args, "target_identity_file", None),
            _capture_output=(args.mode == "default"),
        )
        orchestrate_code = cmd_orchestrate(orchestrate_args)
        if orchestrate_code != 0 and not Path(args.report_file).exists():
            return orchestrate_code
    elif not Path(args.report_file).exists():
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "CHECK_CONTEXT_INCOMPLETE", "detail": "report file is missing and runtime check inputs were not supplied"}, ensure_ascii=True))
        else:
            print("Synrail could not start the check yet.")
            if not getattr(args, "final_result", None):
                proof_request_file = alpha_file(root, "proof_request") if root else None
                if proof_request_file and proof_request_file.exists():
                    proof_request = load_bootstrap_json(proof_request_file)
                    preferred = proof_request.get("preferred_artifacts", {})
                    print("What is missing: Synrail is still waiting for the proof artifacts for this controlled run.")
                    print("What to do next: edit the starter proof files already placed at these paths, then rerun synrail check.")
                    for label in ["final_result", "readback", "scenario_proof"]:
                        if preferred.get(label, ""):
                            print(f"- {label}: {preferred[label]}")
                else:
                    profile = load_project_profile(root)
                    candidates = (profile or {}).get("final_result_candidates", [])
                    print("What is missing: Synrail could not find the agent's final result yet.")
                    if candidates:
                        print("What to do next: pass --final-result or place one result file at one of these paths:")
                        for candidate in candidates[:4]:
                            print(f"- {candidate}")
            else:
                print("What to do next: provide the missing runtime context or rerun with --mode dev for full technical detail.")
        return 2

    args._suppress_summary = True
    thin_code = cmd_thin_output(args)
    if thin_code == 0 and args.mode == "default":
        print_thin_output_summary(Path(args.output))
        thin_payload = load_json(Path(args.output)) if Path(args.output).exists() else {}
        outcome_class = thin_payload.get("outcome_class", "")
        if thin_payload.get("next_command", "") == "synrail refresh-acceptance":
            return thin_code
        if Path(args.report_file).exists():
            report_payload = load_json(Path(args.report_file))
            if report_payload.get("reason", "") in {"CONTROLLED_BOOTSTRAP_NOT_CONFIRMED", "REMOTE_TARGET_UNSUPPORTED"}:
                return thin_code
        if outcome_class not in {"ACCEPTED", ""} and getattr(args, "repair_packet_file", None):
            prompt_output = str(alpha_file(root, "prompt")) if root else str(Path(args.output).with_name("prompt.json"))
            forwarded = [
                "--repair-packet-file", args.repair_packet_file,
                "--output", prompt_output,
            ]
            if getattr(args, "checkpoint_record_file", None):
                forwarded.extend(["--checkpoint-record-file", args.checkpoint_record_file])
            if getattr(args, "doctor_file", None):
                forwarded.extend(["--doctor-file", args.doctor_file])
            prompt_completed = run_python_capture(PROMPT_BRIDGE, forwarded)
            if prompt_completed.returncode == 0:
                print("")
                print("Bounded repair summary:")
                print_prompt_summary_compact(Path(prompt_output), include_prompt=False)
    return thin_code


def cmd_thin_output_reading(args: argparse.Namespace) -> int:
    return run_python(
        THIN_OUTPUT_READING,
        [
            "--thin-output-file", args.thin_output_file,
            "--prompt-bridge-file", args.prompt_bridge_file,
            "--report-file", args.report_file,
            "--repair-packet-file", args.repair_packet_file,
            "--output", args.output,
        ],
    )


def cmd_prompt_followup(args: argparse.Namespace) -> int:
    forwarded = [
        "--repair-packet-file", args.repair_packet_file,
        "--prompt-bridge-file", args.prompt_bridge_file,
        "--output", args.output,
    ]
    if args.thin_output_file:
        forwarded.extend(["--thin-output-file", args.thin_output_file])
    return run_python(PROMPT_FOLLOWUP, forwarded)


def cmd_prompt_retry_guard(args: argparse.Namespace) -> int:
    return run_python(
        PROMPT_RETRY_GUARD,
        [
            "--packet-a-file", args.packet_a_file,
            "--prompt-a-file", args.prompt_a_file,
            "--packet-b-file", args.packet_b_file,
            "--prompt-b-file", args.prompt_b_file,
            "--output", args.output,
        ],
    )


def cmd_consistency_recovery(args: argparse.Namespace) -> int:
    forwarded = [
        "--consistency-file", args.consistency_file,
        "--output", args.output,
    ]
    if args.checkpoint_record_file:
        forwarded.extend(["--checkpoint-record-file", args.checkpoint_record_file])
    return run_python(CONSISTENCY_RECOVERY, forwarded)


def cmd_checkpoint_operator_reading(args: argparse.Namespace) -> int:
    return run_python(
        CHECKPOINT_OPERATOR_READING,
        [
            "--second-operator-file", args.second_operator_file,
            "--thin-output-file", args.thin_output_file,
            "--repair-packet-file", args.repair_packet_file,
            "--output", args.output,
        ],
    )


def cmd_consistency_recovery_prompt(args: argparse.Namespace) -> int:
    forwarded = [
        "--consistency-recovery-file", args.consistency_recovery_file,
        "--output", args.output,
    ]
    if args.thin_output_file:
        forwarded.extend(["--thin-output-file", args.thin_output_file])
    return run_python(CONSISTENCY_RECOVERY_PROMPT, forwarded)


def cmd_consistency_recovery_prompt_reading(args: argparse.Namespace) -> int:
    return run_python(
        CONSISTENCY_RECOVERY_PROMPT_READING,
        [
            "--consistency-recovery-file", args.consistency_recovery_file,
            "--prompt-file", args.prompt_file,
            "--output", args.output,
        ],
    )


def cmd_observability(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--output", args.output,
    ]
    for flag, value in [
        ("--repair-packet-file", args.repair_packet_file),
        ("--repair-receipt-file", args.repair_receipt_file),
        ("--refresh-file", args.refresh_file),
    ]:
        if value:
            forwarded.extend([flag, value])
    return run_python(OBSERVABILITY, forwarded)


def cmd_session_export(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root:
        if not getattr(args, "state_file", None):
            args.state_file = maybe_existing_alpha_file(root, "state")
        if not getattr(args, "report_file", None):
            args.report_file = maybe_existing_alpha_file(root, "report")
        if not getattr(args, "repair_packet_file", None):
            args.repair_packet_file = maybe_existing_alpha_file(root, "repair_packet")
        if not getattr(args, "repair_receipt_file", None):
            args.repair_receipt_file = maybe_existing_alpha_file(root, "repair_receipt")
        if not getattr(args, "refresh_file", None):
            args.refresh_file = maybe_existing_alpha_file(root, "refresh")
        if not getattr(args, "output", None):
            args.output = str(alpha_file(root, "session_export"))
    if not getattr(args, "state_file", None) or not getattr(args, "report_file", None):
        print(json.dumps({"result": "ERROR", "reason": "STATE_AND_REPORT_REQUIRED"}, ensure_ascii=True))
        return 2
    return cmd_observability(args)


def cmd_deploy(args: argparse.Namespace) -> int:
    """Gate deployment side effects behind accepted closure."""
    root = alpha_root_from_args(args)
    if not root:
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2

    state_file = Path(getattr(args, "state_file", "") or str(alpha_file(root, "state")))
    if not state_file.exists():
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({"result": "ERROR", "reason": "NO_STATE_FILE"}, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print("What happened: no run state found. Start a controlled run first.")
            print("What to do next: synrail start")
        return 2

    state = load_json(state_file)
    run_id = state.get("run_id", "")
    current_state = state.get("state", "")

    # Gate 1: state must be CLOSURE_ACCEPTED
    if current_state != "CLOSURE_ACCEPTED":
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({
                "result": "BLOCKED",
                "reason": "DEPLOY_REQUIRES_ACCEPTED_CLOSURE",
                "current_state": current_state,
                "run_id": run_id,
            }, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print(f"What happened: the current run is in state '{current_state}', not 'CLOSURE_ACCEPTED'.")
            print("Deployment is only allowed after Synrail has accepted the proof bundle.")
            if current_state in ("CLOSURE_REJECTED",):
                print("What to do next: fix the issues identified in the proof bundle, then rerun synrail check.")
            else:
                print("What to do next: complete the proof cycle (synrail check) until the run is accepted.")
        return 2

    # Gate 2: verify run_id matches if provided
    deploy_run_id = getattr(args, "deploy_run_id", "") or ""
    if deploy_run_id and deploy_run_id != run_id:
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({
                "result": "BLOCKED",
                "reason": "DEPLOY_RUN_ID_MISMATCH",
                "expected_run_id": deploy_run_id,
                "actual_run_id": run_id,
            }, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print(f"What happened: deploy requested for run '{deploy_run_id}' but accepted run is '{run_id}'.")
            print("What to do next: verify you are deploying the correct run.")
        return 2

    # Gate 3: verify stable target identity binding
    expected_target_identity = expected_target_identity_for_root(root)
    if not expected_target_identity:
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({
                "result": "BLOCKED",
                "reason": "DEPLOY_TARGET_IDENTITY_MISSING",
                "run_id": run_id,
            }, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print("What happened: this run does not have a stable target identity record.")
            print("What to do next: restart the controlled run and keep the target identity attested before deployment.")
        return 2

    deploy_target = (getattr(args, "deploy_target", "") or "").strip()
    if deploy_target and deploy_target != expected_target_identity:
        if getattr(args, "mode", "default") == "dev":
            print(json.dumps({
                "result": "BLOCKED",
                "reason": "DEPLOY_TARGET_MISMATCH",
                "deploy_target": deploy_target,
                "expected_target_identity": expected_target_identity,
            }, ensure_ascii=True))
        else:
            print("Synrail deploy blocked.")
            print(f"What happened: deploy target '{deploy_target}' does not match the attested target identity '{expected_target_identity}'.")
            print("What to do next: verify you are deploying to the correct target.")
        return 2

    # All gates passed — record the deploy receipt
    deploy_receipt = {
        "schema_version": "deploy_receipt_v0",
        "result": "DEPLOY_AUTHORIZED",
        "run_id": run_id,
        "task_class": state.get("task_class", ""),
        "closure_state": current_state,
        "target_identity": expected_target_identity,
        "deploy_target": deploy_target,
        "deploy_time_utc": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "deploy_authorized_by": "synrail deploy gate",
    }

    receipt_path = alpha_file(root, "deploy_receipt")
    save_json(receipt_path, deploy_receipt)

    if getattr(args, "mode", "default") == "dev":
        print(json.dumps(deploy_receipt, ensure_ascii=True))
    else:
        print("Synrail deploy authorized.")
        print(f"Run: {run_id}")
        print(f"State: {current_state}")
        print(f"Target identity: {expected_target_identity}")
        print(f"Receipt: {display_path(receipt_path)}")
        print("You may now proceed with the deployment side effect.")

    return 0


def cmd_deploy_check(args: argparse.Namespace) -> int:
    """Check whether a valid deploy receipt exists (for use by external guards)."""
    root = alpha_root_from_args(args)
    if not root:
        print(json.dumps({"result": "BLOCKED", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2

    receipt_path = alpha_file(root, "deploy_receipt")
    if not receipt_path.exists():
        print(json.dumps({"result": "BLOCKED", "reason": "NO_DEPLOY_RECEIPT"}, ensure_ascii=True))
        return 2

    receipt = load_json(receipt_path)
    if receipt.get("result") != "DEPLOY_AUTHORIZED":
        print(json.dumps({"result": "BLOCKED", "reason": "DEPLOY_NOT_AUTHORIZED", "receipt": receipt}, ensure_ascii=True))
        return 2

    # Cross-check against current state
    state_file = Path(getattr(args, "state_file", "") or str(alpha_file(root, "state")))
    if not state_file.exists():
        print(json.dumps({"result": "BLOCKED", "reason": "NO_STATE_FILE"}, ensure_ascii=True))
        return 2

    state = load_json(state_file)
    if state.get("state", "") != "CLOSURE_ACCEPTED":
        print(json.dumps({
            "result": "BLOCKED",
            "reason": "DEPLOY_CURRENT_STATE_NOT_ACCEPTED",
            "current_state": state.get("state", ""),
        }, ensure_ascii=True))
        return 2
    if state.get("run_id", "") != receipt.get("run_id", ""):
        print(json.dumps({
            "result": "BLOCKED",
            "reason": "DEPLOY_RECEIPT_RUN_ID_STALE",
            "receipt_run_id": receipt.get("run_id", ""),
            "current_run_id": state.get("run_id", ""),
        }, ensure_ascii=True))
        return 2

    expected_target_identity = expected_target_identity_for_root(root)
    receipt_target_identity = (receipt.get("target_identity", "") or "").strip()
    if not receipt_target_identity:
        print(json.dumps({"result": "BLOCKED", "reason": "DEPLOY_RECEIPT_TARGET_IDENTITY_MISSING"}, ensure_ascii=True))
        return 2
    if not expected_target_identity:
        print(json.dumps({"result": "BLOCKED", "reason": "DEPLOY_TARGET_IDENTITY_MISSING"}, ensure_ascii=True))
        return 2
    if receipt_target_identity != expected_target_identity:
        print(json.dumps({
            "result": "BLOCKED",
            "reason": "DEPLOY_RECEIPT_TARGET_IDENTITY_STALE",
            "receipt_target_identity": receipt_target_identity,
            "current_target_identity": expected_target_identity,
        }, ensure_ascii=True))
        return 2

    print(json.dumps({"result": "OK", "deploy_receipt": receipt}, ensure_ascii=True))
    return 0


def cmd_bug_packet(args: argparse.Namespace) -> int:
    root = alpha_root_from_args(args)
    if root:
        for attr, file_id in [
            ("state_file", "state"),
            ("report_file", "report"),
            ("doctor_file", "doctor"),
            ("acceptance_validation_file", "acceptance_validation"),
            ("repair_packet_file", "repair_packet"),
            ("observability_file", "observability"),
            ("thin_output_file", "thin_output"),
        ]:
            if not getattr(args, attr, None):
                value = maybe_existing_alpha_file(root, file_id)
                if value:
                    setattr(args, attr, value)
        if not getattr(args, "observability_file", None):
            session_export = maybe_existing_alpha_file(root, "session_export")
            if session_export:
                args.observability_file = session_export
        if not getattr(args, "output", None):
            args.output = str(alpha_file(root, "bug_packet"))
        if not getattr(args, "issue_output", None):
            args.issue_output = str(root / "bug_packet_issue.md")
    if not getattr(args, "state_file", None) or not getattr(args, "report_file", None):
        print("Synrail could not build the bug packet yet.")
        print("What is missing: state and report are both required.")
        return 2
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--output", args.output,
    ]
    for flag, value in [
        ("--doctor-file", args.doctor_file),
        ("--acceptance-validation-file", args.acceptance_validation_file),
        ("--repair-packet-file", args.repair_packet_file),
        ("--observability-file", args.observability_file),
        ("--thin-output-file", args.thin_output_file),
        ("--issue-output", args.issue_output),
    ]:
        if value:
            forwarded.extend([flag, value])
    code = run_python(BUG_PACKET, forwarded)
    if code == 0:
        print("Bug packet ready.")
        print("What it includes: one compact runtime summary and one issue-ready markdown body.")
        print("Use this only when telemetry export is not enough for the bug report.")
    return code


def cmd_reproducibility(args: argparse.Namespace) -> int:
    return run_python(
        REPRODUCIBILITY,
        [
            "--run-a", args.run_a,
            "--run-b", args.run_b,
            "--output", args.output,
        ],
    )


def cmd_second_operator(args: argparse.Namespace) -> int:
    return run_python(
        SECOND_OPERATOR,
        [
            "--state-file", args.state_file,
            "--repair-packet-file", args.repair_packet_file,
            "--run-file", args.run_file,
            "--output", args.output,
        ],
    )


def cmd_operator_brief(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--report-file", args.report_file,
        "--repair-packet-file", args.repair_packet_file,
        "--output", args.output,
    ]
    if args.doctor_file:
        forwarded.extend(["--doctor-file", args.doctor_file])
    return run_python(OPERATOR_BRIEF, forwarded)


def cmd_operator_brief_chain(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    for brief in args.brief:
        forwarded.extend(["--brief", brief])
    forwarded.extend(["--output", args.output])
    return run_python(OPERATOR_BRIEF_CHAIN, forwarded)


def cmd_operator_render(args: argparse.Namespace) -> int:
    forwarded = ["--output", args.output]
    if args.brief_file:
        forwarded.extend(["--brief-file", args.brief_file])
    if args.chain_file:
        forwarded.extend(["--chain-file", args.chain_file])
    return run_python(OPERATOR_RENDER, forwarded)


def cmd_operator_render_adoption(args: argparse.Namespace) -> int:
    return run_python(
        OPERATOR_RENDER_ADOPTION,
        [
            "--source", args.source,
            "--render", args.render,
            "--label", args.label,
            "--output", args.output,
        ],
    )


def cmd_operator_render_adoption_delta(args: argparse.Namespace) -> int:
    forwarded: list[str] = []
    for record in args.record:
        forwarded.extend(["--record", record])
    forwarded.extend(["--output", args.output])
    return run_python(OPERATOR_RENDER_ADOPTION_DELTA, forwarded)


def cmd_operator_reading(args: argparse.Namespace) -> int:
    return run_python(
        OPERATOR_READING,
        [
            "--second-operator-file", args.second_operator_file,
            "--brief-file", args.brief_file,
            "--render-file", args.render_file,
            "--label", args.label,
            "--output", args.output,
        ],
    )


def cmd_externality_pressure(args: argparse.Namespace) -> int:
    return run_python(
        EXTERNALITY_PRESSURE,
        [
            "--reproducibility-file", args.reproducibility_file,
            "--second-operator-file", args.second_operator_file,
            "--operator-reading-file", args.operator_reading_file,
            "--label", args.label,
            "--output", args.output,
        ],
    )


def cmd_repair_handoff(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--output", args.output,
    ]
    return run_python(REPAIR_HANDOFF, forwarded)


def cmd_repair_packet(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--artifact-root", args.artifact_root,
        "--output", args.output,
    ]
    for flag, value in [
        ("--doctor-run-id", getattr(args, "doctor_run_id", None)),
        ("--doctor-level", getattr(args, "doctor_level", None)),
        ("--target-path", getattr(args, "target_path", None)),
        ("--target-classification", getattr(args, "target_classification", None)),
        ("--baseline-identity", getattr(args, "baseline_identity", None)),
        ("--intended-run-class", getattr(args, "intended_run_class", None)),
        ("--execution-surface-identity", getattr(args, "execution_surface_identity", None)),
        ("--final-result", getattr(args, "final_result", None)),
        ("--prompt-identity", getattr(args, "prompt_identity", None)),
        ("--task-identity", getattr(args, "task_identity", None)),
        ("--previous-packet-file", getattr(args, "previous_packet_file", None)),
        ("--repair-handoff-file", args.repair_handoff_file),
        ("--mode-selection-receipt", args.mode_selection_receipt),
        ("--preparation-receipt-file", args.preparation_receipt_file),
        ("--repair-receipt-file", getattr(args, "repair_receipt_file", None)),
        ("--report-file", getattr(args, "report_file", None)),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--target-identity-file", args.target_identity_file),
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--refresh-output", args.refresh_output),
        ("--refresh-event-type", args.refresh_event_type),
        ("--refresh-recovery-status", args.refresh_recovery_status),
    ]:
        if value:
            forwarded.extend([flag, value])
    for enabled, flag in [
        (args.prompt_identity_ok, "--prompt-identity-ok"),
        (args.clean_surface, "--clean-surface"),
        (args.artifact_viable, "--artifact-viable"),
        (args.helper_ok, "--helper-ok"),
        (args.credentials_ok, "--credentials-ok"),
        (args.refresh_reverification_complete, "--refresh-reverification-complete"),
        (args.refresh_use_bundle, "--refresh-use-bundle"),
        (args.refresh_use_closure, "--refresh-use-closure"),
    ]:
        if enabled:
            forwarded.append(flag)
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    return run_python(REPAIR_PACKET, forwarded)


def load_repair_packet(path: Path) -> dict:
    packet = load_json(path)
    if packet.get("schema_version") != "repair_packet_v0":
        raise ValueError("repair packet must use repair_packet_v0")
    return packet


def apply_resume_input_overrides(args: argparse.Namespace, path: Path) -> None:
    payload = load_json(path)
    if payload.get("schema_version", "resume_input_overrides_v0") != "resume_input_overrides_v0":
        raise ValueError("resume input overrides must use resume_input_overrides_v0")
    scalar_fields = [
        "final_result",
        "readback",
        "scenario_proof",
        "prompt_identity",
        "task_identity",
        "target_identity_file",
        "artifact_path",
        "helper_path",
        "refresh_event_type",
        "refresh_recovery_status",
    ]
    for field in scalar_fields:
        value = payload.get(field)
        if value in {None, ""}:
            continue
        current = getattr(args, field, None)
        if current in {None, ""}:
            setattr(args, field, value)

    truthy_fields = [
        "refresh_reverification_complete",
        "refresh_use_bundle",
        "refresh_use_closure",
        "clean_surface",
        "artifact_viable",
        "helper_ok",
        "credentials_ok",
        "prompt_identity_ok",
    ]
    for field in truthy_fields:
        if payload.get(field) and not getattr(args, field, False):
            setattr(args, field, True)

    if payload.get("credential_env") and not getattr(args, "credential_env", []):
        args.credential_env = list(payload["credential_env"])


def discover_repair_packet_file(args: argparse.Namespace) -> Path | None:
    if getattr(args, "repair_packet_file", None):
        return Path(args.repair_packet_file)
    state_path = Path(args.state_file)
    state_stem = state_path.stem
    prefixed_name = f"{state_stem.removesuffix('_state')}_repair_packet.json" if state_stem.endswith("_state") and state_stem != "state" else ""
    previous_stage_candidate = None
    if state_stem.startswith("stage") and state_stem.endswith("_state"):
        stage_number = state_stem.removeprefix("stage").removesuffix("_state")
        if stage_number.isdigit() and int(stage_number) > 0:
            previous_stage_candidate = state_path.with_name(f"stage{int(stage_number) - 1}_repair_packet.json")
    candidates = [
        state_path.with_name(prefixed_name) if prefixed_name else None,
        previous_stage_candidate,
        state_path.with_name("repair_packet.json"),
    ]
    if getattr(args, "report_output", None):
        candidates.append(Path(args.report_output).with_name("repair_packet.json"))
    for candidate in candidates:
        if candidate is None:
            continue
        if candidate.exists():
            return candidate
    return None


def discover_resume_sibling_inputs(args: argparse.Namespace, state: dict) -> None:
    root = Path(args.state_file).parent
    state_stem = Path(args.state_file).stem
    state_prefix = f"{state_stem.removesuffix('_state')}_" if state_stem.endswith("_state") and state_stem != "state" else ""

    def existing(name: str) -> Path | None:
        candidate = root / name
        return candidate if candidate.exists() else None

    def existing_variants(*names: str) -> Path | None:
        seen: set[str] = set()
        candidates: list[str] = []
        for name in names:
            if state_prefix:
                candidates.append(f"{state_prefix}{name}")
            candidates.append(name)
        for name in candidates:
            if name in seen:
                continue
            seen.add(name)
            candidate = existing(name)
            if candidate:
                return candidate
        return None

    if not getattr(args, "mode_selection_receipt", None):
        candidate = existing_variants("selection_receipt.json")
        if candidate:
            args.mode_selection_receipt = str(candidate)

    if not getattr(args, "repair_receipt_file", None):
        candidate = existing_variants("repair_receipt.json")
        if candidate:
            args.repair_receipt_file = str(candidate)

    if not getattr(args, "repair_handoff_file", None):
        candidate = existing_variants("repair_handoff.json")
        if candidate:
            args.repair_handoff_file = str(candidate)

    if not getattr(args, "final_result", None):
        candidate = existing_variants("fixed_final_result.json", "final_result.json")
        if candidate:
            args.final_result = str(candidate)

    if not getattr(args, "readback", None):
        candidate = existing_variants("later_readback.txt", "readback.txt")
        if candidate:
            args.readback = str(candidate)

    if not getattr(args, "scenario_proof", None):
        candidate = existing_variants("later_scenario.txt", "scenario.txt")
        if candidate:
            args.scenario_proof = str(candidate)

    if not getattr(args, "target_identity_file", None):
        for name in ["target_identity.txt", "target_identity.json"]:
            candidate = existing_variants(name)
            if candidate:
                args.target_identity_file = str(candidate)
                break

    if not getattr(args, "artifact_path", None) and getattr(args, "final_result", None):
        args.artifact_path = args.final_result

    if not getattr(args, "prompt_identity_file", None):
        candidate = existing_variants("prompt_identity.txt")
        if candidate:
            args.prompt_identity_file = str(candidate)

    if not getattr(args, "prompt_identity", None):
        candidate = existing_variants("prompt_identity.txt")
        if candidate:
            args.prompt_identity = candidate.read_text().strip()

    if not getattr(args, "task_identity", None):
        candidate = existing_variants("task_identity.txt")
        if candidate:
            args.task_identity = candidate.read_text().strip()

    resume_inputs_candidate = existing_variants("resume_inputs.json")
    if resume_inputs_candidate:
        apply_resume_input_overrides(args, resume_inputs_candidate)


def synthesize_repair_packet(args: argparse.Namespace, state: dict) -> Path:
    discover_resume_sibling_inputs(args, state)
    root = Path(args.state_file).parent
    state_stem = Path(args.state_file).stem
    state_prefix = f"{state_stem.removesuffix('_state')}_" if state_stem.endswith("_state") and state_stem != "state" else ""

    def sibling_variant(name: str) -> Path | None:
        for candidate_name in ([f"{state_prefix}{name}"] if state_prefix else []) + [name]:
            candidate = root / candidate_name
            if candidate.exists():
                return candidate
        return None

    packet_output = Path(args.repair_packet_output)
    selection_receipt = load_json(Path(args.mode_selection_receipt)) if getattr(args, "mode_selection_receipt", None) else None
    repair_receipt = load_json(Path(args.repair_receipt_file)) if getattr(args, "repair_receipt_file", None) else None

    preparation_receipt = None
    preparation_candidate = sibling_variant("preparation_receipt.json")
    if preparation_candidate:
        preparation_receipt = load_json(preparation_candidate)

    report = None
    report_candidate = sibling_variant("report.json")
    if report_candidate:
        report = load_json(report_candidate)

    packet = build_packet_from_runtime_truth(
        state=state,
        artifact_root=root,
        doctor_run_id=args.doctor_run_id,
        doctor_level=args.doctor_level,
        target_path=args.target_path,
        target_classification=args.target_classification,
        baseline_identity=args.baseline_identity,
        intended_run_class=args.intended_run_class,
        execution_surface_identity=args.execution_surface_identity,
        final_result=args.final_result or "",
        prompt_identity=args.prompt_identity or "",
        task_identity=args.task_identity or "",
        prompt_identity_ok=getattr(args, "prompt_identity_ok", False),
        readback=args.readback or "",
        scenario_proof=args.scenario_proof or "",
        target_identity_file=args.target_identity_file or "",
        clean_surface=getattr(args, "clean_surface", False),
        artifact_viable=getattr(args, "artifact_viable", False),
        helper_ok=getattr(args, "helper_ok", False),
        credentials_ok=getattr(args, "credentials_ok", False),
        artifact_path=args.artifact_path or "",
        helper_path=args.helper_path or "",
        credential_env=list(getattr(args, "credential_env", [])),
        refresh_output=args.refresh_output or "",
        refresh_event_type=args.refresh_event_type or "",
        refresh_recovery_status=args.refresh_recovery_status or "NOT_REQUIRED",
        refresh_reverification_complete=getattr(args, "refresh_reverification_complete", False),
        refresh_use_bundle=getattr(args, "refresh_use_bundle", False),
        refresh_use_closure=getattr(args, "refresh_use_closure", False),
        selection_receipt=selection_receipt,
        preparation_receipt=preparation_receipt,
        repair_receipt=repair_receipt,
        report=report,
    )
    packet_output.write_text(json.dumps(packet, indent=2, ensure_ascii=True) + "\n")
    args.repair_packet_file = str(packet_output)
    return packet_output


def apply_resume_output_defaults(args: argparse.Namespace, state: dict) -> None:
    state_path = Path(args.state_file)
    root = state_path.parent
    state_stem = state_path.stem
    state_prefix = f"{state_stem.removesuffix('_state')}_" if state_stem.endswith("_state") and state_stem != "state" else ""

    def runtime_name(name: str) -> str:
        return f"{state_prefix}{name}" if state_prefix else name

    defaults = {
        "doctor_output": str(root / runtime_name("doctor.json")),
        "bundle_output": str(root / runtime_name("bundle.json")),
        "closure_output": str(root / runtime_name("closure.json")),
        "refresh_output": str(root / runtime_name("refresh.json")),
        "observability_output": str(root / runtime_name("observability.json")),
        "report_output": str(root / runtime_name("report.json")),
        "worked_artifact_output": str(root / runtime_name("orchestration.json")),
        "run_artifact_output": str(root / runtime_name("run.json")),
        "repair_packet_output": str(root / runtime_name("repair_packet.json")),
        "plan_output": str(root / runtime_name("plan.json")),
        "preparation_receipt_output": str(root / runtime_name("preparation_receipt.json")),
    }
    for attr, value in defaults.items():
        if not getattr(args, attr, None):
            setattr(args, attr, value)

    baseline_identity = state.get("target_surface", {}).get("identity", "") or state["run_id"]
    execution_surface_identity = state.get("target_surface", {}).get("identity", "") or baseline_identity
    context_defaults = {
        "doctor_run_id": f"{state['run_id']}_RESUME",
        "doctor_level": "CORE_DOCTOR",
        "target_path": str(root),
        "target_classification": "resume_surface",
        "baseline_identity": baseline_identity,
        "intended_run_class": "core_probe",
        "task_class": state["task_class"],
        "execution_surface_identity": execution_surface_identity,
    }
    for attr, value in context_defaults.items():
        if not getattr(args, attr, None):
            setattr(args, attr, value)

    if getattr(args, "prompt_identity", None) is None:
        args.prompt_identity = ""
    if getattr(args, "task_identity", None) is None:
        args.task_identity = ""
    if getattr(args, "final_result", None) is None:
        args.final_result = ""


def maybe_apply_repair_packet(args: argparse.Namespace, state: dict) -> list[str]:
    packet_path = discover_repair_packet_file(args)
    packet = None
    if packet_path:
        args.repair_packet_file = str(packet_path)
        try:
            packet = load_repair_packet(packet_path)
            if packet["run_id"] != state["run_id"] or packet["from_state"] != state["state"]:
                raise ValueError("repair packet does not match the requested state")
        except ValueError:
            packet = None

    if packet is None:
        discover_resume_sibling_inputs(args, state)
        packet_path = synthesize_repair_packet(args, state)
        packet = load_repair_packet(packet_path)
    else:
        core = dict(packet.get("continuation_core", {}))
        if core.get("requires_sibling_discovery", False):
            discover_resume_sibling_inputs(args, state)

    if packet.get("resumability", {}).get("status", "REPAIRABLE") != "REPAIRABLE":
        return []

    context = packet["resume_context"]
    continuation_plan = packet.get("continuation_plan", {})
    repair_inputs = packet["repair_inputs"]
    output_defaults = packet["output_defaults"]
    temp_files: list[str] = []

    for attr, value in [
        ("doctor_run_id", context["doctor_run_id"]),
        ("doctor_level", context["doctor_level"]),
        ("target_path", context["target_path"]),
        ("target_classification", context["target_classification"]),
        ("baseline_identity", context["baseline_identity"]),
        ("intended_run_class", context["intended_run_class"]),
        ("execution_surface_identity", context["execution_surface_identity"]),
        ("task_class", packet["task_class"]),
        ("final_result", repair_inputs["final_result"]),
        ("prompt_identity", repair_inputs["prompt_identity"]),
        ("task_identity", repair_inputs["task_identity"]),
        ("readback", repair_inputs["readback"]),
        ("scenario_proof", repair_inputs["scenario_proof"]),
        ("artifact_path", repair_inputs["artifact_path"]),
        ("helper_path", repair_inputs["helper_path"]),
        ("prompt_identity_file", ""),
        ("target_identity_file", repair_inputs["target_identity_file"]),
        ("doctor_output", output_defaults["doctor_output"]),
        ("bundle_output", output_defaults["bundle_output"]),
        ("closure_output", output_defaults["closure_output"]),
        ("refresh_output", output_defaults["refresh_output"]),
        ("report_output", output_defaults["report_output"]),
        ("worked_artifact_output", output_defaults["worked_artifact_output"]),
        ("run_artifact_output", output_defaults["run_artifact_output"]),
        ("repair_handoff_output", output_defaults["repair_handoff_output"]),
        ("repair_packet_output", output_defaults["repair_packet_output"]),
        ("repair_receipt_output", output_defaults.get("repair_receipt_output", str(Path(output_defaults["repair_packet_output"]).with_name("repair_receipt.json")))),
        ("plan_output", output_defaults["plan_output"]),
        ("preparation_receipt_output", output_defaults["preparation_receipt_output"]),
    ]:
        current = getattr(args, attr, None)
        if current in {None, ""} and value is not None:
            setattr(args, attr, value)

    if not getattr(args, "preparation_artifact_root", None):
        args.preparation_artifact_root = output_defaults["artifact_root"]

    if not getattr(args, "refresh_recovery_status", None):
        args.refresh_recovery_status = repair_inputs["refresh_recovery_status"]
    if not getattr(args, "refresh_event_type", None) and continuation_plan.get("refresh_event_type"):
        args.refresh_event_type = continuation_plan["refresh_event_type"]
    if repair_inputs["refresh_reverification_complete"]:
        args.refresh_reverification_complete = True
    if continuation_plan.get("refresh_use_bundle"):
        args.refresh_use_bundle = True
    if continuation_plan.get("refresh_use_closure"):
        args.refresh_use_closure = True
    if repair_inputs["clean_surface"]:
        args.clean_surface = True
    if repair_inputs["artifact_viable"]:
        args.artifact_viable = True
    if repair_inputs["helper_ok"]:
        args.helper_ok = True
    if repair_inputs["credentials_ok"]:
        args.credentials_ok = True
    if repair_inputs["prompt_identity_ok"]:
        args.prompt_identity_ok = True
    if not args.credential_env:
        args.credential_env = list(repair_inputs["credential_env"])

    return temp_files


def cmd_orchestrate(args: argparse.Namespace) -> int:
    apply_alpha_runtime_file_defaults(args)
    if not getattr(args, "state_file", None):
        print(json.dumps({"result": "ERROR", "reason": "STATE_FILE_REQUIRED"}, ensure_ascii=True))
        return 2
    forwarded = [
        "--state-file", args.state_file,
        "--doctor-run-id", args.doctor_run_id,
        "--doctor-level", args.doctor_level,
        "--target-path", args.target_path,
        "--target-classification", args.target_classification,
        "--baseline-identity", args.baseline_identity,
        "--intended-run-class", args.intended_run_class,
        "--doctor-output", args.doctor_output,
        "--final-result", args.final_result,
        "--task-class", args.task_class,
        "--bundle-output", args.bundle_output,
        "--closure-output", args.closure_output,
        "--report-output", args.report_output,
        "--execution-surface-identity", args.execution_surface_identity,
        "--prompt-identity", args.prompt_identity,
        "--task-identity", args.task_identity,
    ]
    if getattr(args, "resume_from_state", None):
        forwarded.extend(["--resume-from-state", args.resume_from_state])
    if args.repair_handoff_file:
        forwarded.extend(["--repair-handoff-file", args.repair_handoff_file])
    if args.repair_packet_file:
        forwarded.extend(["--repair-packet-file", args.repair_packet_file])
    if args.mode_selection_receipt:
        forwarded.extend(["--mode-selection-receipt", args.mode_selection_receipt])
    for flag, value in [
        ("--repair-handoff-output", args.repair_handoff_output),
        ("--repair-packet-output", args.repair_packet_output),
        ("--repair-receipt-output", args.repair_receipt_output),
        ("--readback", args.readback),
        ("--scenario-proof", args.scenario_proof),
        ("--plan-output", args.plan_output),
        ("--preparation-receipt-output", args.preparation_receipt_output),
        ("--preparation-artifact-root", args.preparation_artifact_root),
        ("--refresh-output", args.refresh_output),
        ("--observability-output", args.observability_output),
        ("--artifact-consistency-output", args.artifact_consistency_output),
        ("--refresh-event-type", args.refresh_event_type),
        ("--refresh-doctor-status", args.refresh_doctor_status),
        ("--refresh-recovery-status", args.refresh_recovery_status),
        ("--baseline-file", args.baseline_file),
        ("--synrail-file", args.synrail_file),
        ("--comparison-output", args.comparison_output),
        ("--worked-artifact-output", args.worked_artifact_output),
        ("--run-artifact-output", args.run_artifact_output),
        ("--artifact-path", args.artifact_path),
        ("--helper-path", args.helper_path),
        ("--prompt-identity-file", args.prompt_identity_file),
        ("--target-identity-file", args.target_identity_file),
        ("--expected-target-identity", args.execution_surface_identity),
        ("--acceptance-criteria-file", getattr(args, "acceptance_criteria_file", None)),
        ("--acceptance-validation-output", getattr(args, "acceptance_validation_output", None)),
        ("--project-profile-file", getattr(args, "project_profile_file", None)),
        ("--bootstrap-provenance-reason", getattr(args, "bootstrap_provenance_reason", None)),
    ]:
        if value:
            forwarded.extend([flag, value])
    for enabled, flag in [
        (getattr(args, "bootstrap_provenance_ok", False), "--bootstrap-provenance-ok"),
        (args.refresh_reverification_complete, "--refresh-reverification-complete"),
        (args.refresh_use_bundle, "--refresh-use-bundle"),
        (args.refresh_use_closure, "--refresh-use-closure"),
        (args.clean_surface, "--clean-surface"),
        (args.artifact_viable, "--artifact-viable"),
        (args.helper_ok, "--helper-ok"),
        (args.credentials_ok, "--credentials-ok"),
        (args.prompt_identity_ok, "--prompt-identity-ok"),
    ]:
        if enabled:
            forwarded.append(flag)
    for env_name in args.credential_env:
        forwarded.extend(["--credential-env", env_name])
    if getattr(args, "_capture_output", False):
        completed = run_python_capture(SPINE, ["orchestrate", *forwarded])
        if completed.returncode != 0:
            if completed.stderr.strip():
                print(completed.stderr.strip(), file=sys.stderr)
            if completed.stdout.strip():
                print(completed.stdout.strip())
        return completed.returncode
    return run_python(SPINE, ["orchestrate", *forwarded])


def cmd_resume(args: argparse.Namespace) -> int:
    apply_alpha_runtime_file_defaults(args)
    if not getattr(args, "state_file", None):
        print(json.dumps({"result": "ERROR", "reason": "STATE_FILE_REQUIRED"}, ensure_ascii=True))
        return 2
    state_path = Path(args.state_file)
    state = load_json(state_path)
    apply_bootstrap_defaults(args, root=state_path.parent)
    args.resume_from_state = state["state"]
    apply_resume_output_defaults(args, state)
    temp_runtime_files: list[str] = []
    try:
        temp_runtime_files = maybe_apply_repair_packet(args, state)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": "INVALID_REPAIR_PACKET", "detail": str(exc)}, ensure_ascii=True))
        return 2

    for attr in [
        "doctor_run_id",
        "doctor_level",
        "target_path",
        "target_classification",
        "baseline_identity",
        "intended_run_class",
        "doctor_output",
        "task_class",
        "bundle_output",
        "closure_output",
        "report_output",
        "execution_surface_identity",
    ]:
        if not getattr(args, attr, None):
            print(json.dumps({"result": "ERROR", "reason": "RESUME_CONTEXT_INCOMPLETE", "missing_field": attr}, ensure_ascii=True))
            return 2

    try:
        args._capture_output = args.mode == "default"
        code = cmd_orchestrate(args)
        if code == 0 and args.mode == "default":
            root = alpha_root_from_args(args)
            if getattr(args, "output", None):
                thin_output_path = str(Path(args.output))
            elif root:
                thin_output_path = str(alpha_file(root, "thin_output"))
            else:
                thin_output_path = str(Path(args.report_output).with_name("thin_output.json"))
            thin_args = argparse.Namespace(
                artifact_root=args.artifact_root,
                state_file=args.state_file,
                report_file=args.report_output,
                mode="default",
                output=thin_output_path,
                repair_packet_file=getattr(args, "repair_packet_file", None),
                doctor_file=getattr(args, "doctor_output", None),
                checkpoint_id=getattr(args, "checkpoint_id", None),
                checkpoint_record_file=getattr(args, "checkpoint_record_file", None),
                consistency_recovery_file=getattr(args, "consistency_recovery_file", None),
                _suppress_summary=True,
            )
            thin_code = cmd_thin_output(thin_args)
            if thin_code == 0:
                print_thin_output_summary(Path(thin_args.output))
            return thin_code
        return code
    finally:
        for temp_path in temp_runtime_files:
            Path(temp_path).unlink(missing_ok=True)


def add_orchestration_args(
    parser: argparse.ArgumentParser,
    *,
    include_resume_from_state: bool,
    relaxed_runtime: bool = False,
) -> None:
    parser.add_argument("--state-file")
    parser.add_argument("--artifact-root")
    if include_resume_from_state:
        parser.add_argument("--resume-from-state")
    parser.add_argument("--repair-handoff-file")
    parser.add_argument("--repair-handoff-output")
    parser.add_argument("--repair-packet-file")
    parser.add_argument("--repair-packet-output")
    parser.add_argument("--repair-receipt-file")
    parser.add_argument("--repair-receipt-output")
    parser.add_argument("--mode-selection-receipt")
    parser.add_argument("--doctor-run-id", required=not relaxed_runtime)
    parser.add_argument("--doctor-level", required=not relaxed_runtime, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    parser.add_argument("--target-path", required=not relaxed_runtime)
    parser.add_argument("--target-classification", required=not relaxed_runtime)
    parser.add_argument("--baseline-identity", required=not relaxed_runtime)
    parser.add_argument("--intended-run-class", required=not relaxed_runtime, choices=["core_probe", "support_run", "exact_retry"])
    parser.add_argument("--doctor-output", required=not relaxed_runtime)
    parser.add_argument("--final-result", required=not relaxed_runtime)
    parser.add_argument("--task-class", required=not relaxed_runtime)
    parser.add_argument("--bundle-output", required=not relaxed_runtime)
    parser.add_argument("--closure-output", required=not relaxed_runtime)
    parser.add_argument("--report-output", required=not relaxed_runtime)
    parser.add_argument("--execution-surface-identity", required=not relaxed_runtime)
    parser.add_argument("--prompt-identity", required=not relaxed_runtime, default="")
    parser.add_argument("--task-identity", required=not relaxed_runtime, default="")
    parser.add_argument("--readback")
    parser.add_argument("--scenario-proof")
    parser.add_argument("--plan-output")
    parser.add_argument("--preparation-receipt-output")
    parser.add_argument("--preparation-artifact-root")
    parser.add_argument("--refresh-output")
    parser.add_argument("--observability-output")
    parser.add_argument("--refresh-event-type")
    parser.add_argument("--refresh-doctor-status", choices=["PASS", "FAIL"])
    parser.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    parser.add_argument("--refresh-reverification-complete", action="store_true", default=None)
    parser.add_argument("--refresh-use-bundle", action="store_true", default=None)
    parser.add_argument("--refresh-use-closure", action="store_true", default=None)
    parser.add_argument("--baseline-file")
    parser.add_argument("--synrail-file")
    parser.add_argument("--comparison-output")
    parser.add_argument("--artifact-consistency-output")
    parser.add_argument("--worked-artifact-output")
    parser.add_argument("--run-artifact-output")
    parser.add_argument("--clean-surface", action="store_true", default=None)
    parser.add_argument("--artifact-viable", action="store_true", default=None)
    parser.add_argument("--helper-ok", action="store_true", default=None)
    parser.add_argument("--credentials-ok", action="store_true", default=None)
    parser.add_argument("--prompt-identity-ok", action="store_true", default=None)
    parser.add_argument("--artifact-path")
    parser.add_argument("--helper-path")
    parser.add_argument("--credential-env", action="append", default=[])
    parser.add_argument("--prompt-identity-file")
    parser.add_argument("--target-identity-file")
    parser.add_argument("--bootstrap-provenance-ok", action="store_true")
    parser.add_argument("--bootstrap-provenance-reason", default="")
    parser.add_argument("--acceptance-criteria-file")
    parser.add_argument("--acceptance-validation-output")
    parser.add_argument("--project-profile-file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--run-id")
    p_init.add_argument("--task-class", default=DEFAULT_ALPHA_TASK_CLASS)
    p_init.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_init.add_argument("--project-root")
    p_init.add_argument("--task-identity")
    p_init.add_argument("--prompt-identity")
    p_init.add_argument("--telemetry-opt-in", action="store_true")
    p_init.add_argument("--tester-id", default="alpha_tester")
    p_init.add_argument("--mode", default="default", choices=["default", "dev"])
    p_init.add_argument("--output")
    p_init.set_defaults(func=cmd_init)

    p_start = sub.add_parser("start")
    p_start.add_argument("--run-id")
    p_start.add_argument("--task-class", default=DEFAULT_ALPHA_TASK_CLASS)
    p_start.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_start.add_argument("--project-root")
    p_start.add_argument("--task-identity")
    p_start.add_argument("--prompt-identity")
    p_start.add_argument("--telemetry-opt-in", action="store_true")
    p_start.add_argument("--tester-id", default="alpha_tester")
    p_start.add_argument("--mode", default="default", choices=["default", "dev"])
    p_start.add_argument("--output")
    p_start.set_defaults(func=cmd_start)

    p_install_agent_files = sub.add_parser("install-agent-files")
    p_install_agent_files.add_argument("--project-root", default=".")
    p_install_agent_files.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_install_agent_files.add_argument("--force", action="store_true")
    p_install_agent_files.set_defaults(func=cmd_install_agent_files)

    p_refresh_acceptance = sub.add_parser("refresh-acceptance", aliases=["acceptance-refresh"])
    p_refresh_acceptance.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_refresh_acceptance.add_argument("--mode", default="default", choices=["default", "dev"])
    p_refresh_acceptance.set_defaults(func=cmd_refresh_acceptance)

    p_check = sub.add_parser("check")
    p_check.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_check.add_argument("--state-file")
    p_check.add_argument("--report-file")
    p_check.add_argument("--doctor-file")
    p_check.add_argument("--repair-packet-file")
    p_check.add_argument("--repair-handoff-file")
    p_check.add_argument("--repair-handoff-output")
    p_check.add_argument("--repair-packet-output")
    p_check.add_argument("--repair-receipt-file")
    p_check.add_argument("--repair-receipt-output")
    p_check.add_argument("--mode-selection-receipt")
    p_check.add_argument("--checkpoint-id")
    p_check.add_argument("--checkpoint-record-file")
    p_check.add_argument("--consistency-recovery-file")
    p_check.add_argument("--mode", default="default", choices=["default", "dev"])
    p_check.add_argument("--output")
    p_check.add_argument("--doctor-run-id")
    p_check.add_argument("--doctor-level", default="CORE_DOCTOR", choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_check.add_argument("--target-path")
    p_check.add_argument("--target-classification", default="trusted_worktree")
    p_check.add_argument("--baseline-identity")
    p_check.add_argument("--intended-run-class", default="core_probe", choices=["core_probe", "support_run", "exact_retry"])
    p_check.add_argument("--final-result")
    p_check.add_argument("--execution-surface-identity")
    p_check.add_argument("--prompt-identity", default="")
    p_check.add_argument("--task-identity", default="")
    p_check.add_argument("--readback")
    p_check.add_argument("--scenario-proof")
    p_check.add_argument("--plan-output")
    p_check.add_argument("--preparation-receipt-output")
    p_check.add_argument("--preparation-artifact-root")
    p_check.add_argument("--refresh-output")
    p_check.add_argument("--observability-output")
    p_check.add_argument("--artifact-consistency-output")
    p_check.add_argument("--refresh-event-type")
    p_check.add_argument("--refresh-doctor-status", choices=["PASS", "FAIL"])
    p_check.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    p_check.add_argument("--refresh-reverification-complete", action="store_true", default=None)
    p_check.add_argument("--refresh-use-bundle", action="store_true", default=None)
    p_check.add_argument("--refresh-use-closure", action="store_true", default=None)
    p_check.add_argument("--baseline-file")
    p_check.add_argument("--synrail-file")
    p_check.add_argument("--comparison-output")
    p_check.add_argument("--worked-artifact-output")
    p_check.add_argument("--run-artifact-output")
    p_check.add_argument("--clean-surface", action="store_true", default=None)
    p_check.add_argument("--artifact-viable", action="store_true", default=None)
    p_check.add_argument("--helper-ok", action="store_true", default=None)
    p_check.add_argument("--credentials-ok", action="store_true", default=None)
    p_check.add_argument("--prompt-identity-ok", action="store_true", default=None)
    p_check.add_argument("--artifact-path")
    p_check.add_argument("--helper-path")
    p_check.add_argument("--credential-env", action="append", default=[])
    p_check.add_argument("--prompt-identity-file")
    p_check.add_argument("--target-identity-file")
    p_check.set_defaults(func=cmd_check)

    p_status = sub.add_parser("status")
    p_status.add_argument("state_file")
    p_status.set_defaults(func=cmd_status)

    p_bundle = sub.add_parser("bundle-check")
    p_bundle.add_argument("--final-result", required=True)
    p_bundle.add_argument("--task-class", required=True)
    p_bundle.add_argument("--output", required=True)
    p_bundle.add_argument("--run-id")
    p_bundle.add_argument("--readback")
    p_bundle.add_argument("--scenario-proof")
    p_bundle.add_argument("--baseline-identity")
    p_bundle.add_argument("--execution-surface-identity")
    p_bundle.add_argument("--prompt-identity")
    p_bundle.add_argument("--task-identity")
    p_bundle.set_defaults(func=cmd_bundle_check)

    p_apply_bundle = sub.add_parser("apply-bundle")
    p_apply_bundle.add_argument("state_file")
    p_apply_bundle.add_argument("bundle_file")
    p_apply_bundle.set_defaults(func=cmd_apply_bundle)

    p_closure = sub.add_parser("closure")
    p_closure.add_argument("--state-file", required=True)
    p_closure.add_argument("--bundle-file", required=True)
    p_closure.add_argument("--output", required=True)
    p_closure.add_argument("--update-state", action="store_true")
    p_closure.set_defaults(func=cmd_closure)

    p_apply_closure = sub.add_parser("apply-closure")
    p_apply_closure.add_argument("state_file")
    p_apply_closure.add_argument("closure_file")
    p_apply_closure.set_defaults(func=cmd_apply_closure)

    p_refresh = sub.add_parser("refresh")
    p_refresh.add_argument("--state-file", required=True)
    p_refresh.add_argument("--event-type", required=True)
    p_refresh.add_argument("--output", required=True)
    p_refresh.add_argument("--doctor-status", choices=["PASS", "FAIL"])
    p_refresh.add_argument("--bundle-file")
    p_refresh.add_argument("--closure-file")
    p_refresh.add_argument("--recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"])
    p_refresh.add_argument("--reverification-complete", action="store_true")
    p_refresh.add_argument("--update-state", action="store_true")
    p_refresh.set_defaults(func=cmd_refresh)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("--schema", required=True)
    p_validate.add_argument("--document", required=True)
    p_validate.set_defaults(func=cmd_validate)

    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--doctor-run-id", required=True)
    p_doctor.add_argument("--doctor-level", required=True, choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_doctor.add_argument("--target-path", required=True)
    p_doctor.add_argument("--target-classification", required=True)
    p_doctor.add_argument("--baseline-identity", required=True)
    p_doctor.add_argument("--intended-run-class", required=True, choices=["core_probe", "support_run", "exact_retry"])
    p_doctor.add_argument("--output", required=True)
    p_doctor.add_argument("--state-file")
    p_doctor.add_argument("--update-state", action="store_true")
    p_doctor.add_argument("--clean-surface", action="store_true", default=None)
    p_doctor.add_argument("--artifact-viable", action="store_true", default=None)
    p_doctor.add_argument("--helper-ok", action="store_true", default=None)
    p_doctor.add_argument("--credentials-ok", action="store_true", default=None)
    p_doctor.add_argument("--prompt-identity-ok", action="store_true", default=None)
    p_doctor.add_argument("--artifact-path")
    p_doctor.add_argument("--helper-path")
    p_doctor.add_argument("--credential-env", action="append", default=[])
    p_doctor.add_argument("--prompt-identity-file")
    p_doctor.add_argument("--expected-task-identity")
    p_doctor.add_argument("--target-identity-file")
    p_doctor.add_argument("--expected-target-identity")
    p_doctor.add_argument("--changed-file", action="append", default=[])
    p_doctor.add_argument("--allowed-scope-path", action="append", default=[])
    p_doctor.set_defaults(func=cmd_doctor)

    p_compare = sub.add_parser("compare")
    p_compare.add_argument("--baseline-file", required=True)
    p_compare.add_argument("--synrail-file", required=True)
    p_compare.add_argument("--output", required=True)
    p_compare.set_defaults(func=cmd_compare)

    p_substitute_pressure = sub.add_parser("substitute-pressure")
    p_substitute_pressure.add_argument("--record", action="append", required=True)
    p_substitute_pressure.add_argument("--output", required=True)
    p_substitute_pressure.set_defaults(func=cmd_substitute_pressure)

    p_hybrid = sub.add_parser("hybrid-status")
    p_hybrid.add_argument("--cost-record", required=True)
    p_hybrid.add_argument("--hybrid-record", action="append", required=True)
    p_hybrid.add_argument("--output", required=True)
    p_hybrid.set_defaults(func=cmd_hybrid_status)

    p_mode = sub.add_parser("recommend-mode")
    p_mode.add_argument("--cost-record", required=True)
    p_mode.add_argument("--hybrid-status")
    p_mode.add_argument("--scenario-class", required=True)
    p_mode.add_argument("--task-class", required=True)
    p_mode.add_argument("--false-success-risk", required=True, choices=["LOW", "MEDIUM", "HIGH"])
    p_mode.add_argument("--recovery-cost", required=True, choices=["LOW", "MEDIUM", "HIGH"])
    p_mode.add_argument("--execution-surface-ambiguous", action="store_true")
    p_mode.add_argument("--artifact-truth-nontrivial", action="store_true")
    p_mode.add_argument("--explicit-hybrid-ambiguity")
    p_mode.add_argument("--governed-cost-delta")
    p_mode.add_argument("--output", required=True)
    p_mode.set_defaults(func=cmd_recommend_mode)

    p_select = sub.add_parser("select-mode")
    p_select.add_argument("--recommendation-file", required=True)
    p_select.add_argument("--selected-mode", choices=["FULL_GOVERNED_PATH", "LIGHTWEIGHT_BASELINE", "HYBRID_EXCEPTION"])
    p_select.add_argument("--selected-with-preparation", action="store_true")
    p_select.add_argument("--output", required=True)
    p_select.set_defaults(func=cmd_select_mode)

    p_plan = sub.add_parser("plan-proof")
    p_plan.add_argument("--run-id", required=True)
    p_plan.add_argument("--task-class", required=True)
    p_plan.add_argument("--artifact-root", required=True)
    p_plan.add_argument("--baseline-identity", required=True)
    p_plan.add_argument("--execution-surface-identity", required=True)
    p_plan.add_argument("--prompt-identity", required=True)
    p_plan.add_argument("--task-identity", required=True)
    p_plan.add_argument("--output", required=True)
    p_plan.set_defaults(func=cmd_plan_proof)

    p_prep = sub.add_parser("preparation-receipt")
    p_prep.add_argument("--plan-file", required=True)
    p_prep.add_argument("--bundle-file", required=True)
    p_prep.add_argument("--output", required=True)
    p_prep.set_defaults(func=cmd_preparation_receipt)

    p_governed_cost = sub.add_parser("governed-cost")
    p_governed_cost.add_argument("--unprepared-file", required=True)
    p_governed_cost.add_argument("--prepared-file", required=True)
    p_governed_cost.add_argument("--output", required=True)
    p_governed_cost.set_defaults(func=cmd_governed_cost)

    p_checkpoint_create = sub.add_parser("create-checkpoint")
    p_checkpoint_create.add_argument("--checkpoint-id")
    p_checkpoint_create.add_argument("--artifact-root")
    p_checkpoint_create.add_argument("--checkpoint-root")
    p_checkpoint_create.add_argument("--state-file")
    p_checkpoint_create.add_argument("--report-file")
    p_checkpoint_create.add_argument("--orchestration-file")
    p_checkpoint_create.add_argument("--bundle-file")
    p_checkpoint_create.add_argument("--closure-file")
    p_checkpoint_create.add_argument("--refresh-file")
    p_checkpoint_create.add_argument("--selection-file")
    p_checkpoint_create.add_argument("--preparation-file")
    p_checkpoint_create.add_argument("--repair-packet-file")
    p_checkpoint_create.add_argument("--repair-handoff-file")
    p_checkpoint_create.add_argument("--repair-receipt-file")
    p_checkpoint_create.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_create.add_argument("--output")
    p_checkpoint_create.set_defaults(func=cmd_create_checkpoint)

    p_save = sub.add_parser("save")
    p_save.add_argument("--checkpoint-id", default="working")
    p_save.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_save.add_argument("--checkpoint-root")
    p_save.add_argument("--state-file")
    p_save.add_argument("--report-file")
    p_save.add_argument("--orchestration-file")
    p_save.add_argument("--bundle-file")
    p_save.add_argument("--closure-file")
    p_save.add_argument("--refresh-file")
    p_save.add_argument("--selection-file")
    p_save.add_argument("--preparation-file")
    p_save.add_argument("--repair-packet-file")
    p_save.add_argument("--repair-handoff-file")
    p_save.add_argument("--repair-receipt-file")
    p_save.add_argument("--mode", default="default", choices=["default", "dev"])
    p_save.add_argument("--output")
    p_save.set_defaults(func=cmd_save)

    p_checkpoint_verify = sub.add_parser("verify-checkpoint", aliases=["confirm-restore"])
    p_checkpoint_verify.add_argument("--artifact-root")
    p_checkpoint_verify.add_argument("--checkpoint-id")
    p_checkpoint_verify.add_argument("--checkpoint-record-file")
    p_checkpoint_verify.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_verify.add_argument("--output")
    p_checkpoint_verify.set_defaults(func=cmd_verify_checkpoint)

    p_checkpoint_restore = sub.add_parser("restore-checkpoint")
    p_checkpoint_restore.add_argument("--artifact-root")
    p_checkpoint_restore.add_argument("--checkpoint-id")
    p_checkpoint_restore.add_argument("--checkpoint-record-file")
    p_checkpoint_restore.add_argument("--target-root")
    p_checkpoint_restore.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_restore.add_argument("--output")
    p_checkpoint_restore.set_defaults(func=cmd_restore_checkpoint)

    p_checkpoint = sub.add_parser("checkpoint")
    checkpoint_sub = p_checkpoint.add_subparsers(dest="checkpoint_cmd", required=True)

    p_checkpoint_nested_create = checkpoint_sub.add_parser("create")
    p_checkpoint_nested_create.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_checkpoint_nested_create.add_argument("--checkpoint-id", default="working")
    p_checkpoint_nested_create.add_argument("--checkpoint-root")
    p_checkpoint_nested_create.add_argument("--state-file")
    p_checkpoint_nested_create.add_argument("--report-file")
    p_checkpoint_nested_create.add_argument("--orchestration-file")
    p_checkpoint_nested_create.add_argument("--bundle-file")
    p_checkpoint_nested_create.add_argument("--closure-file")
    p_checkpoint_nested_create.add_argument("--refresh-file")
    p_checkpoint_nested_create.add_argument("--selection-file")
    p_checkpoint_nested_create.add_argument("--preparation-file")
    p_checkpoint_nested_create.add_argument("--repair-packet-file")
    p_checkpoint_nested_create.add_argument("--repair-handoff-file")
    p_checkpoint_nested_create.add_argument("--repair-receipt-file")
    p_checkpoint_nested_create.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_nested_create.add_argument("--output")
    p_checkpoint_nested_create.set_defaults(func=cmd_create_checkpoint)

    p_checkpoint_nested_verify = checkpoint_sub.add_parser("verify")
    p_checkpoint_nested_verify.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_checkpoint_nested_verify.add_argument("--checkpoint-id")
    p_checkpoint_nested_verify.add_argument("--checkpoint-record-file")
    p_checkpoint_nested_verify.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_nested_verify.add_argument("--output")
    p_checkpoint_nested_verify.set_defaults(func=cmd_verify_checkpoint)

    p_checkpoint_nested_restore = checkpoint_sub.add_parser("restore")
    p_checkpoint_nested_restore.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_checkpoint_nested_restore.add_argument("--checkpoint-id")
    p_checkpoint_nested_restore.add_argument("--checkpoint-record-file")
    p_checkpoint_nested_restore.add_argument("--target-root")
    p_checkpoint_nested_restore.add_argument("--mode", default="default", choices=["default", "dev"])
    p_checkpoint_nested_restore.add_argument("--output")
    p_checkpoint_nested_restore.set_defaults(func=cmd_restore_checkpoint)

    p_restore = sub.add_parser("restore")
    p_restore.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_restore.add_argument("--checkpoint-id")
    p_restore.add_argument("--checkpoint-record-file")
    p_restore.add_argument("--target-root")
    p_restore.add_argument("--mode", default="default", choices=["default", "dev"])
    p_restore.add_argument("--output")
    p_restore.set_defaults(func=cmd_restore)

    p_telemetry = sub.add_parser("telemetry")
    telemetry_sub = p_telemetry.add_subparsers(dest="telemetry_cmd", required=True)

    p_telemetry_enable = telemetry_sub.add_parser("enable")
    p_telemetry_enable.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_telemetry_enable.add_argument("--tester-id", default="alpha_tester")
    p_telemetry_enable.set_defaults(func=cmd_telemetry_enable)

    p_telemetry_export = telemetry_sub.add_parser("export")
    p_telemetry_export.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_telemetry_export.add_argument("--output")
    p_telemetry_export.add_argument("--issue-output")
    p_telemetry_export.set_defaults(func=cmd_telemetry_export)

    p_artifact_consistency = sub.add_parser("artifact-consistency")
    p_artifact_consistency.add_argument("--artifact-root")
    p_artifact_consistency.add_argument("--state-file")
    p_artifact_consistency.add_argument("--output")
    p_artifact_consistency.add_argument("--report-file")
    p_artifact_consistency.add_argument("--orchestration-file")
    p_artifact_consistency.add_argument("--run-file")
    p_artifact_consistency.add_argument("--repair-packet-file")
    p_artifact_consistency.add_argument("--repair-handoff-file")
    p_artifact_consistency.add_argument("--repair-receipt-file")
    p_artifact_consistency.set_defaults(func=cmd_artifact_consistency)

    p_observability = sub.add_parser("observability")
    p_observability.add_argument("--state-file", required=True)
    p_observability.add_argument("--report-file", required=True)
    p_observability.add_argument("--output", required=True)
    p_observability.add_argument("--repair-packet-file")
    p_observability.add_argument("--repair-receipt-file")
    p_observability.add_argument("--refresh-file")
    p_observability.set_defaults(func=cmd_observability)

    p_session_export = sub.add_parser("session-export")
    p_session_export.add_argument("--artifact-root")
    p_session_export.add_argument("--state-file")
    p_session_export.add_argument("--report-file")
    p_session_export.add_argument("--output")
    p_session_export.add_argument("--repair-packet-file")
    p_session_export.add_argument("--repair-receipt-file")
    p_session_export.add_argument("--refresh-file")
    p_session_export.set_defaults(func=cmd_session_export)

    p_deploy = sub.add_parser("deploy")
    p_deploy.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_deploy.add_argument("--state-file")
    p_deploy.add_argument("--deploy-run-id")
    p_deploy.add_argument("--deploy-target")
    p_deploy.add_argument("--mode", default="default", choices=["default", "dev"])
    p_deploy.set_defaults(func=cmd_deploy)

    p_deploy_check = sub.add_parser("deploy-check")
    p_deploy_check.add_argument("--artifact-root", default=DEFAULT_ALPHA_ARTIFACT_ROOT)
    p_deploy_check.add_argument("--state-file")
    p_deploy_check.set_defaults(func=cmd_deploy_check)

    p_bug_packet = sub.add_parser("bug-packet")
    p_bug_packet.add_argument("--artifact-root")
    p_bug_packet.add_argument("--state-file")
    p_bug_packet.add_argument("--report-file")
    p_bug_packet.add_argument("--output")
    p_bug_packet.add_argument("--doctor-file")
    p_bug_packet.add_argument("--acceptance-validation-file")
    p_bug_packet.add_argument("--repair-packet-file")
    p_bug_packet.add_argument("--observability-file")
    p_bug_packet.add_argument("--thin-output-file")
    p_bug_packet.add_argument("--issue-output")
    p_bug_packet.set_defaults(func=cmd_bug_packet)

    p_thin_output = sub.add_parser("thin-output")
    p_thin_output.add_argument("--artifact-root")
    p_thin_output.add_argument("--state-file")
    p_thin_output.add_argument("--report-file")
    p_thin_output.add_argument("--mode", required=True, choices=["default", "dev"])
    p_thin_output.add_argument("--output")
    p_thin_output.add_argument("--repair-packet-file")
    p_thin_output.add_argument("--doctor-file")
    p_thin_output.add_argument("--checkpoint-id")
    p_thin_output.add_argument("--checkpoint-record-file")
    p_thin_output.add_argument("--consistency-recovery-file")
    p_thin_output.set_defaults(func=cmd_thin_output)

    p_generate_prompt = sub.add_parser("generate-prompt", aliases=["next-step", "repair-step"])
    p_generate_prompt.add_argument("--artifact-root")
    p_generate_prompt.add_argument("--repair-packet-file")
    p_generate_prompt.add_argument("--mode", default="default", choices=["default", "dev"])
    p_generate_prompt.add_argument("--output")
    p_generate_prompt.add_argument("--checkpoint-id")
    p_generate_prompt.add_argument("--checkpoint-record-file")
    p_generate_prompt.add_argument("--doctor-file")
    p_generate_prompt.set_defaults(func=cmd_generate_prompt)

    p_thin_output_reading = sub.add_parser("thin-output-reading")
    p_thin_output_reading.add_argument("--thin-output-file", required=True)
    p_thin_output_reading.add_argument("--prompt-bridge-file", required=True)
    p_thin_output_reading.add_argument("--report-file", required=True)
    p_thin_output_reading.add_argument("--repair-packet-file", required=True)
    p_thin_output_reading.add_argument("--output", required=True)
    p_thin_output_reading.set_defaults(func=cmd_thin_output_reading)

    p_prompt_followup = sub.add_parser("prompt-followup")
    p_prompt_followup.add_argument("--repair-packet-file", required=True)
    p_prompt_followup.add_argument("--prompt-bridge-file", required=True)
    p_prompt_followup.add_argument("--output", required=True)
    p_prompt_followup.add_argument("--thin-output-file")
    p_prompt_followup.set_defaults(func=cmd_prompt_followup)

    p_prompt_retry_guard = sub.add_parser("prompt-retry-guard")
    p_prompt_retry_guard.add_argument("--packet-a-file", required=True)
    p_prompt_retry_guard.add_argument("--prompt-a-file", required=True)
    p_prompt_retry_guard.add_argument("--packet-b-file", required=True)
    p_prompt_retry_guard.add_argument("--prompt-b-file", required=True)
    p_prompt_retry_guard.add_argument("--output", required=True)
    p_prompt_retry_guard.set_defaults(func=cmd_prompt_retry_guard)

    p_consistency_recovery = sub.add_parser("consistency-recovery")
    p_consistency_recovery.add_argument("--consistency-file", required=True)
    p_consistency_recovery.add_argument("--output", required=True)
    p_consistency_recovery.add_argument("--checkpoint-record-file")
    p_consistency_recovery.set_defaults(func=cmd_consistency_recovery)

    p_checkpoint_operator_reading = sub.add_parser("checkpoint-operator-reading")
    p_checkpoint_operator_reading.add_argument("--second-operator-file", required=True)
    p_checkpoint_operator_reading.add_argument("--thin-output-file", required=True)
    p_checkpoint_operator_reading.add_argument("--repair-packet-file", required=True)
    p_checkpoint_operator_reading.add_argument("--output", required=True)
    p_checkpoint_operator_reading.set_defaults(func=cmd_checkpoint_operator_reading)

    p_consistency_recovery_prompt = sub.add_parser("consistency-recovery-prompt")
    p_consistency_recovery_prompt.add_argument("--consistency-recovery-file", required=True)
    p_consistency_recovery_prompt.add_argument("--output", required=True)
    p_consistency_recovery_prompt.add_argument("--thin-output-file")
    p_consistency_recovery_prompt.set_defaults(func=cmd_consistency_recovery_prompt)

    p_consistency_recovery_prompt_reading = sub.add_parser("consistency-recovery-prompt-reading")
    p_consistency_recovery_prompt_reading.add_argument("--consistency-recovery-file", required=True)
    p_consistency_recovery_prompt_reading.add_argument("--prompt-file", required=True)
    p_consistency_recovery_prompt_reading.add_argument("--output", required=True)
    p_consistency_recovery_prompt_reading.set_defaults(func=cmd_consistency_recovery_prompt_reading)

    p_reproducibility = sub.add_parser("reproducibility")
    p_reproducibility.add_argument("--run-a", required=True)
    p_reproducibility.add_argument("--run-b", required=True)
    p_reproducibility.add_argument("--output", required=True)
    p_reproducibility.set_defaults(func=cmd_reproducibility)

    p_second_operator = sub.add_parser("second-operator")
    p_second_operator.add_argument("--state-file", required=True)
    p_second_operator.add_argument("--repair-packet-file", required=True)
    p_second_operator.add_argument("--run-file", required=True)
    p_second_operator.add_argument("--output", required=True)
    p_second_operator.set_defaults(func=cmd_second_operator)

    p_operator_brief = sub.add_parser("operator-brief")
    p_operator_brief.add_argument("--state-file", required=True)
    p_operator_brief.add_argument("--report-file", required=True)
    p_operator_brief.add_argument("--repair-packet-file", required=True)
    p_operator_brief.add_argument("--doctor-file")
    p_operator_brief.add_argument("--output", required=True)
    p_operator_brief.set_defaults(func=cmd_operator_brief)

    p_operator_brief_chain = sub.add_parser("operator-brief-chain")
    p_operator_brief_chain.add_argument("--brief", action="append", required=True)
    p_operator_brief_chain.add_argument("--output", required=True)
    p_operator_brief_chain.set_defaults(func=cmd_operator_brief_chain)

    p_operator_render = sub.add_parser("operator-render")
    p_operator_render.add_argument("--brief-file")
    p_operator_render.add_argument("--chain-file")
    p_operator_render.add_argument("--output", required=True)
    p_operator_render.set_defaults(func=cmd_operator_render)

    p_operator_render_adoption = sub.add_parser("operator-render-adoption")
    p_operator_render_adoption.add_argument("--source", required=True)
    p_operator_render_adoption.add_argument("--render", required=True)
    p_operator_render_adoption.add_argument("--label", required=True)
    p_operator_render_adoption.add_argument("--output", required=True)
    p_operator_render_adoption.set_defaults(func=cmd_operator_render_adoption)

    p_operator_render_adoption_delta = sub.add_parser("operator-render-adoption-delta")
    p_operator_render_adoption_delta.add_argument("--record", action="append", required=True)
    p_operator_render_adoption_delta.add_argument("--output", required=True)
    p_operator_render_adoption_delta.set_defaults(func=cmd_operator_render_adoption_delta)

    p_operator_reading = sub.add_parser("operator-reading")
    p_operator_reading.add_argument("--second-operator-file", required=True)
    p_operator_reading.add_argument("--brief-file", required=True)
    p_operator_reading.add_argument("--render-file", required=True)
    p_operator_reading.add_argument("--label", required=True)
    p_operator_reading.add_argument("--output", required=True)
    p_operator_reading.set_defaults(func=cmd_operator_reading)

    p_externality_pressure = sub.add_parser("externality-pressure")
    p_externality_pressure.add_argument("--reproducibility-file", required=True)
    p_externality_pressure.add_argument("--second-operator-file", required=True)
    p_externality_pressure.add_argument("--operator-reading-file", required=True)
    p_externality_pressure.add_argument("--label", required=True)
    p_externality_pressure.add_argument("--output", required=True)
    p_externality_pressure.set_defaults(func=cmd_externality_pressure)

    p_repair_handoff = sub.add_parser("repair-handoff")
    p_repair_handoff.add_argument("--state-file", required=True)
    p_repair_handoff.add_argument("--output", required=True)
    p_repair_handoff.set_defaults(func=cmd_repair_handoff)

    p_repair_packet = sub.add_parser("repair-packet")
    p_repair_packet.add_argument("--state-file", required=True)
    p_repair_packet.add_argument("--artifact-root", required=True)
    p_repair_packet.add_argument("--output", required=True)
    p_repair_packet.add_argument("--previous-packet-file")
    p_repair_packet.add_argument("--repair-handoff-file")
    p_repair_packet.add_argument("--mode-selection-receipt")
    p_repair_packet.add_argument("--preparation-receipt-file")
    p_repair_packet.add_argument("--repair-receipt-file")
    p_repair_packet.add_argument("--report-file")
    p_repair_packet.add_argument("--doctor-run-id")
    p_repair_packet.add_argument("--doctor-level", choices=["CORE_DOCTOR", "SUPPORT_DOCTOR", "EXACT_RETRY_DOCTOR"])
    p_repair_packet.add_argument("--target-path")
    p_repair_packet.add_argument("--target-classification")
    p_repair_packet.add_argument("--baseline-identity")
    p_repair_packet.add_argument("--intended-run-class", choices=["core_probe", "support_run", "exact_retry"])
    p_repair_packet.add_argument("--execution-surface-identity")
    p_repair_packet.add_argument("--final-result", default="")
    p_repair_packet.add_argument("--prompt-identity", default="")
    p_repair_packet.add_argument("--task-identity", default="")
    p_repair_packet.add_argument("--prompt-identity-ok", action="store_true", default=None)
    p_repair_packet.add_argument("--readback")
    p_repair_packet.add_argument("--scenario-proof")
    p_repair_packet.add_argument("--target-identity-file")
    p_repair_packet.add_argument("--clean-surface", action="store_true", default=None)
    p_repair_packet.add_argument("--artifact-viable", action="store_true", default=None)
    p_repair_packet.add_argument("--helper-ok", action="store_true", default=None)
    p_repair_packet.add_argument("--credentials-ok", action="store_true", default=None)
    p_repair_packet.add_argument("--artifact-path")
    p_repair_packet.add_argument("--helper-path")
    p_repair_packet.add_argument("--credential-env", action="append", default=[])
    p_repair_packet.add_argument("--refresh-output")
    p_repair_packet.add_argument("--refresh-event-type")
    p_repair_packet.add_argument("--refresh-recovery-status", choices=["NOT_REQUIRED", "PENDING", "COMPLETE"], default="NOT_REQUIRED")
    p_repair_packet.add_argument("--refresh-reverification-complete", action="store_true", default=None)
    p_repair_packet.add_argument("--refresh-use-bundle", action="store_true", default=None)
    p_repair_packet.add_argument("--refresh-use-closure", action="store_true", default=None)
    p_repair_packet.set_defaults(func=cmd_repair_packet)

    p_orchestrate = sub.add_parser("orchestrate")
    add_orchestration_args(p_orchestrate, include_resume_from_state=True)
    p_orchestrate.set_defaults(func=cmd_orchestrate)

    p_resume = sub.add_parser("resume", aliases=["continue", "retry"])
    add_orchestration_args(p_resume, include_resume_from_state=False, relaxed_runtime=True)
    p_resume.add_argument("--mode", default="default", choices=["default", "dev"])
    p_resume.set_defaults(func=cmd_resume)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    caught: Exception | None = None
    exit_code = 1
    try:
        exit_code = int(args.func(args))
    except Exception as exc:
        caught = exc
    root = alpha_root_from_args(args) if getattr(args, "cmd", None) else None
    if (
        caught is None
        and getattr(args, "cmd", None) in {"init", "start"}
        and getattr(args, "telemetry_opt_in", False)
        and exit_code == 0
        and root is not None
    ):
        enable_telemetry(root, getattr(args, "tester_id", "alpha_tester"))
    try:
        maybe_capture_alpha_telemetry(
            args,
            exit_code=exit_code,
            explicit_error_class=caught.__class__.__name__ if caught else "",
        )
    except Exception:
        pass
    if caught is not None:
        raise caught
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
