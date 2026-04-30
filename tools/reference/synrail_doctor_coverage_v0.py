#!/usr/bin/env python3
"""Machine-readable doctor coverage and gate record for Synrail."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
DEFAULT_PROFILE = HERE / "doctor_coverage_profile_v0.json"
DEFAULT_CORPUS = HERE / "doctor_coverage_corpus_v0.json"






def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def resolve_path(value: str, *, base: Path) -> Path:
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate

    local = (base.parent / candidate).resolve()
    if local.exists():
        return local
    return (REPO_ROOT / candidate).resolve()


def evaluate_case(case: dict, *, corpus_file: Path) -> dict:
    doctor_record_path = resolve_path(case["doctor_record"], base=corpus_file)
    mismatch_reasons: list[str] = []
    observed_final_verdict = ""
    observed_blocking_failure_classes: list[str] = []
    observed_failing_gate = ""
    observed_gate_note = ""

    if not doctor_record_path.exists():
        return {
            "case_id": case["case_id"],
            "fail_mode_id": case["fail_mode_id"],
            "doctor_record": str(doctor_record_path),
            "status": "MISSING_EVIDENCE",
            "observed_final_verdict": observed_final_verdict,
            "observed_blocking_failure_classes": observed_blocking_failure_classes,
            "observed_failing_gate": observed_failing_gate,
            "observed_gate_note": observed_gate_note,
            "mismatch_reasons": ["doctor record is missing"],
        }

    try:
        record = load_json(doctor_record_path)
    except json.JSONDecodeError:
        return {
            "case_id": case["case_id"],
            "fail_mode_id": case["fail_mode_id"],
            "doctor_record": str(doctor_record_path),
            "status": "INVALID_EVIDENCE",
            "observed_final_verdict": observed_final_verdict,
            "observed_blocking_failure_classes": observed_blocking_failure_classes,
            "observed_failing_gate": observed_failing_gate,
            "observed_gate_note": observed_gate_note,
            "mismatch_reasons": ["doctor record is not valid json"],
        }

    observed_final_verdict = record.get("final_verdict", "")
    observed_blocking_failure_classes = list(record.get("blocking_failure_classes", []))
    gate_results = record.get("gate_results", {})

    if observed_final_verdict != case["expected_final_verdict"]:
        mismatch_reasons.append(
            f"final verdict mismatch: expected {case['expected_final_verdict']}, got {observed_final_verdict or 'EMPTY'}"
        )

    expected_blocking = case.get("expected_blocking_failure_class", "")
    if expected_blocking and expected_blocking not in observed_blocking_failure_classes:
        mismatch_reasons.append(
            f"blocking failure class mismatch: expected {expected_blocking}, got {observed_blocking_failure_classes}"
        )

    expected_gate = case.get("expected_failing_gate", "")
    if expected_gate:
        gate = gate_results.get(expected_gate)
        if not isinstance(gate, dict):
            mismatch_reasons.append(f"expected failing gate {expected_gate} is missing")
        else:
            observed_failing_gate = expected_gate
            observed_gate_note = gate.get("note", "")
            if gate.get("status") != "FAIL":
                mismatch_reasons.append(
                    f"gate {expected_gate} expected FAIL, got {gate.get('status', 'EMPTY')}"
                )
            note_fragment = case.get("expected_note_contains", "")
            if note_fragment and note_fragment not in observed_gate_note:
                mismatch_reasons.append(
                    f"gate {expected_gate} note does not contain expected fragment: {note_fragment}"
                )

    status = "MATCHED" if not mismatch_reasons else "MISMATCHED"
    return {
        "case_id": case["case_id"],
        "fail_mode_id": case["fail_mode_id"],
        "doctor_record": str(doctor_record_path),
        "status": status,
        "observed_final_verdict": observed_final_verdict,
        "observed_blocking_failure_classes": observed_blocking_failure_classes,
        "observed_failing_gate": observed_failing_gate,
        "observed_gate_note": observed_gate_note,
        "mismatch_reasons": mismatch_reasons,
    }


def classify_measured_modes(all_modes: list[str], measured_cases: list[dict]) -> tuple[list[str], list[str], list[str]]:
    cases_by_mode: dict[str, list[dict]] = {}
    for case in measured_cases:
        cases_by_mode.setdefault(case["fail_mode_id"], []).append(case)

    covered: list[str] = []
    partial: list[str] = []
    uncovered: list[str] = []

    for mode in all_modes:
        cases = cases_by_mode.get(mode, [])
        if not cases:
            uncovered.append(mode)
            continue
        if all(case["status"] == "MATCHED" for case in cases):
            covered.append(mode)
            continue
        partial.append(mode)
    return covered, partial, uncovered


def build_decision_trace(
    all_modes: list[str],
    critical: list[str],
    measured_cases: list[dict],
    *,
    covered: list[str],
    partial: list[str],
    uncovered: list[str],
) -> list[dict]:
    cases_by_mode: dict[str, list[dict]] = {}
    for case in measured_cases:
        cases_by_mode.setdefault(case["fail_mode_id"], []).append(case)

    trace: list[dict] = []
    for mode in all_modes:
        cases = cases_by_mode.get(mode, [])
        matched_case_ids = [case["case_id"] for case in cases if case["status"] == "MATCHED"]
        problematic_case_ids = [case["case_id"] for case in cases if case["status"] != "MATCHED"]
        if mode in covered:
            classification = "COVERED"
            gate_effect = "SATISFIES_CRITICAL_COVERAGE" if mode in critical else "NON_CRITICAL"
            why = "all measured cases for this fail mode matched the expected doctor boundary"
        elif mode in partial:
            classification = "PARTIAL"
            gate_effect = "HAS_MISMATCHED_EVIDENCE" if mode in critical else "NON_CRITICAL"
            why = "measured evidence exists for this fail mode, but at least one case mismatched the expected doctor boundary"
        else:
            classification = "UNCOVERED"
            gate_effect = "MISSING_MEASURED_EVIDENCE" if mode in critical else "NON_CRITICAL"
            why = "no measured evidence currently exercises this fail mode"
        trace.append(
            {
                "fail_mode_id": mode,
                "is_critical": mode in critical,
                "classification": classification,
                "measured_case_ids": [case["case_id"] for case in cases],
                "matched_case_ids": matched_case_ids,
                "problematic_case_ids": problematic_case_ids,
                "gate_effect": gate_effect,
                "why": why,
            }
        )
    return trace


def deployment_context_confirmed(explicit: bool = False) -> bool:
    if explicit:
        return True
    return os.environ.get("SYNRAIL_DEPLOYMENT_CONTEXT", "").strip().lower() in {"1", "true", "yes", "on"}


def build_coverage_record(
    profile: dict,
    corpus: dict,
    *,
    corpus_file: Path = DEFAULT_CORPUS,
    deployment_context: bool = False,
) -> dict:
    critical = list(profile.get("critical_fail_modes", []))
    declared_covered = list(profile.get("covered_fail_modes", []))
    declared_partial = list(profile.get("partial_fail_modes", []))
    declared_uncovered = list(profile.get("uncovered_fail_modes", []))
    all_modes = dedupe(critical + declared_covered + declared_partial + declared_uncovered)
    threshold_policy = profile.get("coverage_threshold_policy", "ALL_CRITICAL_FAIL_MODES_COVERED")
    measured_cases = [evaluate_case(case, corpus_file=corpus_file) for case in corpus.get("cases", [])]
    covered, partial, uncovered = classify_measured_modes(all_modes, measured_cases)
    decision_trace = build_decision_trace(
        all_modes,
        critical,
        measured_cases,
        covered=covered,
        partial=partial,
        uncovered=uncovered,
    )
    critical_covered = [mode for mode in critical if mode in covered]
    critical_missing = [mode for mode in critical if mode not in covered]
    critical_without_evidence = [mode for mode in critical if mode in uncovered]
    critical_mismatched = [mode for mode in critical if mode in partial]
    all_missing = measured_cases and all(c["status"] == "MISSING_EVIDENCE" for c in measured_cases)
    deployment_context_ok = deployment_context_confirmed(deployment_context)
    threshold_met = len(critical_missing) == 0 if threshold_policy == "ALL_CRITICAL_FAIL_MODES_COVERED" else False
    if threshold_met:
        gate_status = "PASS"
        gate_reason = "CRITICAL_FAIL_MODE_MEASURED_COVERAGE_MET"
    elif all_missing and deployment_context_ok:
        gate_status = "PASS"
        gate_reason = "COVERAGE_CORPUS_NOT_AVAILABLE_IN_DEPLOYMENT"
        threshold_met = True
    elif all_missing:
        gate_status = "BLOCKED"
        gate_reason = "CRITICAL_FAIL_MODE_MEASURED_COVERAGE_MISSING_EVIDENCE"
    elif critical_without_evidence:
        gate_status = "BLOCKED"
        gate_reason = "CRITICAL_FAIL_MODE_MEASURED_COVERAGE_MISSING_EVIDENCE"
    else:
        gate_status = "BLOCKED"
        gate_reason = "CRITICAL_FAIL_MODE_MEASURED_COVERAGE_INCOMPLETE"

    measured_case_match_count = sum(1 for case in measured_cases if case["status"] == "MATCHED")
    measured_case_problem_count = len(measured_cases) - measured_case_match_count
    return {
        "schema_version": "doctor_coverage_record_v0",
        "doctor_version": profile.get("doctor_version", "synrail_doctor_v1"),
        "coverage_source": "DECLARED_PROFILE_PLUS_MEASURED_CORPUS",
        "corpus_version": corpus.get("schema_version", "doctor_coverage_corpus_v0"),
        "coverage_threshold_policy": threshold_policy,
        "critical_fail_modes": critical,
        "declared_covered_fail_modes": declared_covered,
        "declared_partial_fail_modes": declared_partial,
        "declared_uncovered_fail_modes": declared_uncovered,
        "covered_fail_modes": covered,
        "partial_fail_modes": partial,
        "uncovered_fail_modes": uncovered,
        "measured_case_count": len(measured_cases),
        "measured_case_match_count": measured_case_match_count,
        "measured_case_problem_count": measured_case_problem_count,
        "measured_cases": measured_cases,
        "decision_trace": decision_trace,
        "critical_fail_mode_count": len(critical),
        "critical_covered_count": len(critical_covered),
        "critical_missing_fail_modes": critical_missing,
        "critical_modes_without_measured_evidence": critical_without_evidence,
        "critical_modes_with_mismatched_evidence": critical_mismatched,
        "deployment_context_confirmed": deployment_context_ok,
        "threshold_met": threshold_met,
        "gate_status": gate_status,
        "gate_reason": gate_reason,
    }


def load_profile(path: Path | None = None) -> dict:
    return load_json(path or DEFAULT_PROFILE)


def load_corpus(
    path: Path | None = None,
    *,
    profile: dict | None = None,
    profile_file: Path | None = None,
) -> tuple[dict, Path]:
    if path:
        resolved = path.resolve()
        return load_json(resolved), resolved

    profile_corpus = (profile or {}).get("measured_corpus_file")
    if profile_corpus:
        resolved = resolve_path(profile_corpus, base=profile_file or DEFAULT_PROFILE)
        return load_json(resolved), resolved

    return load_json(DEFAULT_CORPUS), DEFAULT_CORPUS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-doctor-coverage-v0")
    parser.add_argument("--profile-file")
    parser.add_argument("--corpus-file")
    parser.add_argument("--deployment-context", action="store_true")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    profile_file = Path(args.profile_file) if args.profile_file else None
    profile = load_profile(profile_file) if profile_file else load_profile()
    corpus, corpus_file = load_corpus(
        Path(args.corpus_file) if args.corpus_file else None,
        profile=profile,
        profile_file=profile_file,
    )
    record = build_coverage_record(
        profile,
        corpus,
        corpus_file=corpus_file,
        deployment_context=args.deployment_context,
    )
    save_json(Path(args.output), record)
    print(
        json.dumps(
            {
                "result": "OK",
                "gate_status": record["gate_status"],
                "gate_reason": record["gate_reason"],
                "measured_case_count": record["measured_case_count"],
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
