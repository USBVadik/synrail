#!/usr/bin/env python3
"""Aggregate short external-ish pressure records for one Synrail contour."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_record(*, reproducibility: dict, second_operator: dict, operator_reading: dict, label: str) -> dict:
    if reproducibility.get("schema_version") != "reproducibility_record_v0":
        raise ValueError("reproducibility input must use reproducibility_record_v0")
    if second_operator.get("schema_version") != "second_operator_record_v0":
        raise ValueError("second-operator input must use second_operator_record_v0")
    if operator_reading.get("schema_version") != "operator_reading_record_v0":
        raise ValueError("operator-reading input must use operator_reading_record_v0")

    reproducible = reproducibility.get("verdict") == "REPRODUCIBLE_ON_KEY_TRUTH"
    second_followable = second_operator.get("verdict") == "FOLLOWABLE_BY_SECOND_OPERATOR"
    render_followable = operator_reading.get("verdict") == "FOLLOWABLE_WITH_RENDER"
    requires_author_intuition = second_operator.get("requires_author_intuition", True) or operator_reading.get("requires_author_intuition", True)

    dimensions_passed = []
    if reproducible:
        dimensions_passed.append("REPRODUCIBILITY")
    if second_followable:
        dimensions_passed.append("SECOND_OPERATOR")
    if render_followable:
        dimensions_passed.append("OPERATOR_READING")

    uncovered_risks = []
    if not reproducible:
        uncovered_risks.append("key_truth_drift")
    if not second_followable:
        uncovered_risks.append("packet_entry_not_followable")
    if not render_followable:
        uncovered_risks.append("render_drops_operator_decision")
    if requires_author_intuition:
        uncovered_risks.append("author_intuition_still_required")

    verdict = "SURVIVES_SHORT_EXTERNAL_PRESSURE" if len(dimensions_passed) == 3 and not uncovered_risks else "MIXED"
    why = (
        "the uglier contour stays reproducible, packet-followable, and render-followable without hidden author intuition"
        if verdict == "SURVIVES_SHORT_EXTERNAL_PRESSURE"
        else "at least one short external-ish pressure dimension is still failing or leaning on hidden author intuition"
    )

    return {
        "schema_version": "externality_pressure_record_v0",
        "label": label,
        "run_id": reproducibility.get("run_id", ""),
        "task_class": reproducibility.get("task_class", ""),
        "contour_reason": second_operator.get("expected_reason", ""),
        "packet_only_entry": second_operator.get("packet_only_entry", False),
        "requires_author_intuition": requires_author_intuition,
        "dimensions_passed": dimensions_passed,
        "uncovered_risks": uncovered_risks,
        "reproducibility_verdict": reproducibility.get("verdict", ""),
        "second_operator_verdict": second_operator.get("verdict", ""),
        "operator_reading_verdict": operator_reading.get("verdict", ""),
        "verdict": verdict,
        "why": why,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-externality-pressure-v0")
    parser.add_argument("--reproducibility-file", required=True)
    parser.add_argument("--second-operator-file", required=True)
    parser.add_argument("--operator-reading-file", required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        payload = build_record(
            reproducibility=load_json(Path(args.reproducibility_file)),
            second_operator=load_json(Path(args.second_operator_file)),
            operator_reading=load_json(Path(args.operator_reading_file)),
            label=args.label,
        )
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), payload)
    print(json.dumps({"result": "OK", "verdict": payload["verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
