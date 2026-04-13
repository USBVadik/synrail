#!/usr/bin/env python3
"""Inspect one continuation fixture and emit a compact adoption-friction record."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

CONTINUATION_SIDE_FILES = [
    'repair_handoff.json',
    'repair_receipt.json',
    'resume_inputs.json',
    'prompt_identity.txt',
    'task_identity.txt',
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + '\n')


def build_record(*, fixture_root: Path, run_file: Path, label: str) -> dict:
    run = load_json(run_file)
    report = dict(run.get('report', {}))
    repair_packet = dict(run.get('repair_packet', {}))
    repair_history = dict(run.get('repair_history', {}))
    stage_runs = sorted(fixture_root.glob('stage*_run.json'))

    repeated_doctor_blocks = 0
    for path in stage_runs:
        stage_run = load_json(path)
        stage_report = dict(stage_run.get('report', {}))
        if stage_report.get('reason') == 'DOCTOR_NOT_GREEN':
            repeated_doctor_blocks += 1

    present_side_files = [name for name in CONTINUATION_SIDE_FILES if (fixture_root / name).exists()]
    packet = load_json(fixture_root / 'repair_packet.json') if (fixture_root / 'repair_packet.json').exists() else {}
    continuation_core = dict(packet.get('continuation_core', {}))

    return {
        'schema_version': 'continuation_adoption_record_v0',
        'run_id': run.get('run_id', ''),
        'label': label,
        'fixture_root': str(fixture_root),
        'final_result': report.get('result', ''),
        'final_state': report.get('resulting_state', ''),
        'final_closure_status': report.get('closure_status', ''),
        'packet_only_root_entry': bool((fixture_root / 'repair_packet.json').exists() and not present_side_files),
        'root_continuation_side_files': present_side_files,
        'root_continuation_side_files_count': len(present_side_files),
        'stage_run_count': len(stage_runs),
        'repeated_doctor_block_events': repeated_doctor_blocks,
        'repair_history_available': repair_history.get('available', False),
        'repair_history_chain_length': repair_history.get('chain_length', 0),
        'packet_continuation_core_present': bool(continuation_core),
        'packet_core_requires_sibling_discovery': continuation_core.get('requires_sibling_discovery', True),
        'packet_core_selected_with_preparation': continuation_core.get('selected_with_preparation', False),
        'packet_core_operator_focus': continuation_core.get('operator_focus', ''),
        'packet_core_next_step_required_inputs': list(continuation_core.get('next_step_required_inputs', [])),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='synrail-continuation-adoption-v0')
    parser.add_argument('--fixture-root', required=True)
    parser.add_argument('--run-file', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--output', required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    record = build_record(
        fixture_root=Path(args.fixture_root),
        run_file=Path(args.run_file),
        label=args.label,
    )
    save_json(Path(args.output), record)
    print(json.dumps({'result': 'OK', 'run_id': record['run_id'], 'packet_only_root_entry': record['packet_only_root_entry']}, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
