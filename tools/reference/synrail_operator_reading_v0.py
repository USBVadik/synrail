#!/usr/bin/env python3
"""Check whether a derived operator render stays followable on a less-curated contour."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_record(*, second_operator: dict, brief: dict, render_text: str, label: str, source_brief_path: str) -> dict:
    expected_values = [
        brief.get("primary_action", ""),
        brief.get("next_safe_step", ""),
        brief.get("current_step_id", ""),
        brief.get("termination_reason", "") or "NONE",
        second_operator.get("expected_reason", ""),
        second_operator.get("expected_next_safe_step", ""),
    ]
    expected_values.extend(brief.get("next_step_required_inputs", []))
    required_markers = [value for value in expected_values if value]
    missing_markers = [value for value in required_markers if value not in render_text]
    followable = (
        second_operator.get("verdict", "") == "FOLLOWABLE_BY_SECOND_OPERATOR"
        and not second_operator.get("requires_author_intuition", True)
        and not missing_markers
    )
    verdict = "FOLLOWABLE_WITH_RENDER" if followable else "MIXED"
    why = (
        "the repeated-doctor contour stays followable when the operator reads the derived render instead of the raw brief alone"
        if verdict == "FOLLOWABLE_WITH_RENDER"
        else "the derived render lost one or more required operator markers or the contour was not followable without author intuition"
    )
    return {
        "schema_version": "operator_reading_record_v0",
        "label": label,
        "run_id": brief["run_id"],
        "task_class": brief["task_class"],
        "source_brief_path": source_brief_path,
        "render_is_human_readable": True,
        "packet_only_entry": second_operator.get("packet_only_entry", False),
        "requires_author_intuition": second_operator.get("requires_author_intuition", True),
        "expected_reason": second_operator.get("expected_reason", ""),
        "primary_action": brief.get("primary_action", ""),
        "next_safe_step": brief.get("next_safe_step", ""),
        "current_step_id": brief.get("current_step_id", ""),
        "termination_reason": brief.get("termination_reason", "") or "NONE",
        "required_input_count": len(brief.get("next_step_required_inputs", [])),
        "required_markers": required_markers,
        "missing_markers": missing_markers,
        "verdict": verdict,
        "why": why,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-operator-reading-v0")
    parser.add_argument("--second-operator-file", required=True)
    parser.add_argument("--brief-file", required=True)
    parser.add_argument("--render-file", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    second_operator = load_json(Path(args.second_operator_file))
    brief = load_json(Path(args.brief_file))
    render_text = Path(args.render_file).read_text()
    record = build_record(
        second_operator=second_operator,
        brief=brief,
        render_text=render_text,
        label=args.label,
        source_brief_path=args.brief_file,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
