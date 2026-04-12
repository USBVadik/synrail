#!/usr/bin/env python3
"""Minimal terminal-first CLI facade for Synrail v0."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPINE = HERE / "synrail_spine_v0.py"
BUNDLE = HERE / "synrail_bundle_v0.py"
CLOSURE = HERE / "synrail_closure_v0.py"
REFRESH = HERE / "synrail_refresh_v0.py"


def run_python(script: Path, args: list[str]) -> int:
    cmd = [sys.executable, str(script), *args]
    return subprocess.run(cmd, check=False).returncode


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


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


def cmd_closure(args: argparse.Namespace) -> int:
    forwarded = [
        "--state-file", args.state_file,
        "--bundle-file", args.bundle_file,
        "--output", args.output,
    ]
    if args.update_state:
        forwarded.append("--update-state")
    return run_python(CLOSURE, forwarded)


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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail")
    sub = parser.add_subparsers(dest="cmd", required=True)

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

    p_closure = sub.add_parser("closure")
    p_closure.add_argument("--state-file", required=True)
    p_closure.add_argument("--bundle-file", required=True)
    p_closure.add_argument("--output", required=True)
    p_closure.add_argument("--update-state", action="store_true")
    p_closure.set_defaults(func=cmd_closure)

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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
