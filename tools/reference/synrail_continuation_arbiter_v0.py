#!/usr/bin/env python3
"""Runtime continuation arbiter for packet-first Synrail continuation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from .synrail_io_v0 import load_json, save_json
except ImportError:
    from synrail_io_v0 import load_json, save_json

try:
    from .synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project
except ImportError:
    from synrail_path_scope_v0 import ARTIFACT_SCOPE, PathScopeValidationError, validate_namespace_paths, validate_root_within_project


CONTINUATION_ARBITER_PATH_SCOPES = {
    "state_file": ARTIFACT_SCOPE,
    "repair_packet_file": ARTIFACT_SCOPE,
    "output": ARTIFACT_SCOPE,
    "repair_receipt_file": ARTIFACT_SCOPE,
}


def current_project_root() -> Path:
    return Path.cwd().resolve()


def validate_continuation_arbiter_paths(args: argparse.Namespace, *, artifact_root: Path, project_root: Path) -> None:
    validate_namespace_paths(
        args,
        field_scopes=CONTINUATION_ARBITER_PATH_SCOPES,
        project_root=project_root,
        artifact_root=artifact_root,
    )






def latest_history_entry(repair_receipt: dict | None, packet: dict) -> dict:
    if repair_receipt:
        chain = list(repair_receipt.get("repair_history_chain", []))
        if chain:
            return dict(chain[-1])
    receipt_context = packet.get("repair_receipt_context", {})
    chain = list(receipt_context.get("history_chain", []))
    if chain:
        return dict(chain[-1])
    chain = list(packet.get("repair_history_chain", []))
    if chain:
        return dict(chain[-1])
    return {}


def receipt_contour_status(state: dict, packet: dict, repair_receipt: dict | None) -> tuple[bool, str]:
    if not repair_receipt:
        return False, "repair receipt is not available"
    if repair_receipt.get("run_id", "") != state.get("run_id", ""):
        return False, "repair receipt run_id does not match the state file"
    if repair_receipt.get("run_id", "") != packet.get("run_id", ""):
        return False, "repair receipt run_id does not match the repair packet"
    if repair_receipt.get("task_class", "") != state.get("task_class", ""):
        return False, "repair receipt task_class does not match the state file"
    if repair_receipt.get("task_class", "") != packet.get("task_class", ""):
        return False, "repair receipt task_class does not match the repair packet"
    if repair_receipt.get("from_state", "") and packet.get("from_state", "") and repair_receipt.get("from_state", "") != packet.get("from_state", ""):
        return False, "repair receipt from_state does not match the repair packet contour"
    return True, "repair receipt matches the current continuation contour"


def history_contour_status(packet: dict, latest_history: dict, receipt_eligible: bool) -> tuple[bool, str]:
    if not latest_history:
        return False, "repair history chain is not available"
    if not receipt_eligible:
        return False, "repair history chain is ignored because the repair receipt contour is not trusted"
    packet_from_state = packet.get("from_state", "")
    if latest_history.get("from_state", "") and packet_from_state and latest_history.get("from_state", "") != packet_from_state:
        return False, "latest repair history entry does not match the repair packet contour"
    return True, "latest repair history entry matches the current continuation contour"


def comparable(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=True)


def unique_non_empty(values: list) -> list:
    seen: set[str] = set()
    ordered: list = []
    for value in values:
        if value is None:
            continue
        if value == "":
            continue
        if isinstance(value, list) and not value:
            continue
        if isinstance(value, dict) and not value:
            continue
        key = comparable(value)
        if key in seen:
            continue
        seen.add(key)
        ordered.append(value)
    return ordered


def trace_entry(
    *,
    surface: str,
    chosen_source: str,
    chosen_value,
    candidates: list[dict],
    resolution_rule: str,
    why: str,
) -> dict:
    unique_values = unique_non_empty([candidate["value"] for candidate in candidates if candidate.get("eligible", False)])
    return {
        "surface": surface,
        "chosen_source": chosen_source,
        "chosen_value": chosen_value,
        "conflict": len(unique_values) > 1,
        "candidates": candidates,
        "resolution_rule": resolution_rule,
        "why": why,
    }


def build_record(*, state: dict, packet: dict, repair_receipt: dict | None = None) -> dict:
    repair_receipt = repair_receipt or packet.get("repair_receipt")
    latest_history = latest_history_entry(repair_receipt, packet)
    precedence_order = list((packet.get("source_of_truth") or {}).get("precedence_order", []))

    receipt_eligible, receipt_why = receipt_contour_status(state, packet, repair_receipt)
    history_eligible, history_why = history_contour_status(packet, latest_history, receipt_eligible)

    source_status = {
        "state_file": {
            "available": True,
            "eligible": True,
            "why": "state file anchors the current run truth",
        },
        "repair_packet": {
            "available": True,
            "eligible": True,
            "why": "repair packet anchors the continuation contract",
        },
        "repair_receipt": {
            "available": bool(repair_receipt),
            "eligible": receipt_eligible,
            "why": receipt_why,
        },
        "repair_history_chain": {
            "available": bool(latest_history),
            "eligible": history_eligible,
            "why": history_why,
        },
    }
    ignored_sources = [name for name, status in source_status.items() if status["available"] and not status["eligible"]]

    packet_core = packet.get("continuation_core", {})
    receipt_operator = (repair_receipt or {}).get("operator_evidence", {})
    packet_current_step = packet_core.get("current_step_id", "") or (packet.get("repair_policy") or {}).get("next_step_id", "")
    receipt_current_step = ""
    if receipt_eligible:
        receipt_current_step = receipt_operator.get("next_step_id", "") or (repair_receipt or {}).get("next_step_id", "")
    history_current_step = ""
    if history_eligible:
        history_current_step = latest_history.get("next_step_id", "") or latest_history.get("active_step_id", "")
    current_step_trace = trace_entry(
        surface="current_step_id",
        chosen_source=(
            "repair_packet"
            if packet_current_step
            else "repair_receipt"
            if receipt_current_step
            else "repair_history_chain"
            if history_current_step
            else "UNRESOLVED"
        ),
        chosen_value=packet_current_step or receipt_current_step or history_current_step,
        candidates=[
            {"source": "repair_packet", "value": packet_current_step, "eligible": True},
            {"source": "repair_receipt", "value": receipt_current_step, "eligible": receipt_eligible},
            {"source": "repair_history_chain", "value": history_current_step, "eligible": history_eligible},
        ],
        resolution_rule="repair_packet current step wins; repair_receipt and repair_history_chain only fill the gap when the packet does not name a current step",
        why=(
            "the repair packet already names the active continuation step"
            if packet_current_step
            else "the repair receipt refines the latest continuation step because the packet does not name one"
            if receipt_current_step
            else "the latest repair history entry is the only remaining step clue"
            if history_current_step
            else "no source could name the active continuation step"
        ),
    )

    packet_required_inputs = list(packet_core.get("next_step_required_inputs", [])) or list(packet.get("missing_inputs", []))
    receipt_required_inputs = list((repair_receipt or {}).get("next_step_required_inputs", [])) if receipt_eligible else []
    required_inputs_trace = trace_entry(
        surface="next_step_required_inputs",
        chosen_source="repair_packet" if packet_required_inputs else "repair_receipt" if receipt_required_inputs else "UNRESOLVED",
        chosen_value=packet_required_inputs or receipt_required_inputs,
        candidates=[
            {"source": "repair_packet", "value": packet_required_inputs, "eligible": True},
            {"source": "repair_receipt", "value": receipt_required_inputs, "eligible": receipt_eligible},
        ],
        resolution_rule="repair_packet required inputs win; repair_receipt can only fill them when the packet leaves them empty",
        why=(
            "the repair packet already names the required inputs for the active continuation step"
            if packet_required_inputs
            else "the repair receipt supplies the latest required inputs because the packet leaves them empty"
            if receipt_required_inputs
            else "no source could name the required continuation inputs"
        ),
    )

    packet_missing_inputs = list(packet_core.get("missing_inputs", [])) or list(packet.get("missing_inputs", []))
    missing_inputs_trace = trace_entry(
        surface="missing_inputs",
        chosen_source="repair_packet",
        chosen_value=packet_missing_inputs,
        candidates=[
            {"source": "repair_packet", "value": packet_missing_inputs, "eligible": True},
        ],
        resolution_rule="repair_packet missing inputs anchor continuation readiness because state and receipt do not carry a stronger missing-input contract",
        why="the repair packet remains the authoritative source for current missing continuation inputs",
    )

    packet_focus = packet_core.get("operator_focus", "")
    receipt_focus = ""
    if receipt_eligible and current_step_trace["chosen_value"] and current_step_trace["chosen_value"] == receipt_current_step:
        receipt_focus = receipt_operator.get("operator_focus", "")
    history_focus = ""
    if history_eligible and current_step_trace["chosen_value"] and current_step_trace["chosen_value"] == history_current_step:
        history_focus = latest_history.get("operator_focus", "")
    operator_focus_trace = trace_entry(
        surface="operator_focus",
        chosen_source="repair_receipt" if receipt_focus else "repair_packet" if packet_focus else "repair_history_chain" if history_focus else "UNRESOLVED",
        chosen_value=receipt_focus or packet_focus or history_focus,
        candidates=[
            {"source": "repair_packet", "value": packet_focus, "eligible": True},
            {"source": "repair_receipt", "value": receipt_focus, "eligible": receipt_eligible and bool(receipt_focus)},
            {"source": "repair_history_chain", "value": history_focus, "eligible": history_eligible and bool(history_focus)},
        ],
        resolution_rule="repair_receipt can refine operator focus for the same contour and step; otherwise the packet focus remains authoritative",
        why=(
            "the repair receipt carries fresher step-local operator focus for the same continuation step"
            if receipt_focus
            else "the repair packet focus remains authoritative because no fresher matching receipt focus is available"
            if packet_focus
            else "the latest repair history entry is the only remaining operator-focus clue"
            if history_focus
            else "no source could name the operator focus"
        ),
    )

    state_next_safe_step = state.get("next_safe_step", "")
    packet_next_safe_step = packet_core.get("next_safe_step", "") or packet.get("next_safe_step", "")
    next_safe_step_trace = trace_entry(
        surface="next_safe_step",
        chosen_source="state_file" if state_next_safe_step else "repair_packet" if packet_next_safe_step else "UNRESOLVED",
        chosen_value=state_next_safe_step or packet_next_safe_step,
        candidates=[
            {"source": "state_file", "value": state_next_safe_step, "eligible": True},
            {"source": "repair_packet", "value": packet_next_safe_step, "eligible": True},
        ],
        resolution_rule="state_file next safe step wins because state anchors the current run truth; the packet mirrors it only when they still agree",
        why=(
            "the state file already names the current next safe step"
            if state_next_safe_step
            else "the repair packet supplies the next safe step because the state file leaves it empty"
            if packet_next_safe_step
            else "no source could name the next safe step"
        ),
    )

    packet_resumability_status = packet_core.get("resumability_status", "") or (packet.get("resumability") or {}).get("status", "")
    receipt_resumability_status = (repair_receipt or {}).get("resumability", {}).get("status", "") if receipt_eligible else ""
    resumability_trace = trace_entry(
        surface="resumability_status",
        chosen_source="repair_packet" if packet_resumability_status else "repair_receipt" if receipt_resumability_status else "UNRESOLVED",
        chosen_value=packet_resumability_status or receipt_resumability_status,
        candidates=[
            {"source": "repair_packet", "value": packet_resumability_status, "eligible": True},
            {"source": "repair_receipt", "value": receipt_resumability_status, "eligible": receipt_eligible and bool(receipt_resumability_status)},
        ],
        resolution_rule="repair_packet resumability wins because it is the stricter continuation contract; repair_receipt can only fill a missing packet value",
        why=(
            "the repair packet already names resumability for the active contour"
            if packet_resumability_status
            else "the repair receipt supplies resumability because the packet leaves it empty"
            if receipt_resumability_status
            else "no source could name resumability"
        ),
    )

    packet_family = packet_core.get("resumability_family", "") or (packet.get("resumability") or {}).get("family", "")
    receipt_family = (repair_receipt or {}).get("resumability", {}).get("family", "") if receipt_eligible else ""
    family_trace = trace_entry(
        surface="resumability_family",
        chosen_source="repair_packet" if packet_family else "repair_receipt" if receipt_family else "UNRESOLVED",
        chosen_value=packet_family or receipt_family,
        candidates=[
            {"source": "repair_packet", "value": packet_family, "eligible": True},
            {"source": "repair_receipt", "value": receipt_family, "eligible": receipt_eligible and bool(receipt_family)},
        ],
        resolution_rule="repair_packet resumability family wins; repair_receipt can only fill a missing family label",
        why=(
            "the repair packet already names the resumability family"
            if packet_family
            else "the repair receipt supplies the resumability family because the packet leaves it empty"
            if receipt_family
            else "no source could name the resumability family"
        ),
    )

    packet_termination = packet.get("repair_termination", {})
    receipt_result = (repair_receipt or {}).get("result", "") if receipt_eligible else ""
    latest_step_result = receipt_result or latest_history.get("result", "") if history_eligible else receipt_result
    termination_status = packet_termination.get("status", "")
    termination_reason = packet_termination.get("reason", "")
    if not termination_status and receipt_result == "NON_RESUMABLE_BOUNDARY_REACHED":
        termination_status = "TERMINATE"
        termination_reason = "NON_RESUMABLE"
    termination_trace = trace_entry(
        surface="repair_termination",
        chosen_source="repair_packet" if packet_termination else "repair_receipt" if receipt_result == "NON_RESUMABLE_BOUNDARY_REACHED" else "UNRESOLVED",
        chosen_value={"status": termination_status, "reason": termination_reason},
        candidates=[
            {"source": "repair_packet", "value": {"status": packet_termination.get("status", ""), "reason": packet_termination.get("reason", "")}, "eligible": True},
            {"source": "repair_receipt", "value": {"status": "TERMINATE", "reason": "NON_RESUMABLE"} if receipt_result == "NON_RESUMABLE_BOUNDARY_REACHED" else {}, "eligible": receipt_eligible and receipt_result == "NON_RESUMABLE_BOUNDARY_REACHED"},
        ],
        resolution_rule="repair_packet termination wins; repair_receipt can only surface a missing non-resumable boundary signal",
        why=(
            "the repair packet already carries the current termination truth"
            if packet_termination
            else "the repair receipt supplies a non-resumable boundary signal because the packet leaves termination empty"
            if receipt_result == "NON_RESUMABLE_BOUNDARY_REACHED"
            else "no source names a termination boundary"
        ),
    )

    resolved_required_inputs = list(required_inputs_trace["chosen_value"] or [])
    resolved_missing_inputs = list(missing_inputs_trace["chosen_value"] or [])
    resolved_resumability = resumability_trace["chosen_value"]
    terminal_boundary = termination_status == "TERMINATE" and termination_reason == "NON_RESUMABLE"
    if terminal_boundary:
        continuation_status = "TERMINATED"
        ready_for_resume = False
    elif resolved_resumability == "NOT_RESUMABLE":
        continuation_status = "NON_RESUMABLE"
        ready_for_resume = False
    elif packet_core.get("ready_for_resume", False) and not resolved_missing_inputs:
        continuation_status = "READY_TO_RESUME"
        ready_for_resume = True
    else:
        continuation_status = "AWAITING_INPUTS"
        ready_for_resume = False

    essential_unresolved: list[str] = []
    if not resolved_resumability:
        essential_unresolved.append("resumability_status")
    if not next_safe_step_trace["chosen_value"]:
        essential_unresolved.append("next_safe_step")
    if continuation_status in {"READY_TO_RESUME", "AWAITING_INPUTS"} and not current_step_trace["chosen_value"]:
        essential_unresolved.append("current_step_id")
    if continuation_status == "AWAITING_INPUTS" and not resolved_required_inputs and resolved_missing_inputs:
        essential_unresolved.append("next_step_required_inputs")

    resolution_status = "RESOLVED" if not essential_unresolved else "CONFLICT_UNRESOLVED"
    decision_trace = [
        resumability_trace,
        family_trace,
        termination_trace,
        current_step_trace,
        required_inputs_trace,
        missing_inputs_trace,
        operator_focus_trace,
        next_safe_step_trace,
    ]
    conflict_count = sum(1 for entry in decision_trace if entry.get("conflict", False))
    return {
        "schema_version": "continuation_arbiter_record_v0",
        "run_id": state["run_id"],
        "task_class": state["task_class"],
        "entrypoint": "resume",
        "precedence_order": precedence_order,
        "source_status": source_status,
        "ignored_sources": ignored_sources,
        "conflict_count": conflict_count,
        "resolution_status": resolution_status,
        "unresolved_surfaces": essential_unresolved,
        "decision_trace": decision_trace,
        "resolved_decision": {
            "continuation_status": continuation_status,
            "ready_for_resume": ready_for_resume,
            "resumability_status": resolved_resumability,
            "resumability_family": family_trace["chosen_value"],
            "current_step_id": current_step_trace["chosen_value"],
            "current_step_source": current_step_trace["chosen_source"],
            "next_step_required_inputs": resolved_required_inputs,
            "missing_inputs": resolved_missing_inputs,
            "operator_focus": operator_focus_trace["chosen_value"],
            "operator_focus_source": operator_focus_trace["chosen_source"],
            "next_safe_step": next_safe_step_trace["chosen_value"],
            "next_safe_step_source": next_safe_step_trace["chosen_source"],
            "termination_status": termination_status,
            "termination_reason": termination_reason,
            "latest_step_result": latest_step_result,
            "packet_replay_ready": bool((packet.get("source_of_truth") or {}).get("packet_replay_ready", False)),
        },
        "why": (
            "the continuation conflict set resolves cleanly under explicit precedence"
            if resolution_status == "RESOLVED"
            else "the continuation conflict set still leaves required surfaces unresolved after explicit precedence"
        ),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-continuation-arbiter-v0")
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--repair-packet-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--repair-receipt-file")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        artifact_root = Path(args.state_file).expanduser().resolve().parent
        project_root = current_project_root()
        validate_root_within_project(
            "state_file",
            args.state_file,
            root=artifact_root,
            project_root=project_root,
            artifact_root=artifact_root,
        )
        artifact_root.mkdir(parents=True, exist_ok=True)
        validate_continuation_arbiter_paths(args, artifact_root=artifact_root, project_root=project_root)
        record = build_record(
            state=load_json(Path(args.state_file)),
            packet=load_json(Path(args.repair_packet_file)),
            repair_receipt=load_json(Path(args.repair_receipt_file)) if args.repair_receipt_file else None,
        )
    except PathScopeValidationError as exc:
        print(json.dumps(exc.as_payload(), ensure_ascii=True))
        return 2
    save_json(Path(args.output), record)
    print(
        json.dumps(
            {
                "result": "OK",
                "resolution_status": record["resolution_status"],
                "conflict_count": record["conflict_count"],
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
