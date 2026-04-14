"""Package-safe runner for reference helper modules."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python -m reference_runner <helper_module> [args...]", file=sys.stderr)
        return 2
    helper_module = sys.argv[1]
    module_dir = Path(__file__).resolve().parent
    helper_candidates = [
        module_dir / "tools" / "reference",
        module_dir / "synrail" / "tools" / "reference",
    ]
    for helpers_dir in helper_candidates:
        if helpers_dir.exists() and str(helpers_dir) not in sys.path:
            sys.path.insert(0, str(helpers_dir))
    try:
        module = importlib.import_module(f"synrail.tools.reference.{helper_module}")
    except ModuleNotFoundError:
        module = importlib.import_module(f"tools.reference.{helper_module}")
    argv = [helper_module, *sys.argv[2:]]
    previous = sys.argv
    try:
        sys.argv = argv
        return int(module.main())
    finally:
        sys.argv = previous


if __name__ == "__main__":
    raise SystemExit(main())
