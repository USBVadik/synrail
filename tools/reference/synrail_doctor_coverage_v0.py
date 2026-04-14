#!/usr/bin/env python3
"""Machine-readable doctor coverage and gate record for Synrail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_PROFILE = HERE / "doctor_coverage_profile_v0.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def build_coverage_record(profile: dict) -> dict:
    critical = list(profile.get("critical_fail_modes", []))
    covered = list(profile.get("covered_fail_modes", []))
    partial = list(profile.get("partial_fail_modes", []))
    uncovered = list(profile.get("uncovered_fail_modes", []))
    critical_covered = [mode for mode in critical if mode in covered]
    critical_missing = [mode for mode in critical if mode not in covered]
    threshold_policy = profile.get("coverage_threshold_policy", "ALL_CRITICAL_FAIL_MODES_COVERED")
    threshold_met = len(critical_missing) == 0 if threshold_policy == "ALL_CRITICAL_FAIL_MODES_COVERED" else False
    gate_status = "PASS" if threshold_met else "BLOCKED"
    gate_reason = "CRITICAL_FAIL_MODE_COVERAGE_MET" if threshold_met else "CRITICAL_FAIL_MODE_COVERAGE_INCOMPLETE"
    return {
        "schema_version": "doctor_coverage_record_v0",
        "doctor_version": profile.get("doctor_version", "synrail_doctor_v1"),
        "coverage_threshold_policy": threshold_policy,
        "critical_fail_modes": critical,
        "covered_fail_modes": covered,
        "partial_fail_modes": partial,
        "uncovered_fail_modes": uncovered,
        "critical_fail_mode_count": len(critical),
        "critical_covered_count": len(critical_covered),
        "critical_missing_fail_modes": critical_missing,
        "threshold_met": threshold_met,
        "gate_status": gate_status,
        "gate_reason": gate_reason,
    }


def load_profile(path: Path | None = None) -> dict:
    return load_json(path or DEFAULT_PROFILE)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-doctor-coverage-v0")
    parser.add_argument("--profile-file")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    record = build_coverage_record(load_profile(Path(args.profile_file)) if args.profile_file else load_profile())
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "gate_status": record["gate_status"], "gate_reason": record["gate_reason"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
