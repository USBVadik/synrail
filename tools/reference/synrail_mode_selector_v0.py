#!/usr/bin/env python3
"""Cost-aware mode selector for Synrail."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def average(records: list[dict], key: str) -> int:
    if not records:
        return 0
    total = sum(record["economics_summary"][key] for record in records)
    return round(total / len(records))


def unit(value: int, singular: str, plural: str) -> str:
    return singular if value == 1 else plural


def aggregate_verdict(records: list[dict]) -> str:
    if not records:
        return "UNKNOWN"
    verdicts = {record["verdict"] for record in records}
    if "BASELINE_GOOD_ENOUGH" in verdicts:
        return "BASELINE_GOOD_ENOUGH"
    if "UNCLEAR" in verdicts:
        return "UNCLEAR"
    if "SYNRAIL_BETTER" in verdicts:
        return "SYNRAIL_BETTER"
    return "UNKNOWN"


def meaningful_high_risk(args: argparse.Namespace) -> bool:
    if args.false_success_risk == "HIGH":
        return True
    if args.recovery_cost == "HIGH":
        return True
    return args.execution_surface_ambiguous and args.artifact_truth_nontrivial


def choose_mode(
    args: argparse.Namespace,
    *,
    class_verdict: str,
    hybrid_status: str,
    avg_operator_minutes_added: int,
    avg_interventions_added: int,
    avg_closure_latency_minutes_added: int,
    avg_false_green_exposure_reduced: int,
) -> tuple[str, str, str]:
    if meaningful_high_risk(args):
        return (
            "FULL_GOVERNED_PATH",
            "",
            "expensive wrong-closure risk still dominates here, so the extra control remains justified despite added operator cost",
        )

    if class_verdict == "BASELINE_GOOD_ENOUGH":
        why = (
            f"measured class evidence already says baseline is good enough here; using baseline likely avoids about "
            f"{avg_operator_minutes_added} added operator {unit(avg_operator_minutes_added, 'minute', 'minutes')}, "
            f"{avg_interventions_added} extra {unit(avg_interventions_added, 'intervention', 'interventions')}, "
            f"and {avg_closure_latency_minutes_added} extra closure-latency minutes without giving up a decisive safety gain"
        )
        if args.scenario_class == "medium_risk_ambiguous_closure" and args.explicit_hybrid_ambiguity:
            why += "; keep hybrid only as a named exception if this exact ambiguity later proves an earned win"
            return ("LIGHTWEIGHT_BASELINE", "HYBRID_EXCEPTION", why)
        return ("LIGHTWEIGHT_BASELINE", "", why)

    if args.scenario_class == "medium_risk_ambiguous_closure" and hybrid_status == "DEMOTED":
        why = (
            "hybrid is now demoted from default policy, so baseline should stay the default middle-path choice "
            "unless one named ambiguity earns a local exception"
        )
        if args.explicit_hybrid_ambiguity:
            return ("LIGHTWEIGHT_BASELINE", "HYBRID_EXCEPTION", why)
        return ("LIGHTWEIGHT_BASELINE", "", why)

    if args.scenario_class == "medium_risk_ambiguous_closure" and args.explicit_hybrid_ambiguity:
        return (
            "HYBRID_EXCEPTION",
            "",
            "the path is mixed but not expensive enough for the full governed contour, and one explicit ambiguity names why a bounded hybrid exception may be worth trying",
        )

    if class_verdict == "SYNRAIL_BETTER":
        why = (
            f"measured class evidence says Synrail earns its cost here, including about {avg_false_green_exposure_reduced} "
            "units of false-green reduction on the current class signal"
        )
        return ("FULL_GOVERNED_PATH", "", why)

    return (
        "LIGHTWEIGHT_BASELINE",
        "",
        "class evidence is still mixed or absent, so baseline stays the cheaper default until the risk or measured signal clearly justifies more control",
    )


def build_record(args: argparse.Namespace) -> dict:
    cost_record = load_json(Path(args.cost_record))
    if cost_record.get("schema_version") != "cost_of_control_record_v0":
        raise ValueError("cost record must use cost_of_control_record_v0")

    hybrid_status_value = "UNKNOWN"
    if args.hybrid_status:
        hybrid_record = load_json(Path(args.hybrid_status))
        if hybrid_record.get("schema_version") != "hybrid_status_v0":
            raise ValueError("hybrid status must use hybrid_status_v0")
        hybrid_status_value = hybrid_record["current_status"]
    if args.scenario_class != "medium_risk_ambiguous_closure":
        hybrid_status_value = ""

    comparison_records = [load_json(Path(item["path"])) for item in cost_record["source_records"]]
    class_records = [record for record in comparison_records if record["scenario_class"] == args.scenario_class]
    class_verdict = aggregate_verdict(class_records)

    avg_operator_minutes_added = average(class_records, "operator_minutes_added")
    avg_interventions_added = average(class_records, "intervention_count_added")
    avg_closure_latency_minutes_added = average(class_records, "closure_latency_minutes_added")
    avg_false_green_exposure_reduced = average(class_records, "false_green_exposure_reduced")

    recommended_mode, secondary_exception_mode, why = choose_mode(
        args,
        class_verdict=class_verdict,
        hybrid_status=hybrid_status_value,
        avg_operator_minutes_added=avg_operator_minutes_added,
        avg_interventions_added=avg_interventions_added,
        avg_closure_latency_minutes_added=avg_closure_latency_minutes_added,
        avg_false_green_exposure_reduced=avg_false_green_exposure_reduced,
    )

    if recommended_mode == "FULL_GOVERNED_PATH":
        next_safe_step = "run the full governed path"
    elif secondary_exception_mode == "HYBRID_EXCEPTION":
        next_safe_step = "stay baseline by default and only use a bounded hybrid exception if the named ambiguity survives cheap validation"
    elif recommended_mode == "HYBRID_EXCEPTION":
        next_safe_step = "run one bounded hybrid exception and measure whether the extra control actually pays off"
    else:
        next_safe_step = "use the lightweight baseline and only escalate if cheap validation leaves a named ambiguity unresolved"

    return {
        "schema_version": "mode_recommendation_v0",
        "scenario_class": args.scenario_class,
        "task_class": args.task_class,
        "risk_inputs": {
            "false_success_risk": args.false_success_risk,
            "recovery_cost": args.recovery_cost,
            "execution_surface_ambiguous": args.execution_surface_ambiguous,
            "artifact_truth_nontrivial": args.artifact_truth_nontrivial,
            "explicit_hybrid_ambiguity": args.explicit_hybrid_ambiguity or "",
        },
        "evidence_summary": {
            "class_record_count": len(class_records),
            "class_verdict": class_verdict,
            "hybrid_status": hybrid_status_value,
            "avg_operator_minutes_added_if_synrail": avg_operator_minutes_added,
            "avg_interventions_added_if_synrail": avg_interventions_added,
            "avg_closure_latency_minutes_added_if_synrail": avg_closure_latency_minutes_added,
            "avg_false_green_exposure_reduced_if_synrail": avg_false_green_exposure_reduced,
        },
        "recommended_mode": recommended_mode,
        "secondary_exception_mode": secondary_exception_mode,
        "why": why,
        "next_safe_step": next_safe_step,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-mode-selector-v0")
    parser.add_argument("--cost-record", required=True)
    parser.add_argument("--hybrid-status")
    parser.add_argument("--scenario-class", required=True)
    parser.add_argument("--task-class", required=True)
    parser.add_argument("--false-success-risk", required=True, choices=["LOW", "MEDIUM", "HIGH"])
    parser.add_argument("--recovery-cost", required=True, choices=["LOW", "MEDIUM", "HIGH"])
    parser.add_argument("--execution-surface-ambiguous", action="store_true")
    parser.add_argument("--artifact-truth-nontrivial", action="store_true")
    parser.add_argument("--explicit-hybrid-ambiguity")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        record = build_record(args)
    except ValueError as exc:
        print(json.dumps({"result": "ERROR", "reason": str(exc)}, ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(json.dumps({"result": "OK", "recommended_mode": record["recommended_mode"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
