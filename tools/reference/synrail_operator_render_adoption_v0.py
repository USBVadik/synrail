#!/usr/bin/env python3
"""Measure whether operator render reduces reading tax without losing key truth."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def line_count(path: Path) -> int:
    return len(path.read_text().splitlines())


def marker_values_for_brief(payload: dict) -> list[str]:
    markers = [
        payload.get("primary_action", ""),
        payload.get("current_step_id", ""),
        payload.get("next_safe_step", ""),
        payload.get("termination_reason", "") or "NONE",
    ]
    markers.extend(payload.get("next_step_required_inputs", []))
    return [marker for marker in markers if marker]


def marker_values_for_chain(payload: dict) -> list[str]:
    markers = [
        payload.get("final_action", ""),
        payload.get("final_next_safe_step", ""),
    ]
    for stage in payload.get("stage_summaries", []):
        markers.extend(
            [
                stage.get("stage_id", ""),
                stage.get("primary_action", ""),
                stage.get("current_step_id", ""),
                stage.get("next_safe_step", ""),
                stage.get("termination_reason", "") or "NONE",
            ]
        )
        markers.extend(stage.get("next_step_required_inputs", []))
    deduped: list[str] = []
    for marker in markers:
        if marker and marker not in deduped:
            deduped.append(marker)
    return deduped


def build_record(*, source_path: Path, render_path: Path, label: str) -> dict:
    source = load_json(source_path)
    render_text = render_path.read_text()
    schema_version = source.get("schema_version", "")
    if schema_version == "operator_brief_record_v0":
        source_kind = "BRIEF"
        markers = marker_values_for_brief(source)
        run_id = source["run_id"]
        task_class = source["task_class"]
    elif schema_version == "operator_brief_chain_record_v0":
        source_kind = "CHAIN"
        markers = marker_values_for_chain(source)
        run_id = source["run_id"]
        task_class = source["task_class"]
    else:
        raise ValueError("source must use operator_brief_record_v0 or operator_brief_chain_record_v0")

    missing = [marker for marker in markers if marker not in render_text]
    source_lines = line_count(source_path)
    render_lines = line_count(render_path)
    shorter = render_lines < source_lines
    truth_preserved = not missing
    verdict = "READING_TAX_REDUCED_WITHOUT_TRUTH_LOSS" if shorter and truth_preserved else "MIXED"
    why = (
        "the render is shorter than the source artifact and still preserves the key operator markers"
        if verdict == "READING_TAX_REDUCED_WITHOUT_TRUTH_LOSS"
        else "the render either failed to preserve one key operator marker or did not get shorter than the source artifact"
    )
    return {
        "schema_version": "operator_render_adoption_record_v0",
        "label": label,
        "source_kind": source_kind,
        "source_path": str(source_path),
        "render_path": str(render_path),
        "run_id": run_id,
        "task_class": task_class,
        "source_line_count": source_lines,
        "render_line_count": render_lines,
        "line_reduction": source_lines - render_lines,
        "render_is_shorter": shorter,
        "key_marker_count": len(markers),
        "missing_markers": missing,
        "truth_preserved": truth_preserved,
        "verdict": verdict,
        "why": why,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-operator-render-adoption-v0")
    parser.add_argument("--source", required=True)
    parser.add_argument("--render", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        record = build_record(
            source_path=Path(args.source),
            render_path=Path(args.render),
            label=args.label,
        )
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
