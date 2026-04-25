#!/usr/bin/env python3
"""Aggregate operator render adoption records into one bounded reading."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json


def build_record(records: list[dict]) -> dict:
    if not records:
        raise ValueError("at least one adoption record is required")
    for record in records:
        if record.get("schema_version") != "operator_render_adoption_record_v0":
            raise ValueError("all inputs must use operator_render_adoption_record_v0")
    total_line_reduction = sum(record.get("line_reduction", 0) for record in records)
    truth_preserved_all = all(record.get("truth_preserved", False) for record in records)
    render_shorter_all = all(record.get("render_is_shorter", False) for record in records)
    verdict = "READING_TAX_REDUCED_WITHOUT_TRUTH_LOSS" if truth_preserved_all and render_shorter_all else "MIXED"
    why = (
        "every measured render stayed shorter than its source artifact and preserved the required operator markers"
        if verdict == "READING_TAX_REDUCED_WITHOUT_TRUTH_LOSS"
        else "at least one measured render either failed to preserve the key operator markers or did not get shorter than its source artifact"
    )
    return {
        "schema_version": "operator_render_adoption_delta_v0",
        "record_count": len(records),
        "labels": [record["label"] for record in records],
        "total_line_reduction": total_line_reduction,
        "truth_preserved_all": truth_preserved_all,
        "render_shorter_all": render_shorter_all,
        "verdict": verdict,
        "why": why,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-operator-render-adoption-delta-v0")
    parser.add_argument("--record", action="append", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        records = [load_json(Path(path)) for path in args.record]
        payload = build_record(records)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), payload)
    print(json.dumps({"result": "OK", "verdict": payload["verdict"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
