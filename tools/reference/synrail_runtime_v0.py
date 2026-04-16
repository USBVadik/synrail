#!/usr/bin/env python3
"""Compatibility wrapper for the bounded Synrail runtime contour."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPINE = HERE / "synrail_spine_v0.py"


def main() -> int:
    args = [sys.executable, str(SPINE), "orchestrate", *sys.argv[1:]]
    return subprocess.run(args, check=False).returncode


if __name__ == "__main__":
    sys.exit(main())
