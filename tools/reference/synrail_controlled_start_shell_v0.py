#!/usr/bin/env python3
"""Extracted controlled-start shell helpers for Synrail v0."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Callable


def _print_completed_failure(completed) -> int:
    if completed.stderr.strip():
        print(completed.stderr.strip(), file=sys.stderr)
    if completed.stdout.strip():
        print(completed.stdout.strip())
    return completed.returncode


def cmd_init(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    default_alpha_run_id: Callable[[], str],
    alpha_file: Callable[[Path, str], Path],
    default_task_class: str,
    spine_script: Path,
    run_python: Callable[[Path, list[str]], int],
    run_python_capture: Callable[[Path, list[str]], object],
    save_project_profile: Callable[[Path, dict], None],
    build_project_profile: Callable[..., dict],
    save_alpha_identity_files: Callable[..., None],
    write_acceptance_criteria: Callable[..., object],
    print_init_summary: Callable[..., None],
) -> int:
    root = alpha_root_from_args(args, ensure=True)
    project_root = Path(getattr(args, "project_root", "") or Path.cwd()).resolve()
    if not getattr(args, "run_id", None):
        args.run_id = default_alpha_run_id()
    if not getattr(args, "task_class", None):
        args.task_class = default_task_class
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
        code = run_python(spine_script, forwarded)
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
    completed = run_python_capture(spine_script, forwarded)
    if completed.returncode != 0:
        return _print_completed_failure(completed)
    if root:
        save_project_profile(root, build_project_profile(project_root=project_root, root=root, task_class=args.task_class))
        save_alpha_identity_files(
            root,
            task_identity=getattr(args, "task_identity", ""),
            prompt_identity=getattr(args, "prompt_identity", ""),
        )
        criteria_completed = write_acceptance_criteria(root, generated_by="synrail init")
        if criteria_completed.returncode != 0:
            return _print_completed_failure(criteria_completed)
        print_init_summary(root=root, state_file=Path(args.output))
    return 0


def cmd_start(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    alpha_file: Callable[[Path, str], Path],
    load_json: Callable[[Path], dict],
    default_alpha_run_id: Callable[[], str],
    default_task_class: str,
    resolve_start_identities: Callable[..., tuple[str, str]],
    plain_shell_command: Callable[..., str],
    existing_preferred_proof_artifacts: Callable[[Path], list[str]],
    terminal_run_states: set[str],
    shell_command: Callable[..., str],
    print_existing_run_summary: Callable[..., None],
    run_python_capture: Callable[[Path, list[str]], object],
    spine_script: Path,
    build_project_profile: Callable[..., dict],
    save_project_profile: Callable[[Path, dict], None],
    clear_runtime_artifacts_for_start: Callable[[Path], None],
    save_alpha_identity_files: Callable[..., None],
    write_controlled_start_artifacts: Callable[..., None],
    write_acceptance_criteria: Callable[..., object],
    apply_bootstrap_defaults: Callable[..., dict | None],
    save_bootstrap_json: Callable[[Path, dict], None],
    update_last_known_final_result_hash: Callable[[Path, Path | None], None],
    preferred_proof_artifact_paths: Callable[[Path], dict[str, Path]],
    print_start_summary: Callable[..., None],
) -> int:
    root = alpha_root_from_args(args, ensure=True)
    project_root = Path(getattr(args, "project_root", "") or Path.cwd()).resolve()
    if not getattr(args, "output", None):
        if not root:
            raise ValueError("output or artifact root is required")
        args.output = str(alpha_file(root, "state"))

    existing_state_path = Path(args.output)
    existing_state = None
    if existing_state_path.exists():
        try:
            existing_state = load_json(existing_state_path)
        except (OSError, json.JSONDecodeError):
            if args.mode == "dev":
                print(
                    json.dumps(
                        {
                            "result": "ERROR",
                            "reason": "CONTROLLED_START_STATE_UNREADABLE",
                            "state_file": str(existing_state_path),
                            "next_safe_step": "move the corrupted artifact root aside or restore a verified checkpoint before retrying",
                        },
                        ensure_ascii=True,
                    )
                )
            else:
                print("Synrail could not start this run in controlled mode yet.")
                print("What happened: the current run state artifact is unreadable.")
                print(
                    "What to do next: move the corrupted artifact root aside or restore a verified checkpoint before retrying."
                )
            return 2
    if not getattr(args, "run_id", None):
        args.run_id = default_alpha_run_id()
    if not getattr(args, "task_class", None):
        args.task_class = existing_state.get("task_class", default_task_class) if existing_state else default_task_class

    task_identity, prompt_identity = resolve_start_identities(args, root=root)
    if not task_identity:
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "TASK_IDENTITY_REQUIRED_FOR_CONTROLLED_START"}, ensure_ascii=True))
        else:
            print("Synrail could not start a controlled run yet.")
            print("What is missing: the original task request for this run.")
            print(
                "What to do next: run `"
                + plain_shell_command("start", "Describe the bounded local change.", project_root=project_root)
                + "` or pass --task-identity, then retry."
            )
        return 2

    existing_proof = existing_preferred_proof_artifacts(root)
    previous_state = existing_state.get("state", "") if existing_state else ""
    active_bootstrap = alpha_file(root, "bootstrap").exists()
    if existing_state and active_bootstrap and previous_state and previous_state not in terminal_run_states and not existing_proof:
        if args.mode == "dev":
            print(
                json.dumps(
                    {
                        "result": "OK",
                        "reason": "CONTROLLED_RUN_ALREADY_ACTIVE",
                        "reused_existing_run": True,
                        "run_id": existing_state.get("run_id", ""),
                        "next_command": shell_command(root, "check", project_root=project_root),
                    },
                    ensure_ascii=True,
                )
            )
        else:
            print_existing_run_summary(root=root, state_file=existing_state_path, project_root=project_root)
        return 0
    if existing_proof:
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
    completed = run_python_capture(spine_script, forwarded)
    if completed.returncode != 0:
        return _print_completed_failure(completed)

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
        return _print_completed_failure(criteria_completed)
    validation = apply_bootstrap_defaults(args, root=root)
    if validation:
        save_bootstrap_json(alpha_file(root, "bootstrap_validation"), validation)
    update_last_known_final_result_hash(
        Path(args.output),
        preferred_proof_artifact_paths(root)["final_result"],
    )
    print_start_summary(root=root, state_file=Path(args.output), project_root=project_root)
    return 0


def cmd_refresh_acceptance(
    args: argparse.Namespace,
    *,
    alpha_root_from_args: Callable[..., Path | None],
    load_json: Callable[[Path], dict],
    alpha_file: Callable[[Path, str], Path],
    write_acceptance_criteria: Callable[..., object],
    write_acceptance_validation: Callable[..., object],
    print_acceptance_refresh_summary: Callable[..., None],
) -> int:
    root = alpha_root_from_args(args, ensure=True)
    if not root:
        print(json.dumps({"result": "ERROR", "reason": "ARTIFACT_ROOT_REQUIRED"}, ensure_ascii=True))
        return 2
    profile = alpha_file(root, "project_profile")
    if not profile.exists():
        if args.mode == "dev":
            print(json.dumps({"result": "ERROR", "reason": "PROJECT_PROFILE_REQUIRED"}, ensure_ascii=True))
        else:
            print("Synrail could not refresh the acceptance rules yet.")
            print("What to do next: run synrail start first so Synrail can capture the controlled project profile.")
        return 2
    completed = write_acceptance_criteria(root, generated_by="synrail refresh-acceptance")
    if completed.returncode != 0:
        return _print_completed_failure(completed)
    state_file = alpha_file(root, "state")
    if state_file.exists():
        validation_completed = write_acceptance_validation(root, criteria_file=alpha_file(root, "acceptance_criteria"), state_file=state_file)
        if validation_completed.returncode != 0:
            return _print_completed_failure(validation_completed)
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
