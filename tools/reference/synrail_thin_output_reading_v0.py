#!/usr/bin/env python3
"""Check whether thin output plus prompt bridge reduce operator reading tax on a non-green contour."""

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


def build_record(
    *,
    thin_output: dict,
    prompt_bridge: dict,
    report: dict,
    repair_packet: dict,
    thin_output_path: str,
    prompt_bridge_path: str,
    report_path: str,
    repair_packet_path: str,
) -> dict:
    source_line_count = line_count(Path(report_path)) + line_count(Path(repair_packet_path))
    bridge_line_count = line_count(Path(thin_output_path)) + line_count(Path(prompt_bridge_path))
    continuation = repair_packet.get("continuation_core", {})
    expected_current_step = continuation.get("current_step_id", "") or repair_packet.get("repair_history", {}).get("current_step_id", "")
    expected_next_step = report.get("next_safe_step", "")
    missing_markers: list[str] = []
    if not thin_output.get("outcome_class", ""):
        missing_markers.append("outcome_class")
    if not thin_output.get("suggested_command", ""):
        missing_markers.append("suggested_command")
    if thin_output.get("next_step", "") != expected_next_step:
        missing_markers.append("next_step")
    if prompt_bridge.get("current_step_id", "") != expected_current_step:
        missing_markers.append("current_step_id")
    if not prompt_bridge.get("allowed_scope", []):
        missing_markers.append("allowed_scope")
    if not prompt_bridge.get("must_pass", []):
        missing_markers.append("must_pass")
    bridge_shorter = bridge_line_count < source_line_count
    verdict = "READING_TAX_REDUCED" if bridge_shorter and not missing_markers else "NO_CLEAR_READING_GAIN"
    return {
        "schema_version": "thin_output_reading_record_v0",
        "run_id": thin_output["run_id"],
        "task_class": thin_output["task_class"],
        "source_paths": [report_path, repair_packet_path],
        "bridge_paths": [thin_output_path, prompt_bridge_path],
        "source_line_count": source_line_count,
        "bridge_line_count": bridge_line_count,
        "line_reduction": source_line_count - bridge_line_count,
        "bridge_shorter": bridge_shorter,
        "outcome_class": thin_output.get("outcome_class", ""),
        "current_step_id": prompt_bridge.get("current_step_id", ""),
        "missing_markers": missing_markers,
        "verdict": verdict,
        "why": (
            "the thin output plus prompt bridge preserve the current-step and next-step truth while reducing the amount of runtime surface a human must read"
            if verdict == "READING_TAX_REDUCED"
            else "the bridge still loses critical markers or does not reduce enough reading surface yet"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-thin-output-reading-v0")
    parser.add_argument("--thin-output-file", required=True)
    parser.add_argument("--prompt-bridge-file", required=True)
    parser.add_argument("--report-file", required=True)
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_record(
        thin_output=load_json(Path(args.thin_output_file)),
        prompt_bridge=load_json(Path(args.prompt_bridge_file)),
        report=load_json(Path(args.report_file)),
        repair_packet=load_json(Path(args.repair_packet_file)),
        thin_output_path=args.thin_output_file,
        prompt_bridge_path=args.prompt_bridge_file,
        report_path=args.report_file,
        repair_packet_path=args.repair_packet_file,
    )
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "verdict": record["verdict"]}, ensure_ascii=True))
    return 0 if record["verdict"] == "READING_TAX_REDUCED" else 2


if __name__ == "__main__":
    sys.exit(main())
