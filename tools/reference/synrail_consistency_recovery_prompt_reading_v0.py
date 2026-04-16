#!/usr/bin/env python3
"""Check that a consistency recovery prompt stays bounded to the restore-or-reemit plan."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_record(*, recovery: dict, prompt: dict) -> dict:
    expected_scope = list(recovery.get("restore_artifact_ids", [])) + list(recovery.get("reemit_artifact_ids", []))
    missing_markers: list[str] = []

    if prompt.get("allowed_scope", []) != expected_scope:
        missing_markers.append("allowed_scope")
    for instruction in recovery.get("operator_instructions", []):
        if instruction not in prompt.get("must_pass", []):
            missing_markers.append(f"must_pass:{instruction}")
        if instruction not in prompt.get("prompt", ""):
            missing_markers.append(f"prompt:{instruction}")
    if "Do not modify state_file." not in prompt.get("forbidden_scope", []):
        missing_markers.append("forbidden_scope_state_file")

    verdict = "RECOVERY_PROMPT_BOUNDED" if not missing_markers else "RECOVERY_PROMPT_DRIFT"
    return {
        "schema_version": "consistency_recovery_prompt_reading_record_v0",
        "run_id": recovery["run_id"],
        "task_class": recovery["task_class"],
        "primary_action": recovery.get("primary_action", ""),
        "allowed_scope": prompt.get("allowed_scope", []),
        "missing_markers": missing_markers,
        "verdict": verdict,
        "why": (
            "the restore-or-reemit path can be handed to the next agent call without broadening beyond the listed artifact actions"
            if verdict == "RECOVERY_PROMPT_BOUNDED"
            else "the generated recovery prompt drifted away from the concrete restore-or-reemit action set"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-consistency-recovery-prompt-reading-v0")
    parser.add_argument("--consistency-recovery-file", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        recovery=load_json(Path(args.consistency_recovery_file)),
        prompt=load_json(Path(args.prompt_file)),
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0 if record["verdict"] == "RECOVERY_PROMPT_BOUNDED" else 2


if __name__ == "__main__":
    sys.exit(main())
