#!/usr/bin/env python3
"""Emit one machine-readable mode-selection receipt."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_io_v0 import load_json, save_json
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


MODES = {"FULL_GOVERNED_PATH", "LIGHTWEIGHT_BASELINE", "HYBRID_EXCEPTION"}
MODE_RECEIPT_PATH_SCOPES = {
    "recommendation_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_mode_receipt_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=MODE_RECEIPT_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )


def build_receipt(recommendation_path: Path, selected_mode: str | None, selected_with_preparation: bool) -> dict:
    recommendation = load_json(recommendation_path)
    if recommendation.get("schema_version") != "mode_recommendation_v0":
        raise ValueError("recommendation must use mode_recommendation_v0")

    recommended_mode = recommendation["recommended_mode"]
    chosen_mode = selected_mode or recommended_mode
    if chosen_mode not in MODES:
        raise ValueError("selected mode is not recognized")
    if selected_with_preparation and chosen_mode != "FULL_GOVERNED_PATH":
        raise ValueError("selected_with_preparation only makes sense for FULL_GOVERNED_PATH")

    followed_recommendation = chosen_mode == recommended_mode
    heavier_contour_entered = chosen_mode != "LIGHTWEIGHT_BASELINE"

    evidence = recommendation["evidence_summary"]
    avoided_operator_minutes = 0
    avoided_interventions = 0
    avoided_latency = 0

    if chosen_mode == "LIGHTWEIGHT_BASELINE":
        avoided_operator_minutes = evidence["avg_operator_minutes_added_if_synrail"]
        avoided_interventions = evidence["avg_interventions_added_if_synrail"]
        avoided_latency = evidence["avg_closure_latency_minutes_added_if_synrail"]

    return {
        "schema_version": "mode_selection_receipt_v0",
        "recommendation_file": str(recommendation_path),
        "scenario_class": recommendation["scenario_class"],
        "task_class": recommendation["task_class"],
        "recommended_mode": recommended_mode,
        "selected_mode": chosen_mode,
        "secondary_exception_mode": recommendation["secondary_exception_mode"],
        "governed_preparation_recommended": bool(recommendation.get("governed_preparation_recommended", False)),
        "selected_with_preparation": bool(selected_with_preparation),
        "followed_recommendation": followed_recommendation,
        "heavier_contour_entered": heavier_contour_entered,
        "selection_evidence_provenance_mix": list(evidence.get("provenance_mix", [])),
        "estimated_avoided_operator_minutes": avoided_operator_minutes,
        "estimated_avoided_interventions": avoided_interventions,
        "estimated_avoided_closure_latency_minutes": avoided_latency,
        "why": recommendation["why"],
        "next_safe_step": recommendation["next_safe_step"],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-mode-receipt-v0")
    parser.add_argument("--recommendation-file", required=True)
    parser.add_argument("--selected-mode", choices=sorted(MODES))
    parser.add_argument("--selected-with-preparation", action="store_true")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        artifact_root = Path(args.recommendation_file).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "recommendation_file",
            args.recommendation_file,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_mode_receipt_paths(args, artifact_root=artifact_root, project_root=project_root)
        receipt = build_receipt(Path(args.recommendation_file), args.selected_mode, args.selected_with_preparation)
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), receipt)
    print(json.dumps({"result": "OK", "selected_mode": receipt["selected_mode"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
