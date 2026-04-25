#!/usr/bin/env python3
"""Shared JSON IO helpers for Synrail reference tools."""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def save_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n")


def load_json_if_valid(path: Path | None) -> tuple[bool, dict]:
    if path is None:
        return False, {}
    try:
        return True, load_json(path)
    except json.JSONDecodeError:
        return False, {}


def save_json_safe(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    save_json(path, payload)
