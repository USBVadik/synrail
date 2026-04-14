#!/usr/bin/env python3
"""Opt-in alpha telemetry and session replay helpers for the Synrail alpha lane."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import platform
import sys
import uuid
from importlib import metadata as importlib_metadata
from pathlib import Path

CONFIG_BASENAME = "config.json"
COMMAND_SEQUENCE_BASENAME = "command_sequence.jsonl"
DEFAULT_SESSION_REPLAY_BASENAME = "session_replay.json"
DEFAULT_ISSUE_BODY_BASENAME = "github_issue.md"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def save_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def telemetry_dir(root: Path) -> Path:
    return root / "telemetry"


def config_file(root: Path) -> Path:
    return telemetry_dir(root) / CONFIG_BASENAME


def command_log_file(root: Path) -> Path:
    return telemetry_dir(root) / COMMAND_SEQUENCE_BASENAME


def default_session_replay_file(root: Path) -> Path:
    return telemetry_dir(root) / DEFAULT_SESSION_REPLAY_BASENAME


def default_issue_body_file(root: Path) -> Path:
    return telemetry_dir(root) / DEFAULT_ISSUE_BODY_BASENAME


def synrail_version() -> str:
    try:
        return importlib_metadata.version("synrail")
    except importlib_metadata.PackageNotFoundError:
        return "0.1.0"


def platform_record() -> dict:
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "synrail_version": synrail_version(),
    }


def load_json_if_exists(path: Path) -> dict | None:
    if not path.exists():
        return None
    return load_json(path)


def load_config(root: Path) -> dict | None:
    return load_json_if_exists(config_file(root))


def telemetry_enabled(root: Path) -> bool:
    config = load_config(root)
    return bool(config and config.get("enabled", False))


def enable_telemetry(root: Path, tester_id: str) -> dict:
    config = {
        "schema_version": "alpha_telemetry_config_v0",
        "enabled": True,
        "telemetry_session_id": f"TELEMETRY_{uuid.uuid4().hex[:12].upper()}",
        "tester_id": tester_id,
        "enabled_at": now_iso(),
        "platform": platform_record(),
    }
    save_json(config_file(root), config)
    return config


def load_command_events(root: Path) -> list[dict]:
    path = command_log_file(root)
    if not path.exists():
        return []
    events: list[dict] = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        events.append(json.loads(line))
    return events


def append_command_event(root: Path, event: dict) -> None:
    path = command_log_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=True) + "\n")


def repair_attempt_count(repair_packet: dict | None) -> int:
    if not repair_packet:
        return 0
    termination = repair_packet.get("repair_termination", {})
    if isinstance(termination.get("attempt_count"), int):
        return termination["attempt_count"]
    return int(repair_packet.get("repair_history", {}).get("history_chain_length", 0))


def visible_result(report: dict | None, thin_output: dict | None) -> str:
    thin_outcome = (thin_output or {}).get("outcome_class", "")
    report_result = (report or {}).get("result", "")
    report_reason = (report or {}).get("reason", "")
    if thin_outcome and (report_result in {"", "OK"} or report_reason):
        return thin_outcome
    return report_result


def component_error_class(
    *,
    report: dict | None,
    doctor: dict | None,
    thin_output: dict | None,
    explicit_error_class: str = "",
    exit_code: int = 0,
) -> str:
    for candidate in [
        explicit_error_class,
        (report or {}).get("reason", ""),
        (report or {}).get("dominant_blocker", ""),
        (doctor or {}).get("final_verdict", ""),
        (thin_output or {}).get("outcome_class", ""),
    ]:
        if candidate:
            return candidate
    if exit_code != 0:
        return "COMMAND_EXIT_NONZERO"
    return ""


def artifact_snapshot(root: Path) -> dict:
    files = {
        "state": load_json_if_exists(root / "state.json"),
        "report": load_json_if_exists(root / "report.json"),
        "doctor": load_json_if_exists(root / "doctor.json"),
        "repair_packet": load_json_if_exists(root / "repair_packet.json"),
        "observability": load_json_if_exists(root / "observability.json"),
        "thin_output": load_json_if_exists(root / "thin_output.json"),
    }
    return files


def build_command_event(
    root: Path,
    *,
    command_path: list[str],
    flag_names: list[str],
    exit_code: int,
    explicit_error_class: str = "",
) -> dict:
    snapshot = artifact_snapshot(root)
    repair_packet = snapshot["repair_packet"]
    state = snapshot["state"] or {}
    report = snapshot["report"] or {}
    doctor = snapshot["doctor"] or {}
    thin_output = snapshot["thin_output"] or {}
    prior = load_command_events(root)
    return {
        "event_id": len(prior) + 1,
        "timestamp": now_iso(),
        "command_path": command_path,
        "flag_names": sorted(set(flag_names)),
        "exit_code": exit_code,
        "state": state.get("state", ""),
        "result": visible_result(report, thin_output),
        "reason": report.get("reason") or thin_output.get("diagnosis", ""),
        "component_error_class": component_error_class(
            report=report,
            doctor=doctor,
            thin_output=thin_output,
            explicit_error_class=explicit_error_class,
            exit_code=exit_code,
        ),
        "repair_attempt_count": repair_attempt_count(repair_packet),
    }


def pick_error_snapshot(events: list[dict], root: Path) -> dict:
    for event in reversed(events):
        if event.get("exit_code", 0) != 0 or event.get("component_error_class", "") or event.get("result", "") not in {"", "OK", "PASSED", "ACCEPTED"}:
            return {
                "state": event.get("state", ""),
                "result": event.get("result", ""),
                "reason": event.get("reason", ""),
                "component_error_class": event.get("component_error_class", ""),
                "repair_attempt_count": event.get("repair_attempt_count", 0),
                "next_safe_step": (artifact_snapshot(root).get("report") or {}).get("next_safe_step", ""),
            }
    snapshot = artifact_snapshot(root)
    state = snapshot.get("state") or {}
    report = snapshot.get("report") or {}
    return {
        "state": state.get("state", ""),
        "result": report.get("result", ""),
        "reason": report.get("reason", ""),
        "component_error_class": component_error_class(
            report=report,
            doctor=snapshot.get("doctor") or {},
            thin_output=snapshot.get("thin_output") or {},
            exit_code=0,
        ),
        "repair_attempt_count": repair_attempt_count(snapshot.get("repair_packet")),
        "next_safe_step": report.get("next_safe_step", state.get("next_safe_step", "")),
    }


def build_issue_title(record: dict) -> str:
    run_id = record.get("run_id", "UNKNOWN_RUN")
    error_class = record.get("component_error_class", "ALPHA_SIGNAL") or "ALPHA_SIGNAL"
    return f"[synrail alpha] {error_class} on {run_id}"


def build_issue_body(record: dict) -> str:
    lines = [
        "# Synrail Alpha Telemetry",
        "",
        "## Summary",
        f"- telemetry session: `{record['telemetry_session_id']}`",
        f"- tester id: `{record['tester_id']}`",
        f"- synrail version: `{record['platform']['synrail_version']}`",
        f"- os: `{record['platform']['os']} {record['platform']['os_release']}`",
        f"- python: `{record['platform']['python_version']}`",
        f"- run id: `{record['run_id']}`",
        f"- task class: `{record['task_class']}`",
        f"- latest state: `{record['latest_state']}`",
        f"- latest result: `{record['latest_result']}`",
        f"- latest reason: `{record['latest_reason']}`",
        f"- component error class: `{record['component_error_class']}`",
        f"- repair attempt count: `{record['repair_attempt_count']}`",
        f"- next safe step: `{record['next_safe_step']}`",
        "",
        "## Command Sequence",
    ]
    for event in record.get("command_sequence", []):
        command_path = " ".join(event.get("command_path", []))
        flags = " ".join(event.get("flag_names", []))
        lines.append(
            f"- `{command_path}` | exit=`{event.get('exit_code', 0)}` | state=`{event.get('state', '')}` | result=`{event.get('result', '')}` | error=`{event.get('component_error_class', '')}` | flags=`{flags}`"
        )
    lines.extend(
        [
            "",
            "## Questions",
            "- What did Synrail decide correctly?",
            "- Where was the next step unclear?",
            "- What felt like ceremony instead of help?",
        ]
    )
    return "\n".join(lines) + "\n"


def export_session_replay(root: Path, output: Path, issue_output: Path | None = None) -> dict:
    config = load_config(root)
    if not config or not config.get("enabled", False):
        raise ValueError("alpha telemetry is not enabled for this artifact root")
    snapshot = artifact_snapshot(root)
    state = snapshot["state"] or {}
    report = snapshot["report"] or {}
    repair_packet = snapshot["repair_packet"] or {}
    observability = snapshot["observability"] or {}
    events = load_command_events(root)
    record = {
        "schema_version": "alpha_session_replay_record_v0",
        "telemetry_session_id": config["telemetry_session_id"],
        "tester_id": config.get("tester_id", ""),
        "created_at": now_iso(),
        "telemetry_enabled": True,
        "platform": config.get("platform", platform_record()),
        "run_id": state.get("run_id", ""),
        "task_class": state.get("task_class", ""),
        "latest_state": state.get("state", ""),
        "latest_result": visible_result(report, snapshot.get("thin_output") or {}),
        "latest_reason": report.get("reason", ""),
        "next_safe_step": report.get("next_safe_step", state.get("next_safe_step", "")),
        "component_error_class": component_error_class(
            report=report,
            doctor=snapshot.get("doctor") or {},
            thin_output=snapshot.get("thin_output") or {},
        ),
        "repair_attempt_count": repair_attempt_count(repair_packet),
        "command_count": len(events),
        "command_sequence": events,
        "state_at_error": pick_error_snapshot(events, root),
        "observability_summary": {
            "transition_count": (observability.get("event_counts") or {}).get("transition_count", 0),
            "repair_attempt_count": (observability.get("event_counts") or {}).get("repair_attempt_count", 0),
            "rejection_count": (observability.get("event_counts") or {}).get("rejection_count", 0),
        },
    }
    record["issue_title"] = build_issue_title(record)
    record["issue_body"] = build_issue_body(record)
    save_json(output, record)
    if issue_output:
        save_text(issue_output, record["issue_body"])
    return record


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-alpha-telemetry-v0")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_enable = sub.add_parser("enable")
    p_enable.add_argument("--artifact-root", required=True)
    p_enable.add_argument("--tester-id", required=True)

    p_export = sub.add_parser("export")
    p_export.add_argument("--artifact-root", required=True)
    p_export.add_argument("--output", required=True)
    p_export.add_argument("--issue-output")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root = Path(args.artifact_root).expanduser().resolve()
    if args.cmd == "enable":
        config = enable_telemetry(root, args.tester_id)
        print(json.dumps({"result": "OK", "telemetry_session_id": config["telemetry_session_id"]}, ensure_ascii=True))
        return 0
    issue_output = Path(args.issue_output).expanduser().resolve() if args.issue_output else None
    record = export_session_replay(root, Path(args.output).expanduser().resolve(), issue_output)
    print(json.dumps({"result": "OK", "command_count": record["command_count"], "issue_title": record["issue_title"]}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
