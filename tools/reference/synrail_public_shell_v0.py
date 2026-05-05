#!/usr/bin/env python3
"""Extracted public-shell helpers for Synrail v0."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class PublicShellContext:
    alpha_root_from_args: Callable[..., Path | None]
    default_workspace_artifact_root: Callable[..., Path]
    alpha_file: Callable[[Path, str], Path]
    load_json: Callable[[Path], dict]
    display_path: Callable[[Path], str]
    ensure_run_state_extensions: Callable[[dict], dict]
    build_workspace_status: Callable[..., dict]
    print_workspace_dashboard: Callable[[dict], None]
    build_proof_explanation: Callable[..., dict]
    print_proof_explanation: Callable[[dict], None]
    final_result_template_payload: Callable[..., dict]
    scenario_proof_template_text: Callable[..., str]
    readback_template_text: Callable[..., str]
    runtime_helper_text: Callable[..., str]


def default_public_shell_root(args: argparse.Namespace, *, context: PublicShellContext) -> Path:
    return context.alpha_root_from_args(args) or context.default_workspace_artifact_root(project_root=Path.cwd().resolve())


def cmd_status(
    args: argparse.Namespace,
    *,
    context: PublicShellContext,
) -> int:
    project_root = Path.cwd().resolve()
    root = context.alpha_root_from_args(args) or context.default_workspace_artifact_root(project_root=project_root)
    state_path: Path | None = None
    if getattr(args, "state_file", None):
        state_path = Path(args.state_file).expanduser().resolve()
        default_state_path = context.alpha_file(root, "state")
        if state_path != default_state_path.resolve():
            root = state_path.parent
    summary = context.build_workspace_status(root, project_root=project_root, state_path=state_path)
    state_path = (state_path or context.alpha_file(root, "state")).resolve()
    if state_path.exists():
        state = context.ensure_run_state_extensions(context.load_json(state_path))
        summary.update(
            {
                "run_id": state.get("run_id", ""),
                "task_class": state.get("task_class", ""),
                "state": state.get("state", ""),
                "target_surface": state.get("target_surface", {}).get("status", ""),
                "doctor": state.get("doctor", {}).get("status", ""),
                "proof_bundle": state.get("proof_bundle", {}).get("status", ""),
                "closure": state.get("closure", {}).get("status", ""),
                "next_safe_step": state.get("next_safe_step", ""),
            }
        )
    if getattr(args, "json", False):
        print(json.dumps(summary, indent=2, ensure_ascii=True))
    else:
        context.print_workspace_dashboard(summary)
    return 0


def cmd_explain_proof(
    args: argparse.Namespace,
    *,
    context: PublicShellContext,
) -> int:
    root = default_public_shell_root(args, context=context)
    bundle_file = Path(getattr(args, "bundle_file", "") or context.alpha_file(root, "bundle")).expanduser().resolve()
    if not bundle_file.exists():
        if getattr(args, "json", False):
            print(json.dumps({"result": "ERROR", "reason": "BUNDLE_FILE_REQUIRED", "next_command": "synrail check"}, ensure_ascii=True))
        else:
            print("Synrail does not have a proof explanation yet.")
            print("What is missing: bundle.json has not been generated for this run.")
            print("What to do next: run synrail check first so Synrail can evaluate the current proof bundle.")
        return 2
    bundle = context.load_json(bundle_file)
    explanation = context.build_proof_explanation(bundle, root=root)
    if getattr(args, "json", False):
        print(json.dumps(explanation, indent=2, ensure_ascii=True))
    else:
        context.print_proof_explanation(explanation, root=root)
    return 0


def write_text_output(*, text: str, output: str | None, display_path: Callable[[Path], str], written_label: str) -> int:
    if output:
        target = Path(output).expanduser().resolve()
        target.write_text(text)
        print(f"{written_label} {display_path(target)}")
    else:
        print(text, end="")
    return 0


def cmd_final_result_template(
    args: argparse.Namespace,
    *,
    context: PublicShellContext,
) -> int:
    root = default_public_shell_root(args, context=context)
    payload = context.final_result_template_payload(root=root if root.exists() else None)
    text = json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
    return write_text_output(
        text=text,
        output=getattr(args, "output", None),
        display_path=context.display_path,
        written_label="Wrote canonical final_result template to",
    )


def cmd_scenario_proof_template(
    args: argparse.Namespace,
    *,
    context: PublicShellContext,
) -> int:
    root = default_public_shell_root(args, context=context)
    text = context.scenario_proof_template_text(root=root if root.exists() else None)
    return write_text_output(
        text=text,
        output=getattr(args, "output", None),
        display_path=context.display_path,
        written_label="Wrote canonical scenario_proof template to",
    )


def cmd_readback_template(
    args: argparse.Namespace,
    *,
    context: PublicShellContext,
) -> int:
    root = default_public_shell_root(args, context=context)
    text = context.readback_template_text(root=root if root.exists() else None)
    return write_text_output(
        text=text,
        output=getattr(args, "output", None),
        display_path=context.display_path,
        written_label="Wrote canonical readback template to",
    )


def cmd_runtime_helper(
    args: argparse.Namespace,
    *,
    context: PublicShellContext,
) -> int:
    root = default_public_shell_root(args, context=context)
    text = context.runtime_helper_text(root=root if root.exists() else None)
    return write_text_output(
        text=text,
        output=getattr(args, "output", None),
        display_path=context.display_path,
        written_label="Wrote runtime helper guidance to",
    )
