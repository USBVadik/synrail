#!/usr/bin/env python3
"""Compare two continuation adoption records and emit a compact delta."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + '\n')


def build_delta(*, before: dict, after: dict) -> dict:
    side_files_reduced = before.get('root_continuation_side_files_count', 0) - after.get('root_continuation_side_files_count', 0)
    packet_only_entry_gained = (not before.get('packet_only_root_entry', False)) and after.get('packet_only_root_entry', False)
    doctor_pressure_preserved = after.get('repeated_doctor_block_events', 0) >= 1 and before.get('repeated_doctor_block_events', 0) >= 1
    accepted_preserved = before.get('final_closure_status', '') == 'ACCEPTED' and after.get('final_closure_status', '') == 'ACCEPTED'
    verdict = 'FRICTION_REDUCED_WITHOUT_TRUTH_LOSS' if side_files_reduced > 0 and packet_only_entry_gained and doctor_pressure_preserved and accepted_preserved else 'MIXED'
    return {
        'schema_version': 'continuation_adoption_delta_v0',
        'before_run_id': before.get('run_id', ''),
        'after_run_id': after.get('run_id', ''),
        'before_label': before.get('label', ''),
        'after_label': after.get('label', ''),
        'side_files_reduced': side_files_reduced,
        'packet_only_entry_gained': packet_only_entry_gained,
        'doctor_pressure_preserved': doctor_pressure_preserved,
        'accepted_terminal_truth_preserved': accepted_preserved,
        'before_repair_history_chain_length': before.get('repair_history_chain_length', 0),
        'after_repair_history_chain_length': after.get('repair_history_chain_length', 0),
        'before_root_side_files': list(before.get('root_continuation_side_files', [])),
        'after_root_side_files': list(after.get('root_continuation_side_files', [])),
        'verdict': verdict,
        'why': 'minimal continuation entry now reduces visible continuation side-file tax while still preserving repeated doctor pressure and accepted closure on the ugly contour' if verdict == 'FRICTION_REDUCED_WITHOUT_TRUTH_LOSS' else 'friction moved, but the current records do not yet prove a clean reduction without losing contour truth',
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='synrail-continuation-adoption-delta-v0')
    parser.add_argument('--before-file', required=True)
    parser.add_argument('--after-file', required=True)
    parser.add_argument('--output', required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    delta = build_delta(before=load_json(Path(args.before_file)), after=load_json(Path(args.after_file)))
    save_json(Path(args.output), delta)
    print(json.dumps({'result': 'OK', 'verdict': delta['verdict'], 'side_files_reduced': delta['side_files_reduced']}, ensure_ascii=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
