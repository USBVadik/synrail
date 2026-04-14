"""Package-safe runner for reference helper modules."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m synrail.reference_runner <helper_module> [args...]", file=sys.stderr)
        return 2
    helper_module = sys.argv[1]
    helpers_dir = Path(__file__).resolve().parent / "tools" / "reference"
    if str(helpers_dir) not in sys.path:
        sys.path.insert(0, str(helpers_dir))
    module = importlib.import_module(f"synrail.tools.reference.{helper_module}")
    argv = [helper_module, *sys.argv[2:]]
    previous = sys.argv
    try:
        sys.argv = argv
        return int(module.main())
    finally:
        sys.argv = previous


if __name__ == "__main__":
    raise SystemExit(main())
