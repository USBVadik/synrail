#!/usr/bin/env python3
"""Render operator briefs and chains into small human-readable markdown."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_text(path: Path, content: str) -> None:
    path.write_text(content.rstrip() + "\n")


def render_list(values: list[str]) -> str:
    if not values:
        return "- none"
    return "\n".join(f"- `{value}`" for value in values)


def render_suggested_cli(suggested: dict) -> str:
    command = suggested.get("command", "NONE")
    args = suggested.get("args", [])
    if command == "NONE":
        return "`NONE`"
    return "`" + " ".join([command, *args]) + "`"


def render_optional(value: str) -> str:
    return f"`{value}`" if value else "none"


def render_brief(payload: dict) -> str:
    return f"""# Operator Render

## Summary

- run: `{payload["run_id"]}`
- task class: `{payload["task_class"]}`
- entry state: `{payload["entry_state"]}`
- resulting state: `{payload["resulting_state"]}`
- result: `{payload["result"]}`
- stopping stage: `{payload["stopping_stage"]}`
- reason: `{payload["reason"]}`
- primary action: `{payload["primary_action"]}`

## Why

{payload["why_action"]}

## Current step

- current step: `{payload["current_step_id"]}`
- current subsurface: {render_optional(payload.get("current_step_subsurface_id", ""))}
- edit target: {render_optional(payload.get("current_step_target_path", ""))}
- next safe step: `{payload["next_safe_step"]}`
- operator focus: {payload["operator_focus"] or "none"}

## Inputs

{render_list(list(payload.get("next_step_required_inputs", [])))}

## Stale sub-surfaces

{render_list(list(payload.get("next_step_subsurface_ids", [])))}

## Termination

- status: `{payload["termination_status"]}`
- reason: `{payload["termination_reason"] or "NONE"}`
- attempts: `{payload["attempt_count"]}`

## Suggested CLI

{render_suggested_cli(payload.get("suggested_cli", {}))}
"""


def render_chain(payload: dict) -> str:
    stage_lines: list[str] = []
    for stage in payload.get("stage_summaries", []):
        stage_lines.append(
            "\n".join(
                [
                    f"### {stage['stage_id']}",
                    "",
                    f"- resulting state: `{stage['resulting_state']}`",
                    f"- result: `{stage['result']}`",
                    f"- stopping stage: `{stage['stopping_stage']}`",
                    f"- reason: `{stage['reason']}`",
                    f"- primary action: `{stage['primary_action']}`",
                    f"- current step: `{stage['current_step_id']}`",
                    f"- current subsurface: {render_optional(stage.get('current_step_subsurface_id', ''))}",
                    f"- edit target: {render_optional(stage.get('current_step_target_path', ''))}",
                    f"- next safe step: `{stage['next_safe_step']}`",
                    "- required inputs:",
                    render_list(list(stage.get("next_step_required_inputs", []))),
                    f"- termination reason: `{stage['termination_reason'] or 'NONE'}`",
                ]
            )
        )
    action_counts = payload.get("action_counts", {})
    action_lines = "\n".join(f"- `{key}`: `{value}`" for key, value in action_counts.items()) or "- none"
    stage_block = "\n\n".join(stage_lines)
    return f"""# Operator Render

## Summary

- run: `{payload["run_id"]}`
- task class: `{payload["task_class"]}`
- stage count: `{payload["stage_count"]}`
- final action: `{payload["final_action"]}`
- final next safe step: `{payload["final_next_safe_step"]}`
- final resumability family: `{payload["final_resumability_family"]}`

## Action counts

{action_lines}

## Stage sequence

{stage_block}

## Why

{payload["why"]}
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="synrail-operator-render-v0")
    parser.add_argument("--brief-file")
    parser.add_argument("--chain-file")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if bool(args.brief_file) == bool(args.chain_file):
        print(json.dumps({"result": "ERROR", "reason": "provide exactly one of --brief-file or --chain-file"}, ensure_ascii=True))
        return 2
    if args.brief_file:
        payload = load_json(Path(args.brief_file))
        if payload.get("schema_version") != "operator_brief_record_v0":
            print(json.dumps({"result": "ERROR", "reason": "brief file must use operator_brief_record_v0"}, ensure_ascii=True))
            return 2
        content = render_brief(payload)
    else:
        payload = load_json(Path(args.chain_file))
        if payload.get("schema_version") != "operator_brief_chain_record_v0":
            print(json.dumps({"result": "ERROR", "reason": "chain file must use operator_brief_chain_record_v0"}, ensure_ascii=True))
            return 2
        content = render_chain(payload)
    save_text(Path(args.output), content)
    print(json.dumps({"result": "OK", "output": args.output}, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
