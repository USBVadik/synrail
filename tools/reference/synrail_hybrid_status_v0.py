#!/usr/bin/env python3
"""Determine current hybrid-mode status from measured evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_path_value, validate_root_within_project
except ImportError:
    from synrail_io_v0 import load_json, save_json
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_path_value, validate_root_within_project


HYBRID_STATUS_PATH_SCOPES = {
    "cost_record": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_hybrid_status_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    for field, scope in HYBRID_STATUS_PATH_SCOPES.items():
        validate_path_value(
            field,
            str(getattr(args, field)),
            scope=scope,
            project_root=project_root,
            artifact_root=artifact_root,
        )
    for hybrid_record in args.hybrid_record:
        validate_path_value(
            "hybrid_record",
            str(hybrid_record),
            scope=ARTIFACT_SCOPE,
            project_root=project_root,
            artifact_root=artifact_root,
        )


def derive_status(verdicts: list[str]) -> tuple[str, str, str, str]:
    if any(verdict == "BASELINE_GOOD_ENOUGH" for verdict in verdicts):
        return (
            "DEMOTED",
            "DEMOTE_HYBRID_FROM_DEFAULT_POLICY",
            "do not treat hybrid as a default middle mode; reach for baseline unless one explicit hybrid pressure-test justifies the extra control",
            "keep baseline as the default middle-path choice and only revisit hybrid when a named ambiguity produces a decisive measured win",
        )

    better_count = sum(1 for verdict in verdicts if verdict == "SYNRAIL_BETTER")
    unclear_count = sum(1 for verdict in verdicts if verdict == "UNCLEAR")

    if better_count >= 2 and unclear_count == 0:
        return (
            "JUSTIFIED",
            "KEEP_HYBRID_ACTIVE",
            "hybrid now looks justified as a bounded middle mode on its measured scenario set",
            "keep gathering hybrid evidence, but the mode no longer needs provisional handling on its current measured class",
        )

    return (
        "PROVISIONAL",
        "KEEP_HYBRID_SECONDARY",
        "keep hybrid secondary and explicit; do not expand its semantics until the class-level measured signal stops being mixed",
        "either gather one more measured hybrid pressure-test soon or keep hybrid explicitly provisional while the class-level signal stays mixed",
    )


def build_record(cost_record_path: Path, hybrid_record_paths: list[Path]) -> dict:
    cost_record = load_json(cost_record_path)
    hybrid_records = [load_json(path) for path in hybrid_record_paths]

    for record in hybrid_records:
        if record.get("schema_version") != "baseline_comparison_record_v1":
            raise ValueError("hybrid records must use baseline_comparison_record_v1")
        if record.get("scenario_class") != "medium_risk_ambiguous_closure":
            raise ValueError("hybrid records must use the hybrid scenario class")

    verdicts = [record["verdict"] for record in hybrid_records]
    status, decision, default_policy, next_action = derive_status(verdicts)

    return {
        "schema_version": "hybrid_status_v0",
        "source_cost_record": str(cost_record_path),
        "hybrid_record_paths": [str(path) for path in hybrid_record_paths],
        "evidence_count": len(hybrid_records),
        "current_verdicts": verdicts,
        "current_status": status,
        "decision": decision,
        "default_policy": default_policy,
        "promotion_requirements": [
            "add at least one more economics-aware hybrid comparison record",
            "add one uglier hybrid pressure-test instead of another clean policy example",
            "only promote hybrid if the class-level measured signal stops staying unclear",
        ],
        "next_action": next_action,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-hybrid-status-v0")
    parser.add_argument("--cost-record", required=True)
    parser.add_argument("--hybrid-record", action="append", required=True)
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        artifact_root = Path(args.cost_record).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "cost_record",
            args.cost_record,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_hybrid_status_paths(args, artifact_root=artifact_root, project_root=project_root)
        record = build_record(Path(args.cost_record), [Path(path) for path in args.hybrid_record])
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2

    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "status": record["current_status"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
