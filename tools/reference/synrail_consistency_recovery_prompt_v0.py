#!/usr/bin/env python3
"""Build a bounded next-agent prompt from a consistency recovery plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_record(*, recovery: dict, thin_output: dict | None = None) -> dict:
    allowed_scope = list(recovery.get("restore_artifact_ids", [])) + list(recovery.get("reemit_artifact_ids", []))
    forbidden_scope = [
        "Do not modify state_file.",
        "Do not broaden scope beyond the listed artifact recovery actions.",
        "Do not claim readiness, closure, or acceptance from artifact recovery alone.",
    ]
    must_pass = list(recovery.get("operator_instructions", []))
    must_pass.append("Preserve the current non-green contour while restoring or re-emitting derived artifacts.")
    prompt_lines = [
        "Repair the derived artifact surface without broadening scope.",
        f"Primary action: {recovery.get('primary_action', '')}",
        f"Allowed scope: {', '.join(allowed_scope) if allowed_scope else 'none'}",
        "Operator instructions:",
    ]
    for instruction in recovery.get("operator_instructions", []):
        prompt_lines.append(f"- {instruction}")
    if thin_output and thin_output.get("diagnosis", ""):
        prompt_lines.append(f"Current diagnosis: {thin_output['diagnosis']}")
    prompt_lines.append("Do not modify state_file or claim the contour is repaired beyond these artifact actions.")
    return {
        "schema_version": "consistency_recovery_prompt_record_v0",
        "run_id": recovery["run_id"],
        "task_class": recovery["task_class"],
        "primary_action": recovery.get("primary_action", ""),
        "allowed_scope": allowed_scope,
        "forbidden_scope": forbidden_scope,
        "must_pass": must_pass,
        "prompt": "\n".join(prompt_lines),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-consistency-recovery-prompt-v0")
    parser.add_argument("--consistency-recovery-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--thin-output-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        recovery=load_json(Path(args.consistency_recovery_file)),
        thin_output=load_json(Path(args.thin_output_file)) if args.thin_output_file else None,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "primary_action": record["primary_action"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
